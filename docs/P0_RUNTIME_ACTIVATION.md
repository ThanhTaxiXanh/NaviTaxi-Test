# P0 runtime activation is bound to a verified build

The default app and GitHub debug builds never contain approved map data and always render a safe source-free background.

A changed JSON field (e.g. setting `p0_pass=true` or inserting a fake 64-character SHA-256) is **not sufficient** to activate a MapLibre map. `MapRelease` also requires a matching SHA-256 bound into the compiled Flutter build via `--dart-define=NAVITAXI_P0_EVIDENCE_SHA256=...` and a fixed approved style asset path. No such build-time certificate is configured in current CI.

This is defense-in-depth only. A deliberate custom build with a spoofed build-time define does **not** establish authenticity. Any approved release must be built by a protected, independently reviewed release workflow verifying the entire certificate's content and dependencies, provenance, data licensing, independent geometry/semantics, offline parity and **actual Android MapLibre screenshot** evidence. Those controls remain incomplete. The release validator intentionally blocks P0.

`StylePolicy` additionally refuses fake background layers that share the Hoàng Sa/Trường Sa/Biển Đông layer IDs; it requires dedicated visible symbol layers, correct Vietnamese text and feature-ID filters. **A passing style structure test does not imply the coordinates or rendered map are correct**.

Tests: `flutter test test/map_release_test.dart`, and `python -m unittest discover -s tests/sovereignty` for the server-side gate.
