"""Geometry-to-WGS84 diagnostics: synthetic tests with no sovereignty geometry."""
import json
import hashlib
from pathlib import Path
import struct
import tempfile
import unittest

from pipeline.mvt_spatial_audit import (
    MVTAuditError,
    geometry_wgs84,
    reference_gate,
    scan_spatial_archive,
    tile_spatial_summary,
)


def varint(value):
    out = bytearray()
    while value >= 128:
        out.append((value & 127) | 128)
        value >>= 7
    out.append(value)
    return bytes(out)


def field(number, wire, value):
    key = varint((number << 3) | wire)
    if wire == 0:
        return key + varint(value)
    if wire == 2:
        return key + varint(len(value)) + value
    raise AssertionError("fixture only uses varint and length fields")


def coord(value):
    return varint(value * 2 if value >= 0 else -2 * value - 1)


def point_at_world_center():
    # MVT: MoveTo(1), dx=2048, dy=2048, z=0, extent=4096 => (0,0) WGS84.
    return b"\x09" + coord(2048) + coord(2048)


def mvt_point(label="NaviTaxi", geom=None):
    geom = geom if geom is not None else point_at_world_center()
    feat = field(2, 2, b"\x00\x00") + field(3, 0, 1) + field(4, 2, geom)
    layer = (
        field(1, 2, b"roads")
        + field(2, 2, feat)
        + field(3, 2, b"name_vi")
        + field(4, 2, field(1, 2, label.encode("utf-8")))
        + field(5, 0, 4096)
        + field(15, 0, 2)
    )
    return field(3, 2, layer)


def minimal_pmtiles(directory: Path, tile_payload: bytes) -> Path:
    """PMTiles v3 archive with one uncompressed MVT tile at z=0."""
    root = b"".join(varint(v) for v in (1, 0, 1, len(tile_payload), 1))
    meta = b"{}"
    root_offset = 127
    meta_offset = root_offset + len(root)
    leaf_offset = meta_offset + len(meta)
    header = bytearray(127)
    header[:8] = b"PMTiles\x03"
    struct.pack_into(
        "<11Q", header, 8,
        root_offset, len(root), meta_offset, len(meta),
        leaf_offset, 0, leaf_offset, len(tile_payload), 1, 1, 1,
    )
    header[97], header[98], header[99] = 1, 1, 1
    header[100], header[101] = 0, 0
    path = directory / "fixture.pmtiles"
    path.write_bytes(header + root + meta + tile_payload)
    return path


