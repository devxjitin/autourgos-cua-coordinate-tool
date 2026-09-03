# autourgos-cua-coordinate-tool — Features

An LLM-grounded UI coordinate finder for [Autourgos](https://github.com/devxjitin) computer-use agents:
give it a natural-language description ("the Submit button") and a screenshot, and it returns a
normalized on-screen coordinate for that element, using any vision-capable LLM that exposes an
`invoke(prompt, files=, **overrides)`/`ainvoke(...)` interface.

## Full Feature List

- **Provider-agnostic grounding** — drives any vision LLM shaped like `autourgos-openaichat`'s or
  `autourgos-responses`'s `BaseLLM`; no hard dependency on either package, and no coupling to one
  specific vision API
- **Automatic *and* custom screenshots** — omit `image` to auto-capture the current screen (optional
  `mss` dependency), or pass a specific file path/bytes yourself
- **Automatic *and* custom screen dimensions** — auto-detected from a capture, or via optional `Pillow`
  for a caller-supplied image, or forced explicitly
- **Gemini-style normalized coordinates** — output is always 0-1000 on both axes regardless of
  screenshot resolution, matching Gemini's documented computer-use coordinate convention, with
  `.to_pixels()` doing the documented denormalization
- **Fails closed** — raises `CoordinateNotFoundError` (never a fabricated/guessed coordinate) when the
  model reports the element isn't visible, the response can't be parsed, or a parsed coordinate falls
  outside 0-1000; raises `CaptureError` if auto-capture is requested without `mss` installed
- **Ready-made agent tool** — `make_find_coordinates_tool()` wraps a `CoordinateFinder` as a standard
  `autourgos-agent` `Tool` for `agent.add_tools(...)`, returning a structured
  `{"found": bool, "x_norm", "y_norm", "x"?, "y"?, "error"?}` dict
- **Sync and async** — `find()` / `afind()`
- Lower-level helpers exposed directly: `capture_screen()`, `detect_image_size()`
- Minimal footprint: core library has no hard dependency on `mss`/`Pillow`; both are optional extras
  (`[capture]`, `[images]`, `[all]`)

---

## Competitor Comparison

This is a narrow, single-purpose grounding primitive — natural-language description in, normalized
coordinate out — meant to be composed into a larger computer-use agent loop, not a full agent framework
itself. Real comparisons are other GUI-grounding approaches used in computer-use agents.

| Capability | **autourgos-cua-coordinate-tool** | [Anthropic Computer Use tool](https://platform.claude.com/docs/en/agents-and-tools/tool-use/computer-use-tool) | [Microsoft OmniParser](https://github.com/microsoft/OmniParser) | Gemini computer-use API |
|---|---|---|---|---|
| Scope | Standalone Python library — one grounding call | Native tool built into Claude's own agent loop | Screen-parsing model/pipeline, model-agnostic | Native tool built into Gemini's own agent loop |
| Provider lock-in | None — works with any `BaseLLM`-shaped vision model | Claude models only | None — pairs with GPT-4V, Claude, etc. | Gemini models only |
| Approach | Direct LLM-native grounding (ask the vision model where the element is) | Direct LLM-native grounding, coordinates from the model itself | Structured parsing first (detects UI elements + labels/IDs), then hands the LLM a list to choose from rather than raw pixel-to-coordinate guessing | Direct LLM-native grounding |
| Coordinate convention | 0-1000 normalized, explicitly matching Gemini's documented convention | Model-native pixel coordinates mapped to the active display | Bounding boxes/IDs per detected element, not raw normalized coordinates | 0-1000 normalized (this is the convention autourgos-cua-coordinate-tool mirrors) |
| Fails closed on not-found | Yes — explicit `CoordinateNotFoundError`, never guesses | Depends on the calling agent's handling of the model's response | Depends on the calling agent; detection can simply omit an element | Depends on the calling agent |
| Auto screen capture built in | Yes, optional `mss` extra | Provided by the surrounding agent harness, not the tool itself | No — expects a screenshot as input | Provided by the surrounding agent harness |
| Framework coupling | None required; ships an `autourgos-agent` tool wrapper as a convenience | Tied to Anthropic's Claude + agent harness | None — pipeline usable from any stack | Tied to Google's Gemini + agent harness |
| Extra inference cost | One extra vision LLM call per lookup (whatever model you configure) | Included in the same agentic loop call | Extra parsing pass (its own vision/detection model) before the LLM sees anything | Included in the same agentic loop call |
| Pricing | Free, open source | Priced via Claude API usage | Free, open source (Microsoft) | Priced via Gemini API usage |

### How to read this

- autourgos-cua-coordinate-tool is not a competing agent framework — it is a provider-agnostic building
  block for the same grounding step that Anthropic's and Google's native computer-use tools bundle
  directly into their own agent loops. Its value is being usable with *any* vision-capable LLM rather
  than being locked to one vendor's agent harness.
- **vs. Anthropic/Gemini native computer-use tools**: those are more integrated (grounding, action
  execution, and loop control all bundled), but tie you to that one provider's model and agent harness.
  This library gives you the grounding half only, portable across providers, at the cost of having to
  build/own the rest of the action loop yourself.
- **vs. OmniParser**: OmniParser takes a fundamentally different approach — it parses the screenshot
  into structured, labeled UI elements first, then lets the LLM pick from a list, which tends to be more
  reliable for models without strong native grounding. autourgos-cua-coordinate-tool instead asks the
  vision LLM directly for a coordinate, which is simpler (no separate parsing model/pipeline to run) but
  leans entirely on the underlying model's own grounding accuracy.
- The explicit fail-closed behavior (raising rather than guessing a coordinate) is a real differentiator
  versus rolling your own prompt-and-parse grounding call, where a bad parse can silently produce a
  wrong click target.

Sources:
- [Computer use tool - Claude Platform Docs](https://platform.claude.com/docs/en/agents-and-tools/tool-use/computer-use-tool)
- [GitHub - microsoft/OmniParser](https://github.com/microsoft/omniparser)
- [OmniParser V2: Turning Any LLM into a Computer Use Agent - Microsoft Research](https://www.microsoft.com/en-us/research/articles/omniparser-v2-turning-any-llm-into-a-computer-use-agent/)
- [Computer Use and AI Agents: A New Paradigm for Screen Interaction | Towards Data Science](https://towardsdatascience.com/computer-use-and-ai-agents-a-new-paradigm-for-screen-interaction-b2dcbea0df5b/)
- [Anthropic Computer Use API: Desktop Automation Guide](https://www.digitalapplied.com/blog/anthropic-computer-use-api-guide)
- [Moving Beyond Sparse Grounding with Complete Screen Parsing Supervision](https://arxiv.org/html/2602.14276v2)
