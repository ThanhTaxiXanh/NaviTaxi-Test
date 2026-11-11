import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:maplibre_gl/maplibre_gl.dart';

import 'admin_catalog.dart';
import 'admin_search_delegate.dart';
import 'review_label_anchors.dart';
import 'review_map_data.dart';
import 'review_maplibre_style.dart';

/// Native GIS viewer for private DEBUG builds. No production P0 activation.
/// Administrative anchors are derived from source geometry, NOT legal borders.
class ReviewMaplibreScreen extends StatefulWidget {
  const ReviewMaplibreScreen({super.key});

  @override
  State<ReviewMaplibreScreen> createState() => _ReviewMaplibreScreenState();
}

enum _LabelKind { region, province, ward }

class _ProjectedLabel {
  const _ProjectedLabel(this.name, this.x, this.y, this.kind);

  final String name;
  final double x;
  final double y;
  final _LabelKind kind;
}

class _GeoLabel {
  const _GeoLabel(this.name, this.latitude, this.longitude, this.kind);

  final String name;
  final double latitude;
  final double longitude;
  final _LabelKind kind;
}

class _ReviewMaplibreScreenState extends State<ReviewMaplibreScreen> {
  static const bool _reviewRequested = bool.fromEnvironment(
    'NAVITAXI_REVIEW_MODE', defaultValue: false,
  );
  static const double _wardLabelMinZoom = 8.5;

  late final Future<String> _style = _loadStyle();
  List<ReviewLabelAnchor> _regionAnchors = const [];
  AdminCatalog? _catalog;
  List<_ProjectedLabel> _projected = const [];
  MapLibreMapController? _controller;
  double _zoom = 3.4;
  bool _projecting = false;
  bool _projectAgain = false;

  Future<String> _loadStyle() async {
    final data = await ReviewMapData.load();
    final catalog = await AdminCatalog.load();
    final style = ReviewMaplibreStyle.build(data);
    _regionAnchors = ReviewLabelAnchors.fromData(data);
    _catalog = catalog;
    return style;
  }

  Future<void> _search() async {
    final catalog = _catalog;
    if (catalog == null) return;
    final result = await showSearch<AdminPlace?>(
      context: context,
      delegate: AdminSearchDelegate(catalog),
    );
    if (result == null || !mounted) return;
    if (result.hasAnchor) {
      await _move(
        result.latitude!,
        result.longitude!,
        result.isProvince ? 8.0 : 11.0,
      );
      return;
    }
    final groupName = switch (result.code) {
      '20333' => 'Hoàng Sa',
      '22736' => 'Trường Sa',
      _ => null,
    };
    if (groupName != null) {
      // Existing reviewed group-label anchors, never fabricated ward GPS.
      for (final anchor in _regionAnchors) {
        if (anchor.name == groupName) {
          await _move(anchor.latitude, anchor.longitude, 6.0);
          break;
        }
      }
    }
  }

  void _refreshLabels() {
    final controller = _controller;
    if (controller == null || !mounted || _regionAnchors.isEmpty) return;
    if (_projecting) {
      _projectAgain = true;
      return;
    }
    _projecting = true;
    _projectLabels(controller);
  }

  Future<void> _projectLabels(MapLibreMapController controller) async {
    try {
      final labels = <_GeoLabel>[
        for (final anchor in _regionAnchors)
          _GeoLabel(anchor.name, anchor.latitude, anchor.longitude,
              _LabelKind.region),
      ];

      final catalog = _catalog;
      if (catalog != null && catalog.reviewAnchorCount >= 34) {
        final bounds = await controller.getVisibleRegion();
        if (!mounted || _controller != controller) return;
        final showWards = _zoom >= _wardLabelMinZoom;
        if (_zoom >= 3.9) {
          labels.addAll(
            catalog.visible(
              south: bounds.southwest.latitude,
              north: bounds.northeast.latitude,
              west: bounds.southwest.longitude,
              east: bounds.northeast.longitude,
              showWards: showWards,
              limit: showWards ? 120 : 34,
            ).map((place) => _GeoLabel(
                  place.name,
                  place.latitude!,
                  place.longitude!,
                  showWards ? _LabelKind.ward : _LabelKind.province,
                )),
          );
        }
      }

      final pixels = await controller.toScreenLocationBatch(
        labels.map((label) => LatLng(label.latitude, label.longitude)),
      );
      if (!mounted || _controller != controller ||
          pixels.length != labels.length) return;

      final accepted = <_ProjectedLabel>[];
      final occupied = <String>{};
      for (var i = 0; i < labels.length; i++) {
        final x = pixels[i].x.toDouble();
        final y = pixels[i].y.toDouble();
        if (!x.isFinite || !y.isFinite) continue;
        final item = labels[i];
        if (item.kind != _LabelKind.region) {
          // Simple collision grid: readable labels at street-level zoom
          // instead of thousands of overlapping Flutter text widgets.
          final cell = '${(x / 132).floor()}:${(y / 44).floor()}';
          if (!occupied.add(cell)) continue;
        }
        accepted.add(_ProjectedLabel(item.name, x, y, item.kind));
      }
      setState(() => _projected = accepted);
    } catch (_) {
      // Native map may reject queries during layout/style changes.
      // Another camera-idle/style-loaded event can refresh the overlay.
    } finally {
      _projecting = false;
      if (_projectAgain && mounted) {
        _projectAgain = false;
        _refreshLabels();
      }
    }
  }

  Future<void> _move(double latitude, double longitude, double zoom) async {
    final controller = _controller;
    if (controller == null) return;
    await controller.animateCamera(
      CameraUpdate.newLatLngZoom(LatLng(latitude, longitude), zoom),
    );
  }

