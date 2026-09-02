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

    coord = finder.find("screenshot.png", "the Submit button")
    x_px, y_px = coord.to_pixels(1920, 1080)

    # Or as an agent tool:
    tool = make_find_coordinates_tool(finder, screen_width=1920, screen_height=1080)
    agent.add_tools(tool)
"""

from .locator import Coordinate, CoordinateFinder, CoordinateNotFoundError
from .tool import make_find_coordinates_tool

try:
    from importlib.metadata import version as _meta_version
    __version__ = _meta_version("autourgos-cua-coordinate-tool")
except Exception:
    __version__ = "0.1.0"

__all__ = [
    "Coordinate",
    "CoordinateFinder",
    "CoordinateNotFoundError",
    "make_find_coordinates_tool",
]
