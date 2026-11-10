# Android developer setup

**Not yet device-tested.** This repository was bootstrapped without the Flutter SDK or Android SDK in the authoring environment. Follow these steps to generate Flutter's standard Android support files (including Gradle wrapper executable/binary and generated registration), build, and report the actual result.

1. Install Flutter >= 3.29 (use compatible stable), Android SDK / API 36, and JDK 21. Enable USB debugging on test phone.
2. From repo root run:
   ```bash
   flutter doctor -v
   flutter create --platforms=android --project-name=navi_taxi_test --org=vn.navitaxi .
   flutter pub get
   flutter analyze
   flutter test
   python3 -m unittest discover -s tests/sovereignty -v
   flutter devices
   flutter run -d <device-id>
   ```
3. Android Gradle Plugin is pinned to 8.13.2 and Gradle 8.13. If `flutter create` regenerates templates, inspect the diff and keep manually audited Kotlin/Gradle settings.
4. Map UI should show a neutral empty style and P0 warning. It must not display unknown third-party tiles or unsafe labels.
5. Release APK/AAB is prohibited until `python3 pipeline/vietnam_sovereignty_validator.py --repo-root .` passes with real documentary, tile and rendered-image evidence and Android device tests. Development debug signatures are not production signing.

No GPS or offline download is claimed complete.
