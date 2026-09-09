"""
tool.py -- CoordinateFinderTool: the agent-callable form of CoordinateFinder.

Simplest possible surface: construct it with an LLM, pass it straight to
agent.add_tools(...). The wrapped tool call takes a single ``target``
argument (a detailed description of the UI element) and always auto-captures
the current screen into memory (see capture.capture_screen) -- no
screenshot_path, no allowed_dirs, no LLM-supplied image_path to validate.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from autourgos_agent import Tool, tool

from .capture import CaptureError
from .locator import CoordinateFinder, CoordinateNotFoundError

__all__ = ["CoordinateFinderTool"]


class CoordinateFinderTool(Tool):
    """
    A ready-to-use ``find_coordinates(target)`` Tool bound to an LLM.

    ``target`` should be a detailed description of the UI element to find,
    e.g. "the blue Submit button in the bottom-right corner of the form".
    Each call auto-captures the current screen straight into memory and asks
    the LLM to locate ``target`` in it.

    Usage::

        agent.add_tools(CoordinateFinderTool(llm))
    """

    def __init__(
        self,
        llm: Any,
        *,
        image_detail: Optional[str] = None,
    ) -> None:
        finder = CoordinateFinder(llm, image_detail=image_detail)

        def find_coordinates(target: str) -> Dict[str, Any]:
            """Automatically takes a screenshot of the current screen and returns the pixel coordinates of a described UI element on it, scaled to the actual screen size -- no image or dimensions need to be supplied.

            Args:
                target: a detailed description of the UI element to find, e.g. "the blue Submit button in the bottom-right corner".
            """
            try:
                coord = finder.find(target)
            except (CoordinateNotFoundError, CaptureError) as exc:
                return {"found": False, "error": str(exc)}

            result: Dict[str, Any] = {"found": True, "x_norm": coord.x_norm, "y_norm": coord.y_norm}
            if coord.screen_width and coord.screen_height:
                x_px, y_px = coord.to_pixels()
                result["x"] = x_px
                result["y"] = y_px
            return result

        built = tool(find_coordinates, name="find_coordinates")
        super().__init__(built.func, name=built["name"], description=built["description"], parameters=built["parameters"])
