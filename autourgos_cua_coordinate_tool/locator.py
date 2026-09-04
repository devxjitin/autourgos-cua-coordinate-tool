"""
locator.py — CoordinateFinder: LLM-grounded UI coordinate lookup.

Reference: Gemini's computer-use API (https://ai.google.dev/gemini-api/docs/computer-use)
predicts UI element positions as coordinates normalized to a fixed 0-1000
range regardless of actual screen resolution, and callers denormalize with
``actual_x = int(x / 1000 * screen_width)``. CoordinateFinder adopts the same
0-1000 convention so its output is compatible with that ecosystem, but it is
provider-agnostic: it drives a caller-supplied LLM object shaped like
autourgos-openaichat/autourgos-responses' BaseLLM (an ``invoke(prompt, files=,
**overrides)`` / ``ainvoke(...)`` method returning generated text) rather than
calling any specific vision API itself. This package has no dependency on
either of those packages -- any object exposing that duck-typed shape works.
"""
from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass, replace
from typing import Any, Optional, Tuple

from autourgos_core import extract_text

from .capture import capture_screen, detect_image_size

__all__ = ["Coordinate", "CoordinateFinder", "CoordinateNotFoundError"]

_MIN_COORD = 0
_MAX_COORD = 1000

_PROMPT_TEMPLATE = """You are a UI element locator. You are given a screenshot and a \
description of a UI element. Find it and respond with ONLY a single JSON object, \
no other text, no markdown fences.

If the element is visible, respond with:
{{"found": true, "x": <int 0-1000>, "y": <int 0-1000>}}

x and y are the element's center point, normalized to a 0-1000 scale for both \
axes regardless of the screenshot's actual pixel resolution (0,0 is top-left, \
1000,1000 is bottom-right).

If the element is not visible anywhere in the screenshot, respond with:
{{"found": false}}

Element to find: {description}
"""

_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)
_XY_FALLBACK_RE = re.compile(
    r'"?x"?\s*[:=]\s*(-?\d+(?:\.\d+)?).{0,40}?"?y"?\s*[:=]\s*(-?\d+(?:\.\d+)?)',
    re.DOTALL,
)


class CoordinateNotFoundError(Exception):
    """Raised when the element could not be located (or the response was unparseable)."""


@dataclass(frozen=True)
class Coordinate:
    """A located point, normalized to Gemini's 0-1000 coordinate system."""

    x_norm: float
    y_norm: float
    raw_response: str
    # Best-effort screen dimensions detected at find()/afind() time -- either
    # from an auto-capture, or auto-detected (via Pillow) from a caller-given
    # image. None if neither was available; to_pixels() still accepts an
    # explicit override regardless.
    screen_width: Optional[int] = None
    screen_height: Optional[int] = None

    def to_pixels(
        self,
        screen_width: Optional[int] = None,
        screen_height: Optional[int] = None,
    ) -> Tuple[int, int]:
        """
        Denormalize to actual screen pixels using Gemini's documented formula.

        Pass screen_width/screen_height explicitly to force conversion
        against those dimensions (custom); omit both to use the dimensions
        auto-detected when this Coordinate was found (automatic) -- raises
        ValueError if neither is available.
        """
        width = screen_width if screen_width is not None else self.screen_width
        height = screen_height if screen_height is not None else self.screen_height
        if not width or not height or width <= 0 or height <= 0:
            raise ValueError(
                "No positive screen_width/screen_height available -- pass them "
                "explicitly, or find()/afind() with a source that lets them be "
                "auto-detected (auto-captured screen, or an image Pillow can read)."
            )
        x_px = int(self.x_norm / 1000 * width)
        y_px = int(self.y_norm / 1000 * height)
        return x_px, y_px


def _parse_response(text: str) -> Coordinate:
    text = (text or "").strip()

    data: Optional[dict] = None
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        match = _JSON_OBJECT_RE.search(text)
        if match:
            try:
                data = json.loads(match.group(0))
            except json.JSONDecodeError:
                data = None

    if isinstance(data, dict):
        if data.get("found") is False:
            raise CoordinateNotFoundError(f"Model reported element not found: {text!r}")
        if "x" in data and "y" in data:
            return _validated_coordinate(data["x"], data["y"], text)

    # Fallback: pull the first x/y-looking pair out of prose.
    match = _XY_FALLBACK_RE.search(text)
    if match:
        return _validated_coordinate(match.group(1), match.group(2), text)

    raise CoordinateNotFoundError(f"Could not parse a coordinate from model response: {text!r}")


