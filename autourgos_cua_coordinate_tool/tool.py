"""
tool.py — wraps a CoordinateFinder as an agent-callable Tool.

make_find_coordinates_tool() returns an autourgos_agent.Tool (the standard
{"name", "description", "parameters", "func"} dict shape) ready to pass
straight into ``agent.add_tools(...)``, matching the convention every other
tool-producing package in this workspace (toolbox, preiteration, hcix) follows.
"""
from __future__ import annotations

import os
from typing import Any, Callable, Dict, Optional, Sequence, Union

from autourgos_agent import Tool, tool

from .capture import CaptureError
from .locator import CoordinateFinder, CoordinateNotFoundError

__all__ = ["make_find_coordinates_tool"]

_ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"}


class ImagePathRejectedError(Exception):
    """Raised when an LLM-supplied ``image_path`` fails validation."""


def _validate_image_path(image_path: str, allowed_dirs: Sequence[str]) -> str:
    """Resolve ``image_path`` and confirm it sits inside an allowed directory
    and has an image extension. Raises ImagePathRejectedError otherwise.

    This tool's ``image_path`` argument is LLM-callable -- reachable via
    prompt injection from any content the agent views (e.g. a malicious
    page). Without this check it's an arbitrary local-file-read-and-exfiltrate
    primitive: any path, including outside any screenshots directory, gets
    forwarded straight to the configured vision LLM.
    """
    if not allowed_dirs:
        raise ImagePathRejectedError(
            "image_path was supplied but no allowed_dirs are configured for "
            "this tool -- pass screenshot_path and/or allowed_dirs to "
            "make_find_coordinates_tool() to permit explicit image paths."
        )

    ext = os.path.splitext(image_path)[1].lower()
    if ext not in _ALLOWED_IMAGE_EXTENSIONS:
        raise ImagePathRejectedError(f"image_path has a disallowed extension: {image_path!r}")

    resolved = os.path.realpath(image_path)
    for allowed_dir in allowed_dirs:
        allowed_real = os.path.realpath(allowed_dir)
        if resolved == allowed_real or resolved.startswith(allowed_real + os.sep):
            return resolved

    raise ImagePathRejectedError(
        f"image_path {image_path!r} is outside the allowed directories: {list(allowed_dirs)!r}"
    )


def make_find_coordinates_tool(
    finder: CoordinateFinder,
    *,
    screenshot_path: Optional[Union[str, Callable[[], str]]] = None,
    allowed_dirs: Optional[Sequence[str]] = None,
    screen_width: Optional[int] = None,
    screen_height: Optional[int] = None,
    name: str = "find_coordinates",
) -> Tool:
    """
    Build a ``find_coordinates(description, image_path=None)`` Tool bound to
    ``finder``.

    Args:
        finder: the CoordinateFinder driving the actual grounding call.
        screenshot_path: default image path used when the tool is called
            without an explicit ``image_path`` -- a fixed string, or a
            zero-arg callable returning a fresh path each call (matching
            autourgos-preiteration's dynamic file-injection convention). If
            this is also omitted, the tool auto-captures the current screen
            (requires the optional `mss` dependency, the [capture] extra).
            Its directory is also added to ``allowed_dirs`` automatically
            when ``screenshot_path`` is a plain string.
        allowed_dirs: directories an explicit, LLM-supplied ``image_path``
            argument is allowed to resolve into (e.g. a dedicated
            screenshots directory). An ``image_path`` outside all of these
            (or with a non-image extension) is rejected. If this is empty/
            unset and ``screenshot_path`` isn't a plain string either, the
            tool never accepts an explicit ``image_path`` -- only its
            configured default / auto-capture.
        screen_width: fixes the screen width used for the pixel `x`/`y`
            included alongside the emitted normalized coordinates (custom).
            Omit to auto-detect it instead (automatic -- from an
            auto-capture, or from the image via Pillow if installed).
        screen_height: see screen_width.
        name: override the tool's exposed name.
    """
    resolved_allowed_dirs = list(allowed_dirs) if allowed_dirs else []
    if isinstance(screenshot_path, str):
        resolved_allowed_dirs.append(os.path.dirname(os.path.abspath(screenshot_path)) or ".")

    def find_coordinates(description: str, image_path: str = "") -> Dict[str, Any]:
        """Find the on-screen coordinates of a described UI element.

        Args:
            description: what to find, e.g. "the Submit button".
            image_path: path to a specific screenshot to search. Optional --
                falls back to the configured default screenshot_path, and if
                that's also unset, auto-captures the current screen. Must
                resolve inside one of this tool's configured allowed_dirs.
        """
        if image_path:
            try:
                image_arg = _validate_image_path(image_path, resolved_allowed_dirs)
            except ImagePathRejectedError as exc:
                return {"found": False, "error": str(exc)}
        else:
            default_path = _resolve_default(screenshot_path)
            image_arg = default_path if default_path else None  # None -> auto-capture

        try:
            coord = finder.find(
                description,
                image_arg,
                screen_width=screen_width,
                screen_height=screen_height,
            )
        except (CoordinateNotFoundError, CaptureError) as exc:
            return {"found": False, "error": str(exc)}

        result: Dict[str, Any] = {"found": True, "x_norm": coord.x_norm, "y_norm": coord.y_norm}
        if coord.screen_width and coord.screen_height:
            x_px, y_px = coord.to_pixels()
            result["x"] = x_px
            result["y"] = y_px
        return result

    return tool(find_coordinates, name=name)


def _resolve_default(screenshot_path: Optional[Union[str, Callable[[], str]]]) -> str:
    if screenshot_path is None:
        return ""
    if callable(screenshot_path):
        return screenshot_path()
    return screenshot_path
