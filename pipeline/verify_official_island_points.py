#!/usr/bin/env python3
"""Coarse VN-2000 island-name point vs WGS84 province polygon diagnostics.

The point list is from Ministry Circular 33/2024 (official PDF); the ZIP is
quarantined, user-supplied GIS. No legally verified VN-2000->WGS84 transform
is applied; distances are only approximately screened, NOT P0 or geography
of maritime boundaries. No source data/geometry is redistributed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from pipeline.province34_review_gpkg import load_zip

PDF_SHA256 = "acde9b561eca24312b81efdcb36a22a8fc74e2dcb431f6c206199ef72c98e841"
USER_ZIP_SHA256 = "51779d2585600ec053827a60890ba61cd2192f19b5ee153d38be18a2611d24cd"
SECTIONS = {"B": (50, "48", "Đà Nẵng"), "C": (133, "56", "Khánh Hòa")}


def validate_reference(reference: dict) -> list:
    if (not isinstance(reference, dict) or reference.get("schema_version") != 1
            or reference.get("source_pdf_sha256") != PDF_SHA256
            or reference.get("source_datum") != "VN-2000"
            or reference.get("p0_pass") is not False
            or reference.get("geometry_type") != "reference_points_not_boundary_polygons"):
        raise ValueError("Unverified official PDF point-reference identity")
    points = reference.get("points")
    if not isinstance(points, list) or len(points) != 183:
        raise ValueError("Incomplete official B/C point list")
    for group, (expected, _, _) in SECTIONS.items():
        indices = sorted(
            p.get("number") for p in points if p.get("section") == group
        )
        if indices != list(range(1, expected + 1)):
            raise ValueError("Official reference section has missing/duplicate IDs")
    for item in points:
        section, number = item.get("section"), item.get("number")
        lat, lon = item.get("lat_seconds"), item.get("lon_seconds")
        if (section not in SECTIONS or type(number) is not int
                or item.get("id") != f"{section}{number}"
                or not isinstance(item.get("name"), str)
                or not item["name"].strip()
                or type(lat) is not int or type(lon) is not int
                or not 6*3600 <= lat <= 18*3600
                or not 110*3600 <= lon <= 119*3600):
            raise ValueError("Malformed official island-name point")
    return points


def compare(reference: dict, zip_path: Path, roster: Path) -> dict:
    from shapely.geometry import Point, shape
    from shapely.strtree import STRtree
    from shapely.ops import nearest_points
    from pyproj import Geod

    points = validate_reference(reference)
    digest, provinces, _ = load_zip(zip_path, roster, USER_ZIP_SHA256)
    by_code = {
        p["code"]: list(shape(p["geometry"]).geoms)
        for p in provinces if p["code"] in ("48", "56")
    }
    if set(by_code) != {"48", "56"}:
        raise ValueError("Missing province geometry")
    trees = {code: STRtree(parts) for code, parts in by_code.items()}
    geod = Geod(ellps="WGS84")
    details = []
    summary = {
        "B": {"reference_points": 0, "inside": 0, "within_2km": 0,
              "outside_5km": 0, "outside_10km": 0},
        "C": {"reference_points": 0, "inside": 0, "within_2km": 0,
              "outside_5km": 0, "outside_10km": 0},
    }
    for entry in points:
        section = entry["section"]
        code = SECTIONS[section][1]
        lon, lat = entry["lon_seconds"]/3600, entry["lat_seconds"]/3600
        location = Point(lon, lat)
        idx = int(trees[code].nearest(location))
        nearest_shape = by_code[code][idx]
        inside = bool(nearest_shape.covers(location))
        if inside:
            distance_km = 0.0
        else:
            closest = nearest_points(location, nearest_shape)[1]
            distance_km = geod.inv(lon, lat, closest.x, closest.y)[2] / 1000
        distance_km = round(distance_km, 3)
        stats = summary[section]
        stats["reference_points"] += 1
        stats["inside"] += int(inside)
        stats["within_2km"] += int(distance_km <= 2)
        stats["outside_5km"] += int(distance_km > 5)
        stats["outside_10km"] += int(distance_km > 10)
        label_point = entry["id"] in ("B50", "C133")
        details.append({
            "reference_id": entry["id"],
            "name": entry["name"],
            "province": SECTIONS[section][2],
            "point_is_region_label": label_point,
            "published_lat_vn2000": lat,
            "published_lon_vn2000": lon,
            "inside_geojson_polygon": inside,
            "nearest_polygon_distance_km_approx": distance_km,
        })
    flagged = sorted(
        [p for p in details if p["nearest_polygon_distance_km_approx"] > 5],
        key=lambda p: -p["nearest_polygon_distance_km_approx"]
    )
    return {
        "schema_version": 1,
        "status": "183_GOVERNMENT_POINT_REFERENCE_SCREEN_NOT_P0",
        "p0_pass": False,
        "maplibre_activation_allowed": False,
        "official_boundary_geometry_verified": False,
        "datum_transform_verified": False,
        "official_pdf_sha256": PDF_SHA256,
        "user_zip_sha256": digest,
        "reference_counts": {"B": 50, "C": 133},
        "province_polygon_components": {s: len(by_code[SECTIONS[s][1]]) for s in SECTIONS},
        "counts": summary,
        "flagged_over_5km": flagged,
        "points": details,
        "method_warning": (
            "Nearest shape in lon/lat degree-space; approximate WGS84 geodesic "
            "from published VN-2000 numeric coordinates; datum transform NOT verified; "
            "point-vs-admin-polygon cannot validate any legal boundary"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("zip_file", type=Path)
    parser.add_argument("official_points", type=Path)
    parser.add_argument("--roster", type=Path, default=(
        Path(__file__).resolve().parents[1] /
        "assets/geo/province34_names_2025.json"
    ))
    parser.add_argument("--output", type=Path, default=Path("audit-output/tt33-183-screen.json"))
    args = parser.parse_args()
    try:
        reference = json.loads(args.official_points.read_text(encoding="utf-8"))
        result = compare(reference, args.zip_file, args.roster)
        code = 0
    except (OSError, ValueError, TypeError, KeyError) as exc:
        result = {"status": "POINT_REFERENCE_COMPARISON_FAILED",
                  "p0_pass": False, "maplibre_activation_allowed": False,
                  "error": str(exc)}
        code = 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n",
                           encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "points"},
                     ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
