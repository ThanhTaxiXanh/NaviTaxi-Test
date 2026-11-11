import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:navi_taxi_test/core/map_release.dart';
import 'package:navi_taxi_test/core/style_policy.dart';

void main() {
  test('default manifest cannot render unreviewed tile sources', () {
    final release = MapRelease.fromJson(<String, dynamic>{
      'status': 'blocked',
      'p0_pass': false,
      'style_asset': 'assets/styles/vietnam_sovereign_style.json',
    });
    expect(release.mayDisplayVerifiedData, false);
  });

  test('forged manifest approval with a 64-character hash cannot activate', () {
    final release = MapRelease.fromJson(<String, dynamic>{
      'status': 'approved',
      'p0_pass': true,
      'style_asset': 'assets/styles/vietnam_sovereign_style.json',
      'evidence_sha256': 'a' * 64,
    });
    // The development build does not carry a separately pinned P0
    // certificate digest, so a manifest edit alone is insufficient.
    expect(release.mayDisplayVerifiedData, false);
  });

  test('wrong style path cannot activate even with an approval flag', () {
    final release = MapRelease.fromJson(<String, dynamic>{
      'status': 'approved',
      'p0_pass': true,
      'style_asset': 'assets/styles/unapproved.json',
      'evidence_sha256': 'a' * 64,
    });
    expect(release.mayDisplayVerifiedData, false);
  });

  String styleWithLayers(List<Map<String, dynamic>> layers) {
    return jsonEncode({
      'version': 8,
      'sources': {
        'labels': {'type': 'geojson', 'data': {
          'type': 'FeatureCollection',
          'features': <Object>[],
        }},
      },
      'layers': layers,
    });
  }

  List<Map<String, dynamic>> labels() {
    return StylePolicy.requiredLabels.entries.map((entry) {
      return <String, dynamic>{
        'id': entry.key,
        'type': 'symbol',
        'source': 'labels',
        'filter': [
          '==',
          ['get', 'feature_id'],
          StylePolicy.requiredFeatureIds[entry.key],
        ],
        'layout': {'text-field': entry.value, 'visibility': 'visible'},
        'minzoom': 3,
      };
    }).toList();
  }

  test('empty basemap style cannot pass structural review', () {
    expect(
      StylePolicy.isStructurallySafeForApprovedRelease(
        '{"version":8,"sources":{},"layers":['
        '{"id":"background","type":"background"}]}',
      ),
      false,
    );
  });

  test('three dedicated symbol labels can pass structural checks only', () {
    // This is structural validation, NOT legal geographic approval.
    expect(
      StylePolicy.isStructurallySafeForApprovedRelease(styleWithLayers(labels())),
      true,
    );
  });

  test('three fake background layers cannot impersonate island labels', () {
    final faked = labels();
    for (final layer in faked) {
      layer['type'] = 'background';
      layer.remove('source');
    }
    expect(
      StylePolicy.isStructurallySafeForApprovedRelease(styleWithLayers(faked)),
      false,
    );
  });

  test('wrong label text, missing filter and hidden labels fail', () {
    final wrong = labels();
    wrong[1]['layout'] = {'text-field': 'Other label'};
    expect(StylePolicy.isStructurallySafeForApprovedRelease(styleWithLayers(wrong)), false);
    final notScoped = labels();
    notScoped[0].remove('filter');
    expect(StylePolicy.isStructurallySafeForApprovedRelease(styleWithLayers(notScoped)), false);
    final hidden = labels();
    hidden[2]['layout'] = {'text-field': 'Biển Đông', 'visibility': 'none'};
    expect(StylePolicy.isStructurallySafeForApprovedRelease(styleWithLayers(hidden)), false);
  });

  test('labels unavailable at country overview zoom fail', () {
    final zoomed = labels();
    zoomed[0]['minzoom'] = 10;
    expect(StylePolicy.isStructurallySafeForApprovedRelease(styleWithLayers(zoomed)), false);
  });

  test('suspect maritime claim and duplicate layer IDs fail', () {
    final duplicate = labels()..add(Map<String, dynamic>.of(labels().first));
    expect(StylePolicy.isStructurallySafeForApprovedRelease(styleWithLayers(duplicate)), false);
    final suspect = jsonDecode(styleWithLayers(labels())) as Map<String, dynamic>;
    suspect['metadata'] = {'claim': 'nine-dash line'};
    expect(StylePolicy.isStructurallySafeForApprovedRelease(jsonEncode(suspect)), false);
  });
}
