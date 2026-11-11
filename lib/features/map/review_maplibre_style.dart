import 'dart:convert';

import 'review_map_data.dart';

/// Builds a DEBUG-ONLY MapLibre style from an already quarantined preview.
///
/// Province polygons are OUTLINES, never land fills or legal sea borders.
/// The review markers are points, never island footprints. This class must
/// not be used by the production MapRelease activation path.
class ReviewMaplibreStyle {
  static const requiredLabels = <String>{'Hoàng Sa', 'Trường Sa', 'Biển Đông'};

  static String build(ReviewMapData data) {
    if (data.provinces.length != 34 || data.offshore.length != 315 ||
        data.official.length != 14 || data.labels.length != 3) {
      throw const FormatException('Incomplete debug GIS preview');
    }

    final polygons = <Map<String, dynamic>>[];
    for (var i = 0; i < data.polygons.length; i++) {
      final record = data.polygons[i];
      if (record is! List || record.length != 2 || record[1] is! List) {
        throw const FormatException('Malformed province preview polygon');
      }
      final rings = <List<List<num>>>[];
      for (final ring in record[1] as List) {
        if (ring is! List || ring.length < 3) {
          throw const FormatException('Malformed preview polygon ring');
        }
        final coordinates = ring.map((p) => _point(p)).toList();
        final first = coordinates.first;
        final last = coordinates.last;
        if (first[0] != last[0] || first[1] != last[1]) {
          coordinates.add([first[0], first[1]]);
        }
        if (coordinates.length < 4) {
          throw const FormatException('Incomplete preview polygon ring');
        }
        rings.add(coordinates);
      }
      if (rings.isEmpty) {
        throw const FormatException('Empty preview polygon');
      }
      polygons.add(_feature(i, 'Polygon', rings, {
        'review_only': true,
        'not_a_land_or_maritime_boundary': true,
      }));
    }

    final provinces = <Map<String, dynamic>>[];
    for (var i = 0; i < data.provinces.length; i++) {
      final item = data.provinces[i];
      if (item is! List || item.length < 3 || item[0] is! String) {
        throw const FormatException('Malformed province review label');
      }
      provinces.add(_feature(i, 'Point', _point([item[1], item[2]]), {
        'name': item[0], 'review_only': true,
      }));
    }

    final offshore = <Map<String, dynamic>>[];
    for (var i = 0; i < data.offshore.length; i++) {
      final item = data.offshore[i];
      if (item is! List || item.length < 2) {
        throw const FormatException('Malformed offshore review marker');
      }
      offshore.add(_feature(i, 'Point', _point(item), {
        'review_only': true,
        'marker_only_not_island_outline': true,
      }));
    }

    final official = <Map<String, dynamic>>[];
    for (var i = 0; i < data.official.length; i++) {
      final item = data.official[i];
      if (item is! List || item.length < 4 || item[2] is! String) {
        throw const FormatException('Malformed official-name review point');
      }
      official.add(_feature(i, 'Point', _point(item), {
        'name': item[2],
        'review_only': true,
        'datum_transformation_approved': false,
      }));
    }

    final labels = <Map<String, dynamic>>[];
    final observed = <String>{};
    for (var i = 0; i < data.labels.length; i++) {
      final item = data.labels[i];
      if (item is! List || item.length != 3 || item[2] is! String) {
        throw const FormatException('Malformed region review label');
      }
      final label = item[2] as String;
      if (!observed.add(label)) {
        throw const FormatException('Duplicated region review label');
      }
      labels.add(_feature(i, 'Point', _point(item), {
        'name': label,
        'review_only': true,
        'position_is_reference_anchor_not_boundary': true,
      }));
    }
    if (!observed.containsAll(requiredLabels) ||
        observed.length != requiredLabels.length) {
      throw const FormatException('Required Vietnamese review labels absent');
    }

    final style = <String, dynamic>{
      'version': 8,
      'name': 'NaviTaxi GIS debug review, NOT P0',
      'metadata': {
        'navitaxi:debug_only': true,
        'navitaxi:p0_pass': false,
        'navitaxi:source_zip_sha256': ReviewMapData.sourceZipSha256,
        'navitaxi:note': 'Outlines are not legal borders or land. Labels are reference anchors.',
      },
      // Review glyphs need Internet until a separately licensed local glyph
      // package has been bundled and tested in airplane mode.
      'glyphs': 'https://demotiles.maplibre.org/font/{fontstack}/{range}.pbf',
      'sources': {
        'review-polygons': _source(polygons),
        'review-provinces': _source(provinces),
        'review-offshore': _source(offshore),
        'review-official': _source(official),
        'review-regions': _source(labels),
      },
      'layers': [
        {'id': 'background', 'type': 'background', 'paint': {'background-color': '#d7eaf2'}},
        {
          'id': 'review-province-outlines', 'type': 'line',
          'source': 'review-polygons',
          'paint': {'line-color': '#5a736d', 'line-width': 1.25},
        },
        {
          'id': 'review-offshore-centroids', 'type': 'circle',
          'source': 'review-offshore',
          'paint': {'circle-color': '#d78028', 'circle-radius': 2.5},
        },
        {
          'id': 'review-official-points', 'type': 'circle',
          'source': 'review-official',
          'paint': {'circle-color': '#c62e42', 'circle-radius': 4},
        },
        {
          'id': 'review-province-names', 'type': 'symbol',
          'source': 'review-provinces', 'minzoom': 5,
          // Province names are Flutter overlays in the GIS reviewer too.
          'layout': {
            'visibility': 'none',
            'text-field': ['get', 'name'], 'text-size': 11,
            'text-font': ['Noto Sans Regular'],
          },
          'paint': {'text-color': '#1c4556', 'text-halo-color': '#f0f5f5', 'text-halo-width': 1},
        },
        {
          'id': 'review-official-names', 'type': 'symbol',
          'source': 'review-official', 'minzoom': 6,
          'layout': {
            'text-field': ['get', 'name'], 'text-size': 11,
            'text-font': ['Noto Sans Regular'], 'text-offset': [0, -1.3],
          },
          'paint': {'text-color': '#8d1626', 'text-halo-color': '#ffffff', 'text-halo-width': 1},
        },
        {
          'id': 'review-region-names', 'type': 'symbol',
          'source': 'review-regions',
          // Required group labels are drawn with Flutter's bundled text
          // renderer in ReviewMaplibreScreen: no external glyph PBF needed.
          // Keep this debug-only layer as a source diagnostic, but hide it
          // to prevent duplicates and network-dependent native text.
          'layout': {
            'visibility': 'none',
            'text-field': ['get', 'name'], 'text-size': 19,
            'text-font': ['Noto Sans Regular'],
            'text-allow-overlap': true,
            'text-ignore-placement': true,
          },
          'paint': {'text-color': '#164464', 'text-halo-color': '#f5fbfd', 'text-halo-width': 2},
        },
      ],
    };
    return jsonEncode(style);
  }

