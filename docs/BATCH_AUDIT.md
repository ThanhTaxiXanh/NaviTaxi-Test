# Resumable GIS batch scans

The original PMTiles files are **kept in quarantine**. The scanner saves
checkpoint JSON after every contiguous index-entry chunk, letting a local
scan resume without repeating earlier geometry checks.

## Use

Run the following from the repository root. Python 3.10+ is required.

```bash
python3 -m pipeline.spatial_batch_runner /path/to/hotosm_vnm_roads_osm.pmtiles --chunk-size 256 --max-new-chunks 2 --output-dir audit-output
python3 -m pipeline.spatial_batch_runner /path/to/hotosm_vnm_buildings_osm.pmtiles --chunk-size 256 --max-new-chunks 2 --output-dir audit-output

# Repeat the same command without --max-new-chunks to complete all chunks.
python3 -m pipeline.spatial_batch_runner /path/to/hotosm_vnm_roads_osm.pmtiles --chunk-size 256 --output-dir audit-output
```

To continue incrementally, rerun an identical command with the same chunk
size and output directory. Do **not** change chunk size or edit checkpoints
in the middle of a run. Archived partial results are validated before reuse.

## Checkpoints and trust

- Source filename, file byte size and SHA-256 are checked against the
  `assets/manifests/ingestion_inventory.json` quarantine catalog.
- The complete PMTiles directory is inspected before the chunk plan runs.
- New chunk reports are flushed and atomically renamed on local storage.
- Existing reports are checked for source identity, exact range, blocked
  approval status and merger schema before they can be reused.
- `batch_state.json` records new/resumed chunks, scanned entries and precise
  missing ranges; `merged.json` contains the aggregated diagnostic report.
- The full index can be complete only if no entry range is missing or
  overlapping. Run-length entries may still need separate addressed-tile
  geographical checks. Full index coverage is **not P0 approval**.

These reports are untrusted local metadata, not digitally signed evidence.
Commit reviewed aggregate reports only, never unreviewed PMTiles archives
or sensitive raw feature properties. Both the runner and merger permanently
report `p0_status: BLOCKED` regardless of progress.

**Limitations:** No official sovereign GIS reference has been approved.
No prohibited-claim geometry overlay, Android screenshot parity, online/offline
render parity or source licensing review is completed. The release gate stays
fail-closed. This is a CLI audit, not an Android offline download manager.

