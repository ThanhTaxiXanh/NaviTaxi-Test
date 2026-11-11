#!/usr/bin/env python3
"""Audit EPSG transformation SCOPE before using official VN-2000 island points.

PROJ may offer onshore VN-2000->WGS84 transformations with stated ~1 m
accuracy. This does NOT make them applicable to offshore Hoàng Sa/Trường Sa.
This tool reports only displacement sensitivity, not approved WGS84 points,
not shoreline polygons and not legal maritime boundaries.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from pipeline.verify_official_island_points import validate_reference

EXPECTED_OFFICIAL_PDF = (
    "acde9b561eca24312b81efdcb36a22a8fc74e2dcb431f6c206199ef72c98e841"
)
ROOT = Path(__file__).resolve().parents[1]
OUTLIER_BASELINE = (
    ROOT / "docs/audits/2026-11-11-tt33-183-island-point-screen.json"
)


def audit(reference: dict, official_outliers: dict) -> dict:
    from pyproj import CRS, Geod, __version__ as pyproj_version
    from pyproj.transformer import TransformerGroup

    if reference.get("source_pdf_sha256") != EXPECTED_OFFICIAL_PDF:
        raise ValueError("Wrong official PDF checksum")
    points = validate_reference(reference)
    if (official_outliers.get("points_checked") != 183
            or official_outliers.get("source_reference_pdf_sha256") !=
            EXPECTED_OFFICIAL_PDF
            or official_outliers.get("p0_pass") is not False):
        raise ValueError("Unverified source comparison")
    candidates = official_outliers.get("review_candidates_over_5km")
    if (not isinstance(candidates, list) or len(candidates) != 14):
        raise ValueError("Expected pinned 14 reference point outliers")
    source = CRS.from_epsg(4756)  # VN-2000 geographic
    target = CRS.from_epsg(4326)  # WGS 84 geographic
    transformations = TransformerGroup(source, target, always_xy=True)
    if not transformations.transformers:
        raise ValueError("No EPSG transform candidates available")
    geod = Geod(ellps="WGS84")
    operations = []
    for transformer in transformations.transformers:
        area = transformer.area_of_use
        if area is None:
            raise ValueError("Transform has no defined area of use")
        west, south, east, north = area.bounds
        scopes = [
            item.scope for item in transformer.operations
            if item.scope is not None
        ]
        inside = 0
        shifts_m = []
        for point in points:
            lon = point["lon_seconds"] / 3600
            lat = point["lat_seconds"] / 3600
            if west <= lon <= east and south <= lat <= north:
                inside += 1
            x, y = transformer.transform(lon, lat)
            if not (-180 <= x <= 180 and -90 <= y <= 90):
                raise ValueError("Invalid transformed sample position")
            shifts_m.append(geod.inv(lon, lat, x, y)[2])
        operationally_authorized = (
            inside == len(points)
            and not any("not officially adopted" in scope.lower()
                        for scope in scopes)
        )
        operations.append({
            "operation_description": transformer.description,
            "area_of_use_name": area.name,
            "area_of_use_bbox": list(area.bounds),
            "declared_scopes": scopes,
            "epsg_accuracy_m_as_listed": transformer.accuracy,
            "official_points_inside_area_of_use": inside,
            "official_points_total": len(points),
            "displacement_min_m_diagnostic_only": round(min(shifts_m), 3),
            "displacement_max_m_diagnostic_only": round(max(shifts_m), 3),
            "displacement_average_m_diagnostic_only":
                round(sum(shifts_m) / len(shifts_m), 3),
            "usable_as_approved_offshore_transform": operationally_authorized,
        })
    max_shift_km = max(
        op["displacement_max_m_diagnostic_only"] for op in operations
    ) / 1000
    reviewed = []
    for point in candidates:
        distance = point.get("distance_km_approx")
        if not isinstance(distance, (float, int)) or distance < 5:
            raise ValueError("Outlier baseline contains invalid distance")
        reviewed.append({
            "id": point["reference_id"],
            "original_nearest_polygon_km_approx": distance,
            "worst_case_remaining_distance_km_approx":
                round(max(0, distance - max_shift_km), 3),
            "note": "Sensitivity bound only; transform not authorized offshore",
        })
    # Fail closed: no operation in this local EPSG database has confirmed
    # authority to transform all offshore island-name points.
    eligible = [
        op for op in operations if op["usable_as_approved_offshore_transform"]
    ]
    return {
        "schema_version": 1,
        "status": (
            "OFFSHORE_DATUM_SCOPE_REQUIRES_INDEPENDENT_REVIEW"
            if eligible else "NO_AUTHORIZED_OFFSHORE_DATUM_OPERATION"
        ),
        "source_pdf_sha256": EXPECTED_OFFICIAL_PDF,
        "source_datum_epsg": "EPSG:4756",
        "comparison_datum_epsg": "EPSG:4326",
        "pyproj_version": pyproj_version,
        "official_points_reviewed": len(points),
        "transform_operations": operations,
        "offshore_approved_transform_found": bool(eligible),
        "outlier_count": len(reviewed),
        "outliers_remaining_beyond_5km_even_under_diagnostic_shift":
            sum(p["worst_case_remaining_distance_km_approx"] > 5
                for p in reviewed),
        "outlier_shift_sensitivity": reviewed,
        "p0_pass": False,
        "maplibre_activation_allowed": False,
        "important_caveat": (
            "This analysis deliberately evaluates out-of-area transformations "
            "as a diagnostic sensitivity bound. It DOES NOT certify or apply "
            "a valid VN-2000->WGS84 transformation offshore. The listed EPSG "
            "accuracy is only applicable within an operation's valid scope."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("official_points", type=Path)
    parser.add_argument("--outlier-baseline", type=Path, default=OUTLIER_BASELINE)
    parser.add_argument("--output", type=Path,
                        default=Path("build/official-points/datum_scope_qa.json"))
    args = parser.parse_args()
    try:
        reference = json.loads(args.official_points.read_text(encoding="utf-8"))
        baseline = json.loads(args.outlier_baseline.read_text(encoding="utf-8"))
        result = audit(reference, baseline)
        code = 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        result = {"status": "DATUM_SCOPE_AUDIT_FAILED",
                  "error": str(exc), "p0_pass": False,
                  "maplibre_activation_allowed": False}
        code = 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n",
                           encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items()
                      if k != "outlier_shift_sensitivity"},
                     ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
