# PMTiles local audit procedure

The archived HOTOSM exports are intentionally excluded from the repository.

Run this locally when the original uploads are present:

```bash
python3 pipeline/vietnam_sovereignty_validator.py --mode audit --repo-root . --data-root /path/to/pmtiles
```

This reads each PMTiles v3 header, JSON metadata, source-layer names, file byte length and complete SHA-256 digest. `INTAKE_OK_NOT_P0` means the files match the inventory **only**.

`--mode release` independently checks approval, authoritative geometry, style, evidence hashes and screenshots. In the current phase it deliberately returns `FULL_P0_ENGINE_INCOMPLETE`: a structural MVT decoder and WGS84 feature-envelope scanner now exist, and the complete POI index has been scanned, but Roads/Buildings still lack complete geometry scans. More importantly, independent comparison with approved official GIS references, legal-claim geometry detection and Android visual regression have not been implemented. **Do not bypass the blocker by editing the manifest.**

## PMTiles directory tree scan (new)

For each user-supplied archive, verify the full PMTiles v3 root/leaf index,
monotonic tile IDs, tile-data offsets and declared tile counts:

```bash
python3 pipeline/pmtiles_directory_audit.py /path/to/pmtiles/*.pmtiles
```

The output `INTAKE_INDEX_OK_NOT_P0` means the internal archive directory
structure is consistent. It does not scan MVT label/geometry payloads and
does **not** approve sovereign territorial depiction or offline activation.

## Feature-level spatial audit and resumable chunks

See [SPATIAL_AUDIT.md](SPATIAL_AUDIT.md) for commands, real local POI scan evidence, and checksum-bound contiguous range merging. Neither a complete index scan nor a merged diagnostic report can issue P0 approval.
