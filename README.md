# autourgos-cua-coordinate-tool

[![Framework: Autourgos](https://img.shields.io/badge/Framework-Autourgos-orange.svg)](https://github.com/devxjitin)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://pypi.org/project/autourgos-cua-coordinate-tool/)
[![License: Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-green.svg)](https://github.com/devxjitin/autourgos-cua-coordinate-tool/blob/main/LICENSE)
[![Author](https://img.shields.io/badge/Author-Jitin%20Kumar%20Sengar-blue.svg)](https://github.com/devxjitin)

LLM-grounded UI coordinate finding for [Autourgos](https://github.com/devxjitin) computer-use agents.
Give it a description ("the Submit button") and it returns where that element is —
normalized to a 0-1000 scale, the same convention
[Gemini's computer-use API](https://ai.google.dev/gemini-api/docs/computer-use) uses.

There are two ways to use this package — pick one:

| | Use when | Screenshot |
|---|---|---|
| [`CoordinateFinder`](#use-case-1-coordinatefinder-library) | You're calling it directly from your own code. | Automatic (auto-capture) *or* custom (a specific file/bytes) — your choice per call. |
| [`CoordinateFinderTool`](#use-case-2-coordinatefindertool-agent-tool) | You want to hand it to an `autourgos-agent` `Agent` as a tool. | Always automatic — auto-captures the screen into memory on every call. |

---

## Table of Contents

- [Install](#install)
- [Use Case 1: `CoordinateFinder` (library)](#use-case-1-coordinatefinder-library)
  - [Automatic screenshot](#automatic-screenshot)
  - [Custom screenshot](#custom-screenshot)
  - [Async](#async)
  - [Error handling](#error-handling)
- [Use Case 2: `CoordinateFinderTool` (agent tool)](#use-case-2-coordinatefindertool-agent-tool)
- [Coordinate System](#coordinate-system)
- [API Reference](#api-reference)
- [License](#license)

---

## Install

```bash
pip install autourgos-cua-coordinate-tool
```

Optional extras:

```bash
pip install 'autourgos-cua-coordinate-tool[capture]'   # auto-capture the screen (mss)
pip install 'autourgos-cua-coordinate-tool[images]'    # auto-detect a given image's size (Pillow)
pip install 'autourgos-cua-coordinate-tool[all]'       # both
```

- `[capture]` is required for automatic screenshots (either use case).
- `[images]` is only relevant to `CoordinateFinder`'s custom-screenshot path — it's
  used to auto-detect a caller-supplied image's dimensions.
- Neither is required for `CoordinateFinder`'s fully custom path (caller-supplied
  image **and** explicit dimensions).

---

## Use Case 1: `CoordinateFinder` (library)

Call it directly from your own code. Every call takes an explicit `image` argument —
omit it to auto-capture, or pass your own screenshot.

### Automatic screenshot

Auto-captures the current screen and auto-detects its dimensions — nothing to pass in.

```python
from autourgos_cua_coordinate_tool import CoordinateFinder, CoordinateNotFoundError
from autourgos_openaichat import OpenAIChatModel

llm = OpenAIChatModel(model="gpt-4o")
finder = CoordinateFinder(llm)

try:
    coord = finder.find("the search input box")
except CoordinateNotFoundError as exc:
    print("not found:", exc)
else:
    x_px, y_px = coord.to_pixels()
    print(f"click at ({x_px}, {y_px})")
```

### Custom screenshot

Pass a specific screenshot (file path or bytes). Dimensions are auto-detected from it
via Pillow if installed, or you can force them explicitly.

```python
from autourgos_cua_coordinate_tool import CoordinateFinder
from autourgos_openaichat import OpenAIChatModel

llm = OpenAIChatModel(model="gpt-4o")
finder = CoordinateFinder(llm)

# Dimensions auto-detected from the image (needs Pillow).
coord = finder.find("the Submit button", "screenshot.png")
x_px, y_px = coord.to_pixels()

# Or force explicit dimensions instead.
coord = finder.find("the Submit button", "screenshot.png", screen_width=1920, screen_height=1080)
x_px, y_px = coord.to_pixels()
```

You can also force dimensions on an auto-captured screenshot:

```python
coord = finder.find("the Submit button", screen_width=2560, screen_height=1440)
```

### Async

`afind()` mirrors `find()` exactly, for both the automatic and custom paths.

```python
coord = await finder.afind("the Submit button")                    # automatic
coord = await finder.afind("the Submit button", "screenshot.png")  # custom
```

### Error handling

`find()`/`afind()` raise `CoordinateNotFoundError` — never a guessed coordinate — when:

- the model explicitly reports the element isn't visible,
- the response can't be parsed into a coordinate at all, or
- a parsed coordinate falls outside the 0-1000 range.

Auto-capture (`image=None`) raises `CaptureError` instead if the optional `mss`
dependency isn't installed.

```python
from autourgos_cua_coordinate_tool import CoordinateNotFoundError, CaptureError

try:
    coord = finder.find("a button that isn't there")
except CoordinateNotFoundError as exc:
    print("model couldn't find it:", exc)
except CaptureError as exc:
    print("auto-capture unavailable:", exc)
```

---

## Use Case 2: `CoordinateFinderTool` (agent tool)

For `autourgos-agent`. Construct it with your LLM and hand it straight to
`agent.add_tools(...)` — that's the whole surface, nothing else to configure.

```python
from autourgos_agent import Agent
from autourgos_cua_coordinate_tool import CoordinateFinderTool

agent = Agent(llm=my_llm)
agent.add_tools(CoordinateFinderTool(my_llm))

result = agent.invoke("Click the Submit button")
```

Every call auto-captures the current screen straight into memory (no temp file) and
asks the LLM to locate a `target` description in it. The tool has a fixed name
(`find_coordinates`) and description telling the calling LLM it self-captures the
screen and returns pixel coordinates automatically — nothing to configure.

It returns a dict:

```python
{"found": True, "x_norm": 512.0, "y_norm": 780.0, "x": 983, "y": 843}
# or, if not found / mss isn't installed:
{"found": False, "error": "..."}
```

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

### `CoordinateFinderTool(llm, *, image_detail=None) -> Tool`

A `find_coordinates(target)` tool bound to `llm`, with a fixed name and
description stating what it does: it auto-captures the current screen and
returns pixel coordinates for the described element, scaled to the actual
screen size.

### `capture_screen() -> ScreenCapture` / `detect_image_size(image) -> Optional[(int, int)]`

Lower-level helpers `CoordinateFinder` uses internally; exposed directly for other uses.
`capture_screen()` raises `CaptureError` if `mss` isn't installed. `detect_image_size()`
never raises — returns `None` if Pillow isn't installed or the image can't be read.

---

## License

Apache License 2.0. See [LICENSE](LICENSE).
