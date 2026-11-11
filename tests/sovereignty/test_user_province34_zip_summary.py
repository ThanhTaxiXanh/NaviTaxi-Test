"""User ZIP QA metadata contract; source GeoJSON stays outside repository."""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "docs/audits/2026-11-11-user-province34-zip-summary.json"
CATALOG = ROOT / "assets/geo/province34_names_2025.json"


class UserZipQaSummaryTests(unittest.TestCase):
    def test_uploaded_zip_metadata_only_and_p0_stays_blocked(self):
        report = json.loads(REPORT.read_text(encoding="utf-8"))
        catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
        self.assertEqual(len(catalog["units"]), 34)
        self.assertEqual(report["geojson_file_count"], 34)
        self.assertEqual(report["feature_count"], 34)
        self.assertEqual(report["matched_current_province_names_and_codes"], 34)
        self.assertEqual(report["zip_bytes"], 8710932)
        self.assertEqual(
            report["zip_sha256"],
            "51779d2585600ec053827a60890ba61cd2192f19b5ee153d38be18a2611d24cd",
        )
        self.assertGreater(report["checked_vertices"], 1_000_000)
        self.assertEqual(report["provincial_polygon_area_overlaps_gt_1e_minus_9_sq_degree"], 0)
        self.assertEqual(len(report["flagged_area_mismatches"]), 2)
        self.assertEqual(
            {item["code"] for item in report["flagged_area_mismatches"]},
            {"56", "96"},
        )
        self.assertEqual(
            {item["code"] for item in report["flagged_remote_polygon_components"]},
            {"48", "56"},
        )
        self.assertFalse(report["maplibre_activation_allowed"])
        self.assertFalse(report["p0_pass"])
        self.assertIn("QUARANTINE", report["disposition"])


if __name__ == "__main__":
    unittest.main()
