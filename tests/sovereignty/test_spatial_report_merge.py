"""Refuse missing/overlapping or mismatched chunk provenance."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from pipeline.spatial_report_merge import SpatialMergeError, merge_spatial_ranges


def chunk(start, end, total=3, digest="a" * 64):
    return {
        "scanner_schema_version": 1,
        "status": "RANGE_GEOMETRY_DIAGNOSTICS_NOT_P0",
        "p0_status": "BLOCKED",
        "archive": "synthetic.pmtiles",
        "archive_sha256": digest,
        "archive_size_bytes": 500,
        "source_layer": "roads",
        "indexed_tile_entries": total,
        "addressed_tiles_in_index": total,
        "selection": {"mode": "contiguous_range", "start_entry": start,
                      "end_entry_exclusive": end},
        "examined_payload_entries": end - start,
        "geometry_counts": {"point": end - start, "line": 0, "polygon": 0},
        "vertices_projected": 10 * (end - start),
        "paths_checked": end - start,
        "name_fields_checked": end - start,
        "zoom_distribution": {"0": end - start},
        "decoded_feature_envelope_wgs84_unwrapped": [start, 0, end, 2],
        "review_candidates": [],
        "reference_gate": {"status": "REFERENCE_PENDING", "review_overlay": "NOT_RUN"},
    }


class SpatialMergeTests(unittest.TestCase):
    def setUp(self):
        self.ctx = tempfile.TemporaryDirectory()
        self.addCleanup(self.ctx.cleanup)
        self.root = Path(self.ctx.name)

    def write(self, name, data):
        path = self.root / name
        path.write_text(json.dumps(data), encoding="utf-8")
        return path

    def test_contiguous_scan_merges_and_stays_blocked(self):
        first = self.write("first.json", chunk(0, 1))
        second = self.write("second.json", chunk(1, 3))
        merged = merge_spatial_ranges([second, first], inventory=None)
        self.assertTrue(merged["complete_index_entry_coverage"])
        self.assertEqual(merged["examined_payload_entries"], 3)
        self.assertEqual(merged["geometry_counts"], {"point": 3, "line": 0, "polygon": 0})
        self.assertEqual(merged["decoded_feature_envelope_wgs84_unwrapped"], [0, 0, 3, 2])
        self.assertEqual(merged["p0_status"], "BLOCKED")
        self.assertEqual(len(merged["chunk_report_checksums"]), 2)

    def test_gap_fails_by_default_or_is_explicitly_partial(self):
        first = self.write("first.json", chunk(0, 1))
        third = self.write("third.json", chunk(2, 3))
        with self.assertRaises(SpatialMergeError):
            merge_spatial_ranges([first, third], inventory=None)
        partial = merge_spatial_ranges([first, third], inventory=None,
                                       require_complete=False)
        self.assertFalse(partial["complete_index_entry_coverage"])
        self.assertEqual(partial["missing_entry_ranges"], [[1, 2]])

    def test_overlap_and_digest_mismatch_are_rejected(self):
        first = self.write("first.json", chunk(0, 2))
        overlap = self.write("overlap.json", chunk(1, 3))
        with self.assertRaises(SpatialMergeError):
            merge_spatial_ranges([first, overlap], inventory=None)
        changed = self.write("changed.json", chunk(2, 3, digest="b" * 64))
        with self.assertRaises(SpatialMergeError):
            merge_spatial_ranges([first, changed], inventory=None)

    def test_incorrect_status_and_nonrange_are_rejected(self):
        invalid = chunk(0, 3)
        invalid["p0_status"] = "PASS"
        path = self.write("invalid.json", invalid)
        with self.assertRaises(SpatialMergeError):
            merge_spatial_ranges([path], inventory=None)
        invalid["p0_status"] = "BLOCKED"
        invalid["selection"]["mode"] = "spread_sample"
        path = self.write("invalid.json", invalid)
        with self.assertRaises(SpatialMergeError):
            merge_spatial_ranges([path], inventory=None)

    def test_manifest_identity_enforced(self):
        archive = chunk(0, 3)
        path = self.write("range.json", archive)
        inventory = self.write("inventory.json", {
            "status": "quarantine",
            "archives": [{"filename": "synthetic.pmtiles", "bytes": 500,
                          "sha256": "a" * 64, "source_layer": "roads"}],
        })
        self.assertTrue(merge_spatial_ranges([path], inventory=inventory)
                        ["complete_index_entry_coverage"])
        wrong = copy.deepcopy(archive)
        wrong["archive_size_bytes"] = 501
        wrong_path = self.write("changed.json", wrong)
        with self.assertRaises(SpatialMergeError):
            merge_spatial_ranges([wrong_path], inventory=inventory)


if __name__ == "__main__":
    unittest.main()
