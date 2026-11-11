import 'dart:convert';
import 'dart:io';

import 'package:flutter/services.dart';

/// Deliberately coarsened geometry for a reviewer-only debug build.
/// Never reuse these polygons as approved land, legal borders or routing data.
class ReviewMapData {
  const ReviewMapData(this.polygons, this.provinces, this.offshore,
      this.official, this.labels);

  final List<dynamic> polygons;
  final List<dynamic> provinces;
  final List<dynamic> offshore;
  final List<dynamic> official;
  final List<dynamic> labels;

  static const sourceZipSha256 =
      '51779d2585600ec053827a60890ba61cd2192f19b5ee153d38be18a2611d24cd';

  factory ReviewMapData.fromJson(Map<String, dynamic> value) {
    if (value['schema'] != 1 ||
        value['review'] != true ||
        value['p0'] != false ||
        value['source_zip_sha256'] != sourceZipSha256 ||
        value['polygons'] is! List ||
        value['provinces'] is! List ||
        value['offshore'] is! List ||
        value['official'] is! List ||
        value['labels'] is! List) {
      throw const FormatException('Invalid GIS preview source / P0 state');
    }
    final polygons = value['polygons'] as List;
    final provinces = value['provinces'] as List;
    final offshore = value['offshore'] as List;
    final official = value['official'] as List;
    final labels = value['labels'] as List;
    if (polygons.length < 34 ||
        provinces.length != 34 ||
        offshore.length != 315 ||
        official.length != 14 ||
        labels.length != 3 ||
        labels.any((row) => row is! List || row.length != 3) ||
        labels.map((row) => row[2]).toSet().containsAll(
          {'Hoàng Sa', 'Trường Sa', 'Biển Đông'},
        ) == false) {
      throw const FormatException('Incomplete/coerced GIS preview inventory');
    }
    return ReviewMapData(polygons, provinces, offshore, official, labels);
  }

  static Future<ReviewMapData> load() async {
    final encoded = await rootBundle.loadString(
      'assets/review/preview_geometry.b64',
    );
    final compressed = base64Decode(encoded.trim());
    if (compressed.length > 128 * 1024) {
      throw const FormatException('Preview exceeds compressed safety limit');
    }
    final decodedBytes = gzip.decode(compressed);
    if (decodedBytes.length > 1024 * 1024) {
      throw const FormatException('Preview exceeds expanded safety limit');
    }
    final decoded = jsonDecode(utf8.decode(decodedBytes));
    if (decoded is! Map<String, dynamic>) {
      throw const FormatException('Invalid preview JSON root');
    }
    return ReviewMapData.fromJson(decoded);
  }
}
