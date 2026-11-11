import 'dart:math' as math;

import 'package:flutter/material.dart';

import 'review_map_data.dart';

/// A fully offline, debug-only GIS geometry preview.
/// Does not touch MapLibre's approved style and does not enable routing.
class ReviewMapScreen extends StatefulWidget {
  const ReviewMapScreen({super.key});

  @override
  State<ReviewMapScreen> createState() => _ReviewMapScreenState();
}

class _ReviewMapScreenState extends State<ReviewMapScreen> {
  static const double _worldWidth = 1080;
  static const double _worldHeight = 1410;

  final TransformationController _transform = TransformationController();
  late final Future<ReviewMapData> _preview = ReviewMapData.load();
  Size _viewport = Size.zero;
  bool _initialFit = false;
  double _zoom = 1;

  @override
  void dispose() {
    _transform.dispose();
    super.dispose();
  }

  void _camera(double lon, double lat, double scale) {
    if (_viewport.isEmpty) return;
    final x = (lon - 100) / 20 * _worldWidth;
    final y = (25 - lat) / 21 * _worldHeight;
    // Set matrix entries directly: avoids deprecated transform helpers.
    _transform.value = (Matrix4.identity()
      ..setEntry(0, 0, scale)
      ..setEntry(1, 1, scale)
      ..setEntry(0, 3, _viewport.width / 2 - x * scale)
      ..setEntry(1, 3, _viewport.height / 2 - y * scale));
    setState(() => _zoom = scale);
  }

  void _fitOverview() {
    if (_viewport.isEmpty) return;
    final scale = math.min(
      _viewport.width / _worldWidth,
      _viewport.height / _worldHeight,
    ) * .94;
    _camera(110, 14.5, scale);
  }

