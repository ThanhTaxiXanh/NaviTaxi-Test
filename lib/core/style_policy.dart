import 'dart:convert';

/// Defense-in-depth structural check for a P0-approved MapLibre style.
///
/// This prevents label-layer IDs from being faked by background or line
/// layers, or by unrelated labels. It does NOT prove the underlying source
/// geodata correct and can never replace screenshot and semantic tile QA.
class StylePolicy {
  static const Map<String, String> requiredLabels = {
    'sovereignty-hoang-sa': 'Hoàng Sa',
    'sovereignty-truong-sa': 'Trường Sa',
    'sovereignty-bien-dong': 'Biển Đông',
  };

  static const Map<String, String> requiredFeatureIds = {
    'sovereignty-hoang-sa': 'hoang_sa',
    'sovereignty-truong-sa': 'truong_sa',
    'sovereignty-bien-dong': 'bien_dong',
  };

  static const forbiddenClaimIndicators = <String>{
    'nine-dash line',
    'nine dash line',
    'đường chín đoạn',
    'đường lưỡi bò',
  };

  static bool isStructurallySafeForApprovedRelease(String rawStyle) {
    try {
      final value = jsonDecode(rawStyle);
      if (value is! Map<String, dynamic> || value['version'] != 8) {
        return false;
      }
      final layers = value['layers'];
      final sources = value['sources'];
      if (layers is! List || sources is! Map<String, dynamic> ||
          layers.isEmpty || sources.isEmpty) {
        return false;
      }

      final ids = <String>{};
      final requiredSeen = <String>{};
      for (final item in layers) {
        if (item is! Map<String, dynamic>) return false;
        final layerId = item['id'];
        if (layerId is! String || !ids.add(layerId)) return false;
        final sourceId = item['source'];
        if (sourceId != null &&
            (sourceId is! String || !sources.containsKey(sourceId))) {
          return false;
        }
        final requiredText = requiredLabels[layerId];
        if (requiredText == null) continue;
        if (item['type'] != 'symbol' ||
            sourceId is! String ||
            !sources.containsKey(sourceId)) {
          return false;
        }
        final src = sources[sourceId];
        if (src is! Map<String, dynamic> ||
            !const {'geojson', 'vector'}.contains(src['type'])) {
          return false;
        }
        if (src['type'] == 'vector' &&
            (item['source-layer'] is! String ||
             (item['source-layer'] as String).isEmpty)) {
          return false;
        }
        // A dedicated symbol layer displays exactly one required label.
        // The data underneath still must be independently validated.
        final layout = item['layout'];
        if (layout is! Map<String, dynamic> ||
            layout['text-field'] != requiredText ||
            layout['visibility'] == 'none') {
          return false;
        }
        final minZoom = item['minzoom'];
        final maxZoom = item['maxzoom'];
        if ((minZoom is num && minZoom > 4) ||
            (maxZoom is num && maxZoom <= 12) ||
            (minZoom != null && minZoom is! num) ||
            (maxZoom != null && maxZoom is! num)) {
          return false;
        }
        final filter = item['filter'];
        final wantedId = requiredFeatureIds[layerId];
        if (filter is! List || filter.length != 3 ||
            filter[0] != '==' ||
            filter[1] is! List ||
            (filter[1] as List).length != 2 ||
            (filter[1] as List)[0] != 'get' ||
            (filter[1] as List)[1] != 'feature_id' ||
            filter[2] != wantedId) {
          return false;
        }
        requiredSeen.add(layerId);
      }
      if (requiredSeen.length != requiredLabels.length) return false;

      final lowered = rawStyle.toLowerCase();
      return !forbiddenClaimIndicators.any(lowered.contains);
    } on FormatException {
      return false;
    } on TypeError {
      return false;
    }
  }
}