def _validated_coordinate(raw_x: Any, raw_y: Any, raw_response: str) -> Coordinate:
    try:
        x = float(raw_x)
        y = float(raw_y)
    except (TypeError, ValueError):
        raise CoordinateNotFoundError(f"Non-numeric coordinate in model response: {raw_response!r}")

    if not (_MIN_COORD <= x <= _MAX_COORD) or not (_MIN_COORD <= y <= _MAX_COORD):
        raise CoordinateNotFoundError(
            f"Coordinate out of the 0-{_MAX_COORD} normalized range: x={x}, y={y}"
        )

    return Coordinate(x_norm=x, y_norm=y, raw_response=raw_response)


class CoordinateFinder:
    """
    Locates a described UI element in a screenshot using a caller-supplied,
    vision-capable LLM (any object shaped like autourgos-openaichat's or
    autourgos-responses' BaseLLM: ``invoke(prompt, files=, **overrides)`` /
    ``ainvoke(...)`` returning generated text).
    """

    def __init__(self, llm: Any, *, image_detail: Optional[str] = None) -> None:
        if not hasattr(llm, "invoke") or not hasattr(llm, "ainvoke"):
            raise TypeError(
                "llm must expose invoke()/ainvoke() (e.g. an autourgos-openaichat or "
                "autourgos-responses model instance)."
            )
        self.llm = llm
        self.image_detail = image_detail

    def _build_prompt(self, description: str) -> str:
        return _PROMPT_TEMPLATE.format(description=description)

    def _invoke_kwargs(self, overrides: dict) -> dict:
        kwargs = dict(overrides)
        if self.image_detail is not None:
            kwargs.setdefault("image_detail", self.image_detail)
        return kwargs

    @staticmethod
    def _resolve_image(image: Any) -> Tuple[Any, Optional[int], Optional[int]]:
        """(image_to_send, detected_width, detected_height). image=None auto-
        captures the current screen (dimensions come free from the capture);
        a given image has its dimensions best-effort auto-detected via Pillow."""
        if image is None:
            capture = capture_screen()
            return capture.image_bytes, capture.width, capture.height
        size = detect_image_size(image)
        if size is None:
            return image, None, None
        return image, size[0], size[1]

    def find(
        self,
        description: str,
        image: Any = None,
        *,
        screen_width: Optional[int] = None,
        screen_height: Optional[int] = None,
        **overrides: Any,
    ) -> Coordinate:
        """
        Locate ``description`` on screen. Raises CoordinateNotFoundError if
        the element isn't visible or the response can't be parsed.

        image: file path or bytes for a specific screenshot (custom); omit
            (default) to auto-capture the current screen instead (requires
            the optional `mss` dependency -- the [capture] extra).
        screen_width/screen_height: pass explicitly to fix the dimensions
            used by the returned Coordinate.to_pixels() (custom); omit to
            auto-detect them instead (from the auto-capture itself, or from
            ``image`` via Pillow if installed -- the [images] extra).
        """
        resolved_image, detected_w, detected_h = self._resolve_image(image)
        width = screen_width if screen_width is not None else detected_w
        height = screen_height if screen_height is not None else detected_h

        prompt = self._build_prompt(description)
        response = self.llm.invoke(prompt, files=[resolved_image], **self._invoke_kwargs(overrides))
        coord = _parse_response(extract_text(response))
        return replace(coord, screen_width=width, screen_height=height)

    async def afind(
        self,
        description: str,
        image: Any = None,
        *,
        screen_width: Optional[int] = None,
        screen_height: Optional[int] = None,
        **overrides: Any,
    ) -> Coordinate:
        """Async twin of find()."""
        if image is None:
            capture = await asyncio.to_thread(capture_screen)
            resolved_image, detected_w, detected_h = capture.image_bytes, capture.width, capture.height
        else:
            resolved_image, detected_w, detected_h = self._resolve_image(image)
        width = screen_width if screen_width is not None else detected_w
        height = screen_height if screen_height is not None else detected_h

        prompt = self._build_prompt(description)
        response = await self.llm.ainvoke(prompt, files=[resolved_image], **self._invoke_kwargs(overrides))
        coord = _parse_response(extract_text(response))
        return replace(coord, screen_width=width, screen_height=height)
