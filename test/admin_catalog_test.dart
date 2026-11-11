import 'package:flutter_test/flutter_test.dart';
import 'package:navi_taxi_test/features/map/admin_catalog.dart';

const bool generatedAnchorsExpected = bool.fromEnvironment(
  'NAVITAXI_ADMIN_ANCHORS_INCLUDED', defaultValue: false,
);

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('versioned offline catalog includes all 34 + 3321 units', () async {
    final catalog = await AdminCatalog.load();
    expect(catalog.provinces.length, 34);
    expect(catalog.wards.length, 3321);
    expect(catalog.unitCount, 3355);
    expect(catalog.provinceName('01'), 'Thành phố Hà Nội');
    expect(catalog.wards.any((unit) =>
        unit.code == '20333' && unit.name == 'Đặc khu Hoàng Sa'), isTrue);
    expect(catalog.wards.any((unit) =>
        unit.code == '22736' && unit.name == 'Đặc khu Trường Sa'), isTrue);
    expect(catalog.reviewAnchorCount, generatedAnchorsExpected ? 3353 : 0);
  });

  test('search supports Vietnamese text without tone marks', () async {
    final catalog = await AdminCatalog.load();
    expect(
      catalog.search('Ha Noi').any((p) => p.name == 'Thành phố Hà Nội'),
      isTrue,
    );
    expect(
      catalog.search('Ba Dinh').any((p) => p.name == 'Phường Ba Đình'),
      isTrue,
    );
    expect(
      catalog.search('Hoang Sa').any((p) => p.code == '20333'),
      isTrue,
    );
  });

  test('source-derived anchors exclude two offshore group ward codes',
      () async {
    final catalog = await AdminCatalog.load();
    if (!generatedAnchorsExpected) return;
    expect(catalog.provinces.every((p) => p.hasAnchor), isTrue);
    expect(
      catalog.wards.where((p) => p.hasAnchor).length,
      3319,
    );
    expect(
      catalog.wards.where((p) => const {'20333', '22736'}.contains(p.code))
          .every((p) => !p.hasAnchor),
      isTrue,
    );
    final hanoi = catalog.visible(
      south: 20.5, north: 21.5,
      west: 105.2, east: 106.5,
      showWards: false,
    );
    expect(hanoi.any((p) => p.code == '01'), isTrue);
  });
}
