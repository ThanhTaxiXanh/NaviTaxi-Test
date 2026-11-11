#!/usr/bin/env python3
"""VietnamSovereigntyValidator — fail-closed P0 intake/release preflight.

This first stage checks PMTiles archive integrity, metadata, manifest structure,
provenance and required evidence presence. It does NOT yet decode every MVT
feature or perform Android visual regression, and will not issue P0=PASS until
independent tile/geometry, visual and offline checks are implemented and reviewed.

No arbitrary island coordinates or legal maritime boundaries are generated.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import struct
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


REQUIRED_LABELS = {
    "hoang_sa": "Hoàng Sa",
    "truong_sa": "Trường Sa",
    "bien_dong": "Biển Đông",
}
REQUIRED_EVIDENCE = (
    "authoritative_geometry_review",
    "full_mvt_semantic_geometry_scan",
    "rendered_android_visual_regression",
    "online_offline_equivalence",
    "offline_airplane_mode",
    "cache_rollback",
    "license_and_attribution_review",
)
# All these checks need real artifacts and/or device validation, not string searches.
REQUIRED_VISUAL_VIEWS = (
    "vietnam-overview-light",
    "vietnam-overview-dark",
    "hoang-sa",
    "truong-sa",
    "bien-dong",
    "layers-on-off",
    "multi-zoom",
    "offline-airplane-mode",
    "network-restored",
    "style-update-rollback",
)


@dataclass(frozen=True)
class Finding:
    code: str
    message: str


class PMTilesError(ValueError):
    pass


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def read_pmtiles_header_and_metadata(path: Path) -> dict[str, Any]:
    """Parse the PMTiles v3 fixed header and gzip or raw JSON metadata.

    This is archive metadata inspection only, not MVT semantic decoding.
    """
    with path.open("rb") as stream:
        header = stream.read(127)
        if len(header) != 127 or header[:8] != b"PMTiles\x03":
            raise PMTilesError("Not a PMTiles v3 archive")
        metadata_offset, metadata_length = struct.unpack_from("<QQ", header, 24)
        file_size = path.stat().st_size
        if metadata_length == 0 or metadata_length > 16 * 1024 * 1024:
            raise PMTilesError("Invalid metadata length")
        if metadata_offset < 127 or metadata_offset + metadata_length > file_size:
            raise PMTilesError("Metadata location is outside the archive")
        internal_compression, tile_type = header[97], header[99]
        if tile_type != 1:
            raise PMTilesError("Expected vector MVT tile type")
        if internal_compression not in (1, 2):
            raise PMTilesError("Unsupported metadata compression")
        minimum_zoom, maximum_zoom = header[100], header[101]
        if minimum_zoom > maximum_zoom or maximum_zoom > 22:
            raise PMTilesError("Invalid zoom range")
        bbox_values = struct.unpack_from("<iiii", header, 102)
        bbox = [number / 1e7 for number in bbox_values]
        west, south, east, north = bbox
        if not (-180 <= west <= east <= 180 and -90 <= south <= north <= 90):
            raise PMTilesError("Invalid WGS84 bounding box")
        stream.seek(metadata_offset)
        metadata = stream.read(metadata_length)

    if internal_compression == 2:
        try:
            metadata = gzip.decompress(metadata)
        except (EOFError, OSError) as exc:
            raise PMTilesError("Invalid gzip metadata") from exc
    try:
        decoded = json.loads(metadata)
    except (ValueError, UnicodeDecodeError) as exc:
        raise PMTilesError("Invalid JSON metadata") from exc
    if not isinstance(decoded, dict):
        raise PMTilesError("Metadata is not an object")
    layer_ids = [
        item.get("id")
        for item in decoded.get("vector_layers", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    ]
    if not layer_ids:
        raise PMTilesError("Vector archive has no declared source-layers")
    return {
        "spec_version": 3,
        "tile_type": "mvt",
        "minzoom": minimum_zoom,
        "maxzoom": maximum_zoom,
        "bbox_wgs84": bbox,
        "source_layers": layer_ids,
        "generator": decoded.get("generator", "unknown"),
    }


def audit_inventory(
    inventory: dict[str, Any], data_root: Path
) -> tuple[list[Finding], list[dict[str, Any]]]:
    errors: list[Finding] = []
    records: list[dict[str, Any]] = []
    assets = inventory.get("archives")
    if not isinstance(assets, list) or not assets:
        return [Finding("NO_ARCHIVES", "Archive inventory is empty")], records

    for item in assets:
        if not isinstance(item, dict):
            errors.append(Finding("BAD_INVENTORY", "Malformed archive inventory entry"))
            continue
        filename = item.get("filename", "")
        if not isinstance(filename, str) or Path(filename).name != filename:
            errors.append(Finding("UNSAFE_FILENAME", "Archive filename must be a basename"))
            continue
        path = data_root / filename
        if not path.is_file():
            errors.append(Finding("MISSING_ARCHIVE", filename + " is not present"))
            continue
        try:
            metadata = read_pmtiles_header_and_metadata(path)
        except (PMTilesError, OSError) as exc:
            errors.append(Finding("PMTILES_INVALID", filename + ": " + str(exc)))
            continue
        actual_hash = file_sha256(path)
        if actual_hash != item.get("sha256"):
            errors.append(Finding("HASH_MISMATCH", filename + " checksum mismatch"))
        if path.stat().st_size != item.get("bytes"):
            errors.append(Finding("SIZE_MISMATCH", filename + " length mismatch"))
        expected_layer = item.get("source_layer")
        if expected_layer not in metadata["source_layers"]:
            errors.append(Finding("LAYER_MISSING", filename + " missing expected source-layer"))
        records.append({
            "filename": filename,
            "sha256": actual_hash,
            "bytes": path.stat().st_size,
            **metadata,
            "status": "quarantined_not_release_approved",
        })
    return errors, records


def _geometry_coordinates_are_valid(node: Any) -> bool:
    if isinstance(node, list):
        if len(node) >= 2 and all(
            isinstance(value, (int, float)) and not isinstance(value, bool)
            for value in node[:2]
        ):
            lon, lat = node[:2]
            return -180 <= lon <= 180 and -90 <= lat <= 90
        return bool(node) and all(_geometry_coordinates_are_valid(child) for child in node)
    return False


def validate_reference(reference: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    if reference.get("status") != "approved":
        findings.append(Finding("REFERENCE_PENDING", "Approved official GIS reference unavailable"))
    features = reference.get("features")
    if not isinstance(features, list):
        return findings + [Finding("NO_FEATURES", "Expected reviewed GeoJSON features")]
    by_id = {feature.get("feature_id"): feature for feature in features
             if isinstance(feature, dict)}
    for feature_id, label in REQUIRED_LABELS.items():
        feature = by_id.get(feature_id)
        if not isinstance(feature, dict):
            findings.append(Finding("MISSING_REFERENCE", "No verified feature for " + label))
            continue
        if feature.get("name_vi") != label:
            findings.append(Finding("WRONG_LABEL", "Incorrect display name for " + label))
        if not feature.get("authority_document") or not feature.get("reviewed_by"):
            findings.append(Finding("MISSING_AUTHORITY", label + " has no review provenance"))
        geo = feature.get("geometry")
        if not isinstance(geo, dict) or geo.get("type") not in {
            "Point", "MultiPoint", "Polygon", "MultiPolygon",
        } or not _geometry_coordinates_are_valid(geo.get("coordinates")):
            findings.append(Finding("BAD_GEOMETRY", label + " lacks valid reviewed WGS84 geometry"))
    return findings


def validate_style(style: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    if style.get("version") != 8:
        findings.append(Finding("STYLE_VERSION", "Expected MapLibre style version 8"))
    sources = style.get("sources")
    layers = style.get("layers")
    if not isinstance(sources, dict) or not isinstance(layers, list):
        return findings + [Finding("BAD_STYLE", "Sources and layers are required")]
    all_layer_ids = {item.get("id") for item in layers if isinstance(item, dict)}
    for expected in ("sovereignty-hoang-sa", "sovereignty-truong-sa",
                     "sovereignty-bien-dong"):
        if expected not in all_layer_ids:
            findings.append(Finding("ISLAND_SEA_LAYER_MISSING", "Missing " + expected))
    for layer in layers:
        if not isinstance(layer, dict):
            findings.append(Finding("BAD_LAYER", "Layer is not an object"))
            continue
        source = layer.get("source")
        if source is not None and source not in sources:
            findings.append(Finding("MISSING_SOURCE", str(layer.get("id")) + " has no source"))
        if layer.get("layout", {}).get("visibility") == "none" and layer.get("id") in all_layer_ids:
            if layer.get("id", "").startswith("sovereignty-"):
                findings.append(Finding("LABEL_HIDDEN", str(layer.get("id")) + " hidden"))
    # A raw-text check is only a weak warning; actual claims require
    # a spatial + semantic scan of decoded tiles and rendered screenshots.
    lowered = json.dumps(style, ensure_ascii=False).lower()
    if any(term in lowered for term in (
        "nine-dash line", "nine dash line", "đường chín đoạn", "đường lưỡi bò"
    )):
        findings.append(Finding("SUSPECT_STYLE_TEXT", "Potential prohibited claim in style"))
    return findings


def validate_release(repo_root: Path) -> list[Finding]:
    errors: list[Finding] = []
    try:
        manifest = json.loads((repo_root / "assets/manifests/map_release.json").read_text())
        style = json.loads((repo_root / "assets/styles/vietnam_sovereign_style.json").read_text())
        reference = json.loads((repo_root / "assets/geo/approved_reference.json").read_text())
    except (OSError, ValueError) as exc:
        return [Finding("RELEASE_CONFIG_MISSING", str(exc))]

    if manifest.get("status") != "approved" or manifest.get("p0_pass") is not True:
        errors.append(Finding("RELEASE_BLOCKED", "Release manifest is not approved"))
    errors.extend(validate_reference(reference))
    errors.extend(validate_style(style))

    # The original three PMTiles are verified mainland-only. A positive
    # structural MVT scan must not be mistaken for archipelago label coverage.
    # A future island/sea tile package must provide a NEW reviewed P0 artifact,
    # not merely change the status flag in this historical diagnostic.
    gap_report = (
        repo_root /
        "docs/audits/2026-11-11-mainland-pmtiles-offshore-coverage.json"
    )
    try:
        gap = json.loads(gap_report.read_text(encoding="utf-8"))
        if (
            gap.get("p0_pass") is not False or
            gap.get("official_island_name_reference_points") != 183 or
            gap.get("source_archive_count") != 3 or
            gap.get("source_bbox_coverage_count") != 0 or
            gap.get("uncovered_reference_point_count") != 183 or
            gap.get("source_semantic_feature_coverage_verified") is not False
        ):
            errors.append(Finding(
                "OFFSHORE_COVERAGE_AUDIT_INVALID",
                "Mainland source coverage diagnostic is missing or altered"
            ))
        else:
            errors.append(Finding(
                "OFFSHORE_TILE_SOURCE_REQUIRED",
                "Existing HOTOSM PMTiles cover none of the 183 island-name "
                "reference points; a separately reviewed offshore source is needed"
            ))
    except (OSError, ValueError) as exc:
        errors.append(Finding("OFFSHORE_COVERAGE_AUDIT_MISSING", str(exc)))

    evidence = manifest.get("evidence", {})
    if not isinstance(evidence, dict):
        evidence = {}
    for key in REQUIRED_EVIDENCE:
        value = evidence.get(key)
        if not isinstance(value, dict) or value.get("status") != "passed":
            errors.append(Finding("EVIDENCE_MISSING", key + " has no confirmed result"))
            continue
        relative = value.get("artifact", "")
        checksum = value.get("sha256", "")
        if (not isinstance(relative, str) or not relative.startswith("evidence/")
                or ".." in Path(relative).parts):
            errors.append(Finding("BAD_EVIDENCE_PATH", key + " artifact is not scoped"))
            continue
        artifact = repo_root / relative
        if not artifact.is_file() or file_sha256(artifact) != checksum:
            errors.append(Finding("BAD_EVIDENCE_HASH", key + " evidence missing/mismatched"))
    screenshots = manifest.get("visual_views", {})
    if not isinstance(screenshots, dict):
        screenshots = {}
    for name in REQUIRED_VISUAL_VIEWS:
        if screenshots.get(name) != "approved":
            errors.append(Finding("VISUAL_NOT_APPROVED", name + " has no reviewed screenshot"))

    # Fail closed until independent MVT decode + geographic QA + image comparison
    # actually run in this pipeline; evidence-only attestation cannot bypass it.
    errors.append(Finding(
        "FULL_P0_ENGINE_INCOMPLETE",
        "Full MVT geographic scans and Android visual regression are not implemented"
    ))
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--data-root", type=Path, default=None)
    parser.add_argument("--mode", choices=("audit", "release"), default="release")
    args = parser.parse_args(argv)

    root = args.repo_root.resolve()
    output: dict[str, Any] = {"mode": args.mode, "status": "BLOCKED", "archives": []}
    if args.mode == "audit":
        if args.data_root is None:
            parser.error("--data-root is required for --mode audit")
        try:
            inventory = json.loads((root / "assets/manifests/ingestion_inventory.json").read_text())
            findings, records = audit_inventory(inventory, args.data_root.resolve())
        except (OSError, ValueError) as exc:
            findings, records = [Finding("AUDIT_ERROR", str(exc))], []
        output["archives"] = records
        output["status"] = "INTAKE_OK_NOT_P0" if not findings else "INTAKE_FAILED"
    else:
        findings = validate_release(root)
        output["status"] = "P0_PASS" if not findings else "P0_BLOCKED"
    output["findings"] = [asdict(item) for item in findings]
    print(json.dumps(output, ensure_ascii=False, indent=2))
    # Audit success means checksums/headers match only; never sovereignty PASS.
    return 0 if not findings else 1


if __name__ == "__main__":
    sys.exit(main())
