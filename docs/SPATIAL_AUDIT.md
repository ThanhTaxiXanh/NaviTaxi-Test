# MVT feature spatial diagnostics (WGS84)

Stage 2 of the PMTiles intake: `pipeline/mvt_spatial_audit.py` decodes actual MVT
feature geometry, validates command structure and converts individual vertices
from tile-local coordinates into **WGS84 lon/lat**. It reports the union of
decoded **feature bounding boxes**, not just parent tile footprints.

## Commands

Run from the repository root with the original user-provided PMTiles archives
(large archives are intentionally **not** stored in Git):

```bash
python3 -m pipeline.mvt_spatial_audit /path/to/hotosm_vnm_roads_osm.pmtiles --layer roads --max-tiles 128 --report /tmp/roads-spatial.json
python3 -m pipeline.mvt_spatial_audit /path/to/hotosm_vnm_buildings_osm.pmtiles --layer buildings --max-tiles 128 --report /tmp/buildings-spatial.json
python3 -m pipeline.mvt_spatial_audit /path/to/hotosm_vnm_points_of_interest_osm.pmtiles --layer points_of_interest --max-tiles 128 --report /tmp/pois-spatial.json

# Inspect every index payload entry (may take a long time):
python3 -m pipeline.mvt_spatial_audit /path/to/hotosm_vnm_roads_osm.pmtiles --layer roads --max-tiles 0
```

`--max-tiles 0` removes the sampling limit on **directory payload entries**.
If a PMTiles entry has `run_length > 1`, a repeated tile payload represents
multiple addressed tile IDs. The scanner uses the first tile ID for its
geographic transformation, so this is still **not** a complete per-addressed-
tile spatial pass when run-length entries are present.

## Checked

- PMTiles v3 full root/leaf index integrity, declared counts and tile offsets
- MVT protobuf source layer, feature properties, tags and geometry commands
- Valid MoveTo/LineTo/ClosePath sequencing for point, line and polygon paths
- Per-vertex Web Mercator-to-WGS84 conversion using Hilbert tile IDs
- Decoded feature bounding envelopes, geometry counts and names to review
- Existing reference manifest state and strict P0 blocking

Coordinates from buffered vector features can extend outside the nominal tile
bbox. Geographic longitude is reported unwrapped for diagnostics. A feature
envelope is neither a polygon intersection test nor an official jurisdiction.

## Real local archive sample (2026-11-10 UTC)

| Source | Index entries | Sampled | Features | Vertices | Name fields |
| --- | ---: | ---: | ---: | ---: | ---: |
| Roads | 21,055 | 128 | 109,431 | 468,163 | 356,524 |
| Buildings | 18,890 | 128 | 19,959 | 89,060 | 61,938 |
| POI | 4,209 | 128 | 6,448 | 19,421 | 29,271 |
| **Total** | **44,154** | **384** | **135,838** | **576,644** | **447,733** |

These data were computed against the supplied PMTiles archives (the exact SHA-
256 values are recorded in the intake inventory) using deterministic spread
sampling. None of the sampled name fields produced a review-word example.
This does **not** prove prohibited graphics/claims are absent from other tiles,
or that any given administrative relationship is correct.

The machine-readable aggregate report is in
`docs/audits/2026-11-10-feature-spatial-sample.json`. It records no raw features
or private source data. The full WGS84 feature envelopes for selected entries
do not establish coverage of Hoàng Sa, Trường Sa or Biển Đông.

## Unfulfilled P0 requirements

The official reference manifest at `assets/geo/approved_reference.json`
still has status `pending`. The scanner reports `REFERENCE_PENDING` and
`review_overlay=NOT_RUN`. It deliberately **never** issues P0 PASS, including
if someone edits the manifest to claim approval. The independent validation
of official source documents and actual feature-vs-reference polygon overlap
is not yet implemented. Coastlines, illegal-claim lines, admin affiliations,
style render, glyphs and Android visual regressions remain unverified.

Continue to enforce the existing release gate until all sources, geometry
evidence and Android/airplane-mode test cases have been independently vetted.

