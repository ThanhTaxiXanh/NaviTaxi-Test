"""14 offshore name references are not proof of exposed-land polygons."""
import copy
import json
from pathlib import Path
import unittest

from pipeline.resolve_island_reference_gaps import (
    TYPE_BY_ID, CORROBORATION, classify_name, validate_anchor_catalog
)


class IslandReferenceGapsTests(unittest.TestCase):
    def setUp(self):
        self.c = json.loads(CORROBORATION.read_text(encoding="utf-8"))

    def test_4_independent_named_island_points_are_within_1km(self):
        result = validate_anchor_catalog(self.c)
        self.assertEqual(set(result), {"B48", "B15", "B3", "C123"})
        self.assertLess(result["B48"], .2)
        self.assertEqual(result["B15"], 0.)
        self.assertLess(result["B3"], .9)
        self.assertLess(result["C123"], .3)

    def test_14_outliers_are_explicitly_classified(self):
        data = json.loads((Path(__file__).resolve().parents[2] /
            "docs/audits/2026-11-11-tt33-183-island-point-screen.json"
        ).read_text(encoding="utf-8"))
        records = data["review_candidates_over_5km"]
        self.assertEqual({r["reference_id"] for r in records}, set(TYPE_BY_ID))
        counts = {kind: sum(x == kind for x in TYPE_BY_ID.values())
                  for kind in set(TYPE_BY_ID.values())}
        self.assertEqual(counts, {
            "named_island":4, "submerged_bank":3,
            "regional_label":1, "reef_or_shoal":6
        })
        for item in records:
            self.assertEqual(classify_name(item["name"]), TYPE_BY_ID[item["reference_id"]])

    def test_datum_or_release_forgery_rejected(self):
        for key, val in [
            ("p0_pass", True),
            ("maplibre_activation_allowed", True),
            ("source_datum", "WGS84"),
            ("official_pdf_sha256", "0"*64),
        ]:
            changed = copy.deepcopy(self.c)
            changed[key] = val
            with self.assertRaises(ValueError):
                validate_anchor_catalog(changed)
        changed = copy.deepcopy(self.c)
        changed["independent_positions"][0]["independent_position"] = [1, 1]
        with self.assertRaises(ValueError):
            validate_anchor_catalog(changed)


if __name__ == "__main__":
    unittest.main()
