# PMTiles local audit procedure

The archived HOTOSM exports are intentionally excluded from the repository.

Run this locally when the original uploads are present:

```bash
python3 pipeline/vietnam_sovereignty_validator.py --mode audit --repo-root . --data-root /path/to/pmtiles
```

This reads each PMTiles v3 header, JSON metadata, source-layer names, file byte length and complete SHA-256 digest. `INTAKE_OK_NOT_P0` means the files match the inventory **only**.

`--mode release` independently checks approval, authoritative geometry, style, evidence hashes and screenshots. In the current phase it deliberately returns `FULL_P0_ENGINE_INCOMPLETE` because a full MVT semantic/spatial decoder and Android visual comparison have not yet been implemented. **Do not bypass the blocker by editing the manifest.**
