import unittest
from unittest.mock import patch

from autourgos_cua_coordinate_tool import CoordinateFinderTool
from autourgos_cua_coordinate_tool.capture import CaptureError, ScreenCapture


class FakeLLM:
    def __init__(self, response_text):
        self.response_text = response_text

    def invoke(self, prompt, files=None, **overrides):
        return self.response_text

    async def ainvoke(self, prompt, files=None, **overrides):
        return self.response_text


class TestToolShape(unittest.TestCase):
    def setUp(self):
        self.llm = FakeLLM('{"found": true, "x": 400, "y": 600}')

    def test_tool_dict_shape(self):
        t = CoordinateFinderTool(self.llm)
        self.assertEqual(t["name"], "find_coordinates")
        self.assertIn("description", t)
        self.assertEqual(t["parameters"]["type"], "object")
        self.assertIn("target", t["parameters"]["properties"])
        self.assertIn("target", t["parameters"]["required"])
        self.assertTrue(callable(t["func"]))

    def test_description_mentions_auto_screenshot_and_pixel_coords(self):
        t = CoordinateFinderTool(self.llm)
        self.assertIn("screenshot", t["description"].lower())
        self.assertIn("pixel", t["description"].lower())

    def test_param_description_is_not_empty(self):
        t = CoordinateFinderTool(self.llm)
        props = t["parameters"]["properties"]
        self.assertTrue(props["target"]["description"])

    def test_callable_directly(self):
        t = CoordinateFinderTool(self.llm)
        fake_capture = ScreenCapture(image_bytes=b"png-bytes", width=1920, height=1080)

        with patch("autourgos_cua_coordinate_tool.locator.capture_screen", return_value=fake_capture):
            result = t("the Submit button")

        self.assertTrue(result["found"])


class TestToolInvocation(unittest.TestCase):
    """Every call auto-captures the current screen straight into memory."""

    def test_auto_captures_and_includes_autodetected_pixels(self):
        t = CoordinateFinderTool(FakeLLM('{"found": true, "x": 500, "y": 500}'))
        fake_capture = ScreenCapture(image_bytes=b"png-bytes", width=1920, height=1080)

        with patch("autourgos_cua_coordinate_tool.locator.capture_screen", return_value=fake_capture):
            result = t.func("something")

        self.assertTrue(result["found"])
        self.assertEqual(result["x"], 960)
        self.assertEqual(result["y"], 540)

    def test_not_found_returns_error_dict(self):
        t = CoordinateFinderTool(FakeLLM('{"found": false}'))
        fake_capture = ScreenCapture(image_bytes=b"png-bytes", width=1920, height=1080)

        with patch("autourgos_cua_coordinate_tool.locator.capture_screen", return_value=fake_capture):
            result = t.func("nonexistent widget")

        self.assertFalse(result["found"])
        self.assertIn("error", result)

    def test_capture_error_returns_clean_error_dict_not_a_crash(self):
        t = CoordinateFinderTool(FakeLLM('{"found": true, "x": 1, "y": 1}'))

        with patch(
            "autourgos_cua_coordinate_tool.locator.capture_screen",
            side_effect=CaptureError("mss not installed"),
        ):
            result = t.func("something")

        self.assertFalse(result["found"])
        self.assertIn("error", result)


if __name__ == "__main__":
    unittest.main()
