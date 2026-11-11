import 'review_map_data.dart';

/// Geographic anchor for one mandatory Vietnamese review label.
///
/// These are source-provided label positions, not coastlines, maritime
/// borders, or an assertion about the legal extent of an island.
class ReviewLabelAnchor {
  const ReviewLabelAnchor({
    required this.name,
    required this.latitude,
    required this.longitude,
  });

  final String name;
  final double latitude;
  final double longitude;
}

/// Prepare and validate the three essential group labels for Flutter's
/// text overlay. Flutter's text renderer works without MapLibre glyph PBFs.
class ReviewLabelAnchors {
  static const names = <String>{'Hoàng Sa', 'Trường Sa', 'Biển Đông'};

  static List<ReviewLabelAnchor> fromData(ReviewMapData data) {
    if (data.labels.length != names.length) {
      throw const FormatException('Expected exactly three group labels');
    }
    final observed = <String>{};
    final anchors = <ReviewLabelAnchor>[];
    for (final row in data.labels) {
      if (row is! List || row.length != 3 || row[0] is! num ||
          row[1] is! num || row[2] is! String) {
        throw const FormatException('Malformed group label anchor');
      }
      final longitude = (row[0] as num).toDouble();
      final latitude = (row[1] as num).toDouble();
      final name = row[2] as String;
      if (!longitude.isFinite || !latitude.isFinite ||
          longitude < -180 || longitude > 180 ||
          latitude < -90 || latitude > 90 ||
          !names.contains(name) || !observed.add(name)) {
        throw const FormatException('Invalid/duplicated group label');
      }
      anchors.add(ReviewLabelAnchor(
        name: name,
        latitude: latitude,
        longitude: longitude,
      ));
    }
    if (observed.length != names.length) {
      throw const FormatException('Missing Vietnamese island/sea label');
    }
    return List.unmodifiable(anchors);
  }
}
