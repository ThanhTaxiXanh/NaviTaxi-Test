import 'package:flutter_test/flutter_test.dart';
import 'package:navi_taxi_test/features/map/review_map_data.dart';

void main() {
  test('P0 review app uses a source-derived but simplified dataset', () async {
    TestWidgetsFlutterBinding.ensureInitialized();
    final preview = await ReviewMapData.load();
    expect(preview.provinces.length, 34);
    expect(preview.polygons.length, greaterThanOrEqualTo(34));
    expect(preview.offshore.length, 315);
    expect(preview.official.length, 14);
    expect(preview.labels.map((entry) => entry[2]).toSet(),
           {'Hoàng Sa', 'Trường Sa', 'Biển Đông'});
  });

  test('forged approved preview is rejected', () {
    expect(
      () => ReviewMapData.fromJson({
        'schema': 1,
        'review': true,
        'p0': true,
        'source_zip_sha256': ReviewMapData.sourceZipSha256,
      }),
      throwsFormatException,
    );
  });
}
