import 'dart:convert';
import 'package:flutter/services.dart';

/// Read-only source-audit summary; cannot enable rendering.
class Province34Review {
  const Province34Review({
    required this.provinceCount, required this.offshoreCount,
    required this.sourceSha256, required this.packageSha256,
    required this.reviewRegions, required this.remainingChecks,
  });
  final int provinceCount;
  final int offshoreCount;
  final String sourceSha256;
  final String packageSha256;
  final List<OffshoreRegion> reviewRegions;
  final List<String> remainingChecks;

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
