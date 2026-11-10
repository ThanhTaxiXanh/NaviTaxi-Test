"""Executable test cases for input validation and release blocking."""
import gzip
import hashlib
import json
import struct
import tempfile
import unittest
from pathlib import Path

from pipeline.vietnam_sovereignty_validator import (
    PMTilesError,
    audit_inventory,
    read_pmtiles_header_and_metadata,
    validate_reference,
    validate_release,
    validate_style,
)


def make_fixture(path: Path, layers=("roads",)) -> tuple[int, str]:
    payload = gzip.compress(json.dumps({
        "vector_layers": [{"id": name, "fields": {"name_vi": "String"}} for name in layers]
    }).encode("utf-8"))
    header = bytearray(127)
    header[:8] = b"PMTiles\\x03"
    struct.pack_into("<QQ", header, 24, 127, len(payload))
    header[97] = 2
    header[99] = 1
    header[100] = 0
    header[101] = 12
    struct.pack_into("<iiii", header, 102,
                     1020000000, 80000000, 1090000000, 230000000)
    blob = bytes(header) + payload
    path.write_bytes(blob)
    return len(blob), hashlib.sha256(blob).hexdigest()


class PMTilesInspectionTests(unittest.TestCase):
    def test_valid_minimal_metadata(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "roads.pmtiles"
            make_fixture(path)
            metadata = read_pmtiles_header_and_metadata(path)
            self.assertEqual(metadata["source_layers"], ["roads"])
            self.assertEqual(metadata["bbox_wgs84"], [102, 8, 109, 23])
            self.assertEqual(metadata["maxzoom"], 12)

    def test_invalid_magic_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "bad.pmtiles"
            make_fixture(path)
            content = bytearray(path.read_bytes())
            content[0] = 0
            path.write_bytes(content)
            with self.assertRaises(PMTilesError):
                read_pmtiles_header_and_metadata(path)

    def test_wrong_checksum_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "roads.pmtiles"
            size, _ = make_fixture(path)
            inventory = {"archives": [{
                "filename": path.name,
                "bytes": size,
                "sha256": "0" * 64,
                "source_layer": "roads"
            }]}
            findings, _ = audit_inventory(inventory, Path(folder))
            self.assertIn("HASH_MISMATCH", [item.code for item in findings])

    def test_missing_layer_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "roads.pmtiles"
            size, sha = make_fixture(path)
            inventory = {"archives": [{
                "filename": path.name,
                "bytes": size,
                "sha256": sha,
                "source_layer": "buildings"
            }]}
            findings, _ = audit_inventory(inventory, Path(folder))
            self.assertIn("LAYER_MISSING", [item.code for item in findings])

    def test_path_traversal_is_rejected(self):
        findings, _ = audit_inventory(
            {"archives": [{"filename": "../secret.pmtiles"}]}, Path("/tmp")
        )
        self.assertEqual(findings[0].code, "UNSAFE_FILENAME")


class SovereigntyP0Tests(unittest.TestCase):
    def test_no_approved_reference_never_passes(self):
        findings = validate_reference({"status": "pending", "features": []})
        self.assertIn("REFERENCE_PENDING", [item.code for item in findings])
        self.assertEqual(sum(x.code == "MISSING_REFERENCE" for x in findings), 3)

    def test_style_without_island_and_sea_layers_fails(self):
        findings = validate_style({
            "version": 8,
            "sources": {},
            "layers": [{"id": "background", "type": "background"}]
        })
        self.assertEqual(
            sum(x.code == "ISLAND_SEA_LAYER_MISSING" for x in findings), 3
        )

    def test_ambiguous_claim_text_is_flagged(self):
        findings = validate_style({
            "version": 8,
            "sources": {},
            "layers": [],
            "metadata": {"claims": "nine-dash line"}
        })
        self.assertIn("SUSPECT_STYLE_TEXT", [item.code for item in findings])

    def test_current_repository_blocks_release(self):
        repo_root = Path(__file__).resolve().parents[2]
        findings = validate_release(repo_root)
        codes = {item.code for item in findings}
        self.assertIn("RELEASE_BLOCKED", codes)
        self.assertIn("FULL_P0_ENGINE_INCOMPLETE", codes)
        self.assertIn("VISUAL_NOT_APPROVED", codes)


if __name__ == "__main__":
    unittest.main()
