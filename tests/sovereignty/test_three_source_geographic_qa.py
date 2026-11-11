"""Read-only source comparison reports must never activate unreviewed maps."""
import json
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[2]
class ThreeSourceQATests(unittest.TestCase):
    def test_review_is_not_p0(self):
        d=json.loads((ROOT/"docs/audits/2026-11-11-three-source-qa.json").read_text())
        self.assertFalse(d["p0_pass"])
        self.assertFalse(d["maplibre_activation_allowed"])
        self.assertEqual(d["reference_features"],34)
        self.assertEqual(d["uniquely_matched_names"],33)
        self.assertEqual(d["github_duplicate_label"],"Lạng Sơn")
        self.assertEqual(d["github_missing_label"],"Đồng Tháp")
        self.assertTrue(d["source_image_not_georeferenced"])
        release=json.loads((ROOT/"assets/geo/approved_reference.json").read_text())
        self.assertEqual(release["status"],"pending")
if __name__=="__main__": unittest.main()
