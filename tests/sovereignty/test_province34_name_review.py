"""Government 34 province name/code reference for intake only, never P0."""
import json
from pathlib import Path
import unittest
from pipeline.province34_name_review import compare, normal, CATALOG


class ProvinceNameReviewTests(unittest.TestCase):
    def setUp(self):
        self.catalog=json.loads(CATALOG.read_text(encoding="utf-8"))

    def test_authoritative_2025_codes_names_are_distinct(self):
        units=self.catalog["units"]
        self.assertEqual(len(units),34)
        self.assertEqual(len({u["code"] for u in units}),34)
        self.assertEqual(len({normal(u["name"]) for u in units}),34)
        self.assertEqual(sum(u["kind"]=="city" for u in units),6)
        self.assertFalse(self.catalog["p0_pass"])

    def test_names_prefix_variants_match_but_not_geometry(self):
        names=[
          ("Thành phố "+u["name"] if u["kind"]=="city" else "Tỉnh "+u["name"])
          for u in self.catalog["units"]
        ]
        result=compare(names,self.catalog)
        self.assertEqual(result["status"],"NAMES_MATCH_2025_REFERENCE_NOT_GEOMETRY")
        self.assertFalse(result["official_geometry_verified"])
        self.assertEqual(result["p0_status"],"BLOCKED")

    def test_outdated_or_wrong_names_flagged(self):
        names=[u["name"] for u in self.catalog["units"]]
        names[-1]="Bình Thuận"
        result=compare(names,self.catalog)
        self.assertEqual(result["status"],"PROVINCE_NAME_REVIEW_REQUIRED")
        self.assertIn("Cà Mau",result["missing_official_names"])
        self.assertIn("Bình Thuận",result["unmatched_source_names"])


if __name__=="__main__":
    unittest.main()
