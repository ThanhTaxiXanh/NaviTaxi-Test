#!/usr/bin/env python3
"""Review local 34-province GeoJSON for NaviTaxi without activating map layers.

Accepts files supplied by a human after checking the original GIS publisher,
download rights, map version and citation. Never downloads or scrapes a website.
Structural validation is not an official administrative or maritime GIS review.
No generated approval or P0 PASS is possible through this program.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import unicodedata
from zipfile import BadZipFile, ZipFile

MAX_BYTES = 256 * 1024 * 1024
MAX_FEATURES = 10000
MAX_VERTICES = 5_000_000
PROVINCE_COUNT = 34


class ProvinceIntakeError(ValueError):
    """Unparseable, unsupported, or suspicious GeoJSON input."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_geojson_bytes(path: Path) -> tuple[bytes, str]:
    if not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise ProvinceIntakeError("Source missing or above 256 MiB input limit")
    if path.suffix.lower() in (".json", ".geojson"):
        return path.read_bytes(), path.name
    if path.suffix.lower() != ".zip":
        raise ProvinceIntakeError(
            "Use GeoJSON or ZIP containing one GeoJSON file; convert "
            "SHP/KML/GPKG using GDAL ogr2ogr with -t_srs EPSG:4326 first"
        )
    try:
        with ZipFile(path) as z:
            infos = z.infolist()
            if len(infos) > 100:
                raise ProvinceIntakeError("ZIP has too many members")
            for member in infos:
                parts = member.filename.replace("\\", "/").split("/")
                if (member.filename.startswith(("/", "\\")) or
                        ".." in parts or ":" in parts[0] or
                        member.file_size > MAX_BYTES):
                    raise ProvinceIntakeError("Unsafe or oversized ZIP member")
            candidates = [
                item for item in infos
                if not item.is_dir()
                and item.filename.lower().endswith((".geojson", ".json"))
                and not item.filename.startswith("__MACOSX/")
            ]
            if len(candidates) not in (1, PROVINCE_COUNT):
                raise ProvinceIntakeError(
                    "ZIP must contain one 34-feature GeoJSON or 34 single-province GeoJSON files"
                )
            if len(candidates) == 1:
                member = candidates[0]
                with z.open(member) as stream:
                    raw = stream.read(MAX_BYTES + 1)
                if len(raw) > MAX_BYTES:
                    raise ProvinceIntakeError("Uncompressed GeoJSON exceeds 256 MiB")
                return raw, member.filename

            # GIS.vn exports one FeatureCollection with one MultiPolygon for
            # each province. Ignore macOS resource-fork files; DO NOT extract.
            features = []
            unpacked_bytes = 0
            for member in candidates:
                unpacked_bytes += member.file_size
                if unpacked_bytes > MAX_BYTES:
                    raise ProvinceIntakeError("ZIP expands beyond 256 MiB safety limit")
                with z.open(member) as stream:
                    payload = stream.read(member.file_size + 1)
                if len(payload) != member.file_size:
                    raise ProvinceIntakeError("Truncated GeoJSON member")
                try:
                    item = json.loads(payload)
                except (ValueError, UnicodeDecodeError) as exc:
                    raise ProvinceIntakeError("Malformed provincial GeoJSON") from exc
                if (not isinstance(item, dict) or
                        item.get("type") != "FeatureCollection" or
                        "crs" in item or
                        not isinstance(item.get("features"), list) or
                        len(item["features"]) != 1):
                    raise ProvinceIntakeError(
                        "Expected one WGS84 GeoJSON feature per province file"
                    )
                feature = item["features"][0]
                if (not isinstance(feature, dict) or
                        feature.get("type") != "Feature" or
                        not isinstance(feature.get("properties"), dict) or
                        not isinstance(feature["properties"].get("ten_tinh"), str) or
                        not isinstance(feature["properties"].get("ma_tinh"), str)):
                    raise ProvinceIntakeError("Missing ten_tinh/ma_tinh in province file")
                features.append(feature)
            raw = json.dumps(
                {"type": "FeatureCollection", "features": features},
                ensure_ascii=False, separators=(",", ":")
            ).encode("utf-8")
            return raw, "34_separate_GeoJSON_members_merged_in_memory"
    except (BadZipFile, EOFError, RuntimeError) as exc:
        raise ProvinceIntakeError("Broken or unreadable GeoJSON ZIP") from exc


