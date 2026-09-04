import asyncio
import unittest
from unittest.mock import patch

from autourgos_cua_coordinate_tool import Coordinate, CoordinateFinder, CoordinateNotFoundError
from autourgos_cua_coordinate_tool.capture import CaptureError, ScreenCapture


class FakeLLM:
    """Duck-typed BaseLLM-shaped stub: scripted invoke()/ainvoke() text, no real API call."""

    def __init__(self, response_text):
        self.response_text = response_text
        self.calls = []

    def invoke(self, prompt, files=None, **overrides):
        self.calls.append({"prompt": prompt, "files": files, "overrides": overrides})
        return self.response_text

    async def ainvoke(self, prompt, files=None, **overrides):
        self.calls.append({"prompt": prompt, "files": files, "overrides": overrides})
        return self.response_text


class TestCoordinateFinderConstruction(unittest.TestCase):
    def test_rejects_llm_without_invoke_ainvoke(self):
        with self.assertRaises(TypeError):
            CoordinateFinder(object())


class TestFindHappyPath(unittest.TestCase):
    def test_strict_json_response_with_explicit_image(self):
        llm = FakeLLM('{"found": true, "x": 512, "y": 780}')
        finder = CoordinateFinder(llm)

        coord = finder.find("the Submit button", "shot.png")

        self.assertIsInstance(coord, Coordinate)
        self.assertEqual(coord.x_norm, 512.0)
        self.assertEqual(coord.y_norm, 780.0)
        self.assertIn("Submit button", llm.calls[0]["prompt"])
        self.assertEqual(llm.calls[0]["files"], ["shot.png"])

    def test_json_wrapped_in_markdown_fence(self):
        llm = FakeLLM('```json\n{"found": true, "x": 10, "y": 20}\n```')
        finder = CoordinateFinder(llm)

        coord = finder.find("an icon", "shot.png")

        self.assertEqual((coord.x_norm, coord.y_norm), (10.0, 20.0))

    def test_prose_fallback_parsing(self):
        llm = FakeLLM('Sure, I found it at x: 300, y: 450 roughly.')
        finder = CoordinateFinder(llm)

        coord = finder.find("a button", "shot.png")

        self.assertEqual((coord.x_norm, coord.y_norm), (300.0, 450.0))

    def test_to_pixels_matches_gemini_formula(self):
        coord = Coordinate(x_norm=500, y_norm=250, raw_response="")
        x_px, y_px = coord.to_pixels(1920, 1080)
        self.assertEqual(x_px, int(500 / 1000 * 1920))
        self.assertEqual(y_px, int(250 / 1000 * 1080))

    def test_to_pixels_requires_dimensions_from_somewhere(self):
        coord = Coordinate(x_norm=1, y_norm=1, raw_response="")
        with self.assertRaises(ValueError):
            coord.to_pixels()

    def test_structured_output_dict_response_is_extracted_correctly(self):
        """
        Regression: find()/afind() used to str() the whole raw response
        instead of extracting its "response" key -- an LLM wrapper
        constructed with structured_output=True (autourgos-openaichat/
        autourgos-responses) returns a metadata dict, not a plain string.
        str(dict) produced an unparseable Python-repr blob; the x/y values
        could occasionally still be recovered by the prose-fallback regex
        matching lucky substrings of that blob, but raw_response ended up
        as the whole garbled dict repr instead of the model's actual text
        -- asserted here since it's the one difference that doesn't depend
        on fallback-regex luck.
        """
        model_text = '{"found": true, "x": 640, "y": 360}'
        llm = FakeLLM({
            "model": "gpt-4o", "response": model_text,
            "input_tokens": 50, "output_tokens": 12,
        })
        finder = CoordinateFinder(llm)

        coord = finder.find("a button", "shot.png")

        self.assertEqual((coord.x_norm, coord.y_norm), (640.0, 360.0))
        self.assertEqual(coord.raw_response, model_text)

    def test_afind_structured_output_dict_response_is_extracted_correctly(self):
        model_text = '{"found": true, "x": 100, "y": 200}'
        llm = FakeLLM({"model": "gpt-4o", "response": model_text})
        finder = CoordinateFinder(llm)

        coord = asyncio.run(finder.afind("a button", "shot.png"))

        self.assertEqual((coord.x_norm, coord.y_norm), (100.0, 200.0))
        self.assertEqual(coord.raw_response, model_text)

    def test_to_pixels_rejects_non_positive_dimensions(self):
        coord = Coordinate(x_norm=1, y_norm=1, raw_response="")
        with self.assertRaises(ValueError):
            coord.to_pixels(0, 100)


