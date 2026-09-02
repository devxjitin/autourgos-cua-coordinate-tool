# Changelog

## [0.1.0] - 2026-09-02

- Initial release: `CoordinateFinder` locates a described UI element in a
  screenshot using a caller-supplied, vision-capable LLM (any
  autourgos-openaichat/autourgos-responses model instance, or anything
  shaped like their `BaseLLM`), returning a `Coordinate` normalized to a
  0-1000 scale (matching Gemini's computer-use API coordinate convention)
  with `.to_pixels(width, height)` denormalization.
  `make_find_coordinates_tool()` wraps a `CoordinateFinder` as a standard
  `autourgos_agent.Tool` ready for `agent.add_tools(...)`.
