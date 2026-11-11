# Android PMTiles intake: fail-closed quarantine

## Scope and status

This implementation copies **a user-selected PMTiles v3 archive** from Android's
Storage Access Framework into app-private storage. It is not the complete offline
download manager required by the Master Prompt.

Only the three user-provided HOTOSM archives with exact known byte lengths and
SHA-256 digests are accepted. Archive names are selected from a fixed catalog,
not taken from untrusted document providers.

- Android document picker: no broad media or filesystem permission
- Background streaming I/O (128 KiB chunks), bounded to expected size
- SHA-256 verification, eight-byte PMTiles v3 magic check, fd sync
- Temporary .partial file in the same directory as destination
- Rename into quarantine only after the file matches the intake catalog
- Cancelled or failed imports remove the partial file
- Delete and verify operations are constrained to the catalog
- All files live in `filesDir/offline-quarantine`, outside the MapLibre source tree

**These data are never activated as a basemap.** A checksum authenticates the
expected uploaded bytes only, not sovereign geometry, licensing or correctness.
A complete MVT/geometry P0 pipeline, approved reference data, controlled style
and Android screenshots are still mandatory. Kotlin always marks imported data
`p0Approved=false`, even after SHA-256 succeeds.

## Try on a development Android phone

1. Download the debug APK from the latest successful GitHub Actions artifact.
2. Copy one of the three unmodified .pmtiles uploads to the phone.
3. Open NaviTaxi > storage icon > choose archive > select matching file.
4. Import may read hundreds of MB; a completed intake is listed as **Quarantine**.
5. Tap Verify to recompute SHA-256, or Delete to remove an archive.
6. The map remains intentionally source-free and P0-blocked with or without network.

## Not implemented (must not be misrepresented as complete)

WorkManager download, pause/resume, remote manifest signing, update/rollback,
cross-archive style binding, manifest approval, online/offline switching and
rendering from PMTiles are **not implemented** in this stage.

## PMTiles to MapLibre integration, debug reviewer only (12/11/2026)

The DEBUG GIS review APK can now **read and display** the three specific
user-uploaded HOTOSM PMTiles v3 archives *after the user manually imports
them on the Android phone*. This does not enable any archive in the regular
P0-blocked release map.

### What is implemented

- Kotlin SAF importer retains the existing 8-byte PMTiles magic, exact length
  and SHA-256 checks. New `getVerifiedArchivePathsDebug` re-hashes the private
  files and refuses access outside a debuggable Android application.
- Dart reader supports PMTiles v3 index, root/leaf directories, zoom/Hilbert
  tile IDs, raw/gzip MVT and bounds checks. Unit tests use synthetic PMTiles,
  **not** fabricated country boundaries.
- A private, tokenized `http://127.0.0.1:<ephemeral-port>` endpoint supplies
  vector tiles to MapLibre Native. HTTP cleartext is allowed only in the
  Android **debug** manifest. Only imported filenames in the allowlist work.
- Roads appear as orange lines; buildings as grey building footprints; POIs
  as green circles. There are no text-label layers from HOTOSM archives.
  This avoids letting any unreviewed external place/administrative labels
  override NaviTaxi's province, commune or Hoàng Sa/Trường Sa/sea labels.
- Existing 34 province and 3,319 ward representative text overlays (plus
  two special-district reference anchors), and the three required sea/island
  labels remain independent of the base archives. These are **reviewed label
  anchors**, not legal or official boundaries.

### On an Android phone, without a computer

1. Download/install the latest `NaviTaxi-GIS-34Tinh-REVIEW-DEBUG-APK-NOT-P0`
   from the GitHub Actions **Artifacts** for this PR.
2. Download/save your three **original unchanged** PMTiles files to the
   phone: `hotosm_vnm_roads_osm.pmtiles`,
   `hotosm_vnm_buildings_osm.pmtiles`,
   `hotosm_vnm_points_of_interest_osm.pmtiles`. The APK intentionally
   does **not** bundle ~341 MB of diagnostic tiles.
3. Open NaviTaxi -> GIS preview -> tap the layers icon -> in the MapLibre
   viewer tap the **storage** icon -> select each matching downloaded PMTiles
   file. Import succeeds only if checksum/byte length match the catalog.
4. Return to the map. The app re-verifies sources and renders those that
   were imported. Roads begin at medium zoom; buildings/POIs require
   zooming into an urban area. Test once with Internet disabled.
5. If any tile source does not load, consult Android logcat or retry the
   per-file verify option. Do not infer a file is valid from its name.

### Explicit limits

- There is **no downloadable online basemap** and no navigation/routing,
  road directionality, speed limits, traffic conditions, GPS positioning,
  address-to-coordinate geocoding, or turn-by-turn guidance in this release.
- Source archives were previously verified as **mainland-only**. They
  cannot prove or supply offshore island coverage; missing offshore tile
  content is not fixed by textual labels alone.
- Tests for parser/style and a successful debug APK build do **not**
  constitute Android visual QA. A real phone reviewer must inspect tile
  decoding, style placement and offline parity.
- User asserts permission to use project materials for testing, but a
  production/public release still needs source provenance and relevant
  attribution/redistribution checks. The normal P0 gate stays BLOCKED.
- Road/POI source attribution for the original archives is to
  **© OpenStreetMap contributors / HOT**. Project name labels are independent.

No data is uploaded from the phone or read from an unapproved remote map
source by the loopback MVT server.