  /// Add ONLY locally imported, SHA-verified HOTOSM vector layers to the
  /// DEBUG GIS preview. No MVT text/symbol label layer is ever used here.
  /// This does not change the ordinary P0-blocked MapLibre style.
  static String withOfflineMvt(
    String rawReviewStyle,
    Map<String, String> tileTemplates,
  ) {
    if (tileTemplates.isEmpty) return rawReviewStyle;
    if (tileTemplates.keys.any(
      (name) => !const {'roads', 'buildings', 'poi'}.contains(name),
    )) {
      throw const FormatException('Unrecognized PMTiles debug source');
    }
    final value = jsonDecode(rawReviewStyle);
    if (value is! Map<String, dynamic>) {
      throw const FormatException('Review style is not an object');
    }
    final metadata = value['metadata'] as Map<String, dynamic>;
    if (metadata['navitaxi:p0_pass'] != false ||
        metadata['navitaxi:debug_only'] != true) {
      throw const FormatException('Cannot add PMTiles to non-debug style');
    }
    final sources = value['sources'] as Map<String, dynamic>;
    final layers = value['layers'] as List<dynamic>;
    final addedLayers = <Map<String, dynamic>>[];
    final specifications = <String, (String, int)>{
      'roads': ('roads', 13),
      'buildings': ('buildings', 14),
      'poi': ('points_of_interest', 12),
    };
    for (final entry in specifications.entries) {
      final url = tileTemplates[entry.key];
      if (url == null) continue;
      if (!url.startsWith('http://127.0.0.1:') ||
          !url.endsWith('/{z}/{x}/{y}.pbf')) {
        throw const FormatException('Only local tokenized tile URLs allowed');
      }
      final sourceId = 'debug-local-${entry.key}';
      sources[sourceId] = {
        'type': 'vector',
        'tiles': [url],
        'minzoom': 0,
        'maxzoom': entry.value.$2,
      };
      final sourceLayer = entry.value.$1;
      if (entry.key == 'roads') {
        addedLayers.add({
          'id': 'debug-local-roads',
          'type': 'line',
          'source': sourceId,
          'source-layer': sourceLayer,
          'minzoom': 4,
          'paint': {
            'line-color': '#d29359',
            'line-width': ['interpolate', ['linear'], ['zoom'],
              4, 0.6, 12, 2.4, 16, 3.0],
          },
        });
      } else if (entry.key == 'buildings') {
        addedLayers.add({
          'id': 'debug-local-buildings',
          'type': 'fill',
          'source': sourceId,
          'source-layer': sourceLayer,
          'minzoom': 10,
          'paint': {
            'fill-color': '#89999d',
            'fill-opacity': 0.52,
          },
        });
      } else {
        addedLayers.add({
          'id': 'debug-local-poi',
          'type': 'circle',
          'source': sourceId,
          'source-layer': sourceLayer,
          'minzoom': 10,
          'paint': {
            'circle-color': '#24866e',
            'circle-radius': 3,
            'circle-stroke-color': '#ffffff',
            'circle-stroke-width': 0.5,
          },
        });
      }
    }
    // Base geometries render BELOW the reviewed administrative/sea labels.
    layers.insertAll(1, addedLayers);
    metadata['navitaxi:offline_sources'] = tileTemplates.keys.toList()..sort();
    metadata['navitaxi:offline_imported_only'] = true;
    return jsonEncode(value);
  }

  static Map<String, dynamic> _source(List<Map<String, dynamic>> features) => {
    'type': 'geojson',
    'data': {'type': 'FeatureCollection', 'features': features},
  };

  static Map<String, dynamic> _feature(int index, String type,
      Object coordinates, Map<String, dynamic> properties) => {
    'type': 'Feature', 'id': index,
    'properties': properties,
    'geometry': {'type': type, 'coordinates': coordinates},
  };

  static List<num> _point(dynamic value) {
    if (value is! List || value.length < 2 ||
        value[0] is! num || value[1] is! num) {
      throw const FormatException('Invalid preview coordinate');
    }
    final lon = value[0] as num;
    final lat = value[1] as num;
    if (!lon.isFinite || !lat.isFinite ||
        lon < -180 || lon > 180 || lat < -90 || lat > 90) {
      throw const FormatException('Out-of-range preview coordinate');
    }
    return [lon, lat];
  }
}
