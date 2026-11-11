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
    'official_point_review': {
      'datum': 'VN-2000',
      'datum_transform_approved_offshore': false,
      'island_outline_geometry_verified': false,
      'legal_maritime_boundary_verified': false,
      'official_pdf_sha256':
          'acde9b561eca24312b81efdcb36a22a8fc74e2dcb431f6c206199ef72c98e841',
      'total': 183,
      'hoang_sa': 50,
      'truong_sa': 133,
      'inside_source_polygon': 141,
      'within_2km': 156,
      'flagged_over_5km': 14,
      'named_island_point_corroborated': 4,
      'named_island_outlines_missing': 4,
      'reef_or_shoal_exposure_unknown': 6,
      'submerged_or_region_label': 4,
    },
    'remaining_checks': <String>['Rà soát dữ liệu GIS'],
  };

  test('read-only quarantine metadata is parsed', () {
    final record = Province34Review.fromJson(valid());
    expect(record.provinceCount, 34);
    expect(record.offshoreCount, 315);
    expect(record.reviewRegions.length, 2);
    expect(record.officialPointReview.total, 183);
    expect(record.officialPointReview.reefExposureUnknown, 6);
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

  test('cannot falsely claim offshore datum or island outline approval', () {
    final data = valid();
    final review = data['official_point_review'] as Map<String, dynamic>;
    review['datum_transform_approved_offshore'] = true;
    expect(() => Province34Review.fromJson(data), throwsFormatException);
    review['datum_transform_approved_offshore'] = false;
    review['island_outline_geometry_verified'] = true;
    expect(() => Province34Review.fromJson(data), throwsFormatException);
  });

  test('bundled review manifest is structurally safe', () async {
    TestWidgetsFlutterBinding.ensureInitialized();
    final summary = await Province34Review.load();
    expect(summary.provinceCount, 34);
    expect(summary.offshoreCount, 315);
  });
}