  @override
  void dispose() {
    _controller = null;
    super.dispose();
  }

  Widget _labelAt(_ProjectedLabel label) {
    final isRegion = label.kind == _LabelKind.region;
    final isProvince = label.kind == _LabelKind.province;
    return IgnorePointer(
      child: FractionalTranslation(
        translation: const Offset(-0.5, -0.5),
        child: DecoratedBox(
          decoration: BoxDecoration(
            color: isRegion
                ? const Color(0xF4F6FCFF)
                : const Color(0xEAF9FBFC),
            border: Border.all(
              color: isRegion
                  ? const Color(0xFF9AB9C5)
                  : const Color(0x669AB9C5),
            ),
            borderRadius: BorderRadius.circular(6),
          ),
          child: Padding(
            padding: EdgeInsets.symmetric(
              horizontal: isRegion ? 7 : 4,
              vertical: isRegion ? 4 : 2,
            ),
            child: Text(
              label.name,
              maxLines: 1,
              style: TextStyle(
                color: isRegion
                    ? const Color(0xFF164464)
                    : const Color(0xFF244D62),
                fontSize: isRegion ? 15 : (isProvince ? 12 : 10.5),
                fontWeight:
                    isRegion ? FontWeight.w800 : FontWeight.w600,
              ),
            ),
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (!kDebugMode || !_reviewRequested) {
      return const Scaffold(
        body: Center(
          child: Text('Bản xem trước GIS chỉ có trong APK debug.'),
        ),
      );
    }
    return Scaffold(
      appBar: AppBar(
        title: const Text('NaviTaxi • Bản đồ Việt Nam'),
        actions: [
          IconButton(
            tooltip: 'Tìm tỉnh, xã, phường',
            onPressed: _search,
            icon: const Icon(Icons.search),
          ),
        ],
      ),
      body: FutureBuilder<String>(
        future: _style,
        builder: (context, snapshot) {
          if (snapshot.hasError) {
            return const Center(
              child: Text('Không đọc được dữ liệu GIS hoặc danh mục địa danh.'),
            );
          }
          if (!snapshot.hasData) {
            return const Center(child: CircularProgressIndicator());
          }
          return Column(
            children: [
              const MaterialBanner(
                content: Text(
                  'GIS REVIEW • Chưa phải bản đồ dẫn đường. '
                  '34 tỉnh và 3.321 xã/phường/đặc khu có thể tìm theo tên. '
                  'Tên đặt trên bản đồ từ điểm đại diện của GIS; '
                  'không phải mốc ranh giới hay xác nhận chủ quyền.',
                  style: TextStyle(fontSize: 12),
                ),
                actions: [Text('NOT P0')],
              ),
              SizedBox(
                height: 52,
                child: ListView(
                  scrollDirection: Axis.horizontal,
                  children: [
                    TextButton(
                      onPressed: () => _move(14.5, 110, 3.4),
                      child: const Text('Toàn Việt Nam'),
                    ),
                    TextButton(
                      onPressed: () => _move(16.467, 112.225, 6.0),
                      child: const Text('Hoàng Sa'),
                    ),
                    TextButton(
                      onPressed: () => _move(8.808, 114.005, 5.6),
                      child: const Text('Trường Sa'),
                    ),
                    TextButton(
                      onPressed: () => _move(13.5, 111.5, 4.3),
                      child: const Text('Biển Đông'),
                    ),
                    TextButton(
                      onPressed: () => _move(21.028, 105.854, 10.5),
                      child: const Text('Hà Nội'),
                    ),
                    TextButton(
                      onPressed: () => _move(10.776, 106.7, 10.5),
                      child: const Text('TP. Hồ Chí Minh'),
                    ),
                  ],
                ),
              ),
              Expanded(
                child: LayoutBuilder(
                  builder: (context, constraints) => Stack(
                    clipBehavior: Clip.hardEdge,
                    children: [
                      Positioned.fill(
                        child: MapLibreMap(
                          styleString: snapshot.data!,
                          initialCameraPosition: const CameraPosition(
                            target: LatLng(14.5, 110),
                            zoom: 3.4,
                          ),
                          onMapCreated: (controller) {
                            _controller = controller;
                            _refreshLabels();
                          },
                          onStyleLoadedCallback: _refreshLabels,
                          onCameraMove: (camera) {
                            _zoom = camera.zoom;
                            _refreshLabels();
                          },
                          onCameraIdle: _refreshLabels,
                          compassEnabled: true,
                          rotateGesturesEnabled: true,
                          tiltGesturesEnabled: false,
                        ),
                      ),
                      for (final label in _projected)
                        if (label.x >= 0 &&
                            label.y >= 0 &&
                            label.x <= constraints.maxWidth &&
                            label.y <= constraints.maxHeight)
                          Positioned(
                            left: label.x,
                            top: label.y,
                            child: _labelAt(label),
                          ),
                    ],
                  ),
                ),
              ),
              Padding(
                padding: const EdgeInsets.fromLTRB(12, 5, 12, 10),
                child: Text(
                  _catalog?.reviewAnchorCount == 3353
                      ? 'Phóng gần để xem tên xã/phường. '
                          'Nhãn hiển thị không cần Internet; '
                          'đường sá và dẫn đường chưa được tích hợp.'
                      : 'Đã có danh mục 34 tỉnh và 3.321 xã/phường. '
                          'Bản build này chưa có điểm đặt nhãn GIS chi tiết.',
                  textAlign: TextAlign.center,
                  style: const TextStyle(fontSize: 11),
                ),
              ),
            ],
          );
        },
      ),
    );
  }
}
