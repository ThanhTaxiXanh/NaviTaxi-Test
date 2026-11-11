# Quarantined physical GIS context (NOT an official Vietnam map)

This package builds candidate physical land, small landforms, coastline,
water-context polygons and land-only boundary review lines. It is not a
legally approved national map and must not become an active MapLibre source.

## Provenance and licensing

- Installed package: basemap-data 2.0.0.
- Original dataset declared in its installed package metadata: GSHHG 2.3.6,
  processed with GMT 5.x.
- Package metadata declares LGPL-3.0-or-later for the land/sea, coastline
  and political boundary datasets. Keep COPYING and COPYING.LESSER notices.
- References listed in installed metadata, not externally reverified during
  this run: https://github.com/matplotlib/basemap and
  https://www.soest.hawaii.edu/pwessel/gshhg
- Analysis viewport: [97,0,127,27] in WGS84 (west,south,east,north).
  This rectangle is NOT a maritime jurisdiction or legal territorial line.
- At this resolution small offshore islets and reefs are incomplete. Neither
  Hoàng Sa nor Trường Sa is identified or authoritative in these layers.

## Candidate layers

| GeoJSON | Features | Status |
| --- | ---: | --- |
| land_context.geojson | 130 | quarantine |
| small_landforms_review.geojson | 107 | quarantine |
| coastlines_context.geojson | 153 | quarantine |
| water_context.geojson | 1 | quarantine |
| land_borders_REVIEW_ONLY.geojson | 28 | never render before official review |

The 107 small land polygons are geometrically selected landform candidates, not
mapped or named Hoàng Sa or Trường Sa features. The land-border candidate is
separate because political boundary claims cannot be certified from this source.

The water layer is only a physical land complement inside the crop rectangle.
It is NOT the geographic or legal extent of Biển Đông, territorial waters,
exclusive economic zones, or any maritime claim line.

## Rebuild and independently check

Use Python 3.12 or higher in the repository root:

    python -m pip install -r pipeline/requirements-context-gis.txt
    python -m pipeline.generate_physical_context --output-dir build/physical_context
    python -m pipeline.verify_physical_context build/physical_context --expected-manifest assets/geo/physical_context_candidate_manifest.json --report build/physical_context/validation_report.json
    python -m pipeline.bundle_context_licenses --output-dir build/physical_context/LICENSES

The pinned manifest contains exact feature counts, byte lengths and SHA-256
for each candidate GeoJSON. A different output must be reviewed, not silently
accepted. The validator checks validity of all geometries with Shapely,
coordinate bounds, no administrative ownership labels, and exact complement
of physical land/water polygons (zero overlap and zero missing area).

The workflow named Quarantined physical GIS candidates repeats the build and
uploads the artifact navitaxi-physical-gis-QUARANTINE-NOT-P0 for manual review.

## Explicit blockers

1. Vietnamese-authorized cartographic reference and reuse rights.
2. Detailed GIS geometry and confirmed location/name of Hoàng Sa, Trường Sa
   and other small offshore features.
3. Official terrestrial and any genuinely licensed legal marine boundary data.
4. Independent spatial source-to-authority verification and official source
   acceptance documents.
5. Complete Android MapLibre visual proof across styles, zoom, day/night and
   online/offline conditions.

Do not change the P0 BLOCKED release policy or the pending official reference
because a candidate dataset passed structural checks. Do not enable candidate
political boundaries in the Flutter app.
