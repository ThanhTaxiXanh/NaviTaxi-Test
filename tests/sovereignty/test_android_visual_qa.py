"""PNG screenshot integrity is never an approval of offshore GIS rendering."""
import json
from pathlib import Path
import struct
import tempfile
import unittest

from pipeline.package_android_visual_qa import inspect_screenshot, build_report, SCREENSHOTS


class P0SafeFallbackVisualQaTests(unittest.TestCase):
    def test_missing_screenshots_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(ValueError):
                inspect_screenshot(Path(temp)/"missing.png")

    def test_reject_bad_png_and_tiny_dimensions(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp)/"fake.png"
            p.write_bytes(b"not a png"*1024)
            with self.assertRaises(ValueError):
                inspect_screenshot(p)
            p.write_bytes(b"\x89PNG\r\n\x1a\n"+b"\x00"*8+
                          struct.pack(">II",100,200)+b"x"*5000)
            with self.assertRaises(ValueError):
                inspect_screenshot(p)

    def test_synthetic_files_cannot_approve_map_release(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            apk = root/"fake-debug.apk"
            apk.write_bytes(b"X"*(1024*1024+1))
            for index, name in enumerate(SCREENSHOTS):
                (root/(name+".png")).write_bytes(
                    b"\x89PNG\r\n\x1a\n" + b"\x00"*8 +
                    struct.pack(">II",1080,1920) + bytes([index])*5000
                )
            result = build_report(root, apk)
            self.assertEqual(len(result["screenshots"]),4)
            self.assertFalse(result["p0_pass"])
            self.assertFalse(result["maplibre_activation_allowed"])
            self.assertFalse(result["offline_tile_parity_verified"])
            self.assertFalse(result["official_island_labels_rendered_and_verified"])
            self.assertFalse(result["android_rendered_style_review_completed"])


if __name__ == "__main__":
    unittest.main()
