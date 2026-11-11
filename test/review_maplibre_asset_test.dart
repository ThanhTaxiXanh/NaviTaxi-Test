import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:navi_taxi_test/features/map/review_map_data.dart';
import 'package:navi_taxi_test/features/map/review_maplibre_style.dart';

void main() {
  test('bundled preview converts to MapLibre without inventing offshore polygons',
      () async {
    TestWidgetsFlutterBinding.ensureInitialized();
    final preview = await ReviewMapData.load();
    final style = jsonDecode(ReviewMaplibreStyle.build(preview))
        as Map<String, dynamic>;
    final sources = style['sources'] as Map<String, dynamic>;

    List features(String id) =>
        ((sources[id] as Map<String, dynamic>)['data']
            as Map<String, dynamic>)['features'] as List;

    expect(features('review-polygons').length, preview.polygons.length);
    expect(features('review-provinces').length, 34);
    expect(features('review-offshore').length, 315);
    expect(features('review-official').length, 14);
    expect(features('review-regions').length, 3);
    final offshoreTypes = features('review-offshore')
        .map((f) => (f['geometry'] as Map)['type']).toSet();
    expect(offshoreTypes, {'Point'});
    expect((style['metadata'] as Map)['navitaxi:p0_pass'], isFalse);
    expect(
      (style['layers'] as List).any((layer) => layer['type'] == 'fill'),
      isFalse,
    );
  });
}
