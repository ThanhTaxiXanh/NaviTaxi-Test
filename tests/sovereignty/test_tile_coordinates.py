import unittest

from pipeline.tile_coordinates import (
    tile_bounds_wgs84, tileid_to_zxy, slippy_to_lonlat,
)


class PMTilesCoordinateTests(unittest.TestCase):
    def test_zoom_zero_and_zoom_one_hilbert(self):
        self.assertEqual(tileid_to_zxy(0), (0, 0, 0))
        self.assertEqual(tileid_to_zxy(1), (1, 0, 0))
        self.assertEqual(tileid_to_zxy(2), (1, 0, 1))
        self.assertEqual(tileid_to_zxy(3), (1, 1, 1))
        self.assertEqual(tileid_to_zxy(4), (1, 1, 0))

    def test_wgs84_tile_footprints(self):
        box = tile_bounds_wgs84(0)
        self.assertAlmostEqual(box[0], -180)
        self.assertAlmostEqual(box[2], 180)
        self.assertGreater(box[3], 85)
        self.assertLess(box[1], -85)
        center = slippy_to_lonlat(1, 1, 1)
        self.assertAlmostEqual(center[0], 0)
        self.assertAlmostEqual(center[1], 0)

    def test_rejects_invalid_ids(self):
        with self.assertRaises(ValueError):
            tileid_to_zxy(-1)
        with self.assertRaises(ValueError):
            tileid_to_zxy((4 ** 23 - 1) // 3)


if __name__ == "__main__":
    unittest.main()
