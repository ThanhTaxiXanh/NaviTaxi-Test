# GIS reviewer APK: source-derived overview, NOT P0

This dedicated **debug-only** APK displays a simplified overview from the
user-uploaded `GeoJSON 34 Tinh VN.zip` SHA-256
`51779d2585600ec053827a60890ba61cd2192f19b5ee153d38be18a2611d24cd`.
It is intentionally a separate preview screen implemented with Flutter Canvas:
**it does not change MapLibre's P0 gate or release manifest**.

Review content:
- Simplified provincial administrative polygons and 34 province name anchors.
- 315 points at centroids/representative positions of offshore administrative
  polygon components. **Orange markers are not land island outlines.**
- 14 audited outlier island/reef/name-point positions from TT33/2024;
  coordinates are VN-2000 numeric points viewed approximately against
  WGS84 source outlines, not a certified datum transformation.
- Three large Vietnamese review labels: Hoàng Sa, Trường Sa and Biển Đông.
  Group label anchors Hoàng Sa/Trường Sa are from TT33 reference label
  coordinates; Biển Đông label is an illustrative overview anchor.
- Zoom/pan and shortcuts to entire country and both archipelagos.

**Limitations**: This is a lossy, coarse overview for HUMAN INSPECTION, not
the complete original 34 GeoJSON. It omits road/base tiles, physical
coastline details, maritime boundaries and traffic signs. The original
geometries must stay quarantined until provenance and redistribution rights
are verified. The compressed preview is a derivative of user-supplied
materials, not a transferable authoritative basemap. Do not publish the
review APK as a navigation product.

To create the special debug APK:

```bash
flutter build apk --debug --dart-define=NAVITAXI_REVIEW_MODE=true
```

Regular debug builds without the define show the P0-blocked MapLibre screen.
**Release and profile builds cannot select preview mode**, even if the
dart-define is added: the app requires `kDebugMode`.
Neither version can satisfy P0 or activate external tile sources.

GitHub Actions builds a separate artifact
`NaviTaxi-GIS-34Tinh-REVIEW-DEBUG-APK-NOT-P0`, including an APK SHA-256 file.
Only the user should use this for manual review. Review notes and screenshots
do not automatically authorize P0. Source rights and full Android MapLibre
testing remain pending.
