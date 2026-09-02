import asyncio
import unittest

from autourgos_cua_coordinate_tool import Coordinate, CoordinateFinder, CoordinateNotFoundError


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
    def test_strict_json_response(self):
        llm = FakeLLM('{"found": true, "x": 512, "y": 780}')
        finder = CoordinateFinder(llm)

        coord = finder.find("shot.png", "the Submit button")

        self.assertIsInstance(coord, Coordinate)
        self.assertEqual(coord.x_norm, 512.0)
        self.assertEqual(coord.y_norm, 780.0)
        self.assertIn("Submit button", llm.calls[0]["prompt"])
        self.assertEqual(llm.calls[0]["files"], ["shot.png"])

    def test_json_wrapped_in_markdown_fence(self):
        llm = FakeLLM('```json\n{"found": true, "x": 10, "y": 20}\n```')
        finder = CoordinateFinder(llm)

        coord = finder.find("shot.png", "an icon")

        self.assertEqual((coord.x_norm, coord.y_norm), (10.0, 20.0))

    def test_prose_fallback_parsing(self):
        llm = FakeLLM('Sure, I found it at x: 300, y: 450 roughly.')
        finder = CoordinateFinder(llm)

        coord = finder.find("shot.png", "a button")

        self.assertEqual((coord.x_norm, coord.y_norm), (300.0, 450.0))

    def test_to_pixels_matches_gemini_formula(self):
        coord = Coordinate(x_norm=500, y_norm=250, raw_response="")
        x_px, y_px = coord.to_pixels(1920, 1080)
        self.assertEqual(x_px, int(500 / 1000 * 1920))
        self.assertEqual(y_px, int(250 / 1000 * 1080))

    def test_to_pixels_rejects_non_positive_dimensions(self):
        coord = Coordinate(x_norm=1, y_norm=1, raw_response="")
        with self.assertRaises(ValueError):
            coord.to_pixels(0, 100)


class TestFindNotFound(unittest.TestCase):
    def test_explicit_not_found(self):
        llm = FakeLLM('{"found": false}')
        finder = CoordinateFinder(llm)
        with self.assertRaises(CoordinateNotFoundError):
            finder.find("shot.png", "a nonexistent widget")

    def test_unparseable_response(self):
        llm = FakeLLM("I have no idea what you mean.")
        finder = CoordinateFinder(llm)
        with self.assertRaises(CoordinateNotFoundError):
            finder.find("shot.png", "something")

    def test_out_of_range_coordinate_rejected(self):
        llm = FakeLLM('{"found": true, "x": 1500, "y": 20}')
        finder = CoordinateFinder(llm)
        with self.assertRaises(CoordinateNotFoundError):
            finder.find("shot.png", "something")

    def test_negative_coordinate_rejected(self):
        llm = FakeLLM('{"found": true, "x": -5, "y": 20}')
        finder = CoordinateFinder(llm)
        with self.assertRaises(CoordinateNotFoundError):
            finder.find("shot.png", "something")

    def test_non_numeric_coordinate_rejected(self):
        llm = FakeLLM('{"found": true, "x": "left", "y": 20}')
        finder = CoordinateFinder(llm)
        with self.assertRaises(CoordinateNotFoundError):
            finder.find("shot.png", "something")


class TestAsyncFind(unittest.TestCase):
    def test_afind_happy_path(self):
        llm = FakeLLM('{"found": true, "x": 100, "y": 200}')
        finder = CoordinateFinder(llm)

        coord = asyncio.run(finder.afind("shot.png", "a link"))

        self.assertEqual((coord.x_norm, coord.y_norm), (100.0, 200.0))

    def test_afind_not_found(self):
        llm = FakeLLM('{"found": false}')
        finder = CoordinateFinder(llm)

        async def run():
            with self.assertRaises(CoordinateNotFoundError):
                await finder.afind("shot.png", "a link")

        asyncio.run(run())


class TestOverridesForwarded(unittest.TestCase):
    def test_image_detail_and_overrides_forwarded(self):
        llm = FakeLLM('{"found": true, "x": 1, "y": 1}')
        finder = CoordinateFinder(llm, image_detail="high")

        finder.find("shot.png", "x", temperature=0.0)

        call = llm.calls[0]
        self.assertEqual(call["overrides"]["image_detail"], "high")
        self.assertEqual(call["overrides"]["temperature"], 0.0)


if __name__ == "__main__":
    unittest.main()
