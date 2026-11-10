import 'dart:convert';

/// App-side structural preflight. Python + GIS + Android visual P0 checks
/// must independently pass; this preflight alone can NEVER certify P0.
class StylePolicy {
  static const requiredLayerIds = <String>{
    'sovereignty-hoang-sa',
    'sovereignty-truong-sa',
    'sovereignty-bien-dong',
  };

  static const forbiddenClaimIndicators = <String>{
    'nine-dash line',
    'nine dash line',
    'đường chín đoạn',
    'đường lưỡi bò',
  };

  static bool isStructurallySafeForApprovedRelease(String rawStyle) {
    try {
      final style = jsonDecode(rawStyle) as Map<String, dynamic>;
      if (style['version'] != 8) return false;
      final layers = style['layers'];
      final sources = style['sources'];
      if (layers is! List || sources is! Map) return false;

      final ids = <String>{};
      for (final layer in layers) {
        if (layer is! Map) return false;
        final id = layer['id'];
        if (id is! String || !ids.add(id)) return false;
        final source = layer['source'];
        if (source != null && !sources.containsKey(source)) return false;
      }
      if (!ids.containsAll(requiredLayerIds)) return false;

      final lower = rawStyle.toLowerCase();
      if (forbiddenClaimIndicators.any(lower.contains)) return false;

      return true;
    } on FormatException {
      return false;
    } on TypeError {
      return false;
    }
  }
}
