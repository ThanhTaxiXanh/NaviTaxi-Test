# PMTiles MVT payload audit

## Scope and safety

Stage-1 scanner: `pipeline/mvt_tile_audit.py` reads actual decoded MVT feature fields, names,
source-layer IDs, tags and tile-local geometry commands from PMTiles v3.
It first validates **the full PMTiles directory index** via `pmtiles_directory_audit.py`.
It does **not** validate coastlines, national boundaries, maritime legal claims,
administrative authority, MapLibre rendering, font glyphs or label collisions.

## Commands (from repository root, Python 3.10+)

```bash
python3 -m pipeline.mvt_tile_audit /path/to/hotosm_vnm_roads_osm.pmtiles --layer roads --max-tiles 8
python3 -m pipeline.mvt_tile_audit /path/to/hotosm_vnm_buildings_osm.pmtiles --layer buildings --max-tiles 8
python3 -m pipeline.mvt_tile_audit /path/to/hotosm_vnm_points_of_interest_osm.pmtiles --layer points_of_interest --max-tiles 8

# Complete payload scan, resource-intensive on large archives:
python3 -m pipeline.mvt_tile_audit /path/to/hotosm_vnm_roads_osm.pmtiles --layer roads --max-tiles 0 --report /tmp/roads-mvt-report.json
```

`--max-tiles N` selects N evenly spaced PMTiles directory entries. Sampling is
deterministic, not statistically representative. `--max-tiles 0` scans all
payload entries; budget disk/CPU time for millions of vector features.

Checks include strict protobuf varint/length validation, typed value wire types,
UTF-8, source-layer identity, feature tag indexes, and MVT geometry command
integrity. Inflated tile size is capped to 24 MiB as a resource guard.

Suspicious place names such as Sansha, Xisha, Nansha, South China Sea, or
nine-dash-line descriptions are **review candidates only**, not proof of a
political claim or of its absence. A clean sample never implies compliance.

## Local intake sample (November 2026)

| PMTiles archive | Total index entries | Sampled entries | MVT features | Tile-local coordinates |
| --- | ---: | ---: | ---: | ---: |
| roads | 21,055 | 8 | 36,272 | 82,127 |
| buildings | 18,890 | 8 | 2,003 | 8,876 |
| points_of_interest | 4,209 | 8 | 107 | 238 |

The local sample checked 24 payload entries, 38,382 MVT features and 91,241
tile-local coordinate points. No suspect strings were observed in checked
name/admin fields. These are **intake diagnostics**, not `Sovereignty_P0=PASS`.

## Still required for P0

Obtain licensed and approved official Vietnamese sea/island geometry and
reference maps; perform full feature-coordinate transformations, geometry
intersection and forbidden-claim spatial review; validate online/offline
source parity and render screenshots across cameras, zooms and themes on
real Android devices. Keep release blocked until the independent P0 engine
and all required evidence are complete.
