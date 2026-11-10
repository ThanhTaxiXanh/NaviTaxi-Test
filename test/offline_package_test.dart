import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:navi_taxi_test/features/offline/offline_package.dart';
import 'package:navi_taxi_test/platform/android_storage_bridge.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('catalog accepts only a quarantined complete inventory', () {
    const catalog = '''
{
  "status": "quarantine",
  "archives": [
    {"filename":"hotosm_vnm_roads_osm.pmtiles","bytes":249894089,
     "sha256":"ca575f95bc708ec1fb39e0c3b3f5ee4a3f1596e75e5a0b1f6e50f85e8a28bedd"},
    {"filename":"hotosm_vnm_buildings_osm.pmtiles","bytes":75340271,
     "sha256":"8c6f129a2bf2237215d90be72a52475cb6f0f528ac41dfabc5434d832ca37b6f"},
    {"filename":"hotosm_vnm_points_of_interest_osm.pmtiles","bytes":15966991,
     "sha256":"dda5a9de8412e8d6bdc73ae62d4fa2c3f8ef017bcbc0c833bc2a9e441be87763"}
  ]
}
''';
    final parsed = OfflinePackageCatalog.parse(catalog);
    expect(parsed.length, 3);
    expect(parsed.first.label, 'Đường giao thông');
    expect(
      () => OfflinePackageCatalog.parse(
        catalog.replaceFirst('"quarantine"', '"approved"'),
      ),
      throwsFormatException,
    );
  });

  test('unknown or incomplete package catalogs are rejected', () {
    const unsupported = '''
{"status":"quarantine","archives":[
  {"filename":"../unknown.pmtiles","bytes":1,
   "sha256":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}]}
''';
    expect(
      () => OfflinePackageCatalog.parse(unsupported),
      throwsFormatException,
    );
  });

  test('platform intake verification never grants P0 approval', () async {
    const channel = MethodChannel('vn.navitaxi/test_offline_store');
    final messenger = TestDefaultBinaryMessengerBinding
        .instance.defaultBinaryMessenger;
    messenger.setMockMethodCallHandler(channel, (call) async {
      if (call.method == 'listImported') {
        return [
          {
            'filename': 'hotosm_vnm_roads_osm.pmtiles',
            'bytes': 249894089,
            'status': 'quarantined',
          }
        ];
      }
      if (call.method == 'verifyImported') {
        return {
          'sha256Verified': true,
          'p0Approved': false,
          'status': 'quarantined',
        };
      }
      return null;
    });
    addTearDown(() => messenger.setMockMethodCallHandler(channel, null));
    const store = AndroidStorageBridge(channel: channel);
    final rows = await store.listImported();
    expect(rows.single.status, 'quarantined');
    expect(await store.verifyImported(rows.single.filename), isTrue);
  });

  test('Dart bridge rejects a falsely P0-approved verification', () async {
    const channel = MethodChannel('vn.navitaxi/test_offline_bad');
    final messenger = TestDefaultBinaryMessengerBinding
        .instance.defaultBinaryMessenger;
    messenger.setMockMethodCallHandler(channel, (call) async => {
          'sha256Verified': true,
          'p0Approved': true,
        });
    addTearDown(() => messenger.setMockMethodCallHandler(channel, null));
    const store = AndroidStorageBridge(channel: channel);
    expect(await store.verifyImported('hotosm_vnm_roads_osm.pmtiles'), isFalse);
  });
}
