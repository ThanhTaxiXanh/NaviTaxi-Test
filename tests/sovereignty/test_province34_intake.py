"""Synthetic 34-feature fixtures do not represent Vietnamese boundaries."""
import json
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

from pipeline.province34_intake import audit_file, inspect_collection, ProvinceIntakeError


def synthetic(count=34, name_field="name"):
    features = []
    for idx in range(count):
        lon = 101.0 + idx / 30
        lat = 10.0 + idx / 30
        ring = [[lon, lat], [lon + 0.01, lat],
                [lon + 0.01, lat + 0.01], [lon, lat]]
        features.append({
            "type": "Feature",
            "properties": {name_field: f"SYNTHETIC_{idx + 1}"},
            "geometry": {"type": "Polygon", "coordinates": [ring]},
        })
    return {"type": "FeatureCollection", "features": features}


class Province34IntakeTests(unittest.TestCase):
    def test_34_synthetic_features_always_quarantined(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "synthetic.geojson"
            path.write_text(json.dumps(synthetic()), encoding="utf-8")
            report = audit_file(path, source_url="https://example.invalid/not-official")
            self.assertEqual(report["inspection"]["distinct_name_count"], 34)
            self.assertEqual(report["status"],
                             "QUARANTINED_34_PROVINCES_STRUCTURAL_CHECK_NOT_P0")
            self.assertEqual(report["p0_status"], "BLOCKED")
            self.assertFalse(report["maplibre_activation_allowed"])
            self.assertFalse(report["source_document_verified"])

    def test_zip_one_geojson_member_supported_without_network(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "source.zip"
            with ZipFile(path, "w") as zipped:
                zipped.writestr("dataset/provinces.geojson", json.dumps(synthetic()))
            report = audit_file(path)
            self.assertEqual(report["inspection"]["feature_count"], 34)
            self.assertEqual(report["geojson_member"], "dataset/provinces.geojson")

    def test_wrong_unit_count_and_duplicate_names_rejected(self):
        with self.assertRaises(ProvinceIntakeError):
            inspect_collection(json.dumps(synthetic(33)).encode(), "name")
        data = synthetic()
        data["features"][4]["properties"]["name"] = "SYNTHETIC_1"
        with self.assertRaises(ProvinceIntakeError):
            inspect_collection(json.dumps(data).encode(), "name")

    def test_bad_geometry_and_crs_rejected(self):
        data = synthetic()
        data["crs"] = {"type": "name", "properties": {"name": "EPSG:3857"}}
        with self.assertRaises(ProvinceIntakeError):
            inspect_collection(json.dumps(data).encode(), "name")
        data.pop("crs")
        data["features"][0]["geometry"]["coordinates"][0][0] = [500000, 2000000]
        with self.assertRaises(ProvinceIntakeError):
            inspect_collection(json.dumps(data).encode(), "name")

    def test_zip_path_traversal_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "unsafe.zip"
            with ZipFile(path, "w") as zipped:
                zipped.writestr("../danger.geojson", json.dumps(synthetic()))
            result = audit_file(path)
            self.assertEqual(result["status"], "INTAKE_FAILED")
            self.assertEqual(result["p0_status"], "BLOCKED")


if __name__ == "__main__":
    unittest.main()
