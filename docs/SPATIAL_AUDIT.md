# MVT feature spatial diagnostics (WGS84)

Stage 2 of the PMTiles intake: `pipeline/mvt_spatial_audit.py` decodes actual MVT
feature geometry, validates every coordinate pair and converts its extrema
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


### Performance note

For bounding-box-only diagnostics, the inverse Web Mercator function is monotone. The scanner validates every decoded vertex but projects only minimum/maximum tile-local coordinates per feature to WGS84. A 128-entry Buildings sample produced an identical JSON report before and after this optimization. It does not reconstruct the full geodesic feature geometry or test polygon topology.

## Resumable, hash-bound contiguous chunk scans

Large archives can be scanned one consecutive index range at a time. This
allows interruption without losing earlier diagnostic results:

```bash
python3 -m pipeline.mvt_spatial_audit /path/to/poi.pmtiles --layer points_of_interest --max-tiles 0 --start-entry 0 --entry-count 2104 --report /tmp/poi-000.json
python3 -m pipeline.mvt_spatial_audit /path/to/poi.pmtiles --layer points_of_interest --max-tiles 0 --start-entry 2104 --entry-count 2105 --report /tmp/poi-001.json
python3 -m pipeline.spatial_report_merge /tmp/poi-000.json /tmp/poi-001.json --output /tmp/poi-merged.json
```

Use the **actual filename** from the intake catalog. The example above uses
a placeholder short path; the merge requires SHA-256, archive byte size and
source-layer to match `assets/manifests/ingestion_inventory.json`.

Chunk reports store their `[start_entry, end_entry_exclusive)` range and full
archive SHA-256. Merger refuses overlapping ranges, mismatched digests,
unrecognized source archives and gaps in the index. With `--allow-partial`,
it emits the explicit missing index ranges instead of misrepresenting
coverage. All merged results still have `p0_status=BLOCKED`.

### Full POI scan performed locally

The entire 4,209-entry POI file was scanned with the geometry pipeline and
independently re-scanned in two contiguous chunks (2,104 + 2,105 entries).
The two modes agreed exactly on feature counts, WGS84 bounds, vertex totals,
name-field totals and all collected review candidates.

- Total features: **357,628** (164,751 points; 12,964 lines; 179,913 polygons)
- Decoded geometry vertices: **1,120,681**; reviewed name fields: **1,643,167**
- WGS84 union envelope: `[102.1647620, 8.4295196, 109.4581604, 23.3834058]`
- Two flagged fields, **one POI**, name_en and name_latin:
  `View of the South China Sea`

This text is an English name for a viewpoint POI within the input data.
It is **not evidence that MapLibre renders an illegal claim line or a sea label**.
Alternative English labels may remain in query data; release presentation
must still follow verified Vietnamese-language style rules.

The machine-readable results are in
`docs/audits/2026-11-10-poi-full-index-spatial.json`. This documents **full
index-entry coverage of POI**, not full sovereign/legal GIS verification.
All associated source geometry remains quarantined.

### Buildings partial chunk smoke test

Two local contiguous Buildings ranges (`[0,1024)` and `[1024,2048)`) were scanned and merged. They cover **2,048/18,890 index entries**, **1,037,382 features**, and **4,350,788 decoded vertices**. The merger explicitly returned `PARTIAL_INDEX_GEOMETRY_DIAGNOSTICS_NOT_P0` with missing index interval `[2048,18890]`. **Do not cite this partial pass as full Buildings coverage.**
