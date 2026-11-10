"""Full local POI scan report: integrity of metadata, NEVER P0 approval."""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]


class POIFullLocalScanReportTests(unittest.TestCase):
    def test_full_poi_index_report_matches_quarantine_inventory(self):
        report = json.loads(
            (ROOT / "docs/audits/2026-11-10-poi-full-index-spatial.json")
            .read_text(encoding="utf-8")
        )
        inventory = json.loads(
            (ROOT / "assets/manifests/ingestion_inventory.json")
            .read_text(encoding="utf-8")
        )
        source = next(
            item for item in inventory["archives"]
            if item["source_layer"] == "points_of_interest"
        )
        self.assertEqual(report["archive"], source["filename"])
        self.assertEqual(report["archive_sha256"], source["sha256"])
        self.assertEqual(report["p0_status"], "BLOCKED")
        self.assertTrue(report["complete_index_entry_coverage"])
        self.assertEqual(report["indexed_tile_entries"], 4209)
        self.assertEqual(report["examined_payload_entries"], 4209)
        self.assertEqual(report["missing_entry_ranges"], [])
        self.assertEqual(report["reference_gate"]["review_overlay"], "NOT_RUN")
        self.assertEqual(len(report["review_candidates"]), 2)
        self.assertEqual(
            sum(report["geometry_counts"].values()), 357628
        )
        self.assertTrue(
            all(
                item["field"] in ("name_en", "name_latin")
                for item in report["review_candidates"]
            )
        )


if __name__ == "__main__":
    unittest.main()
