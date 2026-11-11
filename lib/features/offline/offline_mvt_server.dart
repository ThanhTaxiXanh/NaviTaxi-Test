import 'dart:async';
import 'dart:io';
import 'dart:math';

import 'package:flutter/foundation.dart';

import 'pmtiles_v3.dart';

/// Loopback-only, tokenized MVT endpoint for private DEBUG GIS review.
/// Serves only SHA-verified user imports returned by the Kotlin allowlist.
///
/// It is NOT a production offline downloader or an approved sovereignty map.
/// The regular MapRelease path never calls this server.
class OfflineMvtServer {
  OfflineMvtServer._(this._server, this._token, this._archives) {
    _subscription = _server.listen((request) {
      unawaited(_handle(request));
    });
  }

  static const sources = <String, String>{
    'roads': 'hotosm_vnm_roads_osm.pmtiles',
    'buildings': 'hotosm_vnm_buildings_osm.pmtiles',
    'poi': 'hotosm_vnm_points_of_interest_osm.pmtiles',
  };

  final HttpServer _server;
  final String _token;
  final Map<String, PmtilesV3Archive> _archives;
  late final StreamSubscription<HttpRequest> _subscription;

  int get sourceCount => _archives.length;
  Iterable<String> get enabledKinds => _archives.keys;


  String tileTemplate(String source) {
    if (!_archives.containsKey(source)) {
      throw ArgumentError.value(source, 'source', 'Not imported/verified');
    }
    return 'http://127.0.0.1:${_server.port}/$_token/$source/{z}/{x}/{y}.pbf';
  }

  static Future<OfflineMvtServer?> start(
    Map<String, String> verifiedByKotlin,
  ) async {
    if (!kDebugMode) {
      throw StateError('Local PMTiles streaming is debug-only');
    }
    if (verifiedByKotlin.isEmpty) return null;
    if (verifiedByKotlin.keys.any((name) => !sources.containsValue(name))) {
      throw const FormatException('Unrecognized offline PMTiles filename');
    }
    final archives = <String, PmtilesV3Archive>{};
    for (final entry in sources.entries) {
      final path = verifiedByKotlin[entry.value];
      if (path == null) continue;
      if (!path.endsWith('/offline-quarantine/${entry.value}')) {
        throw const FormatException('PMTiles must be in the private quarantine');
      }
      archives[entry.key] = await PmtilesV3Archive.open(path);
    }
    if (archives.isEmpty) return null;
    final random = Random.secure();
    final token = List.generate(20, (_) => random.nextInt(256).toRadixString(16).padLeft(2, '0')).join();
    final server = await HttpServer.bind(
      InternetAddress.loopbackIPv4,
      0,
      shared: false,
    );
    return OfflineMvtServer._(server, token, Map.unmodifiable(archives));
  }

  Future<void> _handle(HttpRequest request) async {
    final reply = request.response;
    reply.headers.set(HttpHeaders.cacheControlHeader, 'no-store');
    reply.headers.set('X-Content-Type-Options', 'nosniff');
    reply.persistentConnection = false;
    try {
      final parts = request.uri.pathSegments;
      if (request.method != 'GET' ||
          parts.length != 5 ||
          parts[0] != _token ||
          !_archives.containsKey(parts[1]) ||
          !parts[4].endsWith('.pbf')) {
        reply.statusCode = HttpStatus.notFound;
        return;
      }
      final z = int.tryParse(parts[2]);
      final x = int.tryParse(parts[3]);
      final y = int.tryParse(parts[4].substring(0, parts[4].length - 4));
      if (z == null || x == null || y == null ||
          z < 0 || z > 22 || x < 0 || y < 0 ||
          x >= (1 << z) || y >= (1 << z)) {
        reply.statusCode = HttpStatus.badRequest;
        return;
      }
      final tile = await _archives[parts[1]]!.readMvt(z, x, y);
      if (tile == null) {
        reply.statusCode = HttpStatus.noContent;
        return;
      }
      reply.headers.contentType = ContentType(
        'application', 'vnd.mapbox-vector-tile',
      );
      reply.headers.contentLength = tile.length;
      reply.add(tile);
    } catch (_) {
      try {
        reply.statusCode = HttpStatus.internalServerError;
      } catch (_) {
        // Response may already have started when a client disconnects.
      }
    } finally {
      try {
        await reply.close();
      } catch (_) {
        // A cancelled MapLibre tile request should not crash the app.
      }
    }
  }

  Future<void> close() async {
    await _subscription.cancel();
    await _server.close(force: true);
  }
}