class TestFindNotFound(unittest.TestCase):
    def test_explicit_not_found(self):
        llm = FakeLLM('{"found": false}')
        finder = CoordinateFinder(llm)
        with self.assertRaises(CoordinateNotFoundError):
            finder.find("a nonexistent widget", "shot.png")

    def test_unparseable_response(self):
        llm = FakeLLM("I have no idea what you mean.")
        finder = CoordinateFinder(llm)
        with self.assertRaises(CoordinateNotFoundError):
            finder.find("something", "shot.png")

    def test_out_of_range_coordinate_rejected(self):
        llm = FakeLLM('{"found": true, "x": 1500, "y": 20}')
        finder = CoordinateFinder(llm)
        with self.assertRaises(CoordinateNotFoundError):
            finder.find("something", "shot.png")

    def test_negative_coordinate_rejected(self):
        llm = FakeLLM('{"found": true, "x": -5, "y": 20}')
        finder = CoordinateFinder(llm)
        with self.assertRaises(CoordinateNotFoundError):
            finder.find("something", "shot.png")

    def test_non_numeric_coordinate_rejected(self):
        llm = FakeLLM('{"found": true, "x": "left", "y": 20}')
        finder = CoordinateFinder(llm)
        with self.assertRaises(CoordinateNotFoundError):
            finder.find("something", "shot.png")


class TestAsyncFind(unittest.TestCase):
    def test_afind_happy_path(self):
        llm = FakeLLM('{"found": true, "x": 100, "y": 200}')
        finder = CoordinateFinder(llm)

        coord = asyncio.run(finder.afind("a link", "shot.png"))

        self.assertEqual((coord.x_norm, coord.y_norm), (100.0, 200.0))

    def test_afind_not_found(self):
        llm = FakeLLM('{"found": false}')
        finder = CoordinateFinder(llm)

        async def run():
            with self.assertRaises(CoordinateNotFoundError):
                await finder.afind("a link", "shot.png")

        asyncio.run(run())


class TestOverridesForwarded(unittest.TestCase):
    def test_image_detail_and_overrides_forwarded(self):
        llm = FakeLLM('{"found": true, "x": 1, "y": 1}')
        finder = CoordinateFinder(llm, image_detail="high")

        finder.find("x", "shot.png", temperature=0.0)

        call = llm.calls[0]
        self.assertEqual(call["overrides"]["image_detail"], "high")
        self.assertEqual(call["overrides"]["temperature"], 0.0)


class TestAutomaticCapture(unittest.TestCase):
    """image omitted -> auto-capture; dimensions come free from the capture."""

    def test_find_without_image_auto_captures_and_detects_dims(self):
        llm = FakeLLM('{"found": true, "x": 500, "y": 500}')
        finder = CoordinateFinder(llm)
        fake_capture = ScreenCapture(image_bytes=b"png-bytes", width=1920, height=1080)

        with patch("autourgos_cua_coordinate_tool.locator.capture_screen", return_value=fake_capture) as mocked:
            coord = finder.find("the Submit button")

        mocked.assert_called_once()
        self.assertEqual(llm.calls[0]["files"], [b"png-bytes"])
        self.assertEqual((coord.screen_width, coord.screen_height), (1920, 1080))
        x_px, y_px = coord.to_pixels()
        self.assertEqual((x_px, y_px), (960, 540))

    def test_find_without_mss_installed_raises_capture_error(self):
        llm = FakeLLM('{"found": true, "x": 1, "y": 1}')
        finder = CoordinateFinder(llm)

        with patch(
            "autourgos_cua_coordinate_tool.locator.capture_screen",
            side_effect=CaptureError("mss not installed"),
        ):
            with self.assertRaises(CaptureError):
                finder.find("something")

    def test_afind_without_image_auto_captures(self):
        llm = FakeLLM('{"found": true, "x": 250, "y": 250}')
        finder = CoordinateFinder(llm)
        fake_capture = ScreenCapture(image_bytes=b"png-bytes", width=800, height=600)

        with patch("autourgos_cua_coordinate_tool.locator.capture_screen", return_value=fake_capture):
            coord = asyncio.run(finder.afind("something"))

        self.assertEqual((coord.screen_width, coord.screen_height), (800, 600))

    def test_explicit_image_uses_pillow_autodetected_dims(self):
        llm = FakeLLM('{"found": true, "x": 500, "y": 500}')
        finder = CoordinateFinder(llm)

        with patch(
            "autourgos_cua_coordinate_tool.locator.detect_image_size",
            return_value=(1000, 2000),
        ):
            coord = finder.find("something", "shot.png")

        self.assertEqual((coord.screen_width, coord.screen_height), (1000, 2000))

    def test_explicit_screen_dims_override_autodetected_ones(self):
        llm = FakeLLM('{"found": true, "x": 500, "y": 500}')
        finder = CoordinateFinder(llm)
        fake_capture = ScreenCapture(image_bytes=b"png-bytes", width=1920, height=1080)

        with patch("autourgos_cua_coordinate_tool.locator.capture_screen", return_value=fake_capture):
            coord = finder.find("something", screen_width=100, screen_height=200)

        self.assertEqual((coord.screen_width, coord.screen_height), (100, 200))


if __name__ == "__main__":
    unittest.main()