class MVTSpatialTests(unittest.TestCase):
    def test_decodes_world_center_and_bbox_without_invented_political_areas(self):
        result = geometry_wgs84(point_at_world_center(), 1, 4096, 0)
        self.assertEqual(result.geometry_type, "point")
        self.assertEqual(result.vertices, 1)
        self.assertAlmostEqual(result.bbox_wgs84[0], 0, places=8)
        self.assertAlmostEqual(result.bbox_wgs84[1], 0, places=8)
        self.assertAlmostEqual(result.bbox_wgs84[2], 0, places=8)
        self.assertAlmostEqual(result.bbox_wgs84[3], 0, places=8)

    def test_decodes_polyline_with_two_segments(self):
        # MoveTo(1) [2048,2048], LineTo(2) [+512,0] [0,-512].
        geometry = (
            b"\x09" + coord(2048) + coord(2048)
            + b"\x12" + coord(512) + coord(0) + coord(0) + coord(-512)
        )
        result = geometry_wgs84(geometry, 2, 4096, 0)
        self.assertEqual(result.vertices, 3)
        self.assertEqual(result.paths, 1)
        self.assertAlmostEqual(result.bbox_wgs84[0], 0, places=8)
        self.assertAlmostEqual(result.bbox_wgs84[2], 45, places=8)
        self.assertGreater(result.bbox_wgs84[3], 0)

    def test_polygon_closepath_and_multiple_rings(self):
        ring = (
            b"\x09" + coord(2048) + coord(2048)
            + b"\x12" + coord(256) + coord(0) + coord(0) + coord(256)
            + b"\x0f"
        )
        result = geometry_wgs84(ring + ring, 3, 4096, 0)
        self.assertEqual(result.vertices, 6)
        self.assertEqual(result.paths, 2)
        self.assertEqual(result.geometry_type, "polygon")

    def test_fails_closed_on_broken_geometry(self):
        with self.assertRaises(MVTAuditError):
            geometry_wgs84(b"\x09\x02", 1, 4096, 0)
        with self.assertRaises(MVTAuditError):
            geometry_wgs84(b"\x09\x00\x00", 3, 4096, 0)
        with self.assertRaises(MVTAuditError):
            geometry_wgs84(b"\x09\x00\x00\x0f", 3, 4096, 0)
        with self.assertRaises(MVTAuditError):
            geometry_wgs84(b"\x09\x00\x00\x09\x02\x02", 2, 4096, 0)

    def test_review_candidate_has_geographic_bbox_not_a_legal_finding(self):
        normal = tile_spatial_summary(mvt_point(), "roads", 0)
        self.assertEqual(normal["geometry_counts"]["point"], 1)
        self.assertEqual(normal["name_fields_checked"], 1)
        self.assertEqual(normal["review_candidates"], [])
        suspect = tile_spatial_summary(mvt_point("Sansha"), "roads", 0)
        self.assertEqual(suspect["review_candidates"][0]["value"], "Sansha")
        self.assertEqual(suspect["review_candidates"][0]["tile_id"], "0")
        self.assertEqual(suspect["review_candidates"][0]["feature_bbox_wgs84"], [0, 0, 0, 0])
        with self.assertRaises(MVTAuditError):
            tile_spatial_summary(mvt_point(), "buildings", 0)

    def test_reference_gate_pending_or_fake_approval_never_unblocks(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / "reference.json"
            p.write_text(json.dumps({"schema_version": 1, "status": "pending", "features": []}))
            self.assertEqual(reference_gate(p)["status"], "REFERENCE_PENDING")
            p.write_text(json.dumps({"schema_version": 1, "status": "approved", "features": []}))
            self.assertEqual(reference_gate(p)["status"], "REFERENCE_INVALID")
            p.write_text(json.dumps({
                "schema_version": 1, "status": "approved",
                "source_documents": [{"title": "synthetic test; NOT official"}],
                "features": [{"id": "fake"}],
            }))
            gate = reference_gate(p)
            self.assertEqual(gate["status"], "REFERENCE_REQUIRES_INDEPENDENT_VERIFICATION")
            self.assertEqual(gate["review_overlay"], "NOT_RUN")

    def test_reads_real_minimal_pmtiles_fixture_and_keeps_p0_blocked(self):
        with tempfile.TemporaryDirectory() as temp:
            archive = minimal_pmtiles(Path(temp), mvt_point())
            p = Path(temp) / "pending.json"
            p.write_text(json.dumps({"schema_version": 1, "status": "pending"}))
            result = scan_spatial_archive(archive, "roads", max_tiles=0, reference=p)
            self.assertEqual(result["indexed_tile_entries"], 1)
            self.assertEqual(result["sampled_payload_entries"], 1)
            self.assertFalse(result["sampling"])
            self.assertEqual(result["geometry_counts"], {"point": 1, "line": 0, "polygon": 0})
            self.assertEqual(result["p0_status"], "BLOCKED")
            self.assertEqual(result["reference_gate"]["status"], "REFERENCE_PENDING")
            self.assertEqual(result["decoded_feature_envelope_wgs84_unwrapped"], [0, 0, 0, 0])
            self.assertEqual(result["archive_sha256"], hashlib.sha256(archive.read_bytes()).hexdigest())
            self.assertEqual(result["scanner_schema_version"], 1)
            chunk = scan_spatial_archive(
                archive, "roads", max_tiles=0, reference=p,
                start_entry=0, entry_count=1,
            )
            self.assertEqual(chunk["selection"], {
                "mode": "contiguous_range", "start_entry": 0, "end_entry_exclusive": 1,
            })
            self.assertEqual(chunk["geometry_counts"], result["geometry_counts"])
            with self.assertRaises(ValueError):
                scan_spatial_archive(archive, "roads", max_tiles=0, reference=p,
                                     start_entry=1, entry_count=1)
            with self.assertRaises(ValueError):
                scan_spatial_archive(archive, "roads", max_tiles=3, reference=p,
                                     start_entry=0, entry_count=1)


if __name__ == "__main__":
    unittest.main()
