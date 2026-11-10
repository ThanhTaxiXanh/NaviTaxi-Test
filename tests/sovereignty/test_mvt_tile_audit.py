"""MVT structural and semantic intake tests, not sovereign release tests."""
import gzip
import unittest

from pipeline.mvt_tile_audit import (
    MVTAuditError, decompress_mvt, geometry_points, sample_positions,
    scan_mvt_tile, uint,
)


def varint(n):
    output = bytearray()
    while n >= 128:
        output.append((n & 127) | 128)
        n >>= 7
    output.append(n)
    return bytes(output)


def pb_field(n, wire, data):
    prefix = varint((n << 3) | wire)
    return prefix + (
        varint(data) if wire == 0 else varint(len(data)) + data
    )


def tile(label="Hoàng Sa", geometry=b"\x09\x02\x02"):
    feature = (
        pb_field(2, 2, b"\x00\x00")
        + pb_field(3, 0, 1)
        + pb_field(4, 2, geometry)
    )
    layer = (
        pb_field(1, 2, b"roads")
        + pb_field(2, 2, feature)
        + pb_field(3, 2, b"name_vi")
        + pb_field(4, 2, pb_field(1, 2, label.encode("utf-8")))
        + pb_field(5, 0, 4096)
        + pb_field(15, 0, 2)
    )
    return pb_field(3, 2, layer)


class MVTTests(unittest.TestCase):
    def test_decodes_real_mvt_wire_layout(self):
        stats = scan_mvt_tile(tile(), "roads")
        self.assertEqual(stats["features"], 1)
        self.assertEqual(stats["coordinates"], 1)
        self.assertEqual(stats["named_properties_checked"], 1) if (
            "named_properties_checked" in stats
        ) else self.assertEqual(stats["name_fields"], 1)

    def test_review_string_is_only_an_alert(self):
        stats = scan_mvt_tile(tile("Sansha"), "roads")
        self.assertEqual(stats["suspect_labels"][0]["label"], "Sansha")

    def test_wrong_source_layer_and_truncated_geometry_rejected(self):
        with self.assertRaises(MVTAuditError):
            scan_mvt_tile(tile(), "buildings")
        with self.assertRaises(MVTAuditError):
            scan_mvt_tile(tile(geometry=b"\x09\x02"), "roads")

    def test_bad_geometry_opcode_rejected(self):
        with self.assertRaises(MVTAuditError):
            geometry_points(memoryview(b"\x08"), 1, 4096)

    def test_gzip_corruption_rejected(self):
        payload = tile()
        self.assertEqual(decompress_mvt(gzip.compress(payload), 2), payload)
        with self.assertRaises(MVTAuditError):
            decompress_mvt(b"bad", 2)

    def test_overflow_varint_rejected(self):
        with self.assertRaises(MVTAuditError):
            uint(b"\xff" * 11, 0)

    def test_sampling_is_deterministic(self):
        self.assertEqual(sample_positions(8, 3), [0, 3, 7])
        self.assertEqual(sample_positions(8, 0), list(range(8)))


if __name__ == "__main__":
    unittest.main()
