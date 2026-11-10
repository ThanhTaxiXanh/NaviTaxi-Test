# Android-first architecture (2026-11-10)

## Decision log

1. **Flutter/Dart presentation**: MapScreen, UI widgets and camera controller. Android only at this stage.
2. **MapLibre GL 0.27.1**: native vector rendering, style JSON, PMTiles sources. Requires Flutter >= 3.29, Dart >= 3.7, JDK 21. Pin exact version until a verified upgrade.
3. **Kotlin Android bridge**: minimal MethodChannel for app-scoped storage diagnostics; durable WorkManager downloads follow after manifest/checksum design. No broad filesystem permission.
4. **Source repositories**: independent online vector tile sources, approved geography references, PMTiles offline packages. No public raster provider may override sovereign display policy.
5. **Policy gates**: Flutter `MapRelease` blocks unapproved styles; independent Python validator blocks release. A Dart structural check is **not** a sovereignty validation.
6. **Native PMTiles**: MapLibre Android >= 11.7 supports `pmtiles://https://` and `pmtiles://file://`; it does **not** give PMTiles a built-in offline download/cache system. Use app-managed atomic download+hash validation before activating local archives.
7. **Fail-closed boot**: until approved, only a neutral background renders. Do not use the MapLibre demo style as a production basemap.

## Data flow

GIS intake -> provenance/usage review -> geometry normalization -> authoritative reference reconciliation -> MVT generation -> full tile semantic/geometry scan -> style checks -> PMTiles packaging -> integrity checks -> approved manifest -> Android screenshot/airplane-mode regression -> release.

## Constraints

- Three HOTOSM uploads contain mainland roads, buildings and POIs, not a complete sovereign base map.
- These datasets have no explicit authoritative ocean/island geometry here and their metadata bounds end near 109.46°E.
- Do not infer maritime boundary geometry or fabricate island polygons to satisfy tests.
- Jurisdiction policy is a *presentation configuration*, not an authoritative legal finding.
- Coastline, admin boundaries, maritime claims and water are distinct GIS feature classes.
- Captured screenshots must be checked on actual Android hardware before any P0 = PASS claim.

## Delivery phases

0. **Current**: bootstrap, quarantine manifest, PMTiles audit, P0 validator skeleton, unit tests.
1. Approved online basemap with validated Vietnamese labels, location and search.
2. Kotlin WorkManager/offline package manager with pause/resume/hash/install/rollback.
3. Nationwide+island coverage verified; device performance profiling.
4. Traffic/GIS extensions; iOS only after Android acceptance.

## Reference documents

- https://pub.dev/packages/maplibre_gl/versions/0.27.1
- https://maplibre.org/maplibre-native/android/examples/data/PMTiles/
- https://developer.android.com/build/releases/about-agp

## Android release build guard

`assembleRelease` and `bundleRelease` depend on Gradle `verifySovereigntyP0`, which invokes the independent Python gate. Without the full source, MVT and screenshot evidence, Gradle exits nonzero. Debug builds can still exercise the shell.
