#!/usr/bin/env python3
"""Inspect decoded PMTiles/MVT feature geometry in WGS84.

Diagnostic spatial metadata ONLY. No maritime boundaries, claims or sovereign
reference geometry are inferred. P0 remains blocked, even after a full scan.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import struct

from pipeline.mvt_tile_audit import (
    MAX_FEATURES_PER_LAYER,
    MVTAuditError,
    REVIEW_KEYS,
    REVIEW_WORDS,
    decompress_mvt,
    fields,
    packed,
    sample_positions,
    string_value,
    utf8,
)
from pipeline.pmtiles_directory_audit import (
    DirectoryAuditError,
    audit_directory_tree,
    decode_directory,
)
from pipeline.tile_coordinates import slippy_to_lonlat, tileid_to_zxy


@dataclass(frozen=True)
class GeometryExtent:
    geometry_type: str
    vertices: int
    paths: int
    bbox_wgs84: tuple[float, float, float, float]


def geometry_wgs84(geometry, geom_type: int, extent: int, tile_id: int) -> GeometryExtent:
    """Decode MVT commands, validate paths, and project each vertex to WGS84.

    Web Mercator tile buffers may legitimately extend beyond nominal tile
    footprints. The longitude envelope is therefore *unwrapped* and must not
    be treated as a boundary polygon or official geographic claim.
    """
    kinds = {1: "point", 2: "line", 3: "polygon"}
    if geom_type not in kinds or not (1 <= extent <= 65536):
        raise MVTAuditError("Unsupported MVT geometry type or extent")
    z, tile_x, tile_y = tileid_to_zxy(tile_id)
    x = y = 0
    vertices = paths = 0
    in_path = False
    has_line = False
    closed = False
    polygon_line_vertices = 0
    minimum_x = minimum_y = float("inf")
    maximum_x = maximum_y = float("-inf")
    values = iter(packed(geometry))

    def validate_previous() -> None:
        if not in_path:
            return
        if geom_type == 2 and not has_line:
            raise MVTAuditError("LineString component lacks LineTo")
        if geom_type == 3 and (not closed or polygon_line_vertices < 2):
            raise MVTAuditError("Polygon ring is unclosed or has too few vertices")

    try:
        for word in values:
            command, count = word & 7, word >> 3
            if command not in (1, 2, 7) or count < 1:
                raise MVTAuditError("Invalid MVT geometry command")
            if command == 1:
                if geom_type != 1 and count != 1:
                    raise MVTAuditError("Line/polygon MoveTo must occur once per component")
                validate_previous()
                paths += 1
                in_path = True
                has_line = closed = False
                polygon_line_vertices = 0
            elif command == 2:
                if geom_type == 1 or not in_path or closed:
                    raise MVTAuditError("LineTo without an open path")
                has_line = True
                polygon_line_vertices += count
            else:
                if geom_type != 3 or count != 1 or not in_path or closed:
                    raise MVTAuditError("Invalid polygon ClosePath")
                if polygon_line_vertices < 2:
                    raise MVTAuditError("Polygon ring needs three or more vertices")
                closed = True
                in_path = False
                continue

            for _ in range(count):
                dx, dy = next(values), next(values)
                x += (dx >> 1) ^ -(dx & 1)
                y += (dy >> 1) ^ -(dy & 1)
                if abs(x) > 64 * extent or abs(y) > 64 * extent:
                    raise MVTAuditError("Tile-local coordinates exceed safety limit")
                minimum_x, minimum_y = min(minimum_x, x), min(minimum_y, y)
                maximum_x, maximum_y = max(maximum_x, x), max(maximum_y, y)
                vertices += 1
    except StopIteration as exc:
        raise MVTAuditError("Truncated MVT geometry coordinate pair") from exc

    if not paths or not vertices:
        raise MVTAuditError("Empty MVT geometry")
    validate_previous()
    # The Web Mercator inverse is monotonic on each axis. Two opposite
    # extreme tile-local vertices give the exact union bbox; this avoids
    # expensive trig per vertex and keeps RAM independent of feature size.
    west, north = slippy_to_lonlat(
        z, tile_x + minimum_x / extent, tile_y + minimum_y / extent
    )
    east, south = slippy_to_lonlat(
        z, tile_x + maximum_x / extent, tile_y + maximum_y / extent
    )
    return GeometryExtent(
        geometry_type=kinds[geom_type],
        vertices=vertices,
        paths=paths,
        bbox_wgs84=(west, south, east, north),
    )


def _merge_boxes(a, b):
    if a is None:
        return b
    return (
        min(a[0], b[0]), min(a[1], b[1]),
        max(a[2], b[2]), max(a[3], b[3]),
    )


def tile_spatial_summary(tile: bytes, source_layer: str, tile_id: int) -> dict:
    """Inspect all feature geometries without materializing feature polygons."""
    totals = Counter()
    feature_box = None
    names_checked = 0
    flagged = []
    found_layer = False
    for number, wire, raw_layer in fields(tile):
        if number != 3:
            continue
        if wire != 2:
            raise MVTAuditError("Wrong Tile.layers wire type")
        name, version, extent = None, None, 4096
        features = []
        keys = []
        values = []
        for field, kind, raw in fields(raw_layer):
            if field == 1 and kind == 2:
                name = utf8(raw)
            elif field == 2 and kind == 2:
                features.append(raw)
                if len(features) > MAX_FEATURES_PER_LAYER:
                    raise MVTAuditError("Feature table exceeds maximum")
            elif field == 3 and kind == 2:
                keys.append(utf8(raw))
            elif field == 4 and kind == 2:
                values.append(string_value(raw))
            elif field == 5 and kind == 0:
                extent = raw
            elif field == 15 and kind == 0:
                version = raw
        if name != source_layer or version != 2 or not (1 <= extent <= 65536):
            raise MVTAuditError("Unexpected MVT source layer or version")
        if len(keys) > MAX_FEATURES_PER_LAYER or len(values) > MAX_FEATURES_PER_LAYER:
            raise MVTAuditError("Property table exceeds maximum")
        found_layer = True
        for feature in features:
            tags = []
            geom_type = geom_data = None
            for field, kind, raw in fields(feature):
                if field == 2 and kind == 2:
                    tags.extend(packed(raw))
                elif field == 3 and kind == 0:
                    geom_type = raw
                elif field == 4 and kind == 2:
                    geom_data = raw
            if geom_type is None or geom_data is None:
                raise MVTAuditError("Feature has no geometry")
            extent_data = geometry_wgs84(geom_data, geom_type, extent, tile_id)
            totals[extent_data.geometry_type] += 1
            totals["vertices"] += extent_data.vertices
            totals["paths"] += extent_data.paths
            feature_box = _merge_boxes(feature_box, extent_data.bbox_wgs84)
            if len(tags) % 2:
                raise MVTAuditError("Odd tag count")
            for i in range(0, len(tags), 2):
                key_index, value_index = tags[i : i + 2]
                if key_index >= len(keys) or value_index >= len(values):
                    raise MVTAuditError("Invalid tag index")
                key, value = keys[key_index], values[value_index]
                if isinstance(value, str) and (
                    key in REVIEW_KEYS or key.startswith("name:")
                ):
                    names_checked += 1
                    if REVIEW_WORDS.search(value) and len(flagged) < 20:
                        flagged.append({
                            "tile_id": str(tile_id),
                            "field": key,
                            "value": value[:160],
                            "feature_bbox_wgs84": list(extent_data.bbox_wgs84),
                        })
    if not found_layer:
        raise MVTAuditError("MVT tile has no expected source-layer")
    return {
        "geometry_counts": {k: totals[k] for k in ("point", "line", "polygon")},
        "vertices": totals["vertices"],
        "paths": totals["paths"],
        "feature_bbox_wgs84": list(feature_box) if feature_box else None,
        "name_fields_checked": names_checked,
        "review_candidates": flagged,
    }


def reference_gate(path: Path) -> dict:
    """Read reference status; self-declared approval never grants P0 PASS."""
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
        if obj.get("schema_version") != 1:
            raise ValueError("Unexpected official reference schema")
        if obj.get("status") != "approved":
            return {
                "status": "REFERENCE_PENDING",
                "review_overlay": "NOT_RUN",
                "reason": "Official geographic references are not approved",
            }
        if not obj.get("source_documents") or not obj.get("features"):
            raise ValueError("Claimed approval lacks source documents or geometry")
        return {
            "status": "REFERENCE_REQUIRES_INDEPENDENT_VERIFICATION",
            "review_overlay": "NOT_RUN",
            "reason": "Automatic claims cannot substitute verified geometry provenance",
        }
    except (OSError, ValueError, TypeError, AttributeError) as exc:
        return {
            "status": "REFERENCE_INVALID",
            "review_overlay": "NOT_RUN",
            "reason": str(exc),
        }


def scan_spatial_archive(
    path: Path, source_layer: str, max_tiles: int = 32,
    reference: Path | None = None,
    start_entry: int | None = None, entry_count: int | None = None,
) -> dict:
    indexed = audit_directory_tree(path)
    reference_file = reference or (
        Path(__file__).resolve().parents[1] / "assets/geo/approved_reference.json"
    )
    gate = reference_gate(reference_file)
    with path.open("rb") as stream:
        header = stream.read(127)
        sections = struct.unpack_from("<11Q", header, 8)
        stream.seek(sections[0])
        root = decode_directory(stream.read(sections[1]), header[97])
        entries = []
        for item in root:
            if item.run_length:
                entries.append(item)
            else:
                stream.seek(sections[4] + item.offset)
                entries.extend(decode_directory(stream.read(item.length), header[97]))
        if len(entries) != indexed.tile_entries:
            raise MVTAuditError("PMTiles directory mismatch")
        if start_entry is not None or entry_count is not None:
            if max_tiles != 0:
                raise ValueError("Range scans require --max-tiles 0")
            start = 0 if start_entry is None else start_entry
            count = len(entries) - start if entry_count is None else entry_count
            if start < 0 or start >= len(entries) or count <= 0 or start + count > len(entries):
                raise ValueError("Contiguous entry range is outside the PMTiles index")
            positions = range(start, start + count)
            selection = {
                "mode": "contiguous_range",
                "start_entry": start,
                "end_entry_exclusive": start + count,
            }
        else:
            positions = sample_positions(len(entries), max_tiles)
            selection = {"mode": "spread_sample", "max_tiles": max_tiles}
        geometries = Counter()
        bbox = None
        name_fields = vertices = paths = 0
        candidates = []
        zooms = Counter()
        for position in positions:
            entry = entries[position]
            zoom, _, _ = tileid_to_zxy(entry.tile_id)
            zooms[str(zoom)] += 1
            stream.seek(sections[6] + entry.offset)
            payload = decompress_mvt(stream.read(entry.length), header[98])
            try:
                summary = tile_spatial_summary(payload, source_layer, entry.tile_id)
            except (MVTAuditError, ValueError) as exc:
                raise MVTAuditError(
                    f"{path.name}, tile_id={entry.tile_id}: {exc}"
                ) from exc
            geometries.update(summary["geometry_counts"])
            name_fields += summary["name_fields_checked"]
            vertices += summary["vertices"]
            paths += summary["paths"]
            if summary["feature_bbox_wgs84"]:
                bbox = _merge_boxes(bbox, summary["feature_bbox_wgs84"])
            candidates.extend(summary["review_candidates"][: max(0, 20 - len(candidates))])
    digest = hashlib.sha256()
    with path.open("rb") as archive_stream:
        for block in iter(lambda: archive_stream.read(1024 * 1024), b""):
            digest.update(block)
    return {
        "scanner_schema_version": 1,
        "archive": path.name,
        "archive_sha256": digest.hexdigest(),
        "archive_size_bytes": path.stat().st_size,
        "source_layer": source_layer,
        "selection": selection,
        "indexed_tile_entries": indexed.tile_entries,
        "addressed_tiles_in_index": indexed.addressed_tiles,
        "sampled_payload_entries": len(positions),
        "examined_payload_entries": len(positions),
        "sampling": len(positions) < len(entries),
        "geometry_counts": dict(geometries),
        "vertices_projected": vertices,
        "paths_checked": paths,
        "name_fields_checked": name_fields,
        "decoded_feature_envelope_wgs84_unwrapped": list(bbox) if bbox else None,
        "zoom_distribution": dict(zooms),
        "review_candidates": candidates,
        "reference_gate": gate,
        "p0_status": "BLOCKED",
        "status": (
            "ALL_INDEX_ENTRIES_GEOMETRY_DIAGNOSTICS_NOT_P0"
            if len(positions) == len(entries) else (
                "RANGE_GEOMETRY_DIAGNOSTICS_NOT_P0"
                if selection["mode"] == "contiguous_range"
                else "SAMPLED_GEOMETRY_DIAGNOSTICS_NOT_P0"
            )
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--layer", required=True)
    parser.add_argument("--max-tiles", type=int, default=32)
    parser.add_argument("--start-entry", type=int)
    parser.add_argument("--entry-count", type=int)
    parser.add_argument("--reference", type=Path)
    parser.add_argument("--report", type=Path)
    options = parser.parse_args()
    try:
        report = scan_spatial_archive(
            options.archive, options.layer, options.max_tiles,
            options.reference, options.start_entry, options.entry_count,
        )
        code = 0
    except (OSError, ValueError, DirectoryAuditError, MVTAuditError) as exc:
        report = {
            "archive": options.archive.name,
            "status": "SCAN_FAILED",
            "p0_status": "BLOCKED",
            "error": str(exc),
        }
        code = 1
    encoded = json.dumps(report, ensure_ascii=False, indent=2)
    if options.report:
        options.report.parent.mkdir(parents=True, exist_ok=True)
        options.report.write_text(encoded + "\n", encoding="utf-8")
    print(encoded)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
