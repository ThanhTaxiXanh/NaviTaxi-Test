"""Synthetic index decoding tests; do not assert full sovereignty P0."""
import gzip
import unittest

from pipeline.pmtiles_directory_audit import (
    DirectoryAuditError,
    decode_directory,
)


def pack_varint(number: int) -> bytes:
    result = bytearray()
    while number >= 128:
        result.append((number & 127) | 128)
        number >>= 7
    result.append(number)
    return bytes(result)


def make_directory() -> bytes:
    # two tiles: id=2 length=12 offset=0, id=5 length=8 offset=12
    # encoded offsets 1 (absolute 0) and 0 (previous offset + length)
    return b"".join(
        pack_varint(value) for value in
        (2, 2, 3, 1, 1, 12, 8, 1, 0)
    )


class PMTilesDirectoryTests(unittest.TestCase):
    def test_decodes_uncompressed_and_gzip_index(self):
        for compression, data in (
            (1, make_directory()), (2, gzip.compress(make_directory()))
        ):
            with self.subTest(compression=compression):
                entries = decode_directory(data, compression)
                self.assertEqual(
                    [(row.tile_id, row.run_length, row.length, row.offset)
                     for row in entries],
                    [(2, 1, 12, 0), (5, 1, 8, 12)],
                )

    def test_detects_truncated_and_invalid_gzip(self):
        with self.assertRaises(DirectoryAuditError):
            decode_directory(make_directory()[:-1], 1)
        with self.assertRaises(DirectoryAuditError):
            decode_directory(b"bad-gzip", 2)

    def test_rejects_unsorted_ids(self):
        bad = b"".join(pack_varint(v) for v in (
            2, 3, 0, 1, 1, 12, 8, 1, 0
        ))
        with self.assertRaises(DirectoryAuditError):
            decode_directory(bad, 1)


if __name__ == "__main__":
    unittest.main()
