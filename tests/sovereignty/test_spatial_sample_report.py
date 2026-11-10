"""Committed 128-tile sample is quarantine evidence, never P0 approval."""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]


class SpatialSampleReportTests(unittest.TestCase):
    def test_report_matches_intake_inventory_and_cannot_claim_release(self):
        audit = json.loads((ROOT / "docs/audits/2026-11-10-feature-spatial-sample.json").read_text())
        inventory = json.loads((ROOT / "assets/manifests/ingestion_inventory.json").read_text())
        self.assertFalse(audit["p0_pass"])
        self.assertEqual(audit["reference_gate"], "REFERENCE_PENDING")
        self.assertEqual(audit["status"], "INTAKE_SAMPLED_GEOMETRY_DIAGNOSTICS_NOT_P0")
        reference = {entry["filename"]: entry for entry in inventory["archives"]}
        self.assertEqual(len(audit["archives"]), len(reference))
        for record in audit["archives"]:
            source = reference[record["filename"]]
            self.assertEqual(record["sha256"], source["sha256"])
            self.assertEqual(record["source_layer"], source["source_layer"])
            self.assertEqual(record["sampled_entries"], 128)
            self.assertGreater(record["total_index_entries"], 128)
            self.assertGreater(sum(record["geometry_counts"].values()), 0)
            self.assertEqual(len(record["envelope_wgs84_unwrapped"]), 4)

    def test_approved_reference_remains_pending(self):
        reference = json.loads((ROOT / "assets/geo/approved_reference.json").read_text())
        self.assertEqual(reference["status"], "pending")
        self.assertEqual(reference["source_documents"], [])
        self.assertEqual(reference["features"], [])


if __name__ == "__main__":
    unittest.main()
