"""
autourgos-cua-coordinate-tool — LLM-grounded UI coordinate finding for
Autourgos computer-use agents.

Given a screenshot and a natural-language description of a UI element,
CoordinateFinder asks a caller-supplied vision-capable LLM (any
autourgos-openaichat / autourgos-responses model instance, or anything
shaped like their BaseLLM) to locate it, and returns the position
normalized to a 0-1000 scale -- the same convention Gemini's computer-use
API uses -- plus optional pixel conversion.

Quick start::

    from autourgos_cua_coordinate_tool import CoordinateFinder, make_find_coordinates_tool
    from autourgos_openaichat import OpenAIChatModel

    llm = OpenAIChatModel(model="gpt-4o")
    finder = CoordinateFinder(llm)

    # Automatic: capture the current screen and auto-detect its dimensions.
    coord = finder.find("the Submit button")
    x_px, y_px = coord.to_pixels()

    # Custom: a specific screenshot and explicit dimensions.
    coord = finder.find("the Submit button", "screenshot.png")
    x_px, y_px = coord.to_pixels(1920, 1080)

    # Or as an agent tool (auto-capture/auto-detect by default):
    tool = make_find_coordinates_tool(finder)
    agent.add_tools(tool)
"""

from .capture import CaptureError, ScreenCapture, capture_screen, detect_image_size
from .locator import Coordinate, CoordinateFinder, CoordinateNotFoundError
from .tool import make_find_coordinates_tool

try:
    from importlib.metadata import version as _meta_version
    __version__ = _meta_version("autourgos-cua-coordinate-tool")
except Exception:
    __version__ = "1.0.0"

__all__ = [
    "Coordinate",
    "CoordinateFinder",
    "CoordinateNotFoundError",
    "make_find_coordinates_tool",
    "CaptureError",
    "ScreenCapture",
    "capture_screen",
    "detect_image_size",
]