def _number(value: object) -> float:
    if (type(value) not in (int, float) or not math.isfinite(value)):
        raise ProvinceIntakeError("Nonfinite or nonnumeric WGS84 coordinate")
    return float(value)


def _polygon_rings(geometry: dict) -> list:
    kind = geometry.get("type")
    coordinates = geometry.get("coordinates")
    if kind == "Polygon":
        polygons = [coordinates]
    elif kind == "MultiPolygon":
        polygons = coordinates
    else:
        raise ProvinceIntakeError("Province geometry must be Polygon/MultiPolygon")
    if not isinstance(polygons, list) or not polygons:
        raise ProvinceIntakeError("Empty polygon geometry")
    return polygons


def inspect_collection(raw: bytes, name_field: str) -> dict:
    try:
        document = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProvinceIntakeError("Source is not valid UTF-8 GeoJSON") from exc
    if not isinstance(document, dict) or document.get("type") != "FeatureCollection":
        raise ProvinceIntakeError("Expected GeoJSON FeatureCollection")
    # GeoJSON RFC 7946 uses WGS84 long/lat, not projected metres.
    # Input in another CRS must be explicitly reprojected before inspection.
    if "crs" in document:
        raise ProvinceIntakeError("Legacy GeoJSON CRS detected; reproject to EPSG:4326")
    features = document.get("features")
    if not isinstance(features, list) or not 0 < len(features) <= MAX_FEATURES:
        raise ProvinceIntakeError("Invalid GeoJSON feature count")
    if len(features) != PROVINCE_COUNT:
        raise ProvinceIntakeError(
            f"Expected exactly {PROVINCE_COUNT} province features, got {len(features)}; "
            "merge split provincial geometries first if appropriate"
        )
    names: list[str] = []
    unique: set[str] = set()
    vertices = 0
    rings_total = 0
    bounds = [float("inf"), float("inf"), float("-inf"), float("-inf")]
    try:
        from shapely.geometry import shape
    except ImportError:
        shape = None
    errors = []
    topology_status = "NOT_CHECKED_SHAPELY_UNAVAILABLE" if shape is None else "CHECKED"
    for index, item in enumerate(features):
        if not isinstance(item, dict) or item.get("type") != "Feature":
            raise ProvinceIntakeError(f"Feature {index} is not a GeoJSON feature")
        properties = item.get("properties")
        if not isinstance(properties, dict) or not isinstance(
            properties.get(name_field), str
        ):
            raise ProvinceIntakeError(
                f"Feature {index} has no string property {name_field!r}"
            )
        name = unicodedata.normalize("NFC", properties[name_field].strip())
        if not name:
            raise ProvinceIntakeError(f"Feature {index} has an empty province name")
        key = unicodedata.normalize("NFKC", name).casefold()
        if key in unique:
            raise ProvinceIntakeError(f"Duplicate province name: {name}")
        unique.add(key)
        names.append(name)
        geometry = item.get("geometry")
        if not isinstance(geometry, dict):
            raise ProvinceIntakeError(f"Feature {index} missing polygon geometry")
        for polygon in _polygon_rings(geometry):
            if not isinstance(polygon, list) or not polygon:
                raise ProvinceIntakeError(f"Feature {index}: empty polygon ring list")
            for ring in polygon:
                if not isinstance(ring, list) or len(ring) < 4:
                    raise ProvinceIntakeError(f"Feature {index}: invalid polygon ring")
                rings_total += 1
                first = last = None
                for position in ring:
                    if not isinstance(position, list) or len(position) not in (2, 3):
                        raise ProvinceIntakeError("Coordinates must be lon/lat pairs")
                    x, y = _number(position[0]), _number(position[1])
                    if not (-180 <= x <= 180 and -90 <= y <= 90):
                        raise ProvinceIntakeError("Out-of-range WGS84 coordinate")
                    # This is a broad screening extent, not a sovereign boundary.
                    if not (90 <= x <= 130 and 0 <= y <= 30):
                        raise ProvinceIntakeError(
                            "Coordinate outside broad Vietnam intake screening extent"
                        )
                    bounds[0] = min(bounds[0], x)
                    bounds[1] = min(bounds[1], y)
                    bounds[2] = max(bounds[2], x)
                    bounds[3] = max(bounds[3], y)
                    last = (x, y)
                    if first is None:
                        first = last
                    vertices += 1
                    if vertices > MAX_VERTICES:
                        raise ProvinceIntakeError("Source exceeds vertex safety limit")
                if first != last:
                    raise ProvinceIntakeError(f"Feature {index}: unclosed polygon ring")
        if shape is not None:
            polygon = shape(geometry)
            if polygon.is_empty or not polygon.is_valid or polygon.area <= 0:
                errors.append(
                    f"Invalid/empty planar polygon topology for feature {index}: {name}"
                )
    if errors:
        raise ProvinceIntakeError("; ".join(errors[:8]))
    return {
        "feature_count": len(features),
        "distinct_name_count": len(unique),
        "name_field": name_field,
        "names_in_source": names,
        "vertices_checked": vertices,
        "rings_checked": rings_total,
        "bbox_wgs84": bounds,
        "topology_status": topology_status,
        "topology_approach": "Shapely planar validity; not official political boundary",
    }


