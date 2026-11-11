import 'dart:convert';
import 'package:flutter/services.dart';

/// Read-only source-audit summary; cannot enable rendering.
class Province34Review {
  const Province34Review({
    required this.provinceCount, required this.offshoreCount,
    required this.sourceSha256, required this.packageSha256,
    required this.reviewRegions, required this.remainingChecks,
    required this.officialPointReview,
  });
  final int provinceCount;
  final int offshoreCount;
  final String sourceSha256;
  final String packageSha256;
  final List<OffshoreRegion> reviewRegions;
  final List<String> remainingChecks;
  final OfficialIslandPointReview officialPointReview;

  static final RegExp _checksum = RegExp(r'^[a-f0-9]{64}$');

  factory Province34Review.fromJson(Map<String, dynamic> json) {
    if (json['schema_version'] != 1 ||
        json['status'] != 'quarantined_for_offline_review_not_p0' ||
        json['p0_pass'] != false ||
        json['maplibre_activation_allowed'] != false ||
        json['source_license_verified'] != false ||
        json['official_boundary_verified'] != false ||
        json['offshore_land_classification_verified'] != false ||
        json['source_file_redistributed'] != false ||
        json['review_geopackage_included_in_apk'] != false ||
        json['geometry_roundtrip_checked'] != true ||
        json['province_features'] != 34) {
      throw const FormatException('GIS review metadata not safe for display');
    }
    final total = json['offshore_review_components'];
    final source = json['source_zip_sha256'];
    final package = json['review_geopackage_sha256'];
    final entries = json['offshore_by_code'];
    final remaining = json['remaining_checks'];
    if (total is! int || total < 0 ||
        source is! String || !_checksum.hasMatch(source) ||
        package is! String || !_checksum.hasMatch(package) ||
        entries is! List || entries.length != 2 ||
        remaining is! List || !remaining.every((v) => v is String)) {
      throw const FormatException('Invalid GIS review counts/checksums');
    }
    final regions = entries.map((value) {
      if (value is! Map<String, dynamic>) {
        throw const FormatException('Invalid GIS offshore review row');
      }
      return OffshoreRegion.fromJson(value);
    }).toList(growable: false);
    if (regions.map((r) => r.code).toSet().length != 2 ||
        regions.fold<int>(0, (sum, r) => sum + r.count) != total) {
      throw const FormatException('Inconsistent GIS review region counts');
    }
    return Province34Review(
      provinceCount: 34, offshoreCount: total,
      sourceSha256: source, packageSha256: package,
      reviewRegions: regions,
      remainingChecks: List<String>.unmodifiable(remaining.cast<String>()),
      officialPointReview: OfficialIslandPointReview.fromJson(
        _officialPoints(json),
      ),
    );
  }

  static Future<Province34Review> load() async {
    final raw = await rootBundle.loadString('assets/manifests/province34_review.json');
    final object = jsonDecode(raw);
    if (object is! Map<String, dynamic>) {
      throw const FormatException('Not a GIS review JSON object');
    }
    return Province34Review.fromJson(object);
  }
}

/// Island point counts are read-only QA, NEVER a source of approved polygons.
Map<String, dynamic> _officialPoints(Map<String, dynamic> json) {
  final value = json['official_point_review'];
  if (value is! Map<String, dynamic>) {
    throw const FormatException('Missing official island point QA summary');
  }
  return value;
}

class OfficialIslandPointReview {
  const OfficialIslandPointReview({
    required this.total,
    required this.hoangSa,
    required this.truongSa,
    required this.inside,
    required this.within2km,
    required this.flaggedOver5km,
    required this.independentIslandPoints,
    required this.namedIslandOutlinesMissing,
    required this.reefExposureUnknown,
  });

  final int total;
  final int hoangSa;
  final int truongSa;
  final int inside;
  final int within2km;
  final int flaggedOver5km;
  final int independentIslandPoints;
  final int namedIslandOutlinesMissing;
  final int reefExposureUnknown;

  factory OfficialIslandPointReview.fromJson(Map<String, dynamic> source) {
    if (source['datum'] != 'VN-2000' ||
        source['datum_transform_approved_offshore'] != false ||
        source['island_outline_geometry_verified'] != false ||
        source['legal_maritime_boundary_verified'] != false ||
        source['official_pdf_sha256'] !=
            'acde9b561eca24312b81efdcb36a22a8fc74e2dcb431f6c206199ef72c98e841' ||
        source['total'] != 183 ||
        source['hoang_sa'] != 50 ||
        source['truong_sa'] != 133 ||
        source['inside_source_polygon'] != 141 ||
        source['within_2km'] != 156 ||
        source['flagged_over_5km'] != 14 ||
        source['named_island_point_corroborated'] != 4 ||
        source['named_island_outlines_missing'] != 4 ||
        source['reef_or_shoal_exposure_unknown'] != 6 ||
        source['submerged_or_region_label'] != 4) {
      throw const FormatException('Untrusted/altered island P0 QA statistics');
    }
    return const OfficialIslandPointReview(
      total: 183,
      hoangSa: 50,
      truongSa: 133,
      inside: 141,
      within2km: 156,
      flaggedOver5km: 14,
      independentIslandPoints: 4,
      namedIslandOutlinesMissing: 4,
      reefExposureUnknown: 6,
    );
  }
}

class OffshoreRegion {
  const OffshoreRegion({required this.code, required this.name,
    required this.count, required this.largeCount});
  final String code;
  final String name;
  final int count;
  final int largeCount;

  factory OffshoreRegion.fromJson(Map<String, dynamic> json) {
    final code = json['code'];
    final name = json['name'];
    final count = json['count'];
    final large = json['area_over_25_km2'];
    if (code is! String || !const {'48', '56'}.contains(code) ||
        name is! String || count is! int || count < 0 ||
        large is! int || large < 0 || large > count) {
      throw const FormatException('Invalid offshore screening statistics');
    }
    return OffshoreRegion(code: code, name: name, count: count, largeCount: large);
  }
}
