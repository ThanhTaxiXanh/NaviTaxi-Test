"""PMTiles Hilbert tile-ID and Web Mercator tile-footprint utilities.

Tile footprints are not feature polygons or administrative/sea boundaries.
"""
from __future__ import annotations

import math


def tileid_to_zxy(tile_id: int) -> tuple[int, int, int]:
    """Invert PMTiles v3 zoom/Hilbert tile ID, up to zoom 22."""
    if not isinstance(tile_id, int) or tile_id < 0:
        raise ValueError("Tile ID must be nonnegative")
    for z in range(23):
        next_zoom_base = (4 ** (z + 1) - 1) // 3
        if tile_id < next_zoom_base:
            d = tile_id - (4 ** z - 1) // 3
            n = 1 << z
            x = y = 0
            s = 1
            while s < n:
                rx = 1 & (d // 2)
                ry = 1 & (d ^ rx)
                if ry == 0:
                    if rx == 1:
                        x, y = s - 1 - x, s - 1 - y
                    x, y = y, x
                x += s * rx
                y += s * ry
                d //= 4
                s *= 2
            return z, x, y
    raise ValueError("Tile ID exceeds supported zoom 22")


def slippy_to_lonlat(z: int, x: float, y: float) -> tuple[float, float]:
    """Return WGS84 lon/lat from a fractional Web Mercator tile position."""
    if not 0 <= z <= 22:
        raise ValueError("Unsupported zoom")
    n = 1 << z
    lon = x * 360.0 / n - 180.0
    lat = math.degrees(math.atan(math.sinh(math.pi * (1.0 - 2.0 * y / n))))
    return lon, lat


def tile_bounds_wgs84(tile_id: int) -> list[float]:
    """[west,south,east,north] footprint; not a feature extent."""
    z, x, y = tileid_to_zxy(tile_id)
    west, north = slippy_to_lonlat(z, x, y)
    east, south = slippy_to_lonlat(z, x + 1, y + 1)
    return [west, south, east, north]
