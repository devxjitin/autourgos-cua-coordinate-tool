# Changelog

## [1.0.3] - 2026-09-04

- **Fixed:** `find()`/`afind()` used to `str()` the whole raw LLM response instead of extracting its `"response"` key -- an LLM wrapper constructed with `structured_output=True` (autourgos-openaichat/autourgos-responses) returns a metadata dict, and `str(dict)` produced a garbled Python-repr blob (`coord.raw_response` ended up as that whole blob; x/y parsing could get lucky via the prose-fallback regex or fail outright). Now uses `autourgos_core.extract_text()`. Live-verified against real Azure.
- **Fixed:** `find_coordinates()`'s docstring had bare `description:`/`image_path:` lines with no `Args:` header -- `@tool`'s strict docstring parser requires that header, so both param descriptions silently ended up empty in the tool's JSON schema. Header added.
- Bumped `autourgos-core>=0.4.0` (for `extract_text()`).

## [1.0.2] - 2026-09-04

- Internal: `__version__` resolution moved to `autourgos_core.package_version()` (new `autourgos-core>=0.3.0` dependency). No functional change.

## [1.0.1] - 2026-09-03

- Added `features.md` documenting the module's feature set and a competitor comparison. No code changes.


## [1.0.0] - 2026-09-02

- First PyPI release. No functional change from 0.2.0 -- version set to
  1.0.0 for the initial public PyPI publish per explicit request.

## [0.2.0] - 2026-09-02

- Added: automatic screenshot capture and automatic screen-dimension
  detection, alongside the existing custom/manual path (both are always
  available, never one instead of the other). `CoordinateFinder.find()`/
  `afind()` now take `image=None` by default -- omit it to auto-capture the
  current screen (new optional `mss` dependency, the `[capture]` extra;
  dimensions come free from the capture), or pass a specific path/bytes as
  before. `screen_width`/`screen_height` are now optional on `find()`/
  `afind()` too -- omit them to auto-detect (from the capture, or from a
  given image via the existing optional `Pillow` `[images]` extra), or pass
  them explicitly to force a specific conversion. New `capture.py` module:
  `capture_screen()`, `detect_image_size()`, `ScreenCapture`, `CaptureError`
  (all re-exported from the package root).
- BREAKING (pre-release, never published): `find`/`afind` parameter order
  changed from `(image, description)` to `(description, image=None)` to
  make `image` optional. `Coordinate` gained `screen_width`/`screen_height`
  fields (auto-detected or explicit, `None` if neither available);
  `to_pixels()` now accepts optional `screen_width`/`screen_height` and
  falls back to those stored fields when omitted, instead of requiring both
  arguments every time.
- `make_find_coordinates_tool()`'s generated tool now auto-captures the
  screen when called with no `image_path` and no configured
  `screenshot_path` (previously returned an error in that case), and
  includes pixel `x`/`y` whenever dimensions were auto-detected, not only
  when `screen_width`/`screen_height` were explicitly configured on the
  factory. A `CaptureError` (e.g. `mss` not installed) is caught and
  returned as a clean `{"found": False, "error": ...}` dict rather than
  propagating.

## [0.1.0] - 2026-09-02

- Initial release: `CoordinateFinder` locates a described UI element in a
  screenshot using a caller-supplied, vision-capable LLM (any
  autourgos-openaichat/autourgos-responses model instance, or anything
  shaped like their `BaseLLM`), returning a `Coordinate` normalized to a
  0-1000 scale (matching Gemini's computer-use API coordinate convention)
  with `.to_pixels(width, height)` denormalization.
  `make_find_coordinates_tool()` wraps a `CoordinateFinder` as a standard
  `autourgos_agent.Tool` ready for `agent.add_tools(...)`.
