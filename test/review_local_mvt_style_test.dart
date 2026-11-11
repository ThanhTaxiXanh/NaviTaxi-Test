import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:navi_taxi_test/features/map/review_map_data.dart';
import 'package:navi_taxi_test/features/map/review_maplibre_style.dart';

ReviewMapData _fixture() => ReviewMapData(
  [
    ['example', [
      [[105, 16], [106, 16], [106, 17]],
    ]],
  ],
  List.generate(34, (i) => ['Tỉnh thử nghiệm $i', 105, 16]),
  List.generate(315, (_) => [110, 15]),
  List.generate(14, (i) => [113, 12, 'QA', 'QA$i']),
  [
    [112, 16, 'Hoàng Sa'],
    [114, 9, 'Trường Sa'],
    [111, 13, 'Biển Đông'],
  ],
);

void main() {
  test('local MVT style shows only transport/buildings/POI geometry', () {
    final raw = ReviewMaplibreStyle.build(_fixture());
    final styled = ReviewMaplibreStyle.withOfflineMvt(raw, {
      'roads': 'http://127.0.0.1:12345/session/roads/{z}/{x}/{y}.pbf',
      'buildings':
          'http://127.0.0.1:12345/session/buildings/{z}/{x}/{y}.pbf',
      'poi': 'http://127.0.0.1:12345/session/poi/{z}/{x}/{y}.pbf',
    });
    final data = jsonDecode(styled) as Map<String, dynamic>;
    final metadata = data['metadata'] as Map<String, dynamic>;
    expect(metadata['navitaxi:p0_pass'], false);
    expect(metadata['navitaxi:debug_only'], true);
    expect(metadata['navitaxi:offline_sources'], ['buildings', 'poi', 'roads']);
    final sources = data['sources'] as Map<String, dynamic>;
    expect((sources['debug-local-roads'] as Map)['type'], 'vector');
    expect((sources['debug-local-poi'] as Map)['maxzoom'], 12);
    expect((sources['debug-local-buildings'] as Map)['maxzoom'], 14);
    final layers = data['layers'] as List<dynamic>;
    final debugLayers = layers.where(
      (item) => (item as Map)['id'].toString().startsWith('debug-local-'),
    );
    expect(debugLayers.length, 3);
    expect(debugLayers.any((item) => (item as Map)['type'] == 'symbol'), false);
    expect(debugLayers.every((item) =>
      (item as Map)['source-layer'] is String), true);
    expect((sources['review-regions'] as Map)['type'], 'geojson');
  });

  test('local tiles cannot be enabled through remote URLs or release style', () {
    final raw = ReviewMaplibreStyle.build(_fixture());
    expect(
      () => ReviewMaplibreStyle.withOfflineMvt(raw, {
        'roads': 'https://example.com/{z}/{x}/{y}.pbf',
      }),
      throwsFormatException,
    );
    expect(
      () => ReviewMaplibreStyle.withOfflineMvt(raw, {
        'fake': 'http://127.0.0.1:1/token/fake/{z}/{x}/{y}.pbf',
      }),
      throwsFormatException,
    );
    expect(
      () => ReviewMaplibreStyle.withOfflineMvt(
        '{"version":8,"metadata":{"navitaxi:p0_pass":true,'
        '"navitaxi:debug_only":false},"sources":{},"layers":[]}',
        {'roads': 'http://127.0.0.1:1/t/roads/{z}/{x}/{y}.pbf'},
      ),
      throwsFormatException,
    );
  });
}
