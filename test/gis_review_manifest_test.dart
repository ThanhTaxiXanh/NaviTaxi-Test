import 'package:flutter_test/flutter_test.dart';
import 'package:navi_taxi_test/features/gis_review/province34_review.dart';

void main() {
  Map<String, dynamic> valid() => <String, dynamic>{
    'schema_version': 1,
    'status': 'quarantined_for_offline_review_not_p0',
    'p0_pass': false,
    'maplibre_activation_allowed': false,
    'source_license_verified': false,
    'official_boundary_verified': false,
    'offshore_land_classification_verified': false,
    'source_file_redistributed': false,
    'review_geopackage_included_in_apk': false,
    'geometry_roundtrip_checked': true,
    'province_features': 34,
    'offshore_review_components': 315,
    'source_zip_sha256': List.filled(64, 'a').join(),
    'review_geopackage_sha256': List.filled(64, 'b').join(),
    'offshore_by_code': [
      {'code': '48', 'name': 'Đà Nẵng', 'count': 18, 'area_over_25_km2': 10},
      {'code': '56', 'name': 'Khánh Hòa', 'count': 297, 'area_over_25_km2': 30},
    ],
    'remaining_checks': <String>['Rà soát dữ liệu GIS'],
  };

  test('read-only quarantine metadata is parsed', () {
    final record = Province34Review.fromJson(valid());
    expect(record.provinceCount, 34);
    expect(record.offshoreCount, 315);
    expect(record.reviewRegions.length, 2);
  });

  test('forged P0 approval never passes', () {
    final json = valid()..['p0_pass'] = true;
    expect(() => Province34Review.fromJson(json), throwsFormatException);
  });

  test('forged asset activation never passes', () {
    final json = valid()..['review_geopackage_included_in_apk'] = true;
    expect(() => Province34Review.fromJson(json), throwsFormatException);
  });

  test('mismatched offshore counts rejected', () {
    final json = valid()..['offshore_review_components'] = 300;
    expect(() => Province34Review.fromJson(json), throwsFormatException);
  });

  test('invalid source SHA-256 rejected', () {
    final json = valid()..['source_zip_sha256'] = 'wrong';
    expect(() => Province34Review.fromJson(json), throwsFormatException);
  });

  test('bundled review manifest is structurally safe', () async {
    TestWidgetsFlutterBinding.ensureInitialized();
    final summary = await Province34Review.load();
    expect(summary.provinceCount, 34);
    expect(summary.offshoreCount, 315);
  });
}
