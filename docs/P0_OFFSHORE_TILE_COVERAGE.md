# P0 coverage gap: mainland PMTiles do not cover Hoàng Sa/Trường Sa

**Verified from uploaded PMTiles v3 source headers and all 183 official
Hoàng Sa/Trường Sa name-point coordinates (TT33/2024).** The three PMTiles
archives cover mainland geographic extents, not the two offshore island groups.

| Archive | Maximum eastern longitude (WGS84) | Official 183 points inside bbox |
| --- | ---: | ---: |
| HOTOSM roads | 109.461296°E | 0 |
| HOTOSM buildings | 109.449674°E | 0 |
| HOTOSM POIs | 109.458161°E | 0 |
| **Union** | **109.461296°E** | **0/183** |

The island-name reference points are between roughly 111.1975°E and
117.0075°E, well outside mainland archive coverage. No plausible unverified
VN-2000 datum adjustment (~0.23 km in prior sensitivity check) bridges the
minimum several-hundred-kilometre longitude gap. This is a **coverage
deficiency**, regardless of acceptable administrative polygon generalization.

The user-uploaded 34-province GeoJSON includes offshore administrative
MultiPolygons, but the three separate HOTOSM PMTiles do **not** automatically
gain those islands. A new, reviewed, legally usable island/sea **vector
tile source** is required. Island name points do not supply coastlines or
legal maritime borders.

For the currently quarantined archives, the statement “all relevant island
names have tiles” is false. An archive bounding box *covering* a coordinate
is necessary but insufficient proof that the tile actually contains the
desired layer, feature and readable label.

## Reproduce on the local PMTiles (never upload unlicensed archives)

```bash
python -m pipeline.official_island_point_catalog --pdf /path/to/TT33-annex.pdf --points-output audit-output/official-183.json
python -m pipeline.p0_source_coverage audit-output/official-183.json --data-root /path/to/pmtiles-directory --output audit-output/p0-offshore-coverage.json
```

SHA-256 of all three input PMTiles is required to match
`assets/manifests/ingestion_inventory.json`. Output is a metadata report
not containing source feature geometries. A pinned reproduction from the
original user uploads is in
`docs/audits/2026-11-11-mainland-pmtiles-offshore-coverage.json`.

**Release verdict: P0 BLOCKED.** The current MapLibre style also has no
source layers. Future visual QA must demonstrate the actual island/sea
tile source and approved labels at multiple zooms, light/dark and offline
rather than relying on bounding boxes.
