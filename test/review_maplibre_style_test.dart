import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:navi_taxi_test/features/map/review_map_data.dart';
import 'package:navi_taxi_test/features/map/review_maplibre_style.dart';

ReviewMapData fixture({bool badCoordinate = false, bool missingLabel = false}) {
  return ReviewMapData(
    [
      ['test-only', [
        [[105, 16], [106, 16], [106, 17]],
      ]],
    ],
    List.generate(34, (i) => ['Tỉnh thử nghiệm $i', 105, 16]),
    List.generate(315, (i) => [110, 15]),
    List.generate(14, (i) => [badCoordinate ? 181 : 113, 12, 'Điểm mẫu', 'QA$i']),
    [
      [112, 16, 'Hoàng Sa'],
      [114, 9, missingLabel ? 'Khác' : 'Trường Sa'],
      [111, 13, 'Biển Đông'],
    ],
  );
}

void main() {
  test('builds an isolated review style with closed GeoJSON rings', () {
    final style = jsonDecode(ReviewMaplibreStyle.build(fixture()))
        as Map<String, dynamic>;
    final metadata = style['metadata'] as Map<String, dynamic>;
    expect(metadata['navitaxi:p0_pass'], isFalse);
    expect(metadata['navitaxi:debug_only'], isTrue);
    expect(style['version'], 8);
    final sources = style['sources'] as Map<String, dynamic>;
    final polygons = ((sources['review-polygons'] as Map<String, dynamic>)['data']
        as Map<String, dynamic>)['features'] as List;
    final geometry = (polygons.single as Map<String, dynamic>)['geometry']
        as Map<String, dynamic>;
    final ring = (geometry['coordinates'] as List).single as List;
    expect(ring.length, 4); // GeoJSON requires a closed linear ring.
    expect(ring.first, ring.last);
    final layers = style['layers'] as List;
    expect(layers.any((layer) => layer['type'] == 'fill'), isFalse);
    expect(layers.any((layer) => layer['id'] == 'review-region-names'), isTrue);
    expect(style['sources'].toString(), contains('review-official'));
  });

  test('rejects invalid geodetic coordinates without rendering', () {
    expect(
      () => ReviewMaplibreStyle.build(fixture(badCoordinate: true)),
      throwsFormatException,
    );
  });

  test('refuses missing Vietnamese island/sea label', () {
    expect(
      () => ReviewMaplibreStyle.build(fixture(missingLabel: true)),
      throwsFormatException,
    );
  });
}
