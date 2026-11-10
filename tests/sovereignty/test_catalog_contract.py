"""Ensure Android intake hardcoding exactly matches the controlled asset catalog.

This prevents accepted archives from changing silently across Dart/Kotlin.
It is *not* a semantic or visual sovereignty test.
"""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INVENTORY = ROOT / "assets/manifests/ingestion_inventory.json"
KOTLIN = ROOT / (
    "android/app/src/main/kotlin/vn/navitaxi/navi_taxi_test/OfflinePackageStore.kt"
)
DART = ROOT / "lib/features/offline/offline_package.dart"


class CatalogContractTests(unittest.TestCase):
    def test_native_catalog_matches_sha256_and_size_manifest(self):
        manifest = json.loads(INVENTORY.read_text(encoding="utf-8"))
        self.assertEqual(manifest["status"], "quarantine")
        expected = {
            item["filename"]: (item["bytes"], item["sha256"])
            for item in manifest["archives"]
        }
        self.assertEqual(len(expected), 3)
        text = KOTLIN.read_text(encoding="utf-8")
        pattern = re.compile(
            r'"(hotosm_vnm_[a-z_]+_osm\.pmtiles)"\s+to\s+Spec\(\s*'
            r'(\d+)L,\s*"([0-9a-f]{64})"',
            flags=re.MULTILINE,
        )
        native = {
            filename: (int(length), digest)
            for filename, length, digest in pattern.findall(text)
        }
        self.assertEqual(native, expected)
        for filename, (length, digest) in expected.items():
            self.assertGreater(length, 0)
            self.assertRegex(digest, r"^[a-f0-9]{64}$")
            self.assertRegex(filename, r"^[a-z0-9_]+\.pmtiles$")

    def test_flutter_catalog_names_match_native_contract(self):
        inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
        dart = DART.read_text(encoding="utf-8")
        match = re.search(
            r"static const _labels = <String, String>\{(.*?)\};",
            dart,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(match)
        names = set(re.findall(r"'([^']+\.pmtiles)'\s*:", match.group(1)))
        expected = {item["filename"] for item in inventory["archives"]}
        self.assertEqual(names, expected)

    def test_pending_release_cannot_approve_quarantine(self):
        release = json.loads(
            (ROOT / "assets/manifests/map_release.json").read_text(encoding="utf-8")
        )
        self.assertFalse(release["p0_pass"])
        self.assertNotEqual(release["status"], "approved")


if __name__ == "__main__":
    unittest.main()
