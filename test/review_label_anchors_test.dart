import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:navi_taxi_test/features/map/review_label_anchors.dart';
import 'package:navi_taxi_test/features/map/review_map_data.dart';
import 'package:navi_taxi_test/features/map/review_maplibre_style.dart';

ReviewMapData makeData({List<dynamic>? labels}) => ReviewMapData(
  const [],
  const [],
  const [],
  const [],
  labels ?? [
    [112.225, 16.467, 'Hoàng Sa'],
    [114.005, 8.808, 'Trường Sa'],
    [111.5, 13.5, 'Biển Đông'],
  ],
);

void main() {
  test('three essential labels keep exact Vietnamese names and lon/lat order', () {
    final labels = ReviewLabelAnchors.fromData(makeData());
    expect(labels.map((row) => row.name).toSet(), ReviewLabelAnchors.names);
    expect(labels.first.name, 'Hoàng Sa');
    expect(labels.first.longitude, 112.225);
    expect(labels.first.latitude, 16.467);
  });

  test('rejects substituted and duplicate sovereign review names', () {
    expect(
      () => ReviewLabelAnchors.fromData(makeData(labels: [
        [112, 16, 'Hoàng Sa'],
        [114, 9, 'Trường Sa'],
        [111, 13, 'South China Sea'],
      ])),
      throwsFormatException,
    );
    expect(
      () => ReviewLabelAnchors.fromData(makeData(labels: [
        [112, 16, 'Hoàng Sa'],
        [114, 9, 'Hoàng Sa'],
        [111, 13, 'Biển Đông'],
      ])),
      throwsFormatException,
    );
  });

  test('rejects invalid coordinates and inverted non-numeric anchors', () {
    expect(
      () => ReviewLabelAnchors.fromData(makeData(labels: [
        [200, 16, 'Hoàng Sa'],
        [114, 9, 'Trường Sa'],
        [111, 13, 'Biển Đông'],
      ])),
      throwsFormatException,
    );
    expect(
      () => ReviewLabelAnchors.fromData(makeData(labels: [
        ['112', 16, 'Hoàng Sa'],
        [114, 9, 'Trường Sa'],
        [111, 13, 'Biển Đông'],
      ])),
      throwsFormatException,
    );
  });

  test('required labels are not drawn by the network glyph-dependent layer', () {
    final complete = ReviewMapData(
      [
        ['demo', [
          [[105, 16], [106, 16], [106, 17]],
        ]],
      ],
      List.generate(34, (i) => ['Tỉnh QA $i', 105, 16]),
      List.generate(315, (i) => [110, 15]),
      List.generate(14, (i) => [113, 12, 'Địa danh QA', 'QA$i']),
      makeData().labels,
    );
    final style = jsonDecode(ReviewMaplibreStyle.build(complete))
        as Map<String, dynamic>;
    final labelLayer = (style['layers'] as List).singleWhere(
      (layer) => layer['id'] == 'review-region-names',
    ) as Map<String, dynamic>;
    expect((labelLayer['layout'] as Map)['visibility'], 'none');
    expect((style['metadata'] as Map)['navitaxi:p0_pass'], isFalse);
  });
}
