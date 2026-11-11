#!/usr/bin/env python3
"""Verify candidate GeoJSON integrity, geometry, and fail-closed release status.

Physical/topological QA only. Does not authorize legal or national borders,
maritime jurisdiction, detailed islands, MapLibre rendering, or P0 release.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path

EXPECTED = {
    'land_context.geojson': {'Polygon', 'MultiPolygon'},
    'small_landforms_review.geojson': {'Polygon', 'MultiPolygon'},
    'coastlines_context.geojson': {'LineString', 'MultiLineString'},
    'water_context.geojson': {'Polygon', 'MultiPolygon'},
    'land_borders_REVIEW_ONLY.geojson': {'LineString', 'MultiLineString'},
}


def iter_positions(value):
    if (isinstance(value, list) and len(value) >= 2 and
            all(isinstance(x, (float, int)) for x in value[:2])):
        yield value
    elif isinstance(value, list):
        for entry in value:
            yield from iter_positions(entry)


def validate(source_dir: Path, check_topology: bool = True,
             expected_manifest: Path | None = None) -> dict:
    errors = []
    try:
        m = json.loads((source_dir / 'manifest.json').read_text(encoding='utf-8'))
    except (ValueError, OSError) as exc:
        return {'status': 'FAILED', 'errors': [f'invalid manifest: {exc}'],
                'p0_pass': False}
    if expected_manifest is not None:
        try:
            expected = json.loads(expected_manifest.read_text(encoding='utf-8'))
            if m != expected:
                errors.append('Generated manifest differs from pinned, reviewed intake inventory')
        except (OSError, ValueError) as exc:
            errors.append(f'Expected manifest cannot be read: {exc}')
    if (m.get('schema_version') != 1 or m.get('status') != 'quarantine' or
            m.get('p0_pass') is not False or m.get('ui_activation_allowed') is not False or
            m.get('official_vietnam_reference_verified') is not False or
            m.get('license_clearance_complete') is not False or
            m.get('viewport_is_not_a_maritime_boundary') is not True):
        errors.append('Candidate sovereignty/approval gate has been altered')
    if m.get('viewport_wgs84') != [97.0, 0.0, 127.0, 27.0]:
        errors.append('Unexpected analysis viewport or jurisdiction claim')
    layers = m.get('layers', [])
    if (not isinstance(layers, list) or len(layers) != len(EXPECTED)
            or {layer.get('file') for layer in layers} != set(EXPECTED)):
        errors.append('Missing, duplicated or unexpected GIS layers')
        layers = layers if isinstance(layers, list) else []
    counts = {}
    shapely_layers = {}
    shapely_available = False
    if check_topology:
        try:
            from shapely.geometry import shape
            from shapely.ops import unary_union
            shapely_available = True
        except ImportError:
            errors.append('Shapely is required for the topology audit')
    for layer in layers:
        name = layer.get('file')
        if name not in EXPECTED:
            continue
        try:
            raw = (source_dir / name).read_bytes()
            doc = json.loads(raw)
            if (layer.get('bytes') != len(raw) or
                    hashlib.sha256(raw).hexdigest() != layer.get('sha256')):
                errors.append(f'{name}: byte length/SHA-256 mismatch')
            if (layer.get('status') != 'quarantine' or
                    layer.get('release_allowed') is not False or
                    doc.get('type') != 'FeatureCollection' or
                    doc.get('metadata', {}).get('status') != 'quarantine' or
                    doc.get('metadata', {}).get('p0_approved') is not False or
                    doc.get('metadata', {}).get('suitable_for_release') is not False):
                errors.append(f'{name}: approval status or GeoJSON type invalid')
            features = doc.get('features', [])
            if not isinstance(features, list) or not features or len(features) != layer.get('features'):
                errors.append(f'{name}: unexpected feature count')
                continue
            shapes = []
            for index, item in enumerate(features):
                geometry = item.get('geometry', {})
                props = item.get('properties', {})
                if (item.get('type') != 'Feature' or
                        geometry.get('type') not in EXPECTED[name] or
                        props.get('verification') != 'candidate_only' or
                        'name' in props or 'jurisdiction' in props or 'admin' in props):
                    errors.append(f'{name}: unexpected geometry or political labels')
                coords = list(iter_positions(geometry.get('coordinates', [])))
                if not coords:
                    errors.append(f'{name}: empty geographic coordinates')
                for coord in coords:
                    if (not all(type(v) in (float, int) and math.isfinite(v)
                                for v in coord[:2]) or
                            not (97-1e-5 <= coord[0] <= 127+1e-5) or
                            not (-1e-5 <= coord[1] <= 27+1e-5)):
                        errors.append(f'{name}: invalid/outside viewport coordinate')
                        break
                if shapely_available:
                    geom = shape(geometry)
                    if geom.is_empty or not geom.is_valid:
                        errors.append(f'{name}: invalid/empty topology at feature {index}')
                    shapes.append(geom)
            counts[name] = len(features)
            if shapely_available:
                shapely_layers[name] = unary_union(shapes)
        except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
            errors.append(f'{name}: {exc}')
    overlap = gap = None
    if shapely_available and all(name in shapely_layers for name in (
            'land_context.geojson', 'water_context.geojson')):
        from shapely.geometry import box
        land = shapely_layers['land_context.geojson']
        water = shapely_layers['water_context.geojson']
        viewport = box(97, 0, 127, 27)
        overlap = land.intersection(water).area
        gap = viewport.difference(land.union(water)).area
        if overlap > 1e-9 or gap > 1e-9:
            errors.append('Land/water masks overlap or leave gaps')
        if 'small_landforms_review.geojson' in shapely_layers and not (
                land.buffer(1e-6).covers(shapely_layers['small_landforms_review.geojson'])):
            errors.append('Small landforms lie outside physical land polygons')
    return {
        'status': 'CANDIDATE_GEOMETRY_CHECKS_PASSED_NOT_P0' if not errors else 'FAILED',
        'p0_pass': False,
        'reference_authority': 'NOT_VERIFIED',
        'license_provenance': 'DECLARED_IN_PACKAGE_METADATA_ONLY',
        'source_package': 'basemap-data 2.0.0',
        'upstream_dataset': 'GSHHG 2.3.6 (per installed package metadata)',
        'geojson_features_checked': counts,
        'topology_checked_with_shapely': shapely_available,
        'land_water_overlap_sq_degrees': overlap,
        'land_water_gap_sq_degrees': gap,
        'marine_boundaries_verified': False,
        'offshore_island_completeness_verified': False,
        'errors': errors,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('input_dir', type=Path)
    p.add_argument('--no-topology', action='store_true')
    p.add_argument('--expected-manifest', type=Path)
    p.add_argument('--report', type=Path)
    args = p.parse_args()
    result = validate(args.input_dir, not args.no_topology,
                      args.expected_manifest)
    text = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(text, encoding='utf-8')
    print(text, end='')
    raise SystemExit(0 if result['status'] ==
                     'CANDIDATE_GEOMETRY_CHECKS_PASSED_NOT_P0' else 1)


if __name__ == '__main__':
    main()
