import copy
import importlib.util
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "skills/blueprint-space/scripts/space.py"
spec = importlib.util.spec_from_file_location("space", MODULE)
space = importlib.util.module_from_spec(spec)
spec.loader.exec_module(space)


def fixture():
    return {
        "title": "Test studio",
        "units": "m",
        "floor": [[0, 0], [10, 0], [10, 8], [0, 8]],
        "rooms": [
            {
                "id": "studio",
                "name": "Studio",
                "outline": [[0, 0], [10, 0], [10, 8], [0, 8]],
            }
        ],
        "walls": [
            {
                "id": "north",
                "start": [0, 0],
                "end": [10, 0],
                "height": 2.8,
                "thickness": 0.15,
            }
        ],
        "doors": [
            {"id": "entry", "wall": "north", "offset": 1, "width": 1, "height": 2.1}
        ],
        "windows": [],
        "furniture": [
            {
                "id": "desk",
                "name": "Writing desk",
                "type": "desk",
                "room": "studio",
                "position": [5, 4],
                "size": [1.4, 0.7, 0.75],
                "rotation": 0,
            }
        ],
    }


class SpaceChecks(unittest.TestCase):
    def warnings(self, model):
        space.validate(model)
        return "\n".join(space.layout_warnings(model))

    def test_valid_and_deterministic(self):
        model = fixture()
        before = copy.deepcopy(model)
        page, warnings = space.build(model)
        self.assertEqual(warnings, [])
        self.assertEqual(page, space.build(model)[0])
        self.assertEqual(model, before)
        embedded = re.search(
            r'<script type="application/json" id="space-model">(.*?)</script>',
            page,
            re.DOTALL,
        )[1]
        restored = json.loads(embedded)
        self.assertEqual(restored, model)
        self.assertEqual(space.build(restored)[0], page)
        self.assertNotRegex(page, r'<(?:script|link)[^>]+(?:src|href)="https?://')
        self.assertIn("data:font/woff2;base64,", page)
        self.assertIn("three.js", page)

    def test_overlap_and_rotated_overlap(self):
        model = fixture()
        other = copy.deepcopy(model["furniture"][0])
        other.update(id="desk-2", position=[5.8, 4], rotation=45)
        model["furniture"].append(other)
        self.assertIn("overlap", self.warnings(model))

    def test_aligned_overlap_and_disjoint_concave_rooms(self):
        a = [[0, 0], [4, 0], [4, 1], [0, 1]]
        b = [[2, 0], [6, 0], [6, 1], [2, 1]]
        self.assertTrue(space.overlap(a, b))
        u = [[0, 0], [6, 0], [6, 6], [4, 6], [4, 2], [2, 2], [2, 6], [0, 6]]
        gap = [[2.5, 3], [3.5, 3], [3.5, 5], [2.5, 5]]
        self.assertFalse(space.overlap(u, gap))
        self.assertFalse(space.overlap(a, [[4, 0], [6, 0], [6, 1], [4, 1]]))

    def test_numeric_round_trip(self):
        model = fixture()
        model["furniture"][0]["rotation"] = 0.0
        model["furniture"][0]["position"] = [5.0, 4.0]
        model["metadata"] = {"small": 0.000001, "zero": -0.0}
        page, _ = space.build(model)
        normalized = copy.deepcopy(model)
        normalized["furniture"][0]["rotation"] = 0
        normalized["furniture"][0]["position"] = [5, 4]
        normalized["metadata"]["zero"] = 0
        self.assertEqual(page, space.build(normalized)[0])
        model["metadata"] = {"2": "second", "1": "first"}
        reordered = copy.deepcopy(model)
        reordered["metadata"] = {"1": "first", "2": "second"}
        self.assertEqual(space.build(model)[0], space.build(reordered)[0])
        model["metadata"]["too_large"] = 9007199254740993
        with self.assertRaises(ValueError):
            space.validate(model)

    def test_rotated_outside_room(self):
        model = fixture()
        model["furniture"][0].update(position=[0.5, 4], rotation=45)
        self.assertIn("outside room", self.warnings(model))

    def test_blocked_door(self):
        model = fixture()
        model["furniture"][0]["position"] = [1.5, 0.7]
        self.assertIn("blocks door entry", self.warnings(model))

    def test_wall_collision(self):
        model = fixture()
        model["furniture"][0]["position"] = [5, 0.2]
        self.assertIn("intersects wall north", self.warnings(model))

    def test_unknown_ids(self):
        model = fixture()
        model["furniture"][0]["room"] = "missing"
        model["doors"][0]["wall"] = "missing"
        warnings = self.warnings(model)
        self.assertIn("unknown room missing", warnings)
        self.assertIn("unknown wall missing", warnings)

    def test_invalid_schema(self):
        for mutate in (
            lambda m: m.update(units="ft"),
            lambda m: m["furniture"][0].update(size=[0, 1, 1]),
            lambda m: m["furniture"][0].update(rotation=float("nan")),
            lambda m: m["furniture"][0].update(position=[True, 2]),
            lambda m: m["furniture"][0].update(type="spaceship"),
            lambda m: m["furniture"][0].update(id="studio"),
            lambda m: m.update(floor=[[0, 0], [10, 8], [10, 0], [0, 8]]),
            lambda m: m["walls"][0].update(end=[0, 0]),
            lambda m: m["rooms"][0].update(color="url(https://example.com)"),
        ):
            model = fixture()
            mutate(model)
            with self.subTest(model=model), self.assertRaises(ValueError):
                space.validate(model)

    def test_openings_out_of_wall_and_overlap(self):
        model = fixture()
        model["doors"][0]["offset"] = 9.5
        self.assertIn("outside wall", self.warnings(model))
        model["doors"][0]["offset"] = 1
        model["windows"] = [
            {
                "id": "glazing",
                "wall": "north",
                "offset": 1.5,
                "width": 2,
                "height": 1,
                "sill": 1,
            }
        ]
        self.assertIn("openings entry and glazing overlap", self.warnings(model))

    def test_concave_floor(self):
        model = fixture()
        model["floor"] = [
            [0, 0],
            [10, 0],
            [10, 8],
            [6, 8],
            [6, 2],
            [4, 2],
            [4, 8],
            [0, 8],
        ]
        self.assertIn("outside floor", self.warnings(model))

    def test_overlapping_rooms(self):
        model = fixture()
        model["rooms"].append(
            {
                "id": "other",
                "name": "Other",
                "outline": [[4, 3], [7, 3], [7, 6], [4, 6]],
            }
        )
        self.assertIn("rooms studio and other overlap", self.warnings(model))

    def test_html_is_escaped_and_metadata_preserved(self):
        model = fixture()
        payload = "</script><img src=x onerror=alert(1)>{{TITLE}}"
        model["title"] = payload
        model["furniture"][0]["name"] = payload
        model["metadata"] = {"review": payload}
        page, _ = space.build(model)
        self.assertNotIn(payload, page)
        self.assertIn("&lt;/script&gt;", page)
        embedded = re.search(r'id="space-model">(.*?)</script>', page, re.DOTALL)[1]
        self.assertEqual(json.loads(embedded), model)


if __name__ == "__main__":
    unittest.main()
