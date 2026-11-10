#!/usr/bin/env python3
"""Independent PMTiles v3 directory/tree integrity audit (standard library).

Validates index paths, tile-data offsets, sorted tile IDs, and declared counts.
It does not decode MVT feature geometry/labels or certify territorial depiction.
"""
from __future__ import annotations

import argparse
import gzip
import json
import struct
from dataclasses import asdict, dataclass
from pathlib import Path


class DirectoryAuditError(ValueError):
    """Malformed or unsafe PMTiles index."""


@dataclass(frozen=True)
class Entry:
    tile_id: int
    run_length: int
    length: int
    offset: int


@dataclass(frozen=True)
class DirectoryReport:
    filename: str
    root_entries: int
    leaf_entries: int
    tile_entries: int
    addressed_tiles: int
    minimum_tile_id: int
    maximum_tile_id: int
    status: str = "INDEX_OK_NOT_P0"


def _read_uvarint(data: bytes, index: int) -> tuple[int, int]:
    value = 0
    for shift in range(0, 70, 7):
        if index >= len(data):
            raise DirectoryAuditError("Truncated directory varint")
        byte = data[index]
        index += 1
        if shift == 63 and byte > 1:
            raise DirectoryAuditError("Directory varint overflow")
        value |= (byte & 0x7F) << shift
        if byte < 128:
            return value, index
    raise DirectoryAuditError("Directory varint too long")


def decode_directory(payload: bytes, compression: int) -> list[Entry]:
    if compression == 2:
        try:
            payload = gzip.decompress(payload)
        except (OSError, EOFError) as exc:
            raise DirectoryAuditError("Broken gzip directory") from exc
    elif compression != 1:
        raise DirectoryAuditError("Unsupported internal compression")

    pos = 0
    count, pos = _read_uvarint(payload, pos)
    if count > 2_000_000:
        raise DirectoryAuditError("Directory entry count exceeds safety limit")
    if count == 0:
        return [] if pos == len(payload) else _error("Trailing empty directory data")

    ids: list[int] = []
    current = 0
    for i in range(count):
        delta, pos = _read_uvarint(payload, pos)
        current += delta
        if i and current <= ids[-1]:
            raise DirectoryAuditError("Tile IDs must be strictly increasing")
        ids.append(current)

    runs = []
    lengths = []
    for _ in range(count):
        value, pos = _read_uvarint(payload, pos)
        runs.append(value)
    for _ in range(count):
        value, pos = _read_uvarint(payload, pos)
        if value <= 0:
            raise DirectoryAuditError("Zero-length directory payload")
        lengths.append(value)

    offsets: list[int] = []
    previous = 0
    previous_length = 0
    for length in lengths:
        coded, pos = _read_uvarint(payload, pos)
        offset = previous + previous_length if coded == 0 else coded - 1
        offsets.append(offset)
        previous = offset
        previous_length = length
    if pos != len(payload):
        raise DirectoryAuditError("Trailing directory bytes")
    return [
        Entry(ids[i], runs[i], lengths[i], offsets[i])
        for i in range(count)
    ]


def _error(message: str):
    raise DirectoryAuditError(message)


def audit_directory_tree(path: Path) -> DirectoryReport:
    with path.open("rb") as stream:
        header = stream.read(127)
        if len(header) != 127 or header[:8] != b"PMTiles\x03":
            raise DirectoryAuditError("PMTiles v3 magic/header missing")

        (root_offset, root_length, metadata_offset, metadata_length,
         leaf_offset, leaf_length, tile_offset, tile_length,
         addressed_expected, entries_expected, _,) = struct.unpack_from(
            "<QQQQQQQQQQQ", header, 8
        )
        file_size = path.stat().st_size
        if not (
            127 <= root_offset < metadata_offset <= leaf_offset <= tile_offset
            and root_length > 0
            and root_offset + root_length <= metadata_offset
            and metadata_length > 0
            and metadata_offset + metadata_length <= leaf_offset
            and leaf_offset + leaf_length <= tile_offset
            and tile_offset + tile_length <= file_size
        ):
            raise DirectoryAuditError("Invalid overlapping/out-of-file PMTiles sections")

        internal_compression = header[97]
        max_zoom = header[101]
        if internal_compression not in (1, 2) or max_zoom > 22:
            raise DirectoryAuditError("Unsupported archive metadata/zoom")
        tile_id_limit = (4 ** (max_zoom + 1) - 1) // 3

        stream.seek(root_offset)
        root = decode_directory(stream.read(root_length), internal_compression)
        if not root:
            raise DirectoryAuditError("Empty root directory")

        previous_id = -1
        tile_count = 0
        addressed_count = 0
        leaf_count = 0
        minimum_id = -1
        maximum_id = -1
        for root_entry in root:
            if root_entry.run_length == 0:
                if root_entry.offset + root_entry.length > leaf_length:
                    raise DirectoryAuditError("Leaf directory outside leaf section")
                stream.seek(leaf_offset + root_entry.offset)
                leaves = decode_directory(
                    stream.read(root_entry.length), internal_compression
                )
                leaf_count += len(leaves)
                if not leaves or leaves[0].tile_id != root_entry.tile_id:
                    raise DirectoryAuditError("Incorrect leaf directory tile range")
                tile_items = leaves
            else:
                tile_items = [root_entry]

            for entry in tile_items:
                if (
                    entry.run_length == 0
                    or entry.tile_id <= previous_id
                    or entry.tile_id + entry.run_length > tile_id_limit
                    or entry.offset + entry.length > tile_length
                ):
                    raise DirectoryAuditError("Invalid, unsorted or out-of-range tile entry")
                if minimum_id < 0:
                    minimum_id = entry.tile_id
                maximum_id = entry.tile_id + entry.run_length - 1
                previous_id = maximum_id
                tile_count += 1
                addressed_count += entry.run_length

        if tile_count != entries_expected or addressed_count != addressed_expected:
            raise DirectoryAuditError("Directory count mismatch with PMTiles header")

        return DirectoryReport(
            filename=path.name,
            root_entries=len(root),
            leaf_entries=leaf_count,
            tile_entries=tile_count,
            addressed_tiles=addressed_count,
            minimum_tile_id=minimum_id,
            maximum_tile_id=maximum_id,
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archives", type=Path, nargs="+")
    args = parser.parse_args()
    summaries = []
    errors = []
    for archive in args.archives:
        try:
            summaries.append(asdict(audit_directory_tree(archive)))
        except (OSError, DirectoryAuditError) as exc:
            errors.append({"archive": archive.name, "error": str(exc)})
    print(json.dumps(
        {"status": "INTAKE_INDEX_OK_NOT_P0" if not errors else "INDEX_FAILED",
         "archives": summaries, "errors": errors},
        ensure_ascii=False, indent=2,
    ))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
