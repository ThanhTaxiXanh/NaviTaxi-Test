# Android screenshot capture: source-free P0-safe fallback

This opt-in CI workflow boots a real Android x86_64 emulator, installs the
**debug** APK with P0 blocked and captures PNG screenshots in four conditions:
light online, dark online, dark airplane mode and light after reconnect.
It checks screenshot file integrity and attaches a SHA-256 manifest.

**These images only exercise the source-free BLOCKED state.** They do not
verify correct Hoàng Sa/Trường Sa/Biển Đông labels, imagery, borders, roads,
online/offline parity or permission to redistribute GIS. No
`official_island_labels_rendered_and_verified=true` claim is made.

To perform full P0 visual review later, the project needs a legally cleared
approved geodata bundle, a controlled MapLibre style, evidence of all 10
required cameras/zoom/theme/layer/network transitions, comparison against
official map sources and independent human review. Emulator screenshots from a
blank map MUST NOT be used as release evidence for those conditions.

Workflow `Android MapLibre safe fallback screenshots - NOT P0` runs when
its scripts change or on manual dispatch. It is deliberately independent of
the normal debug APK workflow and not an automatic release promotion.
