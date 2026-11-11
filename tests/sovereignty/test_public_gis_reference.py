"""Protect against silent promotion from independent/source comparisons."""
import json
from pathlib import Path
import unittest
from pipeline.compare_public_gis_reference import bbox_overlap_fraction, norm

ROOT=Path(__file__).resolve().parents[2]


class PublicReferenceQATests(unittest.TestCase):
    def test_geographic_box_overlap_is_only_coarse(self):
        self.assertEqual(bbox_overlap_fraction([0,0,2,2],[0,0,2,2]),1)
        self.assertEqual(bbox_overlap_fraction([0,0,1,1],[2,2,3,3]),0)
        self.assertEqual(bbox_overlap_fraction([0,0,2,2],[1,1,3,3]),round(1/7,4))

    def test_34_summaries_cannot_approve_p0(self):
        report=json.loads(
            (ROOT/"docs/audits/2026-11-11-user-province34-reference-baseline.json")
            .read_text(encoding="utf-8")
        )
        self.assertEqual(len(report["provinces"]),34)
        self.assertFalse(report["p0_pass"])
        self.assertFalse(report["maplibre_activation_allowed"])
        self.assertEqual(len({p["code"] for p in report["provinces"]}),34)
        self.assertEqual(len({norm(p["name"]) for p in report["provinces"]}),34)
        self.assertEqual(report["original_zip_sha256"],
                         "51779d2585600ec053827a60890ba61cd2192f19b5ee153d38be18a2611d24cd")

    def test_names_with_diacritics_match(self):
        self.assertEqual(norm("Thành phố Đà Nẵng"),norm("Đà Nẵng"))
        self.assertEqual(norm("Tỉnh Khánh Hòa"),norm("Khánh Hòa"))
        self.assertEqual(norm("TP. Hồ Chí Minh"),norm("Hồ Chí Minh"))


if __name__=="__main__":
    unittest.main()
