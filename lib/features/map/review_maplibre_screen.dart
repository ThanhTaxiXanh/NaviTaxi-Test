import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:maplibre_gl/maplibre_gl.dart';

import 'review_label_anchors.dart';
import 'review_map_data.dart';
import 'review_maplibre_style.dart';

/// Native MapLibre review renderer, deliberately isolated from P0 activation.
/// The three mandatory Vietnamese labels are Flutter text overlays anchored
/// by the map projection, so their display does not need network glyph PBFs.
class ReviewMaplibreScreen extends StatefulWidget {
  const ReviewMaplibreScreen({super.key});

  @override
  State<ReviewMaplibreScreen> createState() => _ReviewMaplibreScreenState();
}

class _ProjectedLabel {
  const _ProjectedLabel(this.name, this.x, this.y);

  final String name;
  final double x;
  final double y;
}

class _ReviewMaplibreScreenState extends State<ReviewMaplibreScreen> {
  static const bool _reviewRequested = bool.fromEnvironment(
    'NAVITAXI_REVIEW_MODE', defaultValue: false,
  );

  late final Future<String> _style = _loadStyle();
  List<ReviewLabelAnchor> _anchors = const [];
  List<_ProjectedLabel> _projected = const [];
  MapLibreMapController? _controller;
  bool _projecting = false;
  bool _projectAgain = false;

  Future<String> _loadStyle() async {
    final data = await ReviewMapData.load();
    final style = ReviewMaplibreStyle.build(data);
    _anchors = ReviewLabelAnchors.fromData(data);
    return style;
  }

  /// Runs projection against the native map camera rather than using a
  /// hand-written Web Mercator approximation. Repeated camera events are
  /// coalesced, and the final idle event forces a final refresh.
  void _refreshLabels() {
    final controller = _controller;
    if (controller == null || !mounted || _anchors.isEmpty) return;
    if (_projecting) {
      _projectAgain = true;
      return;
    }
    _projecting = true;
    _projectLabels(controller);
  }

  Future<void> _projectLabels(MapLibreMapController controller) async {
    try {
      final screenPoints = await controller.toScreenLocationBatch(
        _anchors.map((anchor) => LatLng(anchor.latitude, anchor.longitude)),
      );
      if (!mounted || _controller != controller) return;
      if (screenPoints.length != _anchors.length) {
        throw const FormatException('Incorrect map projection result');
      }
      final projected = <_ProjectedLabel>[];
      for (var i = 0; i < _anchors.length; i++) {
        final x = screenPoints[i].x.toDouble();
        final y = screenPoints[i].y.toDouble();
        if (!x.isFinite || !y.isFinite) continue;
        projected.add(_ProjectedLabel(_anchors[i].name, x, y));
      }
      setState(() => _projected = projected);
    } catch (_) {
      // Initial camera/style transitions can temporarily reject projection.
      // Subsequent onCameraIdle/onStyleLoadedCallback events retry safely.
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
    return IgnorePointer(
      child: FractionalTranslation(
        translation: const Offset(-0.5, -0.5),
        child: DecoratedBox(
          decoration: BoxDecoration(
            color: const Color(0xF4F6FCFF),
            border: Border.all(color: const Color(0xFF9AB9C5)),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 4),
            child: Text(
              label.name,
              maxLines: 1,
              style: const TextStyle(
                color: Color(0xFF164464),
                fontSize: 15,
                fontWeight: FontWeight.w800,
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
          child: Text('Bản xem trước MapLibre chỉ có trong APK debug GIS.'),
        ),
      );
    }
    return Scaffold(
      appBar: AppBar(title: const Text('NaviTaxi • MapLibre GIS QA')),
      body: FutureBuilder<String>(
        future: _style,
        builder: (context, snapshot) {
          if (snapshot.hasError) {
            return const Center(
              child: Text(
                'Dữ liệu GIS không hợp lệ. Đã từ chối hiển thị bản xem trước.',
              ),
            );
          }
          if (!snapshot.hasData) {
            return const Center(child: CircularProgressIndicator());
          }
          return Column(
            children: [
              const MaterialBanner(
                content: Text(
                  'CHỈ KIỂM THỬ • NOT P0. Hoàng Sa, Trường Sa, Biển Đông '
                  'được ghim bằng nhãn Flutter, không cần glyph trực tuyến. '
                  'Viền tỉnh giản lược không phải đường bờ đảo hay ranh giới biển. '
                  'Tên tỉnh/điểm nhỏ của MapLibre vẫn có thể cần Internet.',
                  style: TextStyle(fontSize: 12),
                ),
                actions: [Text('GIS DEBUG')],
              ),
              SizedBox(
                height: 54,
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
                          onCameraMove: (_) => _refreshLabels(),
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
              const Padding(
                padding: EdgeInsets.fromLTRB(12, 6, 12, 10),
                child: Text(
                  'Nhãn Việt Nam bám tọa độ điểm tham chiếu (không biểu thị '
                  'ranh giới). Không có dữ liệu dẫn đường. '
                  'Cần kiểm tra thực tế chế độ máy bay trước khi kết luận offline.',
                  textAlign: TextAlign.center,
                  style: TextStyle(fontSize: 11),
                ),
              ),
            ],
          );
        },
      ),
    );
  }
}
