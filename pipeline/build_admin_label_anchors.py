#!/usr/bin/env python3
"""Create OFFLINE REVIEW label anchors from a version-pinned administrative GIS ZIP.

Only representative text anchor points are emitted. They are not survey
centroids, island outlines, administrative borders or maritime boundaries.
The underlying 50 MB source archive is never bundled into the APK.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile

from shapely.geometry import shape
from shapely.geometry.base import BaseGeometry

EXPECTED_ZIP_GIT_BLOB = "d6d9b450e96b7be99d9e923cef7142f5dc2f6eb3"
SOURCE_REVISION = "8b78ba5118715e1fa81769286724db79346abf52"
OFFSHORE_GROUP_LABEL_CODES = {"20333", "22736"}
WARD_FILE = re.compile(r"(?:^|/)wards/([0-9]{1,5})_[^/]+\.geojson$", re.I)
PROVINCE_FILE = re.compile(r"(?:^|/)([0-9]{2})_[^/]+/\1_[^/]+\.geojson$", re.I)


def github_blob_sha1(path: Path) -> str:
    digest = hashlib.sha1()
    digest.update(f"blob {path.stat().st_size}\0".encode("ascii"))
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            digest.update(block)
    return digest.hexdigest()


def map_label_point(geometry: dict) -> list[float]:
    obj: BaseGeometry = shape(geometry)
    if obj.is_empty or obj.geom_type not in ("Polygon", "MultiPolygon"):
        raise ValueError("Expected nonempty polygon geometry")
    # A province/ward can have small offshore components. Choose the largest
    # polygon component for a label anchor, not an invented archipelago centre.
    polygons = [obj] if obj.geom_type == "Polygon" else list(obj.geoms)
    dominant = max(polygons, key=lambda polygon: polygon.area)
    point = dominant.representative_point()
    longitude = float(point.x)
    latitude = float(point.y)
    if not 101.5 <= longitude <= 118.5 or not 6.0 <= latitude <= 24.5:
        raise ValueError("Label coordinate outside reviewed Vietnam GIS scope")
    return [round(longitude, 6), round(latitude, 6)]


def build_labels(archive: Path, names_path: Path) -> dict:
    if github_blob_sha1(archive) != EXPECTED_ZIP_GIT_BLOB:
        raise ValueError("ZIP does not match pinned source Git blob")
    data = json.loads(names_path.read_text(encoding="utf-8"))
    if not isinstance(data, list) or len(data) != 34:
        raise ValueError("Expected 34 province records")
    provinces = {}
    wards = {}
    for province in data:
        code = province["Code"]
        if not isinstance(code, str) or code in provinces:
            raise ValueError("Invalid/duplicate province code")
        provinces[code] = province["FullName"]
        for ward in province["Wards"]:
            ward_code = ward["Code"]
            if ward_code in wards or ward["ProvinceCode"] != code:
                raise ValueError("Duplicate ward or invalid province relation")
            wards[ward_code] = (ward["FullName"], code)
    if len(wards) != 3321:
        raise ValueError("Expected 3321 wards/communes")

    province_points = {}
    ward_points = {}
    with zipfile.ZipFile(archive) as zf:
        if zf.testzip() is not None:
            raise ValueError("Corrupt GIS ZIP")
        for info in zf.infolist():
            if info.is_dir() or not info.filename.endswith(".geojson"):
                continue
            path = info.filename.replace("\\", "/")
            match_w = WARD_FILE.search(path)
            match_p = PROVINCE_FILE.search(path)
            if match_w:
                code = match_w.group(1).zfill(5)
                if code not in wards:
                    raise ValueError("Unknown ward GIS code " + code)
                if code in ward_points:
                    raise ValueError("Duplicate ward GIS geometry " + code)
                obj = json.loads(zf.read(info))
                feature = obj["features"][0]
                if str(feature["id"]).zfill(5) != code:
                    raise ValueError("Ward feature id mismatch: " + code)
                ward_points[code] = map_label_point(feature["geometry"])
            elif match_p:
                code = match_p.group(1)
                if code not in provinces:
                    raise ValueError("Unknown province GIS code " + code)
                if code in province_points:
                    raise ValueError("Duplicate province GIS geometry " + code)
                obj = json.loads(zf.read(info))
                feature = obj["features"][0]
                if str(feature["id"]).zfill(2) != code:
                    raise ValueError("Province feature id mismatch: " + code)
                province_points[code] = map_label_point(feature["geometry"])

    missing_provinces = sorted(set(provinces) - set(province_points))
    missing_wards = sorted(set(wards) - set(ward_points))
    if missing_provinces or missing_wards:
        raise ValueError(
            f"Incomplete GIS ZIP: missing provinces {missing_provinces}, "
            f"missing wards {missing_wards[:15]} (count {len(missing_wards)})"
        )
    return {
        "schema_version": 1,
        "status": "DEBUG_ONLY_CANDIDATE_NOT_P0",
        "geometry_role": "representative_label_points_only",
        "dataset_version": "v5.2.0",
        "source_revision": SOURCE_REVISION,
        "source_zip_sha256": sha256(archive),
        "offshore_group_ward_codes_not_drawn_as_land_labels":
            sorted(OFFSHORE_GROUP_LABEL_CODES),
        "provinces": [
            [code, provinces[code], *province_points[code]]
            for code in sorted(provinces)
        ],
        "wards": [
            [code, wards[code][0], wards[code][1], *ward_points[code]]
            for code in sorted(wards)
            if code not in OFFSHORE_GROUP_LABEL_CODES
        ],
        "p0_pass": False,
        "marine_boundaries_verified": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--zip", type=Path, required=True)
    parser.add_argument("--names", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    labels = build_labels(args.zip, args.names)
    if len(labels["provinces"]) != 34 or len(labels["wards"]) != 3319:
        raise ValueError("Unexpected output label count")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(labels, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    report = {
        "status": labels["status"],
        "source_revision": SOURCE_REVISION,
        "source_zip_sha256": labels["source_zip_sha256"],
        "provinces": len(labels["provinces"]),
        "wards_geocoded": len(labels["wards"]),
        "excluded_offshore_group_codes":
            labels["offshore_group_ward_codes_not_drawn_as_land_labels"],
        "asset_sha256": sha256(args.output),
        "data_role": labels["geometry_role"],
        "p0_pass": False,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
