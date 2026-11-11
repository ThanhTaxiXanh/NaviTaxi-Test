#!/usr/bin/env python3
"""Review 14 offshore reference anomalies, retaining native VN-2000 coordinates.

Inputs: official full 183-point JSON from official_island_point_catalog.py
and original user 34-province ZIP. Outputs diagnostic-only JSON and EPSG:4756
GeoPackage POINTS. Never creates synthetic land polygons or legal sea lines.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

from pipeline.verify_official_island_points import validate_reference
from pipeline.province34_review_gpkg import load_zip

ROOT = Path(__file__).resolve().parents[1]
CORROBORATION = ROOT / "assets/geo/island_outlier_independent_references.json"
SAMPLE = ROOT / "docs/audits/2026-11-11-tt33-183-island-point-screen.json"

TYPE_BY_ID = {
    "B3": "named_island",
    "B15": "named_island",
    "B37": "reef_or_shoal",
    "B39": "reef_or_shoal",
    "B48": "named_island",
    "B49": "submerged_bank",
    "B50": "regional_label",
    "C71": "reef_or_shoal",
    "C109": "reef_or_shoal",
    "C122": "submerged_bank",
    "C123": "named_island",
    "C128": "reef_or_shoal",
    "C129": "submerged_bank",
    "C131": "reef_or_shoal",
}
EXPECTED_SOURCE_SHA = "51779d2585600ec053827a60890ba61cd2192f19b5ee153d38be18a2611d24cd"
KINDS = set(TYPE_BY_ID.values())


def classify_name(name: str) -> str:
    if name.startswith("Đảo "):
        return "named_island"
    if name.startswith("Bãi ngầm "):
        return "submerged_bank"
    if name.startswith("Quần đảo "):
        return "regional_label"
    if name.startswith(("Đá ", "Bãi cạn ", "Bãi ")):
        return "reef_or_shoal"
    return "unknown"


def validate_anchor_catalog(catalog: dict, reference: dict | None = None) -> dict:
    from pyproj import Geod
    if (catalog.get("schema_version") != 1
            or catalog.get("p0_pass") is not False
            or catalog.get("maplibre_activation_allowed") is not False
            or catalog.get("source_datum") != "VN-2000"
            or catalog.get("official_pdf_sha256") !=
              "acde9b561eca24312b81efdcb36a22a8fc74e2dcb431f6c206199ef72c98e841"
            or catalog.get("coordinate_transform_from_vn2000_to_wgs84_verified") is not False
            or catalog.get("reference_points_are_not_island_boundaries") is not True):
        raise ValueError("Untrusted island reference identity or release flag")
    entries = catalog.get("independent_positions")
    if not isinstance(entries, list) or len(entries) != 4:
        raise ValueError("Four named-island corroborations are required")
    if {item.get("reference_id") for item in entries} != {
        "B48", "B15", "B3", "C123"
    }:
        raise ValueError("Unexpected island reference IDs")
    geod = Geod(ellps="WGS84")
    checked = {}
    for entry in entries:
        a, b = entry.get("published_vn2000", []), entry.get("independent_position", [])
        if not (len(a) == 2 and len(b) == 2
                and all(type(n) in (float, int) for n in [*a, *b])
                and isinstance(entry.get("url"), str)
                and entry["url"].startswith("https://")):
            raise ValueError("Incomplete corroborating coordinate")
        distance = geod.inv(a[0], a[1], b[0], b[1])[2] / 1000
        if distance > catalog.get("tolerance_km_for_independent_point_screen", 1):
            raise ValueError("Large discrepancy in named-island corroboration")
        checked[entry["reference_id"]] = round(distance, 3)
    if reference:
        points = {
            item["id"]: item for item in validate_reference(reference)
        }
        for entry in entries:
            item = points[entry["reference_id"]]
            official_lon = item["lon_seconds"] / 3600
            official_lat = item["lat_seconds"] / 3600
            if (abs(official_lon - entry["published_vn2000"][0]) > 1e-5 or
                    abs(official_lat - entry["published_vn2000"][1]) > 1e-5):
                raise ValueError("Independent anchor does not match the official PDF")
    return checked


def generate(zip_path: Path, point_path: Path, output_dir: Path, anchors: Path):
    from shapely.geometry import Point, shape
    from shapely.ops import nearest_points, transform
    from pyproj import CRS, Transformer
    import fiona

    catalog = json.loads(anchors.read_text(encoding="utf-8"))
    reference = json.loads(point_path.read_text(encoding="utf-8"))
    verified = validate_anchor_catalog(catalog, reference)
    points = {p["id"]: p for p in validate_reference(reference)}
    baseline = json.loads(SAMPLE.read_text(encoding="utf-8"))
    suspects = baseline.get("review_candidates_over_5km")
    if (not isinstance(suspects, list) or len(suspects) != 14 or
            {p["reference_id"] for p in suspects} != set(TYPE_BY_ID)):
        raise ValueError("Official 14-point QA inventory changed")
    roster = ROOT / "assets/geo/province34_names_2025.json"
    zip_sha, provinces, _ = load_zip(zip_path, roster, EXPECTED_SOURCE_SHA)
    by_code = {
        p["code"]: list(shape(p["geometry"]).geoms)
        for p in provinces if p["code"] in ("48", "56")
    }
    if set(by_code) != {"48", "56"}:
        raise ValueError("Missing reviewed province source polygons")
    findings = []
    for expected in suspects:
        rid = expected["reference_id"]
        pt = points[rid]
        kind = TYPE_BY_ID[rid]
        if classify_name(pt["name"]) != kind:
            raise ValueError("Official name implies a different feature type: " + rid)
        lon, lat = pt["lon_seconds"] / 3600, pt["lat_seconds"] / 3600
        source_code = "48" if rid.startswith("B") else "56"
        place = Point(lon, lat)
        shapes = by_code[source_code]
        minimum = min(place.distance(poly) for poly in shapes)
        neighbors = [poly for poly in shapes
                     if place.distance(poly) <= minimum*1.2 + .05]
        crs = CRS.from_proj4(
            f"+proj=aeqd +lat_0={lat} +lon_0={lon} +datum=WGS84 +units=m +no_defs"
        )
        fn = Transformer.from_crs("EPSG:4326", crs, always_xy=True).transform
        projected_place = transform(fn, place)
        km = min(projected_place.distance(transform(fn, poly))
                 for poly in neighbors) / 1000
        if abs(km - expected["distance_km_approx"]) > 2:
            raise ValueError("Distance changed >2 km from pinned audit: " + rid)
        findings.append({
            "reference_id": rid,
            "name": pt["name"],
            "source_unit_code": source_code,
            "feature_class": kind,
            "vn2000_latitude": lat,
            "vn2000_longitude": lon,
            "distance_to_source_admin_polygon_km_approx": round(km, 3),
            "independent_named_island_point_agreement_km":
                verified.get(rid),
            "classification_review": (
                "NOT_EXPECTED_AS_EXPOSED_LAND"
                if kind in ("submerged_bank", "regional_label") else
                "POINT_CORROBORATED_BUT_LANDFORM_OUTLINE_UNVERIFIED"
                if kind == "named_island" else
                "REVIEW_IF_REEF_EXPOSED_OR_SUBMERGED"
            ),
            "geometry_approved": False,
            "maplibre_activation_allowed": False,
        })
    output_dir.mkdir(parents=True, exist_ok=True)
    report = {
        "schema_version": 1,
        "status": "14_NAME_POINTS_CLASSIFIED_NOT_ISLAND_OUTLINE_APPROVAL",
        "source_pdf_sha256": catalog["official_pdf_sha256"],
        "source_zip_sha256": zip_sha,
        "points_screened": len(findings),
        "classification_counts": {
            kind: sum(row["feature_class"] == kind for row in findings)
            for kind in sorted(KINDS)
        },
        "corroborated_named_island_reference_points": len(verified),
        "unverified_named_island_outlines": 4,
        "rock_reef_shoal_exposure_unknown": 6,
        "classification_resolved_non_land_or_region_label": 4,
        "coordinate_transform_verified": False,
        "official_maritime_boundary_verified": False,
        "source_redistribution_rights_verified": False,
        "p0_pass": False,
        "maplibre_activation_allowed": False,
        "rows": findings,
    }
    (output_dir / "point_classification.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2)+"\n",
        encoding="utf-8",
    )

    # EPSG:4756 is VN-2000 geographic; do not mislabeled VN-2000 as WGS84 GeoJSON.
    gpkg = output_dir / "island_reference_points_VN2000_REVIEW_ONLY.gpkg"
    if gpkg.exists():
        gpkg.unlink()
    with fiona.open(
        gpkg, "w", driver="GPKG",
        layer="named_points_NOT_P0", crs="EPSG:4756",
        schema={"geometry": "Point", "properties": {
            "id": "str:8", "name": "str:100",
            "kind": "str:32", "distance_km": "float",
            "approval": "str:20",
        }},
    ) as dest:
        for row in findings:
            dest.write({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [
                    row["vn2000_longitude"], row["vn2000_latitude"]
                ]},
                "properties": {
                    "id": row["reference_id"], "name": row["name"],
                    "kind": row["feature_class"],
                    "distance_km": row["distance_to_source_admin_polygon_km_approx"],
                    "approval": "QUARANTINED",
                }
            })
    with fiona.open(gpkg, layer="named_points_NOT_P0") as check:
        if len(check) != 14 or check.crs.to_epsg() != 4756:
            raise ValueError("GeoPackage lost point geometry or VN-2000 CRS")
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("source_zip", type=Path)
    p.add_argument("official_reference_json", type=Path)
    p.add_argument("--output-dir", type=Path, default=Path("audit-output/14-point-review"))
    p.add_argument("--anchors", type=Path, default=CORROBORATION)
    args = p.parse_args()
    report = generate(args.source_zip, args.official_reference_json,
                      args.output_dir, args.anchors)
    print(json.dumps({
        k: v for k, v in report.items() if k != "rows"
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
