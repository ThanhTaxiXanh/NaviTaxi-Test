"""Check full MVT structural evidence remains consistent and non-releasing."""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
FULL = ROOT / "docs/audits/2026-11-11-all-archives-full-structural-scan.json"


class FullStructuralScanEvidenceTests(unittest.TestCase):
    def test_all_archives_match_catalog_and_are_unapproved(self):
        evidence = json.loads(FULL.read_text(encoding="utf-8"))
        intake = json.loads(
            (ROOT / "assets/manifests/ingestion_inventory.json")
            .read_text(encoding="utf-8")
        )
        self.assertFalse(evidence["p0_pass"])
        self.assertFalse(evidence["release_eligible"])
        self.assertEqual(evidence["source_status"], "quarantine")
        self.assertEqual(evidence["reference_status"], "pending")
        originals = {e["filename"]: e for e in intake["archives"]}
        self.assertEqual(
            {a["filename"] for a in evidence["archives"]},
            set(originals),
        )
        for archive in evidence["archives"]:
            expected = originals[archive["filename"]]
            self.assertEqual(archive["sha256"], expected["sha256"])
            self.assertEqual(archive["source_layer"], expected["source_layer"])
            self.assertEqual(archive["entries_scanned"], archive["index_entries"])
            self.assertEqual(archive["addressed_tiles"], archive["index_entries"])
            self.assertEqual(archive["run_length_gt_one_entries"], 0)
            self.assertEqual(
                sum(archive["geometry_counts"].values()),
                archive["feature_instances"],
            )
            self.assertGreater(archive["vertices_scanned"], 0)

    def test_totals_and_poi_python_parity(self):
        evidence = json.loads(FULL.read_text(encoding="utf-8"))
        totals = evidence["totals"]
        archives = evidence["archives"]
        for item in ("index_entries", "addressed_tiles", "feature_instances",
                     "vertices_scanned", "paths_scanned", "name_fields_scanned"):
            key = "index_entries" if item == "index_entries" else item
            self.assertEqual(
                totals[item],
                sum(archive[key] for archive in archives),
            )
        poi_native = next(
            a for a in archives if a["source_layer"] == "points_of_interest"
        )
        poi_python = json.loads(
            (ROOT / "docs/audits/2026-11-10-poi-full-index-spatial.json")
            .read_text(encoding="utf-8")
        )
        self.assertEqual(poi_native["geometry_counts"], poi_python["geometry_counts"])
        self.assertEqual(poi_native["vertices_scanned"], poi_python["vertices_projected"])
        self.assertEqual(poi_native["paths_scanned"], poi_python["paths_checked"])
        self.assertEqual(poi_native["name_fields_scanned"], poi_python["name_fields_checked"])
        self.assertEqual(poi_native["entries_scanned"], poi_python["examined_payload_entries"])

    def test_release_policy_stays_blocked(self):
        release = json.loads(
            (ROOT / "assets/manifests/map_release.json").read_text(encoding="utf-8")
        )
        self.assertEqual(release["status"], "blocked")
        self.assertFalse(release["p0_pass"])


if __name__ == "__main__":
    unittest.main()
