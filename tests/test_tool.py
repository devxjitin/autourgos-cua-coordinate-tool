import unittest

from autourgos_cua_coordinate_tool import CoordinateFinder, make_find_coordinates_tool


class FakeLLM:
    def __init__(self, response_text):
        self.response_text = response_text

    def invoke(self, prompt, files=None, **overrides):
        return self.response_text

    async def ainvoke(self, prompt, files=None, **overrides):
        return self.response_text


class TestToolShape(unittest.TestCase):
    def setUp(self):
        self.finder = CoordinateFinder(FakeLLM('{"found": true, "x": 400, "y": 600}'))

    def test_tool_dict_shape(self):
        t = make_find_coordinates_tool(self.finder)
        self.assertEqual(t["name"], "find_coordinates")
        self.assertIn("description", t)
        self.assertEqual(t["parameters"]["type"], "object")
        self.assertIn("description", t["parameters"]["properties"])
        self.assertIn("description", t["parameters"]["required"])
        self.assertTrue(callable(t["func"]))

    def test_custom_name(self):
        t = make_find_coordinates_tool(self.finder, name="locate_ui_element")
        self.assertEqual(t["name"], "locate_ui_element")


class TestToolInvocation(unittest.TestCase):
    def test_explicit_image_path_normalized_only(self):
        finder = CoordinateFinder(FakeLLM('{"found": true, "x": 250, "y": 750}'))
        t = make_find_coordinates_tool(finder)

        result = t.func("the Submit button", "shot.png")

        self.assertEqual(result, {"found": True, "x_norm": 250.0, "y_norm": 750.0})

    def test_pixels_included_when_screen_dims_configured(self):
        finder = CoordinateFinder(FakeLLM('{"found": true, "x": 500, "y": 500}'))
        t = make_find_coordinates_tool(finder, screen_width=1000, screen_height=800)

        result = t.func("something", "shot.png")

        self.assertEqual(result["x"], 500)
        self.assertEqual(result["y"], 400)

    def test_not_found_returns_error_dict(self):
        finder = CoordinateFinder(FakeLLM('{"found": false}'))
        t = make_find_coordinates_tool(finder)

        result = t.func("nonexistent widget", "shot.png")

        self.assertFalse(result["found"])
        self.assertIn("error", result)

    def test_default_screenshot_path_used_when_omitted(self):
        finder = CoordinateFinder(FakeLLM('{"found": true, "x": 1, "y": 1}'))
        t = make_find_coordinates_tool(finder, screenshot_path="/tmp/default.png")

        result = t.func("something")

        self.assertTrue(result["found"])

    def test_default_screenshot_path_callable(self):
        calls = []

        def next_path():
            calls.append(1)
            return "/tmp/dynamic.png"

        finder = CoordinateFinder(FakeLLM('{"found": true, "x": 1, "y": 1}'))
        t = make_find_coordinates_tool(finder, screenshot_path=next_path)

        t.func("something")

        self.assertEqual(len(calls), 1)

    def test_missing_image_path_and_no_default_errors_cleanly(self):
        finder = CoordinateFinder(FakeLLM('{"found": true, "x": 1, "y": 1}'))
        t = make_find_coordinates_tool(finder)

        result = t.func("something")

        self.assertFalse(result["found"])
        self.assertIn("error", result)


if __name__ == "__main__":
    unittest.main()
