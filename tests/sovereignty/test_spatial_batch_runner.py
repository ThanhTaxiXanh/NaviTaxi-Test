"""Check resumption, integrity failures and fail-closed P0 status."""
import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

from pipeline.spatial_batch_runner import BatchAuditError, run_batch


class ResumableBatchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.archive = self.root / "test_archive.pmtiles"
        self.archive.write_bytes(b"PMTiles\x03" + b"\0" * 256)
        self.inventory = self.root / "inventory.json"
        self.inventory.write_text(json.dumps({
            "status": "quarantine",
            "archives": [{
                "filename": self.archive.name,
                "bytes": self.archive.stat().st_size,
                "sha256": hashlib.sha256(self.archive.read_bytes()).hexdigest(),
                "source_layer": "roads",
            }],
        }))
        self.calls = []

    def fake_scan(self, path, layer, *, max_tiles, start_entry, entry_count):
        self.assertEqual(max_tiles, 0)
        self.calls.append((start_entry, entry_count))
        return {
            "scanner_schema_version": 1,
            "archive": path.name,
            "archive_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "archive_size_bytes": path.stat().st_size,
            "source_layer": layer,
            "selection": {
                "mode": "contiguous_range", "start_entry": start_entry,
                "end_entry_exclusive": start_entry + entry_count,
            },
            "indexed_tile_entries": 5,
            "addressed_tiles_in_index": 5,
            "examined_payload_entries": entry_count,
            "p0_status": "BLOCKED",
            "status": "RANGE_GEOMETRY_DIAGNOSTICS_NOT_P0",
            "geometry_counts": {
                "point": entry_count, "line": 0, "polygon": 0,
            },
            "vertices_projected": entry_count,
            "paths_checked": entry_count,
            "name_fields_checked": entry_count,
            "zoom_distribution": {"0": entry_count},
            "decoded_feature_envelope_wgs84_unwrapped": [0, 0, 2, 2],
            "review_candidates": [],
            "reference_gate": {
                "status": "REFERENCE_PENDING", "review_overlay": "NOT_RUN",
            },
        }

    def run_it(self, max_new_chunks, chunk_size=2):
        return run_batch(
            self.archive, inventory=self.inventory,
            output_dir=self.root / "audit-output", chunk_size=chunk_size,
            max_new_chunks=max_new_chunks, scan=self.fake_scan,
            inspect_index=lambda _: SimpleNamespace(tile_entries=5),
        )

    def test_resume_until_complete_without_duplicate_scan(self):
        first = self.run_it(1)
        self.assertEqual(first["checked_index_entries"], 2)
        self.assertEqual(first["missing_entry_ranges"], [[2, 5]])
        second = self.run_it(1)
        self.assertEqual(second["resumed_chunks"], 1)
        self.assertEqual(second["missing_entry_ranges"], [[4, 5]])
        last = self.run_it(None)
        self.assertTrue(last["complete_index_entry_coverage"])
        self.assertEqual(last["checked_index_entries"], 5)
        self.assertEqual(last["p0_status"], "BLOCKED")
        self.assertEqual(self.calls, [(0, 2), (2, 2), (4, 1)])
        merged = json.loads(
            (self.root / "audit-output" / "test_archive" / "merged.json")
            .read_text()
        )
        self.assertEqual(merged["geometry_counts"]["point"], 5)
        self.assertEqual(merged["p0_status"], "BLOCKED")

    def test_corrupted_checkpoint_refused(self):
        self.run_it(1)
        path = (self.root / "audit-output" / "test_archive" /
                "range_00000000_00000002.json")
        record = json.loads(path.read_text())
        record["selection"]["start_entry"] = 1
        path.write_text(json.dumps(record))
        with self.assertRaises(BatchAuditError):
            self.run_it(1)
        self.assertEqual(self.calls, [(0, 2)])

    def test_modified_archive_refused(self):
        self.run_it(1)
        with self.archive.open("ab") as stream:
            stream.write(b"modified")
        with self.assertRaises(BatchAuditError):
            self.run_it(1)

    def test_bad_configuration_and_inventory_refused(self):
        with self.assertRaises(BatchAuditError):
            self.run_it(1, chunk_size=0)
        self.inventory.write_text(json.dumps({
            "status": "approved", "archives": [],
        }))
        with self.assertRaises(BatchAuditError):
            self.run_it(1)

    def test_zero_budget_explicitly_partial(self):
        result = self.run_it(0)
        self.assertEqual(result["checked_index_entries"], 0)
        self.assertEqual(result["missing_entry_ranges"], [[0, 5]])
        self.assertFalse(result["complete_index_entry_coverage"])
        self.assertEqual(result["p0_status"], "BLOCKED")


if __name__ == "__main__":
    unittest.main()
