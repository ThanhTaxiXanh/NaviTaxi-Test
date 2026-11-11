"""No silently partial official island point corpus and no P0 promotion."""
from pathlib import Path
import tempfile
import unittest
from pipeline.official_island_point_catalog import extract_points


class OfficialPointCatalogTests(unittest.TestCase):
    def test_bad_pdf_is_not_accepted_as_official_source(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "fake.pdf"
            path.write_text("not an official PDF")
            with self.assertRaises(ValueError):
                extract_points(path)


if __name__ == "__main__":
    unittest.main()