def audit_file(path: Path, *, name_field: str = "name",
               source_url: str | None = None,
               publisher: str | None = None,
               license_note: str | None = None) -> dict:
    """Return portable diagnostic data, without endorsing or redistributing source."""
    result = {
        "schema_version": 1,
        "status": "INTAKE_FAILED",
        "p0_status": "BLOCKED",
        "maplibre_activation_allowed": False,
        "official_geometry_verified": False,
        "source_document_verified": False,
        "license_and_redistribution_verified": False,
        "input_file": path.name,
        "provenance": {
            "user_declared_source_url": source_url,
            "user_declared_publisher": publisher,
            "user_declared_license_note": license_note,
            "website_access_verified": False,
        },
        "required_next_evidence": [
            "Verifiable original 34-unit GIS source and publication date",
            "Proof of permission to reuse/redistribute vector data and attribution",
            "Coordinate reference system and latest administrative map version",
            "Independent official geometry/topology comparison",
            "Hoang Sa, Truong Sa, Bien Dong sources and visual QA",
            "MapLibre online/offline and Android screenshot regression",
        ],
    }
    try:
        raw, inside_name = _read_geojson_bytes(path)
        if (inside_name == "34_separate_GeoJSON_members_merged_in_memory"
                and name_field == "name"):
            # The provider's actual field is ten_tinh, not name.
            name_field = "ten_tinh"
        report = inspect_collection(raw, name_field)
        result.update({
            "status": "QUARANTINED_34_PROVINCES_STRUCTURAL_CHECK_NOT_P0",
            "original_input_sha256": sha256_file(path),
            "geojson_sha256": hashlib.sha256(raw).hexdigest(),
            "geojson_member": inside_name,
            "inspection": report,
        })
    except (OSError, ValueError, TypeError) as exc:
        result["error"] = str(exc)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--name-field", default="name")
    parser.add_argument("--source-url", help="Provenance URL, not a download request")
    parser.add_argument("--publisher")
    parser.add_argument("--license-note")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    report = audit_file(
        args.source, name_field=args.name_field,
        source_url=args.source_url, publisher=args.publisher,
        license_note=args.license_note,
    )
    encoded = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0 if report["status"].startswith("QUARANTINED_34_") else 1


if __name__ == "__main__":
    raise SystemExit(main())
