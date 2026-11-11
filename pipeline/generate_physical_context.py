#!/usr/bin/env python3
"""Generate unapproved physical context layers, never a sovereignty map.

Source: locally installed basemap-data 2.0.0 intermediate GSHHG 2.3.6
coastlines/land and political-boundary segments. Package metadata declares
LGPL-3.0-or-later. Neither Vietnamese cartographic authority nor detailed
offshore-island completeness nor all downstream distribution obligations
are established by this metadata.

Only uses installed local packages; performs no network requests.
"""
from __future__ import annotations
import argparse
import hashlib
from importlib import metadata
import json
from pathlib import Path
import math

from mpl_toolkits.basemap import Basemap
from shapely.geometry import Polygon, LineString, box, mapping
from shapely.ops import unary_union

REGION = (97.0, 0.0, 127.0, 27.0)  # analysis viewport, NOT marine jurisdiction
PROJECT = 'NaviTaxi-Test'
SOURCE_PACKAGE = 'basemap-data'
SOURCE_VERSION = '2.0.0'
GRID_SIMPLIFY_DEG = 0.003


def rounded(obj):
    if isinstance(obj, float):
        return round(obj, 6)
    if isinstance(obj, dict):
        return {k: rounded(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [rounded(v) for v in obj]
    return obj


def write_layer(root: Path, filename: str, features: list[dict], purpose: str) -> dict:
    content = {
        'type': 'FeatureCollection',
        'name': filename.removesuffix('.geojson'),
        'metadata': {
            'status': 'quarantine',
            'p0_approved': False,
            'source': 'basemap-data 2.0.0, intermediate physical/political boundary data',
            'purpose': purpose,
            'jurisdiction': 'not assessed',
            'suitable_for_release': False,
            'zoom_generalization': 'intermediate; small offshore features may be absent',
        },
        'features': features,
    }
    p = root / filename
    p.write_text(json.dumps(content, ensure_ascii=False, sort_keys=True, separators=(',', ':'))+'\n',encoding='utf-8')
    h = hashlib.sha256(p.read_bytes()).hexdigest()
    return {'file': filename, 'features': len(features), 'bytes': p.stat().st_size,
            'sha256': h, 'status': 'quarantine', 'release_allowed': False}


def candidates(output: Path) -> dict:
    version = metadata.version(SOURCE_PACKAGE)
    if version != SOURCE_VERSION:
        raise ValueError(f'basemap-data version mismatch: {version}, expected {SOURCE_VERSION}')
    # Cylindrical projection preserves longitude/latitude values of coordinates.
    m = Basemap(projection='cyl', llcrnrlon=REGION[0], llcrnrlat=REGION[1],
                urcrnrlon=REGION[2], urcrnrlat=REGION[3], resolution='i')
    view = box(*REGION)
    land = []
    for p in m.landpolygons:
        shape = Polygon(p.get_coords()).intersection(view)
        if shape.is_valid and not shape.is_empty and shape.area > 1e-8:
            land.append(shape.simplify(GRID_SIMPLIFY_DEG, preserve_topology=True))
    if len(land) < 30:
        raise ValueError('Suspiciously few GSHHS land components')
    land_union = unary_union(land)
    water = view.difference(land_union)
    output.mkdir(parents=True, exist_ok=True)

    def row(geom, layer, index):
        if geom.is_empty or not geom.is_valid:
            raise ValueError('Invalid generated geometry')
        data = rounded(mapping(geom))
        return {'type': 'Feature', 'id': f'{layer}-{index:04d}',
                'properties': {'class': layer, 'verification': 'candidate_only'},
                'geometry': data}

    results=[]
    results.append(write_layer(
        output, 'land_context.geojson',
        [row(g, 'physical_land', i) for i,g in enumerate(land)],
        'physical coast and land only; contains NO administrative ownership claims'))
    small = [p for p in land if p.area < .1 and not p.is_empty]
    results.append(write_layer(
        output, 'small_landforms_review.geojson',
        [row(g, 'small_physical_landform', i) for i,g in enumerate(small)],
        'small land polygons, NOT verified identities of Hoang Sa or Truong Sa'))
    coast=[]
    for coords in m.coastsegs:
        ln = LineString(coords).intersection(view)
        if not ln.is_empty and ln.length > .002:
            coast.append(ln.simplify(GRID_SIMPLIFY_DEG, preserve_topology=True))
    results.append(write_layer(
        output, 'coastlines_context.geojson',
        [row(g, 'coastline_physical', i) for i,g in enumerate(coast)],
        'physical shoreline only; no country or sea boundary inference'))
    results.append(write_layer(
        output, 'water_context.geojson',
        [row(water, 'physical_water_context', 0)],
        'background physical water outside land polygons; NOT maritime legal zones'))

    # International political linework has no established Vietnam official
    # provenance. Store it in a separately named review-only layer. Prevent
    # marine lines from being mixed in by clipping to terrestrial features.
    raw_country_lines, _ = m._readboundarydata('countries')
    review_lines=[]
    land_envelope=land_union.buffer(.005)
    for coords in raw_country_lines:
        shape=LineString(coords).intersection(view).intersection(land_envelope)
        if not shape.is_empty and shape.length > .01:
            review_lines.append(shape.simplify(GRID_SIMPLIFY_DEG, preserve_topology=True))
    results.append(write_layer(
        output, 'land_borders_REVIEW_ONLY.geojson',
        [row(g,'unverified_terrestrial_border',i) for i,g in enumerate(review_lines)],
        'unverified political boundary candidates; prohibited from basemap rendering'))
    # Do not invent a Hoang Sa / Truong Sa / Bien Dong anchor point or maritime
    # boundary from approximate coastlines.
    manifest={
        'schema_version':1,
        'status':'quarantine',
        'p0_pass':False,
        'official_vietnam_reference_verified':False,
        'license_clearance_complete':False,
        'source_package':SOURCE_PACKAGE,
        'source_version':SOURCE_VERSION,
        'declared_package_license':'LGPL-3.0-or-later',
        'source_origin':'Bundled GSHHS-derived physical data and political boundary linework',
        'source_original_version':'GSHHG 2.3.6 (as stated in installed basemap-data 2.0.0 METADATA)',
        'viewport_wgs84':[REGION[0],REGION[1],REGION[2],REGION[3]],
        'viewport_is_not_a_maritime_boundary':True,
        'missing_verification':[
            'Vietnamese official cartographic source and version',
            'Hoang Sa and Truong Sa detailed island and reef geometries',
            'Vietnamese official boundary and island administrative attribution',
            'LGPL-3.0-or-later attribution/distribution obligations and official source acceptance',
            'Spatial comparison with approved official references',
            'MapLibre and Android rendered screenshot review',
        ],
        'layers':results,
        'ui_activation_allowed':False,
    }
    (output/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    return manifest


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,default=Path('data/candidates/physical_context'))
    args=parser.parse_args()
    print(json.dumps(candidates(args.output_dir),ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()
