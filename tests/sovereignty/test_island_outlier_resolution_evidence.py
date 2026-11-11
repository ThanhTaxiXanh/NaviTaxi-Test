"""Pin the 14-classification evidence, never promote political boundaries."""
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[2]

class OffshoreFourteenResolutionTests(unittest.TestCase):
    def test_all_14_are_classified_but_no_land_polygons_approved(self):
        x=json.loads((ROOT/"docs/audits/2026-11-11-14-island-outlier-resolution.json").read_text(encoding="utf-8"))
        self.assertEqual(len(x["points"]),14)
        self.assertEqual(x["feature_counts"],{"named_island":4,"reef_or_shoal":6,
                                             "submerged_bank":3,"regional_label":1})
        self.assertEqual(x["island_points_independently_corroborated_within_1km"],4)
        self.assertEqual(x["non_land_or_label_classification_explained"],4)
        self.assertEqual(x["verified_island_or_reef_land_polygons"],0)
        self.assertEqual({p["id"] for p in x["points"]},
                         {"B3","B15","B37","B39","B48","B49","B50",
                          "C71","C109","C122","C123","C128","C129","C131"})
        self.assertTrue(all(not p["allowed_as_physical_land_polygon"] for p in x["points"]))
        self.assertFalse(x["p0_pass"])
        self.assertFalse(x["maplibre_activation_allowed"])

    def test_release_gate_stays_independent(self):
        release=json.loads((ROOT/"assets/manifests/map_release.json").read_text())
        reference=json.loads((ROOT/"assets/geo/approved_reference.json").read_text())
        self.assertFalse(release["p0_pass"])
        self.assertEqual(reference["status"],"pending")

if __name__=="__main__":
    unittest.main()
