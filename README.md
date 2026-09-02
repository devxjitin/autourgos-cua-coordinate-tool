# autourgos-cua-coordinate-tool

[![Framework: Autourgos](https://img.shields.io/badge/Framework-Autourgos-orange.svg)](https://github.com/devxjitin)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://pypi.org/project/autourgos-cua-coordinate-tool/)
[![License: Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-green.svg)](https://github.com/devxjitin/autourgos-cua-coordinate-tool/blob/main/LICENSE)
[![Author](https://img.shields.io/badge/Author-Jitin%20Kumar%20Sengar-blue.svg)](https://github.com/devxjitin)

LLM-grounded UI coordinate finding for [Autourgos](https://github.com/devxjitin) computer-use agents.
Give it a description ("the Submit button") and it returns where that element is —
normalized to a 0-1000 scale, the same convention
[Gemini's computer-use API](https://ai.google.dev/gemini-api/docs/computer-use) uses. It can
auto-capture the current screen and auto-detect screen dimensions, or take an explicit
screenshot/dimensions instead — both paths are always available.

```python
from autourgos_cua_coordinate_tool import CoordinateFinder
from autourgos_openaichat import OpenAIChatModel

llm = OpenAIChatModel(model="gpt-4o")
finder = CoordinateFinder(llm)

# Automatic: capture the current screen and auto-detect its dimensions.
coord = finder.find("the Submit button")
x_px, y_px = coord.to_pixels()

# Custom: a specific screenshot and explicit dimensions.
coord = finder.find("the Submit button", "screenshot.png")
x_px, y_px = coord.to_pixels(1920, 1080)
```

---

## Features

- **Provider-agnostic grounding** — drives any vision-capable LLM shaped like
  [`autourgos-openaichat`](https://github.com/devxjitin/autourgos-openaichat)'s or
  [`autourgos-responses`](https://github.com/devxjitin/autourgos-responses)'s `BaseLLM`
  (`invoke(prompt, files=, **overrides)` / `ainvoke(...)`). No hard dependency on either
  package, and no coupling to one vision API.
- **Automatic *and* custom screenshots** — omit `image` to auto-capture the current
  screen (optional `mss` dependency), or pass a specific file path/bytes yourself.
- **Automatic *and* custom screen dimensions** — omit `screen_width`/`screen_height` to
  auto-detect them (free from an auto-capture, or via optional `Pillow` for a
  caller-supplied image), or pass them explicitly to force a specific conversion.
- **Gemini-style normalized coordinates** — output is always 0-1000 on both axes
  regardless of screenshot resolution, matching Gemini computer-use's own convention,
  with `.to_pixels()` doing the documented denormalization.
- **Fails closed** — an element the model can't find, or a response that can't be
  parsed, raises `CoordinateNotFoundError` instead of returning a fabricated coordinate.
- **Ready-made agent tool** — `make_find_coordinates_tool()` wraps a `CoordinateFinder`
  as a standard [`autourgos-agent`](https://github.com/devxjitin/autourgos-agent) `Tool`
  for `agent.add_tools(...)`.
- **Sync and async** — `find()` / `afind()`.

---

## Table of Contents

- [Install](#install)
- [Quick Start](#quick-start)
- [Automatic vs Custom](#automatic-vs-custom)
- [Async](#async)
- [As an Agent Tool](#as-an-agent-tool)
- [Coordinate System](#coordinate-system)
- [Error Handling](#error-handling)
- [API Reference](#api-reference)
- [License](#license)

---

## Install

```bash
pip install autourgos-cua-coordinate-tool
```

For automatic screen capture (`mss`) and/or automatic image dimension detection
(`Pillow`):

```bash
pip install 'autourgos-cua-coordinate-tool[capture]'   # auto-capture the screen
pip install 'autourgos-cua-coordinate-tool[images]'    # auto-detect a given image's size
pip install 'autourgos-cua-coordinate-tool[all]'       # both
```

Neither is required for the fully custom (caller-supplied image + dimensions) path.

---

## Quick Start

```python
from autourgos_cua_coordinate_tool import CoordinateFinder, CoordinateNotFoundError
from autourgos_openaichat import OpenAIChatModel

llm = OpenAIChatModel(model="gpt-4o")
finder = CoordinateFinder(llm)

try:
    coord = finder.find("the search input box")   # auto-captures the current screen
except CoordinateNotFoundError as exc:
    print("not found:", exc)
else:
    x_px, y_px = coord.to_pixels()                 # dimensions auto-detected from the capture
    print(f"click at ({x_px}, {y_px})")
```

Works the same with `autourgos-responses` model instances, or any object that
exposes `invoke(prompt, files=, **overrides)` / `ainvoke(...)`.

---

## Automatic vs Custom

`find(description, image=None, *, screen_width=None, screen_height=None, **overrides)`
supports both, and you can mix them freely:

| `image` | `screen_width`/`screen_height` | Behavior |
|---|---|---|
| omitted (`None`) | omitted | **Fully automatic** — captures the current screen (`mss`), dimensions come free from the capture. |
| omitted (`None`) | given | Auto-captures the screen, but forces pixel conversion against the dimensions you passed. |
| given | omitted | **Custom screenshot**, dimensions auto-detected from it via Pillow if installed (falls back to `None` if not — `to_pixels()` then needs explicit dimensions). |
| given | given | **Fully custom** — no auto-capture, no auto-detection. |

```python
# Fully automatic
coord = finder.find("the Submit button")

# Custom screenshot, automatic dimensions (via Pillow)
coord = finder.find("the Submit button", "screenshot.png")

# Automatic screenshot, custom (forced) dimensions
coord = finder.find("the Submit button", screen_width=2560, screen_height=1440)

# Fully custom
coord = finder.find("the Submit button", "screenshot.png", screen_width=1920, screen_height=1080)
```

---

## Async

```python
coord = await finder.afind("the Submit button")   # auto-capture works here too
```

---

## As an Agent Tool

```python
from autourgos_agent import Agent
from autourgos_cua_coordinate_tool import CoordinateFinder, make_find_coordinates_tool

finder = CoordinateFinder(llm)

# Fully automatic (auto-captures the screen, auto-detects dimensions):
find_coordinates = make_find_coordinates_tool(finder)

# Custom instead:
find_coordinates = make_find_coordinates_tool(
    finder,
    screen_width=1920,
    screen_height=1080,
    screenshot_path="/tmp/screen.png",  # default when the agent omits image_path;
                                         # can also be a zero-arg callable for a
                                         # fresh path each call
)

agent = Agent(llm=my_llm)
agent.add_tools(find_coordinates)
result = agent.invoke("Click the Submit button")
```

The tool returns a dict: `{"found": True, "x_norm": ..., "y_norm": ..., "x": ..., "y": ...}`
(pixel `x`/`y` only present when dimensions were configured or auto-detected), or
`{"found": False, "error": "..."}` — including when auto-capture is requested but
`mss` isn't installed.

---

## Coordinate System

Every `Coordinate` is normalized to **0-1000** on both axes, independent of the
screenshot's actual resolution — the same convention documented for Gemini's
computer-use API:

```python
actual_x = int(x_norm / 1000 * screen_width)
actual_y = int(y_norm / 1000 * screen_height)
```

`Coordinate.to_pixels(screen_width=None, screen_height=None)` implements this exactly —
pass dimensions explicitly to force them (custom), or omit both to use whatever was
auto-detected when the `Coordinate` was found (automatic).

---

## Error Handling

`CoordinateFinder.find()`/`afind()` raise `CoordinateNotFoundError` — never a
guessed coordinate — when:

- the model explicitly reports the element isn't visible,
- the response can't be parsed into a coordinate at all, or
- a parsed coordinate falls outside the 0-1000 range.

Auto-capture (`image=None`) raises `CaptureError` instead if the optional `mss`
dependency isn't installed.

---

## API Reference

### `CoordinateFinder(llm, *, image_detail=None)`

- `find(description, image=None, *, screen_width=None, screen_height=None, **overrides) -> Coordinate`
- `afind(description, image=None, *, screen_width=None, screen_height=None, **overrides) -> Coordinate` (async)

`image` is a file path or bytes, or omit it to auto-capture the current screen.
`**overrides` are forwarded to the underlying `llm.invoke()`/`ainvoke()` call (e.g.
`temperature=`).

### `Coordinate`

- `x_norm: float`, `y_norm: float` — 0-1000 normalized position
- `raw_response: str` — the model's raw text, for debugging
- `screen_width`, `screen_height: Optional[int]` — auto-detected (or explicitly
  passed) dimensions at find() time, if any
- `to_pixels(screen_width=None, screen_height=None) -> (int, int)`

### `make_find_coordinates_tool(finder, *, screenshot_path=None, screen_width=None, screen_height=None, name="find_coordinates") -> Tool`

Builds a `find_coordinates(description, image_path=None)` tool bound to `finder`.
`image_path` omitted (and no `screenshot_path` configured) auto-captures the screen.

### `capture_screen() -> ScreenCapture` / `detect_image_size(image) -> Optional[(int, int)]`

Lower-level helpers `CoordinateFinder` uses internally; exposed directly for other uses.
`capture_screen()` raises `CaptureError` if `mss` isn't installed. `detect_image_size()`
never raises — returns `None` if Pillow isn't installed or the image can't be read.

---

## License

Apache License 2.0. See [LICENSE](LICENSE).
