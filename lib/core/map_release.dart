import 'dart:convert';

import 'package:flutter/services.dart';

/// A product release flag, not a substitute for independent P0 verification.
class MapRelease {
  const MapRelease({
    required this.status,
    required this.p0Pass,
    required this.stylePath,
    required this.evidenceDigest,
  });

  final String status;
  final bool p0Pass;
  final String stylePath;
  final String evidenceDigest;

  bool get mayDisplayVerifiedData =>
      status == 'approved' &&
      p0Pass &&
      RegExp(r'^[a-fA-F0-9]{64}$').hasMatch(evidenceDigest);

  factory MapRelease.fromJson(Map<String, dynamic> value) => MapRelease(
        status: value['status'] is String ? value['status'] as String : 'blocked',
        p0Pass: value['p0_pass'] == true,
        stylePath: value['style_asset'] is String
            ? value['style_asset'] as String
            : '',
        evidenceDigest: value['evidence_sha256'] is String
            ? value['evidence_sha256'] as String
            : '',
      );

  static Future<MapRelease> load() async {
    final text = await rootBundle.loadString(
      'assets/manifests/map_release.json',
    );
    final parsed = jsonDecode(text) as Map<String, dynamic>;
    return MapRelease.fromJson(parsed);
  }
}
