"""
tool.py — wraps a CoordinateFinder as an agent-callable Tool.

make_find_coordinates_tool() returns an autourgos_agent.Tool (the standard
{"name", "description", "parameters", "func"} dict shape) ready to pass
straight into ``agent.add_tools(...)``, matching the convention every other
tool-producing package in this workspace (toolbox, preiteration, hcix) follows.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, Optional, Union

from autourgos_agent import Tool, tool

from .capture import CaptureError
from .locator import CoordinateFinder, CoordinateNotFoundError

__all__ = ["make_find_coordinates_tool"]


def make_find_coordinates_tool(
    finder: CoordinateFinder,
    *,
    screenshot_path: Optional[Union[str, Callable[[], str]]] = None,
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
        screen_width: fixes the screen width used for the pixel `x`/`y`
            included alongside the emitted normalized coordinates (custom).
            Omit to auto-detect it instead (automatic -- from an
            auto-capture, or from the image via Pillow if installed).
        screen_height: see screen_width.
        name: override the tool's exposed name.
    """

    def find_coordinates(description: str, image_path: str = "") -> Dict[str, Any]:
        """Find the on-screen coordinates of a described UI element.

        description: what to find, e.g. "the Submit button".
        image_path: path to a specific screenshot to search. Optional --
            falls back to the configured default screenshot_path, and if
            that's also unset, auto-captures the current screen.
        """
        resolved_path = image_path or _resolve_default(screenshot_path)
        image_arg = resolved_path if resolved_path else None  # None -> auto-capture

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
