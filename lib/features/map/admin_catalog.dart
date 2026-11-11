import 'dart:convert';

import 'package:flutter/services.dart';

/// One administrative name and an optional, source-derived review anchor.
/// An absent anchor is NOT replaced with a fake GPS coordinate.
class AdminPlace {
  const AdminPlace({
    required this.code,
    required this.name,
    required this.provinceCode,
    required this.isProvince,
    this.longitude,
    this.latitude,
  });

  final String code;
  final String name;
  final String provinceCode;
  final bool isProvince;
  final double? longitude;
  final double? latitude;

  bool get hasAnchor => latitude != null && longitude != null;
}

/// Offline names plus optional labelled-point GIS review data.
///
/// This is a UI/search catalog, not a geocoder, legal boundary or proof of
/// legal geospatial accuracy. Province/ward identities are pinned to v5.2.0.
class AdminCatalog {
  const AdminCatalog(this.provinces, this.wards, this.reviewAnchorCount);

  final List<AdminPlace> provinces;
  final List<AdminPlace> wards;
  final int reviewAnchorCount;

  int get unitCount => provinces.length + wards.length;

  static Future<AdminCatalog> load() async {
    final namesRaw = jsonDecode(await rootBundle.loadString(
      'assets/geo/provinces_wards_v5_2.json',
    ));
    dynamic anchorsRaw;
    try {
      anchorsRaw = jsonDecode(await rootBundle.loadString(
        'assets/geo/ward_label_anchors.json',
      ));
    } on FlutterError {
      // Ordinary P0-blocked builds never require debug GIS anchor assets.
      // The user can still search 34 + 3321 names without invented locations.
      anchorsRaw = null;
    }
    return AdminCatalog.fromJson(namesRaw, anchorsRaw);
  }

  static AdminCatalog fromJson(dynamic names, dynamic anchors) {
    if (names is! List || names.length != 34) {
      throw const FormatException('Expected 34 Vietnamese provinces');
    }
    final byProvince = <String, String>{};
    final byWard = <String, (String, String)>{};
    for (final row in names) {
      if (row is! Map || row['Code'] is! String ||
          row['FullName'] is! String || row['Wards'] is! List) {
        throw const FormatException('Invalid administrative name record');
      }
      final code = row['Code'] as String;
      if (byProvince.containsKey(code)) {
        throw const FormatException('Duplicate province code');
      }
      byProvince[code] = row['FullName'] as String;
      for (final ward in row['Wards'] as List) {
        if (ward is! Map || ward['Code'] is! String ||
            ward['FullName'] is! String || ward['ProvinceCode'] != code) {
          throw const FormatException('Invalid commune/ward relation');
        }
        final wardCode = ward['Code'] as String;
        if (byWard.containsKey(wardCode)) {
          throw const FormatException('Duplicate commune/ward code');
        }
        byWard[wardCode] = (ward['FullName'] as String, code);
      }
    }
    if (byWard.length != 3321) {
      throw const FormatException('Expected 3321 communes/wards');
    }

    final provinceAnchors = <String, (double, double)>{};
    final wardAnchors = <String, (double, double)>{};
    if (anchors != null) {
      if (anchors is! Map || anchors['schema_version'] != 1 ||
          anchors['status'] != 'DEBUG_ONLY_CANDIDATE_NOT_P0' ||
          anchors['p0_pass'] != false ||
          anchors['geometry_role'] != 'representative_label_points_only' ||
          anchors['source_revision'] !=
              '8b78ba5118715e1fa81769286724db79346abf52' ||
          anchors['provinces'] is! List ||
          anchors['wards'] is! List) {
        throw const FormatException('Untrusted administrative label anchors');
      }
      final provincePoints = anchors['provinces'] as List;
      final wardPoints = anchors['wards'] as List;
      if (provincePoints.length != 34 || wardPoints.length != 3319) {
        throw const FormatException('Incomplete administrative label points');
      }
      for (final row in provincePoints) {
        if (row is! List || row.length != 4 || row[0] is! String ||
            row[1] is! String) {
          throw const FormatException('Bad province label anchor');
        }
        final code = row[0] as String;
        if (byProvince[code] != row[1] ||
            provinceAnchors.containsKey(code)) {
          throw const FormatException('Province name/anchor mismatch');
        }
        provinceAnchors[code] = _validatedPoint(row[2], row[3]);
      }
      for (final row in wardPoints) {
        if (row is! List || row.length != 5 || row[0] is! String ||
            row[1] is! String || row[2] is! String) {
          throw const FormatException('Bad ward label anchor');
        }
        final code = row[0] as String;
        if (byWard[code] != (row[1], row[2]) ||
            wardAnchors.containsKey(code) ||
            const {'20333', '22736'}.contains(code)) {
          throw const FormatException('Ward name/anchor mismatch');
        }
        wardAnchors[code] = _validatedPoint(row[3], row[4]);
      }
    }

    final provinces = [
      for (final code in byProvince.keys.toList()..sort())
        AdminPlace(
          code: code, name: byProvince[code]!, provinceCode: code,
          isProvince: true,
          longitude: provinceAnchors[code]?.$1,
          latitude: provinceAnchors[code]?.$2,
        ),
    ];
    final wards = [
      for (final code in byWard.keys.toList()..sort())
        AdminPlace(
          code: code, name: byWard[code]!.$1,
          provinceCode: byWard[code]!.$2, isProvince: false,
          longitude: wardAnchors[code]?.$1,
          latitude: wardAnchors[code]?.$2,
        ),
    ];
    return AdminCatalog(
      List.unmodifiable(provinces),
      List.unmodifiable(wards),
      provinceAnchors.length + wardAnchors.length,
    );
  }