  void _zoomBy(double factor) {
    if (_viewport.isEmpty) return;
    final center = _transform.toScene(
      Offset(_viewport.width / 2, _viewport.height / 2),
    );
    final lon = 100 + center.dx / _worldWidth * 20;
    final lat = 25 - center.dy / _worldHeight * 21;
    _camera(lon, lat, (_zoom * factor).clamp(.25, 12));
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(
          title: const Text('NaviTaxi • Xem trước GIS'),
          actions: [
            IconButton(
              tooltip: 'Phóng to',
              icon: const Icon(Icons.add),
              onPressed: () => _zoomBy(1.4),
            ),
            IconButton(
              tooltip: 'Thu nhỏ',
              icon: const Icon(Icons.remove),
              onPressed: () => _zoomBy(1 / 1.4),
            ),
          ],
        ),
        body: FutureBuilder<ReviewMapData>(
          future: _preview,
          builder: (context, snapshot) {
            if (snapshot.hasError) {
              return const Center(
                child: Text('Không xác minh được dữ liệu xem trước GIS.'),
              );
            }
            if (!snapshot.hasData) {
              return const Center(child: CircularProgressIndicator());
            }
            final data = snapshot.data!;
            return Column(
              children: [
                const MaterialBanner(
                  content: Text(
                    'BẢN XEM TRƯỚC, CHƯA ĐẠT P0. '
                    'Đường viền tỉnh đã giản lược; dấu ngoài khơi '
                    'không biểu thị diện tích đất đảo hay ranh giới biển. '
                    'Không dùng bản đồ này để dẫn đường.',
                    style: TextStyle(fontSize: 12),
                  ),
                  actions: [Text('GIS REVIEW')],
                ),
                SizedBox(
                  height: 58,
                  child: ListView(
                    scrollDirection: Axis.horizontal,
                    padding: const EdgeInsets.symmetric(horizontal: 8),
                    children: [
                      TextButton.icon(
                        icon: const Icon(Icons.public),
                        label: const Text('Toàn Việt Nam'),
                        onPressed: _fitOverview,
                      ),
                      TextButton(
                        onPressed: () => _camera(112.225, 16.467, 3.2),
                        child: const Text('Hoàng Sa'),
                      ),
                      TextButton(
                        onPressed: () => _camera(114.005, 8.808, 2.7),
                        child: const Text('Trường Sa'),
                      ),
                      TextButton(
                        onPressed: () => _camera(111.5, 13.5, 1.3),
                        child: const Text('Biển Đông'),
                      ),
                    ],
                  ),
                ),
                Expanded(
                  child: LayoutBuilder(
                    builder: (context, box) {
                      final next = Size(box.maxWidth, box.maxHeight);
                      _viewport = next;
                      if (!_initialFit) {
                        _initialFit = true;
                        WidgetsBinding.instance.addPostFrameCallback((_) {
                          if (mounted) _fitOverview();
                        });
                      }
                      return InteractiveViewer(
                        transformationController: _transform,
                        boundaryMargin: const EdgeInsets.all(1800),
                        constrained: false,
                        minScale: .24,
                        maxScale: 12,
                        onInteractionUpdate: (details) {
                          final value = _transform.value.getMaxScaleOnAxis();
                          if ((value - _zoom).abs() > .02) {
                            setState(() => _zoom = value);
                          }
                        },
                        child: CustomPaint(
                          size: const Size(_worldWidth, _worldHeight),
                          painter: _ReviewMapPainter(data, _zoom),
                        ),
                      );
                    },
                  ),
                ),
                const Padding(
                  padding: EdgeInsets.fromLTRB(10, 4, 10, 10),
                  child: Text(
                    'Be: đa giác tỉnh giản lược  •  Cam: tâm thành phần ngoài khơi  '
                    '•  Đỏ: địa danh VN-2000 cần rà soát. '
                    'Không bao gồm bản đồ đường, biển báo hoặc giới hạn tốc độ.',
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

class _ReviewMapPainter extends CustomPainter {
  const _ReviewMapPainter(this.data, this.scale);

  final ReviewMapData data;
  final double scale;

  Offset _point(num lon, num lat) => Offset(
        (lon - 100) / 20 * 1080,
        (25 - lat) / 21 * 1410,
      );

  void _label(Canvas canvas, String label, Offset at,
      {Color color = const Color(0xFF254E6C), double fontSize = 15,
      FontWeight weight = FontWeight.w600}) {
    final painter = TextPainter(
      text: TextSpan(
        text: label,
        style: TextStyle(
          fontSize: fontSize / scale,
          color: color,
          fontWeight: weight,
          backgroundColor: const Color(0xDFF5F9FA),
        ),
      ),
      textDirection: TextDirection.ltr,
      maxLines: 1,
    )..layout(maxWidth: 230 / scale);
    painter.paint(
      canvas,
      at - Offset(painter.width / 2, painter.height / 2),
    );
  }

  @override
  void paint(Canvas canvas, Size size) {
    canvas.drawColor(const Color(0xFFB8E0EF), BlendMode.src);
    final grid = Paint()
      ..color = const Color(0x5581BDD0)
      ..strokeWidth = .8 / scale;
    for (var lon = 100; lon <= 120; lon += 2) {
      canvas.drawLine(_point(lon, 5), _point(lon, 25), grid);
    }
    for (var lat = 5; lat <= 25; lat += 2) {
      canvas.drawLine(_point(100, lat), _point(120, lat), grid);
    }

    for (final entry in data.polygons) {
      if (entry is! List || entry.length != 2) continue;
      final rings = entry[1];
      if (rings is! List) continue;
      final path = Path()..fillType = PathFillType.evenOdd;
      for (final ring in rings) {
        if (ring is! List || ring.length < 3) continue;
        var started = false;
        for (final coord in ring) {
          if (coord is! List || coord.length < 2 ||
              coord[0] is! num || coord[1] is! num) {
            continue;
          }
          final at = _point(coord[0] as num, coord[1] as num);
          if (!started) {
            path.moveTo(at.dx, at.dy);
            started = true;
          } else {
            path.lineTo(at.dx, at.dy);
          }
        }
        if (started) path.close();
      }
      canvas.drawPath(
        path,
        Paint()..color = const Color(0xFFF1E8D1),
      );
      canvas.drawPath(
        path,
        Paint()
          ..color = const Color(0xFF849289)
          ..style = PaintingStyle.stroke
          ..strokeWidth = 1.1 / scale,
      );
    }

    final offshorePaint = Paint()
      ..color = const Color(0xFFDB8124);
    for (final row in data.offshore) {
      if (row is! List || row.length < 2) continue;
      canvas.drawCircle(
        _point(row[0] as num, row[1] as num),
        2.0 / scale,
        offshorePaint,
      );
    }

    final namedPointPaint = Paint()
      ..color = const Color(0xFFD43847);
    for (final row in data.official) {
      if (row is! List || row.length < 4) continue;
      final at = _point(row[0] as num, row[1] as num);
      canvas.drawCircle(at, 4.5 / scale, namedPointPaint);
      if (scale > 1.6) {
        _label(
          canvas,
          row[2].toString(),
          at + Offset(0, -13 / scale),
          color: const Color(0xFFA51B2B),
          fontSize: 10,
        );
      }
    }

    if (scale > .85) {
      for (final row in data.provinces) {
        if (row is! List || row.length < 3) continue;
        _label(
          canvas,
          row[0].toString(),
          _point(row[1] as num, row[2] as num),
          fontSize: 11,
        );
      }
    }
    for (final row in data.labels) {
      if (row is! List || row.length < 3) continue;
      _label(
        canvas,
        row[2].toString(),
        _point(row[0] as num, row[1] as num),
        fontSize: 20,
        weight: FontWeight.w800,
      );
    }
  }

  @override
  bool shouldRepaint(covariant _ReviewMapPainter oldDelegate) =>
      oldDelegate.data != data || oldDelegate.scale != scale;
}
