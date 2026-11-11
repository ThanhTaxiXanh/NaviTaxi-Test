import 'dart:io';
import 'dart:typed_data';

/// Minimal, read-only PMTiles v3 index reader for the three SHA-verified
/// HOTOSM diagnostic archives. No third-party PMTiles URL/protocol handler.
///
/// Supports v3 Hilbert XYZ lookup, leaf directories and internal/tile gzip.
/// All binary offsets are checked against the selected file. This parser
/// never interprets administrative or maritime boundaries.
class PmtilesV3Archive {
  PmtilesV3Archive._(
    this.file,
    this._size,
    this._leafOffset,
    this._leafLength,
    this._tileOffset,
    this._tileLength,
    this._internalCompression,
    this._tileCompression,
    this.minZoom,
    this.maxZoom,
    this._root,
  );

  final File file;
  final int _size;
  final int _leafOffset;
  final int _leafLength;
  final int _tileOffset;
  final int _tileLength;
  final int _internalCompression;
  final int _tileCompression;
  final int minZoom;
  final int maxZoom;
  final List<_DirectoryEntry> _root;
  final Map<int, List<_DirectoryEntry>> _leaves = {};

  static const _maximumDirectoryBytes = 4 * 1024 * 1024;
  static const _maximumTileBytes = 6 * 1024 * 1024;
  static const _maximumInflatedTileBytes = 12 * 1024 * 1024;

  static Future<PmtilesV3Archive> open(String path) async {
    final file = File(path);
    final size = await file.length();
    if (size < 127) throw const FormatException('PMTiles header truncated');
    final header = await _readBytes(file, size, 0, 127);
    if (String.fromCharCodes(header.sublist(0, 7)) != 'PMTiles' ||
        header[7] != 3) {
      throw const FormatException('PMTiles v3 magic missing');
    }
    final fields = ByteData.sublistView(header);
    int q(int offset) => fields.getUint64(offset, Endian.little);
    final rootOffset = q(8);
    final rootLength = q(16);
    final metadataOffset = q(24);
    final metadataLength = q(32);
    final leafOffset = q(40);
    final leafLength = q(48);
    final tileOffset = q(56);
    final tileLength = q(64);
    final internalCompression = header[97];
    final tileCompression = header[98];
    final tileType = header[99];
    final minZoom = header[100];
    final maxZoom = header[101];
    if (!(rootOffset >= 127 &&
            rootLength > 0 &&
            rootOffset + rootLength <= metadataOffset &&
            metadataLength > 0 &&
            metadataOffset + metadataLength <= leafOffset &&
            leafOffset + leafLength <= tileOffset &&
            tileOffset + tileLength <= size) ||
        rootLength > _maximumDirectoryBytes ||
        tileType != 1 ||
        !const {1, 2}.contains(internalCompression) ||
        !const {1, 2}.contains(tileCompression) ||
        minZoom > maxZoom ||
        maxZoom > 22) {
      throw const FormatException('Unsupported/corrupt PMTiles v3 header');
    }

    final rootBytes = await _readBytes(file, size, rootOffset, rootLength);
    final root = _decodeDirectory(rootBytes, internalCompression);
    if (root.isEmpty) throw const FormatException('Empty PMTiles directory');
    return PmtilesV3Archive._(
      file,
      size,
      leafOffset,
      leafLength,
      tileOffset,
      tileLength,
      internalCompression,
      tileCompression,
      minZoom,
      maxZoom,
      root,
    );
  }

  Future<Uint8List?> readMvt(int z, int x, int y) async {
    if (z < minZoom || z > maxZoom ||
        x < 0 || y < 0 || x >= (1 << z) || y >= (1 << z)) {
      return null;
    }
    final tileId = xyzToTileId(z, x, y);
    var entry = _find(_root, tileId);
    if (entry == null) return null;
    if (entry.runLength == 0) {
      if (entry.offset + entry.length > _leafLength ||
          entry.length > _maximumDirectoryBytes) {
        throw const FormatException('PMTiles leaf outside leaf section');
      }
      var directory = _leaves[entry.offset];
      if (directory == null) {
        final payload = await _readBytes(
          file, _size, _leafOffset + entry.offset, entry.length,
        );
        directory = _decodeDirectory(payload, _internalCompression);
        // Bound memory to a modest number of opened leaf directories.
        if (_leaves.length >= 32) _leaves.remove(_leaves.keys.first);
        _leaves[entry.offset] = directory;
      }
      entry = _find(directory, tileId);
    }
    if (entry == null || entry.runLength == 0 ||
        tileId >= entry.tileId + entry.runLength) {
      return null;
    }
    if (entry.length > _maximumTileBytes ||
        entry.offset + entry.length > _tileLength) {
      throw const FormatException('PMTiles MVT payload out of bounds');
    }
    final payload = await _readBytes(
      file, _size, _tileOffset + entry.offset, entry.length,
    );
    if (_tileCompression == 1) return payload;
    final expanded = Uint8List.fromList(gzip.decode(payload));
    if (expanded.length > _maximumInflatedTileBytes) {
      throw const FormatException('PMTiles MVT payload exceeds size limit');
    }
    return expanded;
  }

