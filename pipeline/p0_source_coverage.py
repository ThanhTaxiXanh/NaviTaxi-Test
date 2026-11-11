#!/usr/bin/env python3
"""Find offshore island-label COVERAGE GAPS in existing quarantined PMTiles.

PMTiles header bboxes are only ENVELOPES; even a point inside a bbox does
not prove the tile contains a visible geographic feature or name. A point
outside every bbox DOES prove no tile from those sources covers its location.
The 183 reference points are official TT33/2024 VN-2000; datum differences
are not resolved but cannot bridge the ~2° minimum longitudinal gap here.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

from pipeline.vietnam_sovereignty_validator import (
    audit_inventory,
)
from pipeline.verify_official_island_points import validate_reference

ROOT = Path(__file__).resolve().parents[1]


def compute_coverage(reference: dict, archives: list[dict]) -> dict:
    points = validate_reference(reference)
    if not isinstance(archives, list) or not archives:
        raise ValueError("No verified PMTiles archive header information")
    bounds = []
    for item in archives:
        box = item.get("bbox_wgs84")
        if (not isinstance(box, list) or len(box) != 4 or
                item.get("status") != "quarantined_not_release_approved"):
            raise ValueError("Untrusted PMTiles coverage inventory")
        if not all(type(x) in (float, int) for x in box):
            raise ValueError("Malformed PMTiles WGS84 geographic envelope")
        west, south, east, north = box
        if not (-180 <= west <= east <= 180 and -90 <= south <= north <= 90):
            raise ValueError("Invalid PMTiles geographic envelope")
        bounds.append((item["filename"], (west,south,east,north)))
    overall = 0
    per_archive = {name:0 for name,_ in bounds}
    per_section = {"B":{"covered":0,"total":50},"C":{"covered":0,"total":133}}
    names_missing = []
    for item in points:
        lon,lat = item["lon_seconds"]/3600, item["lat_seconds"]/3600
        covered_sources = [
            name for name, (west,south,east,north) in bounds
            if west <= lon <= east and south <= lat <= north
        ]
        for name in covered_sources:
            per_archive[name]+=1
        if covered_sources:
            overall+=1
            per_section[item["section"]]["covered"]+=1
        else:
            names_missing.append(item["id"])
    critical = ("B50","C133","B48","C123","B15","B3")
    return {
        "schema_version": 1,
        "status": ("OFFSHORE_SOURCE_BBOX_COVERAGE_INCOMPLETE_NOT_P0"
                   if overall < len(points) else
                   "SOURCE_BBOX_ENVELOPES_COVER_POINTS_NOT_SEMANTICS"),
        "point_crs": "VN-2000 / EPSG:4756",
        "source_bbox_crs": "WGS84 / EPSG:4326",
        "approved_datum_transform_used": False,
        "official_island_name_reference_points": len(points),
        "source_archive_count": len(bounds),
        "source_bbox_coverage_count": overall,
        "uncovered_reference_point_count": len(names_missing),
        "covered_reference_points_per_archive": per_archive,
        "section_coverage": per_section,
        "missing_critical_island_group_label_ids": [
            point for point in critical if point in names_missing
        ],
        "source_archive_envelopes": [
            {"file":name, "bbox_wgs84":list(box)} for name,box in bounds
        ],
        "source_semantic_feature_coverage_verified": False,
        "official_boundary_geometry_verified": False,
        "p0_pass": False,
        "maplibre_activation_allowed": False,
        "notice": (
            "All-source envelope coverage is NECESSARY but NOT SUFFICIENT "
            "for a rendered label. Bboxes cannot prove there are matching "
            "tile payloads, names or island features; the input sources "
            "are deliberately quarantine-only."
        ),
    }


def inspect(reference_path: Path, inventory_path: Path, data_root: Path) -> dict:
    ref = json.loads(reference_path.read_text(encoding="utf-8"))
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    errors, archives = audit_inventory(inventory, data_root)
    if errors:
        raise ValueError(
            "PMTiles source integrity check failed: " +
            ", ".join(e.code for e in errors)
        )
    output = compute_coverage(ref, archives)
    output["input_archives_sha256"] = {
        item["filename"]:item["sha256"] for item in archives
    }
    output["official_pdf_sha256"] = ref["source_pdf_sha256"]
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("official_reference_json", type=Path)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--inventory", type=Path,
                        default=ROOT/"assets/manifests/ingestion_inventory.json")
    parser.add_argument("--output", type=Path,
                        default=Path("audit-output/pmtiles-offshore-coverage.json"))
    args = parser.parse_args()
    try:
        report = inspect(args.official_reference_json, args.inventory, args.data_root)
        code = 0
    except (OSError, ValueError, TypeError, KeyError) as exc:
        report = {
            "status": "SOURCE_COVERAGE_AUDIT_FAILED",
            "error": str(exc),
            "p0_pass": False,
            "maplibre_activation_allowed": False,
        }
        code = 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",
                           encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
