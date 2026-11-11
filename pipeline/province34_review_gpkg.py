#!/usr/bin/env python3
"""Generate a QUARANTINED GeoPackage from 34 separate provincial GeoJSONs.

Original polygons are preserved byte-for-byte at the coordinate level;
offshore components are DUPLICATED in a second review-only layer. This is
not physical land, an authoritative border, or a P0-approved basemap.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import tempfile
import unicodedata
from zipfile import ZipFile

MAX_ZIP = 128 * 1024 * 1024
MAX_MEMBER = 60 * 1024 * 1024
MAX_EXPANDED = 250 * 1024 * 1024
REMOTE_LONGITUDE_SCREEN = {"48": 110.0, "56": 111.0}


class ReviewPackageError(ValueError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def normalize(name: str) -> str:
    if not isinstance(name, str):
        raise ReviewPackageError("Province name is not a string")
    name = unicodedata.normalize("NFC", name).strip().casefold()
    name = re.sub(r"^(?:(?:thành\s*phố)|(?:tỉnh)|(?:tp\.?))\s+", "", name)
    return " ".join(name.split())


def candidates(archive: ZipFile):
    members = archive.infolist()
    if len(members) > 150:
        raise ReviewPackageError("ZIP has too many entries")
    accepted, expanded = [], 0
    for item in members:
        segments = item.filename.replace("\\", "/").split("/")
        mode = (item.external_attr >> 16) & 0o170000
        if (item.filename.startswith(("/", "\\")) or ".." in segments or
                ":" in segments[0] or mode == 0o120000 or
                item.file_size > MAX_MEMBER):
            raise ReviewPackageError("Unsafe ZIP member")
        if item.is_dir() or segments[0] == "__MACOSX" or segments[-1].startswith("._"):
            continue
        if not item.filename.lower().endswith(".geojson"):
            raise ReviewPackageError("ZIP contains unexpected non-GeoJSON file")
        expanded += item.file_size
        if expanded > MAX_EXPANDED:
            raise ReviewPackageError("ZIP expanded bytes exceed safety limit")
        accepted.append(item)
    if len(accepted) != 34:
        raise ReviewPackageError("ZIP must have 34 individual GeoJSON members")
    return accepted


def load_zip(path: Path, roster: Path, expected_sha: str | None = None):
    from shapely.geometry import shape, mapping
    from pyproj import Geod

    if not path.is_file() or path.stat().st_size > MAX_ZIP:
        raise ReviewPackageError("Missing/oversized source ZIP")
    digest = sha256_file(path)
    if expected_sha is not None and digest != expected_sha.lower():
        raise ReviewPackageError("Uploaded source does not match pinned SHA-256")
    listing = json.loads(roster.read_text(encoding="utf-8"))["units"]
    expected = {str(p["code"]).zfill(2): p for p in listing}
    if len(expected) != 34:
        raise ReviewPackageError("34-province roster is invalid")
    seen, provinces, offshore = set(), [], []
    geod = Geod(ellps="WGS84")
    with ZipFile(path) as archive:
        entries = candidates(archive)
        if archive.testzip() is not None:
            raise ReviewPackageError("ZIP CRC verification failed")
        for entry in entries:
            with archive.open(entry) as stream:
                raw = stream.read(entry.file_size + 1)
            if len(raw) != entry.file_size:
                raise ReviewPackageError("Uncompressed member size mismatch")
            doc = json.loads(raw)
            if (doc.get("type") != "FeatureCollection" or "crs" in doc or
                    not isinstance(doc.get("features"), list) or
                    len(doc["features"]) != 1):
                raise ReviewPackageError("Expected one WGS84 provincial feature")
            feature = doc["features"][0]
            props = feature.get("properties") or {}
            code = str(props.get("ma_tinh", "")).zfill(2)
            name = props.get("ten_tinh")
            if (code not in expected or normalize(name) != normalize(expected[code]["name"])
                    or code in seen):
                raise ReviewPackageError("Unknown/duplicate 34-province code/name")
            seen.add(code)
            geom = feature["geometry"]
            polygon = shape(geom)
            if polygon.geom_type != "MultiPolygon" or polygon.is_empty or not polygon.is_valid:
                raise ReviewPackageError("Invalid provincial MultiPolygon")
            west, south, east, north = polygon.bounds
            if not (90 <= west <= east <= 130 and 0 <= south <= north <= 30):
                raise ReviewPackageError("Coordinates outside broad screening extent")
            provinces.append({
                "code": code, "name": expected[code]["name"],
                "geometry": geom,
                "member_sha256": hashlib.sha256(raw).hexdigest(),
            })
            if code in REMOTE_LONGITUDE_SCREEN:
                for idx, part in enumerate(polygon.geoms):
                    if part.centroid.x <= REMOTE_LONGITUDE_SCREEN[code]:
                        continue
                    signed_area, perimeter = geod.geometry_area_perimeter(part)
                    offshore.append({
                        "code": code, "index": idx, "geometry": mapping(part),
                        "area_km2": abs(signed_area) / 1e6,
                        "compactness": (4 * math.pi * abs(signed_area) / perimeter**2)
                        if perimeter else 0,
                    })
    if len(seen) != 34:
        raise ReviewPackageError("Missing province(s)")
    return digest, sorted(provinces, key=lambda p: p["code"]), sorted(
        offshore, key=lambda p: (p["code"], p["index"])
    )


def build(zip_path: Path, roster: Path, target: Path,
          expected_sha: str | None = None) -> dict:
    from shapely.geometry import shape
    import fiona

    archive_hash, provinces, offshore = load_zip(zip_path, roster, expected_sha)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix=".incoming-", suffix=".gpkg", dir=target.parent, delete=False
        ) as handle:
            temporary = Path(handle.name)
        temporary.unlink()
        with fiona.open(
            temporary, "w", driver="GPKG", layer="province34_review",
            crs="EPSG:4326", schema={
                "geometry": "MultiPolygon",
                "properties": {"code": "str:2", "name": "str:80",
                               "source_sha": "str:64", "status": "str:32"}
            }
        ) as output:
            for p in provinces:
                output.write({"type": "Feature", "geometry": p["geometry"],
                              "properties": {
                                  "code": p["code"], "name": p["name"],
                                  "source_sha": p["member_sha256"],
                                  "status": "QUARANTINE_NOT_P0",
                              }})
        with fiona.open(
            temporary, "w", driver="GPKG",
            layer="offshore_components_REVIEW_ONLY", crs="EPSG:4326",
            schema={"geometry": "Polygon",
                    "properties": {"source_code": "str:2",
                                   "component": "int", "area_km2": "float",
                                   "status": "str:32"}}
        ) as output:
            for item in offshore:
                output.write({"type": "Feature", "geometry": item["geometry"],
                              "properties": {"source_code": item["code"],
                                             "component": item["index"],
                                             "area_km2": round(item["area_km2"], 5),
                                             "status": "REVIEW_NOT_LANDFILL"}})
        # No geometry edits may be silently introduced by GIS export.
        source_by_code = {p["code"]: shape(p["geometry"]) for p in provinces}
        with fiona.open(temporary, layer="province34_review") as layer:
            records = list(layer)
            if len(records) != 34:
                raise ReviewPackageError("GeoPackage lost province features")
            for feature in records:
                code = feature["properties"]["code"]
                if code not in source_by_code or not source_by_code[code].equals(
                        shape(feature["geometry"])):
                    raise ReviewPackageError("GeoPackage geometry changed during export")
        with fiona.open(temporary, layer="offshore_components_REVIEW_ONLY") as layer:
            if len(layer) != len(offshore):
                raise ReviewPackageError("Offshore review component count changed")
        os.replace(temporary, target)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    stats = {}
    for code, threshold in REMOTE_LONGITUDE_SCREEN.items():
        selected = [p for p in offshore if p["code"] == code]
        stats[code] = {
            "count": len(selected),
            "area_over_25_km2": sum(p["area_km2"] > 25 for p in selected),
            "area_over_100_km2": sum(p["area_km2"] > 100 for p in selected),
            "largest_area_km2": round(max((p["area_km2"] for p in selected), default=0), 2),
            "centroid_longitude_screen": threshold,
        }
    return {
        "schema_version": 1,
        "status": "QUARANTINED_GPKG_GEOMETRY_ROUNDTRIP_NOT_P0",
        "source_filename": zip_path.name,
        "source_sha256": archive_hash,
        "output_filename": target.name,
        "output_sha256": sha256_file(target),
        "output_bytes": target.stat().st_size,
        "crs": "EPSG:4326",
        "layer_counts": {"province34_review": 34,
                         "offshore_components_REVIEW_ONLY": len(offshore)},
        "offshore_centroid_screen": stats,
        "provenance_verified": False,
        "redistribution_license_verified": False,
        "independent_official_geometry_verified": False,
        "offshore_island_land_area_verified": False,
        "geometry_roundtrip_equal": True,
        "maplibre_activation_allowed": False,
        "p0_pass": False,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("source_zip", type=Path)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--roster", type=Path, default=Path(__file__).resolve().parents[1] /
                   "assets/geo/province34_names_2025.json")
    p.add_argument("--require-sha256")
    p.add_argument("--manifest", type=Path)
    args = p.parse_args()
    try:
        result = build(args.source_zip, args.roster, args.output, args.require_sha256)
        code = 0
    except (OSError, ValueError, TypeError, RuntimeError) as exc:
        result = {"status": "GPKG_BUILD_FAILED", "p0_pass": False,
                  "maplibre_activation_allowed": False, "error": str(exc)}
        code = 1
    raw = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.manifest:
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text(raw, encoding="utf-8")
    print(raw, end="")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
