import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:maplibre_gl/maplibre_gl.dart';

import 'review_map_data.dart';
import 'review_maplibre_style.dart';

/// Actual native MapLibre renderer for quarantined, simplified GIS review.
/// Only reachable in the explicitly requested DEBUG review APK.
/// It never reads or changes MapRelease, the production style or its P0 gate.
class ReviewMaplibreScreen extends StatefulWidget {
  const ReviewMaplibreScreen({super.key});

  @override
  State<ReviewMaplibreScreen> createState() => _ReviewMaplibreScreenState();
}

class _ReviewMaplibreScreenState extends State<ReviewMaplibreScreen> {
  static const bool _reviewRequested = bool.fromEnvironment(
    'NAVITAXI_REVIEW_MODE', defaultValue: false,
  );
  late final Future<String> _style = _loadStyle();
  MapLibreMapController? _controller;

  Future<String> _loadStyle() async =>
      ReviewMaplibreStyle.build(await ReviewMapData.load());

  Future<void> _move(double latitude, double longitude, double zoom) async {
    final controller = _controller;
    if (controller == null) return;
    await controller.animateCamera(
      CameraUpdate.newLatLngZoom(LatLng(latitude, longitude), zoom),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (!kDebugMode || !_reviewRequested) {
      return const Scaffold(
        body: Center(child: Text('Bản xem trước MapLibre chỉ có trong APK debug GIS.')),
      );
    }
    return Scaffold(
      appBar: AppBar(title: const Text('NaviTaxi • MapLibre GIS QA')),
      body: FutureBuilder<String>(
        future: _style,
        builder: (context, snapshot) {
          if (snapshot.hasError) {
            return const Center(child: Text(
              'Dữ liệu GIS không hợp lệ. Đã từ chối hiển thị bản xem trước.',
            ));
          }
          if (!snapshot.hasData) {
            return const Center(child: CircularProgressIndicator());
          }
          return Column(
            children: [
              const MaterialBanner(
                content: Text(
                  'CHỈ KIỂM THỬ • NOT P0. Các nét vẽ là viền dữ liệu '
                  'hành chính giản lược, không phải bờ đảo hay biên giới biển. '
                  'Điểm cam/đỏ không phải đa giác đất nổi. '
                  'Nhãn MapLibre cần Internet để tải glyph ở bản thử này.',
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
                child: MapLibreMap(
                  styleString: snapshot.data!,
                  initialCameraPosition: const CameraPosition(
                    target: LatLng(14.5, 110),
                    zoom: 3.4,
                  ),
                  onMapCreated: (controller) => _controller = controller,
                  compassEnabled: true,
                  rotateGesturesEnabled: true,
                  tiltGesturesEnabled: false,
                ),
              ),
              const Padding(
                padding: EdgeInsets.fromLTRB(12, 6, 12, 10),
                child: Text(
                  'Viền: ranh tỉnh sơ bộ • Cam: điểm vùng xa bờ • '
                  'Đỏ: địa danh cần rà soát. Không có đường sá/định tuyến. '
                  'P0 tiếp tục BLOCKED.',
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
