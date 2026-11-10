import 'dart:convert';

import 'package:flutter/services.dart';

/// Catalog check is a fixed-input intake check, not a release approval.
class OfflineArchive {
  const OfflineArchive({
    required this.filename,
    required this.bytes,
    required this.sha256,
    required this.label,
  });

  final String filename;
  final int bytes;
  final String sha256;
  final String label;

  double get sizeMiB => bytes / (1024 * 1024);
}

class OfflinePackageCatalog {
  const OfflinePackageCatalog._();

  static const _labels = <String, String>{
    'hotosm_vnm_roads_osm.pmtiles': 'Đường giao thông',
    'hotosm_vnm_buildings_osm.pmtiles': 'Công trình',
    'hotosm_vnm_points_of_interest_osm.pmtiles': 'Địa điểm (POI)',
  };

  static List<OfflineArchive> parse(String input) {
    final parsed = jsonDecode(input) as Map<String, dynamic>;
    if (parsed['status'] != 'quarantine') {
      throw const FormatException('Offline intake catalog is not quarantined');
    }
    final archives = parsed['archives'];
    if (archives is! List) throw const FormatException('Missing archives');

    final found = <String>{};
    final entries = <OfflineArchive>[];
    for (final item in archives) {
      if (item is! Map) throw const FormatException('Malformed archive');
      final filename = item['filename'];
      final bytes = item['bytes'];
      final hash = item['sha256'];
      if (filename is! String ||
          !_labels.containsKey(filename) ||
          !found.add(filename) ||
          bytes is! int ||
          bytes <= 0 ||
          hash is! String ||
          !RegExp(r'^[a-f0-9]{64}$').hasMatch(hash)) {
        throw const FormatException('Untrusted archive catalog entry');
      }
      entries.add(
        OfflineArchive(
          filename: filename,
          bytes: bytes,
          sha256: hash,
          label: _labels[filename]!,
        ),
      );
    }
    if (found.length != _labels.length) {
      throw const FormatException('Incomplete PMTiles intake catalog');
    }
    return List<OfflineArchive>.unmodifiable(entries);
  }

  static Future<List<OfflineArchive>> load() async => parse(
        await rootBundle.loadString(
          'assets/manifests/ingestion_inventory.json',
        ),
      );
}

class QuarantinedArchive {
  const QuarantinedArchive({
    required this.filename,
    required this.bytes,
    required this.status,
  });

  final String filename;
  final int bytes;
  final String status;

  factory QuarantinedArchive.fromMap(Map<dynamic, dynamic> value) {
    final name = value['filename'];
    final bytes = value['bytes'];
    final status = value['status'];
    if (name is! String || bytes is! int || status != 'quarantined') {
      throw const FormatException('Invalid platform quarantine record');
    }
    return QuarantinedArchive(
      filename: name,
      bytes: bytes,
      status: status,
    );
  }
}