  static (double, double) _validatedPoint(dynamic longitude, dynamic latitude) {
    if (longitude is! num || latitude is! num) {
      throw const FormatException('Non-numeric geographic label anchor');
    }
    final lon = longitude.toDouble();
    final lat = latitude.toDouble();
    if (!lon.isFinite || !lat.isFinite ||
        lon < 101.5 || lon > 118.5 || lat < 6 || lat > 24.5) {
      throw const FormatException('Label anchor outside Vietnam GIS scope');
    }
    return (lon, lat);
  }

  /// Case-insensitive and Vietnamese diacritic-insensitive name search.
  List<AdminPlace> search(String query, {int limit = 70}) {
    final q = _normalized(query);
    if (q.isEmpty) return provinces.take(limit).toList();
    final matches = <AdminPlace>[];
    for (final place in [...provinces, ...wards]) {
      if (_normalized(place.name).contains(q) || place.code.contains(q)) {
        matches.add(place);
      }
    }
    matches.sort((a, b) {
      final ap = _normalized(a.name).startsWith(q) ? 0 : 1;
      final bp = _normalized(b.name).startsWith(q) ? 0 : 1;
      final rank = ap.compareTo(bp);
      if (rank != 0) return rank;
      if (a.isProvince != b.isProvince) return a.isProvince ? -1 : 1;
      return a.name.compareTo(b.name);
    });
    return matches.take(limit).toList();
  }

  List<AdminPlace> visible({
    required double south,
    required double north,
    required double west,
    required double east,
    required bool showWards,
    int limit = 130,
  }) {
    final source = showWards ? wards : provinces;
    return source.where((place) {
      if (!place.hasAnchor) return false;
      final lat = place.latitude!;
      final lon = place.longitude!;
      return lat >= south && lat <= north &&
          (west <= east
              ? lon >= west && lon <= east
              : lon >= west || lon <= east);
    }).take(limit).toList();
  }

  String provinceName(String code) {
    for (final province in provinces) {
      if (province.code == code) return province.name;
    }
    return '';
  }

  static String _normalized(String input) {
    const pairs = {
      'a': 'àáảãạăằắẳẵặâầấẩẫậ',
      'e': 'èéẻẽẹêềếểễệ',
      'i': 'ìíỉĩị',
      'o': 'òóỏõọôồốổỗộơờớởỡợ',
      'u': 'ùúủũụưừứửữự',
      'y': 'ỳýỷỹỵ',
      'd': 'đ',
    };
    final buffer = StringBuffer();
    for (final char in input.toLowerCase().split('')) {
      var reduced = char;
      for (final entry in pairs.entries) {
        if (entry.value.contains(char)) {
          reduced = entry.key;
          break;
        }
      }
      buffer.write(reduced);
    }
    return buffer.toString().trim();
  }
}
