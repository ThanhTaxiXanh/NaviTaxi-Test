import 'dart:convert';

import 'package:flutter/services.dart';

/// P0 release gate applied IN THE APP, not just in its JSON manifest.
///
/// A manifest may never turn a debug or unreviewed build into an approved
/// basemap. An independent build must explicitly pin the SHA-256 of its
/// reviewed P0 certificate with --dart-define=NAVITAXI_P0_EVIDENCE_SHA256=...
/// after the CI/QA release approval process is completed.
///
/// This is an additional build binding, not a replacement for source
/// verification, semantic tile audits, license review, or Android screenshots.
class MapRelease {
  const MapRelease({
    required this.status,
    required this.p0Pass,
    required this.stylePath,
    required this.evidenceDigest,
  });

  static const String _buildAttestedDigest = String.fromEnvironment(
    'NAVITAXI_P0_EVIDENCE_SHA256',
    defaultValue: '',
  );

  static const String _reviewedStyleAsset =
      'assets/styles/vietnam_sovereign_style.json';

  final String status;
  final bool p0Pass;
  final String stylePath;
  final String evidenceDigest;

  static final RegExp _digestFormat = RegExp(r'^[a-f0-9]{64}$');

  /// A modified manifest alone must NEVER activate unknown source tiles.
  bool get mayDisplayVerifiedData =>
      status == 'approved' &&
      p0Pass &&
      stylePath == _reviewedStyleAsset &&
      _digestFormat.hasMatch(evidenceDigest) &&
      _buildAttestedDigest.isNotEmpty &&
      _digestFormat.hasMatch(_buildAttestedDigest) &&
      evidenceDigest == _buildAttestedDigest;

  factory MapRelease.fromJson(Map<String, dynamic> value) => MapRelease(
        status: value['status'] is String
            ? value['status'] as String
            : 'blocked',
        p0Pass: value['p0_pass'] == true,
        stylePath: value['style_asset'] is String
            ? value['style_asset'] as String
            : '',
        evidenceDigest: value['evidence_sha256'] is String
            ? value['evidence_sha256'] as String
            : '',
      );

  static Future<MapRelease> load() async {
    final raw = await rootBundle.loadString(
      'assets/manifests/map_release.json',
    );
    final value = jsonDecode(raw);
    if (value is! Map<String, dynamic>) {
      throw const FormatException('Invalid P0 map release manifest');
    }
    return MapRelease.fromJson(value);
  }
}
