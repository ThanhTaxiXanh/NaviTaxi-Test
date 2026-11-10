#!/usr/bin/env python3
"""Combine hash-bound, contiguous MVT spatial-audit chunks. Never releases P0.

Chunk reports are diagnostics, not signed proof or independently approved GIS.
The merge rejects gaps/overlaps by default and enforces consistent archive SHA.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re


class SpatialMergeError(ValueError):
    pass


def _bbox_union(first, second):
    if second is None:
        return first
    if not isinstance(second, list) or len(second) != 4 or not all(
        isinstance(value, (int, float)) and math.isfinite(value) for value in second
    ) or second[0] > second[2] or second[1] > second[3]:
        raise SpatialMergeError("Malformed geographic envelope")
    if first is None:
        return list(second)
    return [min(first[0], second[0]), min(first[1], second[1]),
            max(first[2], second[2]), max(first[3], second[3])]


def merge_spatial_ranges(
    paths: list[Path], *, require_complete: bool = True,
    inventory: Path | None = None,
) -> dict:
    if not paths:
        raise SpatialMergeError("Missing input chunk reports")
    reports = []
    hashes = []
    for path in paths:
        raw = path.read_bytes()
        try:
            item = json.loads(raw)
        except (ValueError, UnicodeError) as exc:
            raise SpatialMergeError(f"Invalid JSON in {path.name}") from exc
        if not isinstance(item, dict):
            raise SpatialMergeError("Chunk must contain a JSON object")
        if (item.get("scanner_schema_version") != 1 or
                item.get("p0_status") != "BLOCKED" or
                item.get("status") not in (
                    "RANGE_GEOMETRY_DIAGNOSTICS_NOT_P0",
                    "ALL_INDEX_ENTRIES_GEOMETRY_DIAGNOSTICS_NOT_P0",
                )):
            raise SpatialMergeError("Unsupported or unsafe chunk audit status")
        selection = item.get("selection") or {}
        if selection.get("mode") != "contiguous_range":
            raise SpatialMergeError("Only explicit contiguous scan ranges can merge")
        start = selection.get("start_entry")
        end = selection.get("end_entry_exclusive")
        total = item.get("indexed_tile_entries")
        count = item.get("examined_payload_entries")
        if not all(type(n) is int for n in (start, end, total, count)) or not (
            0 <= start < end <= total and end - start == count
        ):
            raise SpatialMergeError("Invalid or inconsistent range coordinates")
        sha = item.get("archive_sha256")
        if not isinstance(sha, str) or not re.fullmatch(r"[a-f0-9]{64}", sha):
            raise SpatialMergeError("Archive checksum not present in chunk")
        ref = item.get("reference_gate")
        if not isinstance(ref, dict) or ref.get("review_overlay") != "NOT_RUN":
            raise SpatialMergeError("Chunk reference audit is inconsistent")
        reports.append(item)
        hashes.append({"filename": path.name, "sha256": hashlib.sha256(raw).hexdigest()})

    reports.sort(key=lambda item: item["selection"]["start_entry"])
    anchor = reports[0]
    keys = (
        "archive", "archive_sha256", "archive_size_bytes",
        "source_layer", "indexed_tile_entries", "addressed_tiles_in_index",
        "reference_gate",
    )
    if any(item.get(key) != anchor.get(key) for item in reports for key in keys):
        raise SpatialMergeError("Chunk reports refer to different data or reference states")
    if not isinstance(anchor.get("archive_size_bytes"), int) or anchor["archive_size_bytes"] < 127:
        raise SpatialMergeError("Archive size is missing")

    if inventory is not None:
        manifest = json.loads(inventory.read_text(encoding="utf-8"))
        entries = {item["filename"]: item for item in manifest["archives"]}
        source = entries.get(anchor["archive"])
        if (manifest.get("status") != "quarantine" or source is None or
                source["sha256"] != anchor["archive_sha256"] or
                source["bytes"] != anchor["archive_size_bytes"] or
                source["source_layer"] != anchor["source_layer"]):
            raise SpatialMergeError("Chunk data does not match the quarantine inventory")

    bbox = None
    stats = Counter()
    zooms = Counter()
    candidates = []
    names = vertices = paths_checked = entries_scanned = 0
    cursor = 0
    gaps = []
    for item in reports:
        selection = item["selection"]
        start, end = selection["start_entry"], selection["end_entry_exclusive"]
        if start < cursor:
            raise SpatialMergeError("Overlapping chunk ranges")
        if start > cursor:
            gaps.append([cursor, start])
        cursor = end
        entries_scanned += item["examined_payload_entries"]
        counts = item.get("geometry_counts") or {}
        if not isinstance(counts, dict):
            raise SpatialMergeError("Missing geometry histogram")
        for key in ("point", "line", "polygon"):
            value = counts.get(key, 0)
            if type(value) is not int or value < 0:
                raise SpatialMergeError("Invalid geometry histogram")
            stats[key] += value
        for field, counter in (
            ("vertices_projected", "vertices"),
            ("paths_checked", "paths"),
            ("name_fields_checked", "names"),
        ):
            val = item.get(field)
            if type(val) is not int or val < 0:
                raise SpatialMergeError(f"Invalid {field}")
            if counter == "vertices":
                vertices += val
            elif counter == "paths":
                paths_checked += val
            else:
                names += val
        bbox = _bbox_union(bbox, item.get("decoded_feature_envelope_wgs84_unwrapped"))
        for zoom, count in (item.get("zoom_distribution") or {}).items():
            if not isinstance(zoom, str) or type(count) is not int or count < 0:
                raise SpatialMergeError("Invalid zoom histogram")
            zooms[zoom] += count
        for hit in item.get("review_candidates", [])[:max(0, 20 - len(candidates))]:
            candidates.append(hit)
    if cursor < anchor["indexed_tile_entries"]:
        gaps.append([cursor, anchor["indexed_tile_entries"]])
    complete = not gaps and entries_scanned == anchor["indexed_tile_entries"]
    if require_complete and not complete:
        raise SpatialMergeError(f"Incomplete scan: unscanned entry ranges {gaps}")
    return {
        "schema_version": 1,
        "status": "COMPLETE_INDEX_GEOMETRY_DIAGNOSTICS_NOT_P0" if complete
                  else "PARTIAL_INDEX_GEOMETRY_DIAGNOSTICS_NOT_P0",
        "p0_status": "BLOCKED",
        "archive": anchor["archive"],
        "archive_sha256": anchor["archive_sha256"],
        "source_layer": anchor["source_layer"],
        "indexed_tile_entries": anchor["indexed_tile_entries"],
        "addressed_tiles_in_index": anchor["addressed_tiles_in_index"],
        "examined_payload_entries": entries_scanned,
        "complete_index_entry_coverage": complete,
        "missing_entry_ranges": gaps,
        "geometry_counts": dict(stats),
        "vertices_projected": vertices,
        "paths_checked": paths_checked,
        "name_fields_checked": names,
        "decoded_feature_envelope_wgs84_unwrapped": bbox,
        "zoom_distribution": dict(zooms),
        "review_candidates": candidates,
        "reference_gate": anchor["reference_gate"],
        "chunk_report_checksums": hashes,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reports", nargs="+", type=Path)
    parser.add_argument("--allow-partial", action="store_true")
    parser.add_argument("--inventory", type=Path, default=(
        Path(__file__).resolve().parents[1] / "assets/manifests/ingestion_inventory.json"
    ))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        merged = merge_spatial_ranges(
            args.reports, require_complete=not args.allow_partial,
            inventory=args.inventory,
        )
        code = 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        merged = {"status": "MERGE_FAILED", "p0_status": "BLOCKED", "error": str(exc)}
        code = 1
    text = json.dumps(merged, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
