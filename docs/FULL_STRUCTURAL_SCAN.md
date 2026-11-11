# Full index-entry MVT structural scan of supplied HOTOSM archives

**Date:** 2026-11-11 UTC. **Status:** full diagnostic scan, P0 BLOCKED.

This is the first end-to-end structural read of all source index entries.
The three original user-provided PMTiles archives were checked against their
catalog SHA-256 digests. Each archive had `run_length=1` for every entry, so
the 44,154 index entries correspond to 44,154 addressed tile payloads.

| Source | Scanned tile payloads | MVT feature instances | Geometry vertices |
| --- | ---: | ---: | ---: |
| Roads | 21,055 | 10,157,687 | 57,892,171 |
| Buildings | 18,890 | 4,172,084 | 18,373,831 |
| POI | 4,209 | 357,628 | 1,120,681 |
| **Total** | **44,154** | **14,687,399** | **77,386,683** |

**These are tile feature instances across different zoom levels, not distinct
real-world road segments, buildings or places.** No licensing, ownership or
administrative sovereignty inference is justified from the counts.

## Method and cross-check

The initial Python WGS84 feature scanner was too slow for complete Roads and
Buildings scans in a single time-bounded invocation. A local independent
C++17/zlib MVT parser completed structural checks and geographical envelope
calculation for all three archives. The original archive SHA-256 digests were
checked separately with Python. Full POI metrics from both parsers matched
exactly. The first 256 Roads entries also matched exactly on point, line and
polygon counts, geometry vertices, paths and name fields.

The machine-readable result is at
`docs/audits/2026-11-11-all-archives-full-structural-scan.json`.
The local C++ prototype's source and binary hashes are included in that
record for provenance; this prototype is **not** a certified release tool.
The repository's reproducible Python `spatial_batch_runner.py` and chunk
merger remain the primary independent audit implementation.

Two native substring hints were found in the full POI archive: English and
Latin name properties for one viewpoint named `View of the South China Sea`.
The native filter was narrower than the case-insensitive Python policy filter.
Accordingly, a zero native hint count for Roads/Buildings is **not** proof
that those archives contain no problematic strings or geometries.

## What this does not prove

- It does not validate legal country boundaries, foreign administrative
  affiliations, island polygons or possible maritime claim lines.
- It does not prove that Hoàng Sa, Trường Sa or Biển Đông are represented
  in a complete, correct and licensed basemap.
- It does not check MapLibre rendered labels, UI styles, zoom collisions,
  Android screenshots, switching networks or offline parity.
- It does not clear redistribution or attribution of HOTOSM/OSM data.

The archives remain quarantined and the independent release validator must
continue to fail closed. Do not mark P0 PASS on the basis of this report.

