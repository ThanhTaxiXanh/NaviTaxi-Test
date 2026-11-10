#!/usr/bin/env python3
"""Decode MVT protobuf features/geometry in PMTiles; never asserts P0 PASS.

Deterministic, bounded sampling by default. Full payload scan: --max-tiles 0.
Suspicious labels are review candidates, NOT legal or GIS findings.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import struct
import zlib

from pipeline.pmtiles_directory_audit import (
    audit_directory_tree, decode_directory, DirectoryAuditError,
)

MAX_TILE_BYTES = 24 * 1024 * 1024
MAX_FEATURES_PER_LAYER = 2_000_000
REVIEW_WORDS = re.compile(
    r"(?i)(?:nine[ -]?dash|đường\s+(?:chín\s+đoạn|lưỡi\s+bò)|"
    r"sansha|xisha|nansha|south\s+china\s+sea)"
)
REVIEW_KEYS = {
    "name", "name_vi", "name:vi", "name_en", "name_latin",
    "adm0_name", "adm1_name", "adm2_name", "admin_name", "operator",
}


class MVTAuditError(ValueError):
    pass


def uint(buf, pos):
    value = 0
    for i in range(10):
        if pos >= len(buf):
            raise MVTAuditError("Truncated protobuf varint")
        octet = buf[pos]
        pos += 1
        if i == 9 and octet > 1:
            raise MVTAuditError("Overflowing protobuf varint")
        value |= (octet & 127) << (i * 7)
        if octet < 128:
            return value, pos
    raise MVTAuditError("Invalid protobuf varint")


def fields(data):
    buf = memoryview(data)
    pos = 0
    while pos < len(buf):
        key, pos = uint(buf, pos)
        number, wire = key >> 3, key & 7
        if number == 0:
            raise MVTAuditError("Protobuf field number 0")
        if wire == 0:
            value, pos = uint(buf, pos)
        elif wire in (1, 5):
            width = 8 if wire == 1 else 4
            if pos + width > len(buf):
                raise MVTAuditError("Truncated fixed-width protobuf field")
            value = buf[pos:pos + width]
            pos += width
        elif wire == 2:
            length, pos = uint(buf, pos)
            if length > len(buf) - pos:
                raise MVTAuditError("Invalid protobuf length")
            value = buf[pos:pos + length]
            pos += length
        else:
            raise MVTAuditError("Unsupported protobuf wire type")
        yield number, wire, value


def packed(buf):
    pos = 0
    while pos < len(buf):
        value, pos = uint(buf, pos)
        yield value


def utf8(value):
    try:
        return bytes(value).decode("utf-8")
    except UnicodeDecodeError as exc:
        raise MVTAuditError("Invalid MVT UTF-8") from exc


def string_value(data):
    found = False
    output = None
    for number, wire, value in fields(data):
        if 1 <= number <= 7:
            if found:
                raise MVTAuditError("Multiple typed values in one MVT Value")
            found = True
            correct_wire = 2 if number == 1 else (
                5 if number == 2 else 1 if number == 3 else 0
            )
            if wire != correct_wire:
                raise MVTAuditError("MVT value wire mismatch")
            if number == 1:
                output = utf8(value)
    if not found:
        raise MVTAuditError("Empty MVT Value")
    return output


def geometry_points(data, kind, extent):
    if kind not in (1, 2, 3):
        raise MVTAuditError("Invalid MVT geometry type")
    numbers = iter(packed(data))
    x = y = count = 0
    moved = lined = closed = False
    try:
        for command_word in numbers:
            command, times = command_word & 7, command_word >> 3
            if not times or command not in (1, 2, 7):
                raise MVTAuditError("Invalid MVT geometry opcode")
            if command == 7:
                if kind != 3 or not lined:
                    raise MVTAuditError("Unexpected ClosePath")
                closed = True
                continue
            if command == 2 and (kind == 1 or not moved):
                raise MVTAuditError("Unexpected LineTo")
            moved |= command == 1
            lined |= command == 2
            for _ in range(times):
                dx, dy = next(numbers), next(numbers)
                x += (dx >> 1) ^ -(dx & 1)
                y += (dy >> 1) ^ -(dy & 1)
                # Buffered tile coordinates may fall outside 0..extent.
                if abs(x) > 64 * extent or abs(y) > 64 * extent:
                    raise MVTAuditError("Unreasonable tile-local coordinate")
                count += 1
    except StopIteration as exc:
        raise MVTAuditError("Truncated MVT geometry") from exc
    if not moved or not count:
        raise MVTAuditError("Empty geometry")
    if kind == 2 and not lined:
        raise MVTAuditError("LineString has no LineTo")
    if kind == 3 and (not lined or not closed):
        raise MVTAuditError("Polygon is not closed")
    return count


def scan_mvt_tile(raw, expected_layer):
    layer_counts = Counter()
    feature_total = coordinate_total = name_total = 0
    suspicious = []
    for number, wire, raw_layer in fields(raw):
        if number != 3:
            continue
        if wire != 2:
            raise MVTAuditError("Invalid Tile.layers wire")
        name = None
        features = []
        keys = []
        values = []
        extent, version = 4096, None
        for field, kind, data in fields(raw_layer):
            if field == 1 and kind == 2:
                name = utf8(data)
            elif field == 2 and kind == 2:
                features.append(data)
                if len(features) > MAX_FEATURES_PER_LAYER:
                    raise MVTAuditError("Too many MVT features")
            elif field == 3 and kind == 2:
                keys.append(utf8(data))
            elif field == 4 and kind == 2:
                values.append(string_value(data))
            elif field == 5 and kind == 0:
                extent = data
            elif field == 15 and kind == 0:
                version = data
        if name != expected_layer or version != 2 or not (1 <= extent <= 65536):
            raise MVTAuditError("Unexpected layer name, MVT version or extent")
        if len(keys) > MAX_FEATURES_PER_LAYER or len(values) > MAX_FEATURES_PER_LAYER:
            raise MVTAuditError("MVT property table too large")
        layer_counts[name] += len(features)
        feature_total += len(features)
        for item in features:
            tags = []
            geom_kind = geom = None
            for field, kind, data in fields(item):
                if field == 2 and kind == 2:
                    tags.extend(packed(data))
                elif field == 3 and kind == 0:
                    geom_kind = data
                elif field == 4 and kind == 2:
                    geom = data
            if geom_kind is None or geom is None:
                raise MVTAuditError("Feature missing geometry")
            coordinate_total += geometry_points(geom, geom_kind, extent)
            if len(tags) % 2:
                raise MVTAuditError("Odd MVT feature tag count")
            for i in range(0, len(tags), 2):
                key_idx, val_idx = tags[i], tags[i + 1]
                if key_idx >= len(keys) or val_idx >= len(values):
                    raise MVTAuditError("Out-of-range feature tag")
                key, value = keys[key_idx], values[val_idx]
                if isinstance(value, str) and (key in REVIEW_KEYS or key.startswith("name:")):
                    name_total += 1
                    if REVIEW_WORDS.search(value) and len(suspicious) < 20:
                        suspicious.append({
                            "layer": name, "field": key, "label": value[:160],
                        })
    if not layer_counts:
        raise MVTAuditError("Tile has no vector layers")
    return {
        "features": feature_total,
        "coordinates": coordinate_total,
        "name_fields": name_total,
        "layers": dict(layer_counts),
        "suspect_labels": suspicious,
    }


def decompress_mvt(payload, method):
    if method == 1:
        if len(payload) > MAX_TILE_BYTES:
            raise MVTAuditError("Uncompressed tile too large")
        return payload
    if method != 2:
        raise MVTAuditError("Unsupported tile compression")
    try:
        decompressor = zlib.decompressobj(16 + zlib.MAX_WBITS)
        decoded = decompressor.decompress(payload, MAX_TILE_BYTES + 1)
        if len(decoded) > MAX_TILE_BYTES or not decompressor.eof or decompressor.unconsumed_tail:
            raise MVTAuditError("Oversized or truncated compressed tile")
        return decoded
    except zlib.error as exc:
        raise MVTAuditError("Damaged gzip MVT tile") from exc


def sample_positions(count, max_tiles):
    if max_tiles < 0:
        raise ValueError("max_tiles must not be negative")
    if max_tiles == 0 or max_tiles >= count:
        return list(range(count))
    if max_tiles == 1:
        return [0]
    return sorted({i * (count - 1) // (max_tiles - 1) for i in range(max_tiles)})


def audit_archive(path: Path, source_layer: str, max_tiles: int = 12):
    index_report = audit_directory_tree(path)  # always validates full index
    with path.open("rb") as stream:
        header = stream.read(127)
        sections = struct.unpack_from("<11Q", header, 8)
        root_offset, root_length = sections[0:2]
        leaf_offset, tile_offset = sections[4], sections[6]
        stream.seek(root_offset)
        entries = []
        for entry in decode_directory(stream.read(root_length), header[97]):
            if entry.run_length:
                entries.append(entry)
            else:
                stream.seek(leaf_offset + entry.offset)
                entries.extend(decode_directory(stream.read(entry.length), header[97]))
        if len(entries) != index_report.tile_entries:
            raise MVTAuditError("PMTiles index changed during audit")
        positions = sample_positions(len(entries), max_tiles)
        counts = Counter()
        features = coordinates = names = 0
        reviews = []
        for position in positions:
            entry = entries[position]
            stream.seek(tile_offset + entry.offset)
            blob = stream.read(entry.length)
            raw = decompress_mvt(blob, header[98])
            try:
                tile = scan_mvt_tile(raw, source_layer)
            except MVTAuditError as exc:
                raise MVTAuditError(f"tile {entry.tile_id}: {exc}") from exc
            counts.update(tile["layers"])
            features += tile["features"]
            coordinates += tile["coordinates"]
            names += tile["name_fields"]
            if len(reviews) < 20:
                for hit in tile["suspect_labels"][:20 - len(reviews)]:
                    reviews.append({"tile_id": str(entry.tile_id), **hit})
    sampled = len(positions) < len(entries)
    return {
        "archive": path.name,
        "source_layer": source_layer,
        "directory_entries": len(entries),
        "tiles_scanned": len(positions),
        "sampling": sampled,
        "features_scanned": features,
        "coordinates_checked": coordinates,
        "named_properties_checked": names,
        "layer_feature_counts": dict(counts),
        "suspect_label_examples": reviews,
        "status": "SAMPLE_OK_NOT_P0" if sampled else "FULL_MVT_STRUCTURAL_SCAN_NOT_P0",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--layer", required=True)
    parser.add_argument("--max-tiles", type=int, default=12)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    try:
        result = audit_archive(args.archive, args.layer, args.max_tiles)
        code = 0
    except (MVTAuditError, DirectoryAuditError, OSError, ValueError) as exc:
        result = {"status": "SCAN_FAILED", "archive": args.archive.name, "error": str(exc)}
        code = 1
    content = json.dumps(result, ensure_ascii=False, indent=2)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(content + "\n", encoding="utf-8")
    print(content)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
