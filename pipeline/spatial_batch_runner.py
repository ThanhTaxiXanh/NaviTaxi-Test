#!/usr/bin/env python3
"""Resume quarantined PMTiles spatial diagnostics via bounded index-entry chunks.

This reports structural geometry evidence only. P0 remains BLOCKED.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Callable

from pipeline.mvt_spatial_audit import scan_spatial_archive
from pipeline.pmtiles_directory_audit import audit_directory_tree
from pipeline.spatial_report_merge import merge_spatial_ranges, SpatialMergeError


class BatchAuditError(ValueError):
    """Unexpected archive identity, invalid configuration or bad checkpoint."""


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_atomic(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent,
            prefix=".incoming-", suffix=".json", delete=False,
        ) as stream:
            temp = Path(stream.name)
            json.dump(record, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)


def inventory_entry(path: Path, filename: str) -> dict:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("status") != "quarantine":
        raise BatchAuditError("Only quarantine inventory may be audited")
    if not re.fullmatch(r"[a-z0-9_]+\.pmtiles", filename):
        raise BatchAuditError("Unsafe filename")
    for source in manifest.get("archives", []):
        if source.get("filename") == filename:
            if (type(source.get("bytes")) is not int or source["bytes"] < 127 or
                    not isinstance(source.get("sha256"), str) or
                    not re.fullmatch(r"[0-9a-f]{64}", source["sha256"]) or
                    not isinstance(source.get("source_layer"), str)):
                raise BatchAuditError("Invalid catalog entry")
            return source
    raise BatchAuditError("Archive is not in the quarantine catalog")


def verify_checkpoint(path: Path, start: int, end: int, total: int,
                      source: dict, checksum: str, inventory: Path) -> None:
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
        if (not isinstance(report, dict) or
                report.get("archive") != source["filename"] or
                report.get("source_layer") != source["source_layer"] or
                report.get("archive_sha256") != checksum or
                report.get("archive_size_bytes") != source["bytes"] or
                report.get("indexed_tile_entries") != total or
                report.get("examined_payload_entries") != end - start or
                report.get("p0_status") != "BLOCKED" or
                report.get("selection") != {
                    "mode": "contiguous_range",
                    "start_entry": start,
                    "end_entry_exclusive": end,
                }):
            raise BatchAuditError("Checkpoint does not match source and interval")
        merge_spatial_ranges([path], require_complete=False, inventory=inventory)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise BatchAuditError("Unsafe checkpoint: " + path.name) from exc


def run_batch(
    archive: Path, *, inventory: Path, output_dir: Path,
    chunk_size: int = 256, max_new_chunks: int | None = None,
    scan: Callable = scan_spatial_archive,
    inspect_index: Callable = audit_directory_tree,
) -> dict:
    if chunk_size < 1 or (max_new_chunks is not None and max_new_chunks < 0):
        raise BatchAuditError("Chunk size must be positive and budget nonnegative")
    source = inventory_entry(inventory, archive.name)
    if not archive.is_file() or archive.stat().st_size != source["bytes"]:
        raise BatchAuditError("Archive is missing or has the wrong byte size")
    checksum = file_sha256(archive)
    if checksum != source["sha256"]:
        raise BatchAuditError("Archive SHA-256 differs from quarantine inventory")
    total = inspect_index(archive).tile_entries
    if type(total) is not int or total < 1:
        raise BatchAuditError("Invalid PMTiles index entry count")

    workdir = output_dir / archive.stem
    workdir.mkdir(parents=True, exist_ok=True)
    checked = []
    new_chunks = resumed = 0
    ranges = [(start, min(start + chunk_size, total))
              for start in range(0, total, chunk_size)]
    for start, end in ranges:
        checkpoint = workdir / f"range_{start:08d}_{end:08d}.json"
        if checkpoint.exists():
            verify_checkpoint(checkpoint, start, end, total,
                              source, checksum, inventory)
            checked.append(checkpoint)
            resumed += 1
            continue
        if max_new_chunks is not None and new_chunks >= max_new_chunks:
            continue
        result = scan(archive, source["source_layer"], max_tiles=0,
                      start_entry=start, entry_count=end - start)
        write_atomic(checkpoint, result)
        try:
            verify_checkpoint(checkpoint, start, end, total,
                              source, checksum, inventory)
        except BatchAuditError:
            checkpoint.unlink(missing_ok=True)
            raise
        checked.append(checkpoint)
        new_chunks += 1

    if checked:
        merged = merge_spatial_ranges(
            checked, require_complete=False, inventory=inventory
        )
        write_atomic(workdir / "merged.json", merged)
    else:
        merged = {
            "complete_index_entry_coverage": False,
            "examined_payload_entries": 0,
            "missing_entry_ranges": [[0, total]],
        }

    state = {
        "schema_version": 1,
        "status": ("INDEX_CHUNKS_COMPLETE_NOT_P0"
                   if merged["complete_index_entry_coverage"]
                   else "INDEX_CHUNKS_PARTIAL_NOT_P0"),
        "p0_status": "BLOCKED",
        "archive": archive.name,
        "archive_sha256": checksum,
        "source_layer": source["source_layer"],
        "indexed_tile_entries": total,
        "chunk_size": chunk_size,
        "new_chunks": new_chunks,
        "resumed_chunks": resumed,
        "planned_chunks": len(ranges),
        "checked_chunks": len(checked),
        "checked_index_entries": merged["examined_payload_entries"],
        "complete_index_entry_coverage": merged["complete_index_entry_coverage"],
        "missing_entry_ranges": merged["missing_entry_ranges"],
        "reference_and_visual_p0": "NOT_APPROVED",
    }
    write_atomic(workdir / "batch_state.json", state)
    return state


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--chunk-size", type=int, default=256)
    parser.add_argument("--max-new-chunks", type=int)
    parser.add_argument("--inventory", type=Path, default=(
        Path(__file__).resolve().parents[1] /
        "assets/manifests/ingestion_inventory.json"
    ))
    parser.add_argument("--output-dir", type=Path, default=Path("audit-output"))
    args = parser.parse_args()
    try:
        result = run_batch(
            args.archive, inventory=args.inventory, output_dir=args.output_dir,
            chunk_size=args.chunk_size, max_new_chunks=args.max_new_chunks,
        )
        status = 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        result = {"status": "BATCH_FAILED", "p0_status": "BLOCKED",
                  "error": str(exc)}
        status = 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return status


if __name__ == "__main__":
    raise SystemExit(main())
