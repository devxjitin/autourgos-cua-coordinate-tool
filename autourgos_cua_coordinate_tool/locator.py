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

import json
import re
from dataclasses import dataclass
from typing import Any, Optional, Tuple

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

    def to_pixels(self, screen_width: int, screen_height: int) -> Tuple[int, int]:
        """Denormalize to actual screen pixels using Gemini's documented formula."""
        if screen_width <= 0 or screen_height <= 0:
            raise ValueError("screen_width and screen_height must be positive.")
        x_px = int(self.x_norm / 1000 * screen_width)
        y_px = int(self.y_norm / 1000 * screen_height)
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

    def find(self, image: Any, description: str, **overrides: Any) -> Coordinate:
        """Locate ``description`` in ``image`` (a file path or bytes). Raises
        CoordinateNotFoundError if the element isn't visible or the response
        can't be parsed."""
        prompt = self._build_prompt(description)
        response = self.llm.invoke(prompt, files=[image], **self._invoke_kwargs(overrides))
        return _parse_response(response if isinstance(response, str) else str(response))

    async def afind(self, image: Any, description: str, **overrides: Any) -> Coordinate:
        """Async twin of find()."""
        prompt = self._build_prompt(description)
        response = await self.llm.ainvoke(prompt, files=[image], **self._invoke_kwargs(overrides))
        return _parse_response(response if isinstance(response, str) else str(response))
