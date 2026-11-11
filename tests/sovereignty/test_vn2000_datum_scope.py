"""Evidence about EPSG area-of-use limitations must not imply P0 approval."""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "docs/audits/2026-11-11-vn2000-datum-offshore-scope.json"


class OffshoreDatumScopeEvidenceTests(unittest.TestCase):
    def test_onshore_operations_are_not_adopted_for_island_points(self):
        report = json.loads(REPORT.read_text(encoding="utf-8"))
        self.assertEqual(report["official_points_reviewed"], 183)
        self.assertFalse(report["offshore_approved_transform_found"])
        self.assertEqual(report["outliers_remaining_beyond_5km_even_under_diagnostic_shift"], 14)
        self.assertEqual(report["outlier_count"], 14)
        self.assertFalse(report["p0_pass"])
        self.assertFalse(report["maplibre_activation_allowed"])
        for op in report["transform_operations"]:
            self.assertEqual(op["official_points_inside_area_of_use"], 0)
            self.assertFalse(op["usable_as_approved_offshore_transform"])
            self.assertLess(op["displacement_max_m_diagnostic_only"], 500)
            self.assertTrue(any(
                "not officially adopted" in scope.lower()
                for scope in op["declared_scopes"]
            ))

    def test_release_reference_remains_pending(self):
        pending = json.loads(
            (ROOT / "assets/geo/approved_reference.json").read_text()
        )
        self.assertEqual(pending["status"], "pending")


if __name__ == "__main__":
    unittest.main()
