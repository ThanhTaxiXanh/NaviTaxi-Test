import 'package:flutter/services.dart';

/// Android storage diagnostics only. No downloading or package installation yet.
class AndroidStorageBridge {
  const AndroidStorageBridge();

  static const _channel = MethodChannel('vn.navitaxi/map_storage');

  Future<String> getOfflineDirectory() async =>
      (await _channel.invokeMethod<String>('getOfflineDirectory')) ?? '';

  Future<int> getAvailableBytes() async =>
      (await _channel.invokeMethod<int>('getAvailableBytes')) ?? 0;
}
