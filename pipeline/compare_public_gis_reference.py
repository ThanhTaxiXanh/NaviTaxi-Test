#!/usr/bin/env python3
"""Compare GeoJSON regional extents with a pinned independent public GitHub source.

No external raw files are committed or re-published. Image/photo comparison is
regional only (not georeferenced pixel-by-pixel). All output remains NOT P0.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import unicodedata
from urllib.parse import quote
from urllib.request import Request, urlopen

SOURCE_REPO = "nguyenduy1133/Free-GIS-Data"
SOURCE_COMMIT = "ccb9f4ae992418bfeefd06da1eb42d0249632176"
SOURCE_PATH = (
    "Vietnam Administrative Divisions (Post-2025) - "
    "Đơn vị hành chính Việt Nam (Từ 2025)/Provinces.geojson"
)
SOURCE_URL = (
    "https://raw.githubusercontent.com/" + SOURCE_REPO + "/"
    + SOURCE_COMMIT + "/" + quote(SOURCE_PATH, safe="/")
)
MAX_SOURCE_SIZE = 30 * 1024 * 1024


def norm(name):
    name = name.strip().lower().replace("đ", "d")
    name = "".join(
        character for character in unicodedata.normalize("NFD", name)
        if unicodedata.category(character) != "Mn"
    )
    name = re.sub(r"^(tinh|thanh pho|tp\.?)\s+", "", name)
    name = name.replace(".", " ")
    return " ".join(name.split())


def bbox_overlap_fraction(a, b):
    x0, y0 = max(a[0], b[0]), max(a[1], b[1])
    x1, y1 = min(a[2], b[2]), min(a[3], b[3])
    intersection = max(0.0, x1 - x0) * max(0.0, y1 - y0)
    box_area = lambda r: max(0, r[2] - r[0]) * max(0, r[3] - r[1])
    union = box_area(a) + box_area(b) - intersection
    return round(intersection / union, 4) if union > 0 else 0.0


def load_reference(path: Path | None):
    if path is not None:
        raw = path.read_bytes()
    else:
        req = Request(SOURCE_URL, headers={
            "User-Agent": "NaviTaxi-Reference-QA/1.0 (public GIS source audit)",
            "Accept": "application/geo+json,application/json",
        })
        with urlopen(req, timeout=50) as response:
            raw = response.read(MAX_SOURCE_SIZE + 1)
    if len(raw) > MAX_SOURCE_SIZE:
        raise ValueError("Reference exceeds size safety limit")
    doc = json.loads(raw)
    if not isinstance(doc, dict) or doc.get("type") != "FeatureCollection":
        raise ValueError("Public reference is not GeoJSON FeatureCollection")
    return raw, doc


def compare_reference(reference: dict, baseline: dict) -> dict:
    from pyproj import Geod
    from shapely.geometry import shape

    geod = Geod(ellps="WGS84")
    roster = {norm(p["name"]): p for p in baseline["provinces"]}
    seen = set()
    matches = []
    unmatched = []
    for index, feature in enumerate(reference.get("features", [])):
        props = feature.get("properties") or {}
        identities = {
            norm(v) for v in props.values()
            if isinstance(v, str) and norm(v) in roster
        }
        if len(identities) != 1:
            unmatched.append({
                "feature_index": index,
                "string_property_preview": {
                    k: str(v)[:75] for k, v in list(props.items())[:6]
                },
                "candidate_identity_count": len(identities),
            })
            continue
        name = next(iter(identities))
        baseline_row = roster[name]
        if name in seen:
            unmatched.append({"feature_index": index, "reason": "duplicate province"})
            continue
        seen.add(name)
        g = shape(feature["geometry"])
        parts = list(g.geoms) if g.geom_type == "MultiPolygon" else [g]
        if not parts or not all(p.is_valid and not p.is_empty for p in parts):
            raise ValueError("Invalid independent-reference geometry")
        geodesic_area = round(
            sum(abs(geod.geometry_area_perimeter(p)[0]) for p in parts) / 1e6, 2
        )
        base_area = baseline_row["geodesic_area_km2"]
        matches.append({
            "code": baseline_row["code"],
            "province": baseline_row["name"],
            "independent_bbox_wgs84": [round(x, 5) for x in g.bounds],
            "user_bbox_wgs84": baseline_row["bbox_wgs84"],
            "bbox_iou_degrees": bbox_overlap_fraction(g.bounds, baseline_row["bbox_wgs84"]),
            "independent_area_km2": geodesic_area,
            "user_area_km2": base_area,
            "absolute_area_difference_pct_of_user": round(
                abs(geodesic_area - base_area) / base_area * 100, 2
            ),
            "reference_polygon_components": len(parts),
            "user_polygon_components": baseline_row["polygon_components"],
        })
    matches.sort(key=lambda record: record["code"])
    mismatched = [
        x for x in matches if
        x["absolute_area_difference_pct_of_user"] > 10 or x["bbox_iou_degrees"] < 0.7
    ]
    return {
        "matched_provinces": len(matches),
        "total_reference_features": len(reference.get("features", [])),
        "unmatched_reference_features": unmatched[:40],
        "missing_user_provinces": [
            p["name"] for k, p in roster.items() if k not in seen
        ],
        "high_variance_regions": mismatched,
        "full_34_province_comparison": matches,
        "cautions": [
            "Two non-government datasets agreeing does not establish official correctness",
            "BBox IoU is an envelope metric, NOT actual polygon intersection",
            "Aerial/remote components can be reefs, generalized administrative extents, or islands",
            "Image is raster without registered ground control points: visual grid check only",
            "Neither source grants P0 or automatic MapLibre activation",
        ],
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--reference", type=Path, help="Use a previously downloaded copy; no network")
    p.add_argument("--baseline", type=Path, default=Path(
        "docs/audits/2026-11-11-user-province34-reference-baseline.json"
    ))
    p.add_argument("--output", type=Path, default=Path(
        "build/reference-qa/reference-comparison.json"
    ))
    args = p.parse_args()
    output = {
        "schema_version": 1,
        "status": "REFERENCE_COMPARISON_FAILED",
        "source_repo": SOURCE_REPO,
        "source_commit": SOURCE_COMMIT,
        "source_path": SOURCE_PATH,
        "source_url": SOURCE_URL,
        "raw_reference_redistributed": False,
        "formal_source_license_verified": False,
        "official_geometry_verified": False,
        "maplibre_activation_allowed": False,
        "p0_pass": False,
    }
    try:
        baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
        if (baseline.get("p0_pass") is not False or
                baseline.get("maplibre_activation_allowed") is not False or
                len(baseline.get("provinces", [])) != 34):
            raise ValueError("Unsafe or incomplete user ZIP diagnostic baseline")
        raw, doc = load_reference(args.reference)
        output["reference_sha256"] = hashlib.sha256(raw).hexdigest()
        output["reference_bytes"] = len(raw)
        output["comparison"] = compare_reference(doc, baseline)
        output["status"] = "REFERENCE_COMPARISON_COMPLETED_NOT_P0"
        code = 0
    except Exception as exc:
        output["error_type"] = type(exc).__name__
        output["error"] = str(exc)[:400]
        code = 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
