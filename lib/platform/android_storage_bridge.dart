import 'package:flutter/services.dart';

import '../features/offline/offline_package.dart';

/// Communicates with Kotlin's private PMTiles quarantine intake store.
/// A successful SHA-256 never implies P0 approval or basemap activation.
class AndroidStorageBridge {
  const AndroidStorageBridge({
    this.channel = const MethodChannel('vn.navitaxi/map_storage'),
  });

  final MethodChannel channel;

  Future<String> getOfflineDirectory() async =>
      (await channel.invokeMethod<String>('getOfflineDirectory')) ?? '';

  Future<int> getAvailableBytes() async =>
      (await channel.invokeMethod<int>('getAvailableBytes')) ?? 0;

  Future<List<QuarantinedArchive>> listImported() async {
    final entries = await channel.invokeListMethod<dynamic>('listImported');
    return (entries ?? const <dynamic>[])
        .map((entry) => QuarantinedArchive.fromMap(entry as Map))
        .toList(growable: false);
  }

  /// Returns null when the user dismisses the document picker.
  Future<bool?> importArchive(String filename) async {
    final result = await channel.invokeMapMethod<dynamic, dynamic>(
      'importArchive',
      <String, String>{'filename': filename},
    );
    return result == null ? null : result['sha256Verified'] == true;
  }

  Future<bool> verifyImported(String filename) async {
    final result = await channel.invokeMapMethod<dynamic, dynamic>(
      'verifyImported',
      <String, String>{'filename': filename},
    );
    return result?['sha256Verified'] == true &&
        result?['p0Approved'] == false;
  }

  Future<bool> deleteImported(String filename) async =>
      await channel.invokeMethod<bool>(
        'deleteImported',
        <String, String>{'filename': filename},
      ) ??
      false;
}
