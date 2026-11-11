"""Full TT33/2024 technical screening evidence is never a border approval."""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]


class OfficialPointScreenEvidenceTests(unittest.TestCase):
    def test_all_183_points_recorded_and_cross_checked(self):
        path = ROOT / "docs/audits/2026-11-11-tt33-183-island-point-screen.json"
        report = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(report["points_checked"], 183)
        groups = report["source_provinces"]
        self.assertEqual([row["reference_points"] for row in groups], [50, 133])
        self.assertEqual(sum(row["inside"] for row in groups), 141)
        self.assertEqual(sum(row["inside_or_within_2km"] for row in groups), 156)
        self.assertEqual(sum(row["outside_5km"] for row in groups), 14)
        self.assertEqual(report["inside_source_polygon"], 141)
        self.assertEqual(report["outside_5km"], 14)
        self.assertEqual(report["outside_10km"], 11)
        self.assertEqual(len(report["review_candidates_over_5km"]), 14)
        self.assertFalse(report["p0_pass"])
        self.assertFalse(report["maplibre_activation_allowed"])

    def test_no_authoritative_boundary_approval(self):
        report = json.loads(
            (ROOT / "docs/audits/2026-11-11-tt33-183-island-point-screen.json")
            .read_text(encoding="utf-8")
        )
        self.assertEqual(report["verification_matrix"]["official_2025_province_boundary_vectors"], "NOT_OBTAINED")
        self.assertEqual(report["verification_matrix"]["official_national_or_maritime_border_vectors"], "NOT_OBTAINED")
        source = json.loads((ROOT / "assets/geo/approved_reference.json").read_text())
        self.assertEqual(source["status"], "pending")
        self.assertFalse(source.get("p0_pass", False))


if __name__ == "__main__":
    unittest.main()
