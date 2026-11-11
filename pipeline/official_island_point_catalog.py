#!/usr/bin/env python3
"""Extract point coordinates from Ministry circular 33/2024 Annex sections B/C.

This checks official place-name POINTS, not polygon boundaries; VN-2000
datum not presumed identical to source WGS84. Never sets P0 PASS.
"""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile
import urllib.request
import zlib

SOURCE = "https://mae.gov.vn/noidung/Lists/VBQPPL/Attachments/514/1_DanhMuc_TT_DiaDanh_BanHanh.pdf"
DMS = re.compile(r"(\d{1,3})\s*[°º]\s*(\d{1,2})\s*['’′]\s*(\d{1,2})")
PROVINCES = {"B": ("Đà Nẵng", 50), "C": ("Khánh Hòa", 133)}


def extract_points(pdf_path: Path):
    with tempfile.TemporaryDirectory() as temp:
        text_path = Path(temp) / "source.txt"
        result = subprocess.run(
            ["pdftotext", "-layout", "-nopgbrk", str(pdf_path), str(text_path)],
            text=True, capture_output=True,
        )
        if result.returncode:
            raise ValueError("PDF text extraction failed: " + result.stderr[:200])
        text = text_path.read_text(encoding="utf-8")
    b = list(re.finditer(r"(?m)^\s*B\s+QUẦN ĐẢO HOÀNG\s+SA\b", text))
    c = list(re.finditer(r"(?m)^\s*C\s+QUẦN ĐẢO TRƯỜNG\s+SA\b", text))
    if not b or not c or b[-1].start() >= c[-1].start():
        raise ValueError("Official sections B/C not found in expected order")
    ranges = {"B": text[b[-1].start():c[-1].start()],
              "C": text[c[-1].start():]}
    points = []
    for section, block in ranges.items():
        province, required = PROVINCES[section]
        for line in block.splitlines():
            if province not in line or "°" not in line:
                continue
            coords = list(DMS.finditer(line))
            if len(coords) != 2:
                continue
            m = re.match(r"^\s*(\d{1,3})\s+(.+?)\s+" + province + r"\b", line)
            if not m:
                continue
            index = int(m.group(1))
            if not (1 <= index <= required):
                continue
            latd, latm, lats = (int(n) for n in coords[0].groups())
            lond, lonm, lons = (int(n) for n in coords[1].groups())
            if latm > 59 or lonm > 59 or lats > 60 or lons > 60:
                raise ValueError(f"Out-of-range official coordinate at {section} {index}")
            lat_sec, lon_sec = latd * 3600 + latm * 60 + lats, lond * 3600 + lonm * 60 + lons
            if not (6*3600 <= lat_sec <= 18*3600 and
                    110*3600 <= lon_sec <= 119*3600):
                raise ValueError("Official coordinate outside screening extent")
            points.append([section, index, m.group(2).strip(), lat_sec, lon_sec])
        actual = sorted(p[1] for p in points if p[0] == section)
        if actual != list(range(1, required+1)):
            raise ValueError(f"Incomplete official section {section}: {len(actual)}/{required}; first IDs: {actual[:25]}")
    return points


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", type=Path)
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--output", type=Path, default=Path("build/official-points/qa.json"))
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.download:
        req = urllib.request.Request(SOURCE, headers={"User-Agent":"NaviTaxi-Official-GIS-Point-QA/1.0"})
        with urllib.request.urlopen(req, timeout=50) as response:
            raw = response.read(16 * 1024 * 1024)
        if not raw.startswith(b"%PDF") or len(raw) >= 16 * 1024 * 1024:
            raise ValueError("Official PDF missing/oversized")
        path = args.output.parent / "official_source.pdf"
        path.write_bytes(raw)
    elif args.pdf:
        path = args.pdf
        raw = path.read_bytes()
    else:
        parser.error("Specify --pdf or --download")
    data = extract_points(path)
    record = {
        "source": SOURCE,
        "pdf_sha256": hashlib.sha256(raw).hexdigest(),
        "coordinates_crs": "VN-2000",
        "sections": {"hoang_sa": 50, "truong_sa": 133},
        "list_is_not_polygon_geometry": True,
        "p0_pass": False,
        "count": len(data),
    }
    args.output.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    encoded = base64.b64encode(
        zlib.compress(json.dumps(data, ensure_ascii=False, separators=(",",":")).encode("utf-8"), 9)
    ).decode("ascii")
    print("OFFICIAL_POINT_COUNT=" + str(len(data)))
    print("OFFICIAL_PDF_SHA256=" + record["pdf_sha256"])
    print("OFFICIAL_POINTS_B64_ZLIB=" + encoded)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
