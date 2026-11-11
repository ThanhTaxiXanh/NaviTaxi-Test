"""Official island-name coordinates are reference points, never P0 borders."""
import copy
import unittest
from pipeline.verify_official_island_points import validate_reference


def fake_reference():
    points = []
    for section, total in (("B", 50), ("C", 133)):
        for n in range(1, total+1):
            points.append({
                "section": section, "number": n,
                "id": f"{section}{n}", "name": f"SYNTHETIC_{section}_{n}",
                "lat_seconds": 10*3600+n, "lon_seconds": 112*3600+n,
            })
    return {
        "schema_version": 1,
        "source_pdf_sha256": (
            "acde9b561eca24312b81efdcb36a22a8fc74e2dcb431f6c206199ef72c98e841"
        ),
        "source_datum": "VN-2000", "p0_pass": False,
        "geometry_type": "reference_points_not_boundary_polygons",
        "points": points
    }


class OfficialIslandReferenceTests(unittest.TestCase):
    def test_183_point_schema_requires_each_id_exactly_once(self):
        self.assertEqual(len(validate_reference(fake_reference())), 183)

    def test_missing_point_or_duplicate_never_passes(self):
        sample = fake_reference()
        sample["points"].pop()
        with self.assertRaises(ValueError):
            validate_reference(sample)
        sample = fake_reference()
        sample["points"][-1]["number"] = 132
        sample["points"][-1]["id"] = "C132"
        with self.assertRaises(ValueError):
            validate_reference(sample)

    def test_claimed_approval_and_malformed_position_refused(self):
        for field, value in (("p0_pass", True), ("source_datum", "WGS84"),
                             ("source_pdf_sha256", "0"*64)):
            sample = fake_reference()
            sample[field] = value
            with self.assertRaises(ValueError):
                validate_reference(sample)
        sample = fake_reference()
        sample["points"][0]["lon_seconds"] = 0
        with self.assertRaises(ValueError):
            validate_reference(sample)


if __name__ == "__main__":
    unittest.main()
