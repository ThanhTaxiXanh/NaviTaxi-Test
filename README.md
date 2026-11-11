# NaviTaxi Việt Nam — Vietnam Sovereign Map Engine

Android-first Flutter + Kotlin + MapLibre foundation for a Vietnamese online/offline mapping platform.

> **Release status: P0 BLOCKED.** No approved territorial dataset or Android visual-regression evidence has been supplied. The app deliberately renders an empty background, not unverified basemap tiles. Do not advertise this source tree as a validated map application.

## Repository structure

- `lib/`: Flutter presentation, offline quarantine UI and policy-gated map bootstrap
- `android/`: Kotlin MethodChannel, SAF archive import and Android project configuration
- `assets/styles/`: candidate MapLibre style, currently source-free
- `assets/manifests/`: release policy flags
- `pipeline/`: PMTiles intake, WGS84 feature review, chunk merger and P0 validation tooling
- `tests/sovereignty/`: independent Python validation unit tests
- `test/`: Dart policy tests
- `docs/`: architecture, source provenance and Android setup

## Run (after installing Flutter >= 3.29, Android SDK and JDK 21)

```bash
flutter create --platforms=android --project-name=navi_taxi_test --org=vn.navitaxi .
flutter pub get
flutter test
flutter run -d <android-device-id>
python3 -m unittest discover -s tests/sovereignty -v
python3 pipeline/vietnam_sovereignty_validator.py --repo-root .
```

The last command **must fail** until all required P0 evidence, source provenance and Android screenshots have been approved. A running shell app is **not** completion of P1/P2 or P0.

See [34-province GIS source intake](docs/GISVN_34_PROVINCES.md), [candidate GIS context](docs/PHYSICAL_CONTEXT_CANDIDATES.md), [full structural scan evidence](docs/FULL_STRUCTURAL_SCAN.md), [resumable batch audit](docs/BATCH_AUDIT.md), [WGS84 feature audit](docs/SPATIAL_AUDIT.md), [MVT payload audit](docs/MVT_TILE_AUDIT.md), [offline intake](docs/OFFLINE_INTAKE.md), [architecture](docs/ARCHITECTURE.md), [data provenance](docs/DATA_PROVENANCE.md), [Android setup](docs/BUILD_ANDROID.md) and the [original Master Prompt](docs/MASTER_PROMPT.txt).
