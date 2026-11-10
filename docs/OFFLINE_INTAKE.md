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
