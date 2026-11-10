import 'package:flutter_test/flutter_test.dart';
import 'package:navi_taxi_test/core/map_release.dart';
import 'package:navi_taxi_test/core/style_policy.dart';

void main() {
  test('default manifest is not allowed to render unverified tiles', () {
    final release = MapRelease.fromJson(<String, dynamic>{
      'status': 'blocked',
      'p0_pass': false,
      'style_asset': 'assets/styles/vietnam_sovereign_style.json',
    });
    expect(release.mayDisplayVerifiedData, false);
  });

  test('a claimed approval without verified evidence is rejected', () {
    final release = MapRelease.fromJson(<String, dynamic>{
      'status': 'approved',
      'p0_pass': true,
      'style_asset': 'assets/styles/vietnam_sovereign_style.json',
      'evidence_sha256': '',
    });
    expect(release.mayDisplayVerifiedData, false);
  });

  test('background-only style cannot pass structural P0 preflight', () {
    expect(
      StylePolicy.isStructurallySafeForApprovedRelease(
        '{"version":8,"sources":{},"layers":'
        '[{"id":"background","type":"background"}]}',
      ),
      false,
    );
  });

  test('forbidden claim indicator is rejected', () {
    expect(
      StylePolicy.isStructurallySafeForApprovedRelease(
        '{"version":8,"sources":{},"layers":['
        '{"id":"sovereignty-hoang-sa","type":"background"},'
        '{"id":"sovereignty-truong-sa","type":"background"},'
        '{"id":"sovereignty-bien-dong","type":"background"}],'
        '"metadata":{"warning":"nine-dash line"}}',
      ),
      false,
    );
  });
}
