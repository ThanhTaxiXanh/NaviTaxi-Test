import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:maplibre_gl/maplibre_gl.dart';

import '../../core/map_release.dart';
import '../../core/style_policy.dart';
import '../offline/offline_packages_screen.dart';
import '../../platform/android_storage_bridge.dart';

class MapScreen extends StatefulWidget {
  const MapScreen({super.key});

  @override
  State<MapScreen> createState() => _MapScreenState();
}

class _BootStyle {
  const _BootStyle(this.style, this.dataApproved, this.reason);

  final String style;
  final bool dataApproved;
  final String reason;
}

class _MapScreenState extends State<MapScreen> {
  static const _fallbackStyle = '{"version":8,"sources":{},'
      '"layers":[{"id":"background","type":"background",'
      '"paint":{"background-color":"#e5edf2"}}]}';

  late final Future<_BootStyle> _bootStyle = _loadBootStyle();
  MapLibreMapController? _controller;
  final _storage = const AndroidStorageBridge();

  Future<_BootStyle> _loadBootStyle() async {
    try {
      final release = await MapRelease.load();
      if (!release.mayDisplayVerifiedData) {
        return const _BootStyle(
          _fallbackStyle,
          false,
          'Bộ bản đồ chưa có phê duyệt P0. Không tải tile chưa xác minh.',
        );
      }
      if (!release.stylePath.startsWith('assets/styles/')) {
        throw const FormatException('Invalid style asset path');
      }
      final rawStyle = await rootBundle.loadString(release.stylePath);
      if (!StylePolicy.isStructurallySafeForApprovedRelease(rawStyle)) {
        throw const FormatException('Style failed structural preflight');
      }
      return _BootStyle(rawStyle, true, 'Bộ bản đồ đã qua tiền kiểm ứng dụng.');
    } catch (_) {
      return const _BootStyle(
        _fallbackStyle,
        false,
        'Không thể xác minh manifest/style. Đã chặn dữ liệu bản đồ.',
      );
    }
  }

  Future<void> _showStorage() async {
    try {
      final path = await _storage.getOfflineDirectory();
      final bytes = await _storage.getAvailableBytes();
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Thư mục offline: $path\\nBộ nhớ trống: ${bytes ~/ (1024 * 1024)} MiB'),
        ),
      );
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Chưa kết nối được dịch vụ lưu trữ Android.')),
      );
    }
  }

  Future<void> _zoom(bool zoomIn) async {
    final controller = _controller;
    if (controller == null) return;
    await controller.animateCamera(
      zoomIn ? CameraUpdate.zoomIn() : CameraUpdate.zoomOut(),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: FutureBuilder<_BootStyle>(
        future: _bootStyle,
        builder: (context, snapshot) {
          if (!snapshot.hasData) {
            return const Center(child: CircularProgressIndicator());
          }
          final boot = snapshot.data!;
          return Stack(
            children: [
              Positioned.fill(
                child: MapLibreMap(
                  styleString: boot.style,
                  initialCameraPosition: const CameraPosition(
                    target: LatLng(16.05, 106.0),
                    zoom: 4.0,
                  ),
                  onMapCreated: (controller) {
                    _controller = controller;
                  },
                  compassEnabled: true,
                  rotateGesturesEnabled: true,
                  tiltGesturesEnabled: true,
                ),
              ),
              SafeArea(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Row(
                    children: [
                      Expanded(
                        child: Card(
                          elevation: 2,
                          child: Padding(
                            padding: const EdgeInsets.all(12),
                            child: Text(
                              'NaviTaxi Việt Nam  •  ${boot.dataApproved ? 'Bản đồ được duyệt' : 'P0: CHƯA ĐẠT'}',
                              style: const TextStyle(fontWeight: FontWeight.w600),
                            ),
                          ),
                        ),
                      ),
                      IconButton.filledTonal(
                        tooltip: 'Thông tin bộ nhớ offline',
                        onPressed: () {
                          Navigator.of(context).push(
                            MaterialPageRoute<void>(
                              builder: (_) => const OfflinePackagesScreen(),
                            ),
                          );
                        },
                        icon: const Icon(Icons.storage_outlined),
                      ),
                    ],
                  ),
                ),
              ),
              Positioned(
                right: 12,
                bottom: 166,
                child: Column(
                  children: [
                    FloatingActionButton.small(
                      heroTag: 'zoom-plus',
                      onPressed: () => _zoom(true),
                      child: const Icon(Icons.add),
                    ),
                    const SizedBox(height: 8),
                    FloatingActionButton.small(
                      heroTag: 'zoom-minus',
                      onPressed: () => _zoom(false),
                      child: const Icon(Icons.remove),
                    ),
                  ],
                ),
              ),
              Positioned(
                left: 14,
                right: 14,
                bottom: 30,
                child: Card(
                  child: Padding(
                    padding: const EdgeInsets.all(14),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Text(
                          'Chế độ an toàn dữ liệu GIS',
                          style: TextStyle(fontWeight: FontWeight.bold),
                        ),
                        const SizedBox(height: 4),
                        Text(boot.reason),
                        const SizedBox(height: 6),
                        const Text(
                          'Chưa triển khai tìm kiếm, GPS và tải bản đồ offline.',
                          style: TextStyle(fontSize: 12),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ],
          );
        },
      ),
    );
  }
}
