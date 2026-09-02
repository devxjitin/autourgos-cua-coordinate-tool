# autourgos-cua-coordinate-tool

[![Framework: Autourgos](https://img.shields.io/badge/Framework-Autourgos-orange.svg)](https://github.com/devxjitin)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://pypi.org/project/autourgos-cua-coordinate-tool/)
[![License: Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-green.svg)](https://github.com/devxjitin/autourgos-cua-coordinate-tool/blob/main/LICENSE)
[![Author](https://img.shields.io/badge/Author-Jitin%20Kumar%20Sengar-blue.svg)](https://github.com/devxjitin)

LLM-grounded UI coordinate finding for [Autourgos](https://github.com/devxjitin) computer-use agents.
Give it a screenshot and a description ("the Submit button") and it returns where that
element is — normalized to a 0-1000 scale, the same convention
[Gemini's computer-use API](https://ai.google.dev/gemini-api/docs/computer-use) uses.

```python
from autourgos_cua_coordinate_tool import CoordinateFinder
from autourgos_openaichat import OpenAIChatModel

llm = OpenAIChatModel(model="gpt-4o")
finder = CoordinateFinder(llm)

coord = finder.find("screenshot.png", "the Submit button")
print(coord.x_norm, coord.y_norm)          # 0-1000 normalized
x_px, y_px = coord.to_pixels(1920, 1080)   # actual screen pixels
```

---

## Features

- **Provider-agnostic grounding** — drives any vision-capable LLM shaped like
  [`autourgos-openaichat`](https://github.com/devxjitin/autourgos-openaichat)'s or
  [`autourgos-responses`](https://github.com/devxjitin/autourgos-responses)'s `BaseLLM`
  (`invoke(prompt, files=, **overrides)` / `ainvoke(...)`). No hard dependency on either
  package, and no coupling to one vision API.
- **Gemini-style normalized coordinates** — output is always 0-1000 on both axes
  regardless of screenshot resolution, matching Gemini computer-use's own convention,
  with `.to_pixels(width, height)` doing the documented denormalization.
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

For automatic screenshot width/height detection (Pillow):

```bash
pip install 'autourgos-cua-coordinate-tool[images]'
```

---

## Quick Start

```python
from autourgos_cua_coordinate_tool import CoordinateFinder, CoordinateNotFoundError
from autourgos_openaichat import OpenAIChatModel

llm = OpenAIChatModel(model="gpt-4o")
finder = CoordinateFinder(llm)

try:
    coord = finder.find("screenshot.png", "the search input box")
except CoordinateNotFoundError as exc:
    print("not found:", exc)
else:
    x_px, y_px = coord.to_pixels(screen_width=1920, screen_height=1080)
    print(f"click at ({x_px}, {y_px})")
```

Works the same with `autourgos-responses` model instances, or any object that
exposes `invoke(prompt, files=, **overrides)` / `ainvoke(...)`.

---

## Async

```python
coord = await finder.afind("screenshot.png", "the Submit button")
```

---

## As an Agent Tool

```python
from autourgos_agent import Agent
from autourgos_cua_coordinate_tool import CoordinateFinder, make_find_coordinates_tool

finder = CoordinateFinder(llm)
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
(pixel `x`/`y` only present when `screen_width`/`screen_height` were configured), or
`{"found": False, "error": "..."}`.

---

## Coordinate System

Every `Coordinate` is normalized to **0-1000** on both axes, independent of the
screenshot's actual resolution — the same convention documented for Gemini's
computer-use API:

```python
actual_x = int(x_norm / 1000 * screen_width)
actual_y = int(y_norm / 1000 * screen_height)
```

`Coordinate.to_pixels(screen_width, screen_height)` implements this exactly.

---

## Error Handling

`CoordinateFinder.find()`/`afind()` raise `CoordinateNotFoundError` — never a
guessed coordinate — when:

- the model explicitly reports the element isn't visible,
- the response can't be parsed into a coordinate at all, or
- a parsed coordinate falls outside the 0-1000 range.

---

## API Reference

### `CoordinateFinder(llm, *, image_detail=None)`

- `find(image, description, **overrides) -> Coordinate`
- `afind(image, description, **overrides) -> Coordinate` (async)

`image` is a file path or bytes; `**overrides` are forwarded to the underlying
`llm.invoke()`/`ainvoke()` call (e.g. `temperature=`).

### `Coordinate`

- `x_norm: float`, `y_norm: float` — 0-1000 normalized position
- `raw_response: str` — the model's raw text, for debugging
- `to_pixels(screen_width, screen_height) -> (int, int)`

### `make_find_coordinates_tool(finder, *, screenshot_path=None, screen_width=None, screen_height=None, name="find_coordinates") -> Tool`

Builds a `find_coordinates(description, image_path=None)` tool bound to `finder`.

---

## License

Apache License 2.0. See [LICENSE](LICENSE).
