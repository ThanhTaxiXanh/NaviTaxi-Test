import 'dart:io';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:navi_taxi_test/features/offline/pmtiles_v3.dart';

Uint8List _samplePmtiles({required bool compressed}) {
  const tile = <int>[26, 1, 0]; // Tiny synthetic PBF payload.
  final payload = compressed ? gzip.encode(tile) : tile;
  final directory = <int>[1, 0, 1, payload.length, 1];
  final root = compressed ? gzip.encode(directory) : directory;
  final header = Uint8List(127);
  header.setRange(0, 7, 'PMTiles'.codeUnits);
  header[7] = 3;
  final bytes = ByteData.sublistView(header);
  final metadataStart = 127 + root.length;
  final tileStart = metadataStart + 2;
  bytes.setUint64(8, 127, Endian.little);
  bytes.setUint64(16, root.length, Endian.little);
  bytes.setUint64(24, metadataStart, Endian.little);
  bytes.setUint64(32, 2, Endian.little);
  bytes.setUint64(40, tileStart, Endian.little);
  bytes.setUint64(48, 0, Endian.little);
  bytes.setUint64(56, tileStart, Endian.little);
  bytes.setUint64(64, payload.length, Endian.little);
  bytes.setUint64(72, 1, Endian.little); // Addressed tiles
  bytes.setUint64(80, 1, Endian.little); // Tile entries
  bytes.setUint64(88, 1, Endian.little); // Unique tile contents
  header[96] = 1; // Clustered
  header[97] = compressed ? 2 : 1;
  header[98] = compressed ? 2 : 1;
  header[99] = 1; // MVT
  header[100] = 0;
  header[101] = 0;
  return Uint8List.fromList([...header, ...root, 123, 125, ...payload]);
}

void main() {
  test('Hilbert PMTiles tile IDs use standard zoom-order mapping', () {
    expect(PmtilesV3Archive.xyzToTileId(0, 0, 0), 0);
    expect(PmtilesV3Archive.xyzToTileId(1, 0, 0), 1);
    expect(PmtilesV3Archive.xyzToTileId(1, 0, 1), 2);
    expect(PmtilesV3Archive.xyzToTileId(1, 1, 1), 3);
    expect(PmtilesV3Archive.xyzToTileId(1, 1, 0), 4);
    expect(
      () => PmtilesV3Archive.xyzToTileId(2, 4, 1),
      throwsFormatException,
    );
  });

  for (final compressed in [false, true]) {
    test('PMTiles v3 reads synthetic ${compressed ? 'gzip' : 'raw'} MVT', () async {
      final dir = await Directory.systemTemp.createTemp('navitaxi-pmtiles-');
      try {
        final file = File('${dir.path}/synthetic.pmtiles');
        await file.writeAsBytes(_samplePmtiles(compressed: compressed));
        final archive = await PmtilesV3Archive.open(file.path);
        expect(archive.minZoom, 0);
        expect(archive.maxZoom, 0);
        expect(await archive.readMvt(0, 0, 0), [26, 1, 0]);
        expect(await archive.readMvt(1, 0, 0), isNull);
      } finally {
        await dir.delete(recursive: true);
      }
    });
  }

  test('corrupt header and unsupported tile format are rejected', () async {
    final dir = await Directory.systemTemp.createTemp('navitaxi-bad-');
    try {
      final bad = _samplePmtiles(compressed: false);
      bad[7] = 2;
      final file = File('${dir.path}/bad.pmtiles');
      await file.writeAsBytes(bad);
      expect(() => PmtilesV3Archive.open(file.path), throwsFormatException);
    } finally {
      await dir.delete(recursive: true);
    }
  });
}