  static _DirectoryEntry? _find(List<_DirectoryEntry> entries, int id) {
    var low = 0;
    var high = entries.length;
    while (low < high) {
      final mid = (low + high) ~/ 2;
      if (entries[mid].tileId <= id) {
        low = mid + 1;
      } else {
        high = mid;
      }
    }
    if (low == 0) return null;
    final entry = entries[low - 1];
    if (entry.runLength != 0 && id >= entry.tileId + entry.runLength) {
      return null;
    }
    return entry;
  }

  static List<_DirectoryEntry> _decodeDirectory(
    Uint8List bytes,
    int compression,
  ) {
    final input = compression == 2
        ? Uint8List.fromList(gzip.decode(bytes))
        : bytes;
    if (input.length > _maximumDirectoryBytes) {
      throw const FormatException('PMTiles directory too large');
    }
    var offset = 0;

    int varint() {
      var value = 0;
      for (var shift = 0; shift < 70; shift += 7) {
        if (offset >= input.length) {
          throw const FormatException('Truncated PMTiles directory varint');
        }
        final byte = input[offset++];
        if (shift == 63 && byte > 1) {
          throw const FormatException('PMTiles varint overflow');
        }
        value |= (byte & 127) << shift;
        if (byte < 128) return value;
      }
      throw const FormatException('PMTiles varint too long');
    }

    final count = varint();
    if (count > 300000) {
      throw const FormatException('PMTiles directory count too large');
    }
    final ids = <int>[];
    var id = 0;
    for (var i = 0; i < count; i++) {
      id += varint();
      if (i > 0 && id <= ids.last) {
        throw const FormatException('Unsorted PMTiles tile IDs');
      }
      ids.add(id);
    }
    final runs = List<int>.generate(count, (_) => varint());
    final lengths = List<int>.generate(count, (_) => varint());
    final offsets = <int>[];
    var previous = 0;
    var previousLength = 0;
    for (var i = 0; i < count; i++) {
      final encoded = varint();
      final current = encoded == 0 ? previous + previousLength : encoded - 1;
      if (lengths[i] <= 0) {
        throw const FormatException('Empty PMTiles directory payload');
      }
      offsets.add(current);
      previous = current;
      previousLength = lengths[i];
    }
    if (offset != input.length) {
      throw const FormatException('Trailing PMTiles directory bytes');
    }
    return List.unmodifiable(
      List.generate(
        count,
        (i) => _DirectoryEntry(ids[i], runs[i], lengths[i], offsets[i]),
      ),
    );
  }

  static Future<Uint8List> _readBytes(
    File file,
    int fileSize,
    int offset,
    int length,
  ) async {
    if (offset < 0 || length < 0 || offset + length > fileSize) {
      throw const FormatException('PMTiles random access out of bounds');
    }
    final handle = await file.open();
    try {
      await handle.setPosition(offset);
      final bytes = await handle.read(length);
      if (bytes.length != length) {
        throw const FormatException('PMTiles truncated read');
      }
      return bytes;
    } finally {
      await handle.close();
    }
  }

  /// Standard PMTiles zoom-order Hilbert tile ID, XYZ coordinates.
  static int xyzToTileId(int z, int x, int y) {
    if (z < 0 || z > 22 ||
        x < 0 || y < 0 || x >= (1 << z) || y >= (1 << z)) {
      throw const FormatException('Invalid tile coordinate');
    }
    final n = 1 << z;
    var d = 0;
    var xx = x;
    var yy = y;
    for (var s = n >> 1; s > 0; s >>= 1) {
      final rx = (xx & s) == 0 ? 0 : 1;
      final ry = (yy & s) == 0 ? 0 : 1;
      d += s * s * ((3 * rx) ^ ry);
      if (ry == 0) {
        if (rx == 1) {
          xx = s - 1 - xx;
          yy = s - 1 - yy;
        }
        final tmp = xx;
        xx = yy;
        yy = tmp;
      }
    }
    return ((1 << (2 * z)) - 1) ~/ 3 + d;
  }
}

class _DirectoryEntry {
  const _DirectoryEntry(
    this.tileId,
    this.runLength,
    this.length,
    this.offset,
  );

  final int tileId;
  final int runLength;
  final int length;
  final int offset;
}
