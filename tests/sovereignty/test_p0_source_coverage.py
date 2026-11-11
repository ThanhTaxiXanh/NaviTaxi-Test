"""No mainland-only PMTiles envelope may masquerade as archipelago coverage."""
import json
from pathlib import Path
import unittest
from pipeline.p0_source_coverage import compute_coverage

ROOT=Path(__file__).resolve().parents[2]
REPORT=ROOT/"docs/audits/2026-11-11-mainland-pmtiles-offshore-coverage.json"


def fake_reference():
    points=[]
    for section,n in (("B",50),("C",133)):
        for idx in range(1,n+1):
            points.append({"section":section,"number":idx,
                           "id":f"{section}{idx}","name":f"SYNTHETIC_{section}{idx}",
                           "lat_seconds":16*3600 if section=="B" else 9*3600,
                           "lon_seconds":112*3600 if section=="B" else 114*3600})
    return {
        "schema_version":1,
        "source_pdf_sha256":"acde9b561eca24312b81efdcb36a22a8fc74e2dcb431f6c206199ef72c98e841",
        "source_datum":"VN-2000",
        "geometry_type":"reference_points_not_boundary_polygons",
        "p0_pass":False,
        "points":points,
    }


class ExistingPmtilesOffshoreCoverageTests(unittest.TestCase):
    def test_all_183_are_outside_mainland_only_archive_envelopes(self):
        result=json.loads(REPORT.read_text(encoding="utf-8"))
        self.assertEqual(result["official_island_name_reference_points"],183)
        self.assertEqual(result["source_archive_count"],3)
        self.assertEqual(result["source_bbox_coverage_count"],0)
        self.assertEqual(result["uncovered_reference_point_count"],183)
        self.assertEqual(result["section_coverage"]["B"]["covered"],0)
        self.assertEqual(result["section_coverage"]["C"]["covered"],0)
        self.assertEqual(len(result["missing_critical_island_group_label_ids"]),6)
        self.assertFalse(result["source_semantic_feature_coverage_verified"])
        self.assertFalse(result["p0_pass"])
        self.assertFalse(result["maplibre_activation_allowed"])

    def test_source_bbox_coverage_is_necessary_not_sufficient(self):
        archives=[{
            "filename":"synthetic-mainland.pmtiles",
            "status":"quarantined_not_release_approved",
            "bbox_wgs84":[102,8,109,23]
        }]
        report=compute_coverage(fake_reference(),archives)
        self.assertEqual(report["source_bbox_coverage_count"],0)
        archives[0]["bbox_wgs84"]=[100,0,120,27]
        report=compute_coverage(fake_reference(),archives)
        self.assertEqual(report["source_bbox_coverage_count"],183)
        self.assertFalse(report["source_semantic_feature_coverage_verified"])
        self.assertFalse(report["p0_pass"])

    def test_forged_approved_archive_status_rejected(self):
        with self.assertRaises(ValueError):
            compute_coverage(fake_reference(), [{
                "filename":"unknown.pmtiles","bbox_wgs84":[100,0,120,27],
                "status":"approved"
            }])


if __name__=="__main__":
    unittest.main()
