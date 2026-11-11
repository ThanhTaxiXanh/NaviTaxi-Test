"""Native MVT scanner parity and source fingerprint, no P0 acceptance."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "tools/native_mvt_scan.cpp"
REPORT = ROOT / "docs/audits/2026-11-11-all-archives-full-structural-scan.json"


def varint(n):
    out = bytearray()
    while n >= 128:
        out.append((n & 127) | 128)
        n >>= 7
    out.append(n)
    return bytes(out)


def field(n, wire, val):
    head = varint((n << 3) | wire)
    return head + (varint(val) if wire == 0 else varint(len(val)) + val)


def fixture(path: Path, geom: bytes):
    feature = field(2, 2, b"\x00\x00") + field(3, 0, 1) + field(4, 2, geom)
    layer = (
        field(1, 2, b"roads") +
        field(2, 2, feature) +
        field(3, 2, b"name_vi") +
        field(4, 2, field(1, 2, "Hoàng Sa".encode())) +
        field(5, 0, 4096) + field(15, 0, 2)
    )
    tile = field(3, 2, layer)
    entry = b"".join(varint(v) for v in (1, 0, 1, len(tile), 1))
    meta = b"{}"
    header = bytearray(127)
    header[:8] = b"PMTiles\x03"
    struct.pack_into("<11Q", header, 8,
                     127, len(entry), 127 + len(entry), len(meta),
                     127 + len(entry) + len(meta), 0,
                     127 + len(entry) + len(meta), len(tile), 1, 1, 1)
    header[97:100] = b"\x01\x01\x01"
    path.write_bytes(header + entry + meta + tile)


class NativeMVTTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.native_executable = os.environ.get("NATIVE_MVT_SCANNER")
        if not cls.native_executable:
            raise RuntimeError("CI must set NATIVE_MVT_SCANNER to its built binary")

    def test_committed_source_matches_recorded_scanner_fingerprint(self):
        record = json.loads(REPORT.read_text(encoding="utf-8"))
        actual = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
        self.assertEqual(actual, record["methodology"]["local_scanner_source_sha256"])

    def test_synthetic_vector_tile_is_readable_but_p0_blocked(self):
        # MoveTo(1), delta (2048, 2048): world center at z0.
        geom = b"\x09\x80\x20\x80\x20"
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "synthetic.pmtiles"
            fixture(archive, geom)
            result = subprocess.run(
                [self.native_executable, str(archive), "roads"],
                check=True, text=True, capture_output=True,
            )
            scanned = json.loads(result.stdout)
            self.assertEqual(scanned["index_entries"], 1)
            self.assertEqual(scanned["point"], 1)
            self.assertEqual(scanned["line"], 0)
            self.assertEqual(scanned["polygon"], 0)
            self.assertEqual(scanned["vertices"], 1)
            self.assertEqual(scanned["name_fields"], 1)
            self.assertEqual(scanned["p0_status"], "BLOCKED")
            for coordinate in scanned["bbox"]:
                self.assertAlmostEqual(coordinate, 0, places=6)

    def test_rejects_wrong_source_layer_and_truncated_geometry(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "synthetic.pmtiles"
            fixture(archive, b"\x09\x80\x20\x80\x20")
            mismatched = subprocess.run(
                [self.native_executable, str(archive), "buildings"],
                text=True, capture_output=True,
            )
            self.assertNotEqual(mismatched.returncode, 0)
            fixture(archive, b"\x09\x02")
            damaged = subprocess.run(
                [self.native_executable, str(archive), "roads"],
                text=True, capture_output=True,
            )
            self.assertNotEqual(damaged.returncode, 0)


if __name__ == "__main__":
    unittest.main()
