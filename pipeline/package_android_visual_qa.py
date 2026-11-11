#!/usr/bin/env python3
"""Package Android safe-fallback screenshots WITHOUT ever calling them P0 PASS.

A PNG and an APK checksum prove that files exist, not that a rendered map
satisfies sovereignty policy. Manual review and an approved tile/style are
still required for actual P0.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import struct

SCREENSHOTS = (
    "blocked-light-online",
    "blocked-dark-online",
    "blocked-dark-airplane",
    "blocked-light-restored",
)
MAGIC = b"\x89PNG\r\n\x1a\n"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            digest.update(block)
    return digest.hexdigest()


def inspect_screenshot(path: Path) -> dict:
    if not path.is_file() or path.stat().st_size < 4096:
        raise ValueError(f"Missing/too-small Android screenshot: {path}")
    with path.open("rb") as source:
        data = source.read(24)
    if len(data) != 24 or data[:8] != MAGIC:
        raise ValueError("Screenshot is not a PNG file")
    width, height = struct.unpack_from(">II", data, 16)
    if width < 400 or height < 700 or width > 8192 or height > 8192:
        raise ValueError("Unexpected screenshot dimensions")
    return {
        "file": path.name,
        "sha256": sha256(path),
        "bytes": path.stat().st_size,
        "width": width,
        "height": height,
        "verified_what": "image_file_integrity_only",
    }


def build_report(directory: Path, apk: Path) -> dict:
    if not apk.is_file() or apk.stat().st_size < 1024 * 1024:
        raise ValueError("The debug APK does not exist")
    screenshots = [
        inspect_screenshot(directory / (name + ".png"))
        for name in SCREENSHOTS
    ]
    if len({s["sha256"] for s in screenshots}) == 1:
        # MapLibre and overlays may be very similar across modes, but we still
        # require a genuine new capture in every scenario.
        raise ValueError("All screenshots have identical SHA-256")
    return {
        "schema_version": 1,
        "status": "ANDROID_P0_SAFE_FALLBACK_IMAGES_NOT_TERRITORIAL_REVIEW",
        "apk_type": "debug",
        "apk_sha256": sha256(apk),
        "screenshots": screenshots,
        "p0_pass": False,
        "maplibre_activation_allowed": False,
        "approved_basemap_shown": False,
        "official_island_labels_rendered_and_verified": False,
        "offline_tile_parity_verified": False,
        "android_rendered_style_review_completed": False,
        "manual_visual_reviewer_signoff": False,
        "notice": (
            "Screenshots confirm test-run debug fallback output exists. "
            "PNG checksums do not establish P0 or pixel/semantic correctness. "
            "GeoJSON/PMTiles source assets were not included in this build."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=Path("build/qa/p0-safe-fallback"))
    parser.add_argument("--apk", type=Path,
                        default=Path("build/app/outputs/flutter-apk/app-debug.apk"))
    args = parser.parse_args()
    report = build_report(args.directory, args.apk)
    (args.directory / "manifest.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
