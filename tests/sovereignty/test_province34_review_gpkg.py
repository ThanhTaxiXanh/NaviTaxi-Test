"""Quarantined GPKG tool tests: no released map or actual boundaries in CI."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

from pipeline.province34_review_gpkg import (
    ReviewPackageError, build, candidates, normalize
)

GIS_READY = all(importlib.util.find_spec(lib) is not None
                for lib in ("fiona", "shapely", "pyproj"))


def synthetic_zip(folder: Path):
    roster = json.loads((Path(__file__).resolve().parents[2] /
                         "assets/geo/province34_names_2025.json").read_text())
    archive = folder / "synthetic-provinces.zip"
    with ZipFile(archive, "w") as z:
        for idx, province in enumerate(roster["units"]):
            x, y = 101 + (idx % 7) / 10, 10 + (idx // 7) / 10
            # Explicitly synthetic tiny province polygons.
            ring = [[x,y], [x+.01,y], [x+.01,y+.01], [x,y+.01], [x,y]]
            item = {"type":"FeatureCollection","features":[{
                "type":"Feature",
                "properties":{"ma_tinh": province["code"],
                              "ten_tinh": province["name"]},
                "geometry":{"type":"MultiPolygon","coordinates":[[ring]]}
            }]}
            z.writestr(f"p{idx:02d}.geojson", json.dumps(item))
    return archive


class ProvinceReviewGpkgTests(unittest.TestCase):
    def test_name_normalization(self):
        self.assertEqual(normalize("TP. Hồ Chí Minh"), normalize("Hồ Chí Minh"))
        self.assertEqual(normalize("Thành phố Đà Nẵng"), normalize("Đà Nẵng"))

    def test_zip_member_safety(self):
        with tempfile.TemporaryDirectory() as temp:
            zpath = Path(temp) / "unsafe.zip"
            with ZipFile(zpath, "w") as z:
                z.writestr("../bad.geojson", "{}")
            with ZipFile(zpath) as z:
                with self.assertRaises(ReviewPackageError):
                    candidates(z)

    @unittest.skipUnless(GIS_READY, "Full Fiona/Shapely/pyproj integration in dedicated CI")
    def test_synthetic_geometry_roundtrip_and_p0_blocked(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            zip_path = synthetic_zip(folder)
            roster = Path(__file__).resolve().parents[2] / "assets/geo/province34_names_2025.json"
            output = folder / "synthetic-review.gpkg"
            digest = hashlib.sha256(zip_path.read_bytes()).hexdigest()
            result = build(zip_path, roster, output, digest)
            self.assertEqual(result["layer_counts"]["province34_review"], 34)
            self.assertEqual(result["layer_counts"]["offshore_components_REVIEW_ONLY"], 0)
            self.assertTrue(result["geometry_roundtrip_equal"])
            self.assertFalse(result["p0_pass"])
            self.assertFalse(result["maplibre_activation_allowed"])
            self.assertEqual(result["source_sha256"], digest)
            with self.assertRaises(ReviewPackageError):
                build(zip_path, roster, folder / "bad.gpkg", "0"*64)


if __name__ == "__main__":
    unittest.main()
