#!/usr/bin/env python3
"""Compare a GIS intake's 34 names to the published 2025 government list.

Checks administrative names ONLY, never verifies source geometry, ownership
of islands, maritime legal lines, source licensing, or P0 release.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
import unicodedata

CATALOG = Path(__file__).resolve().parents[1] / "assets/geo/province34_names_2025.json"


def normal(name):
    if not isinstance(name,str):
        raise ValueError("Province name must be text")
    value = unicodedata.normalize("NFC",name).casefold().strip()
    value = re.sub(r"\s+"," ",value)
    value = re.sub(r"^(?:(?:tỉnh)|(?:thành\s*phố)|(?:tp\.?))\s+","",value)
    return value


def compare(source_names:list[str], catalog:dict) -> dict:
    expected = {normal(item["name"]):item for item in catalog["units"]}
    actual = {normal(name):name for name in source_names}
    if len(expected)!=34 or len(actual)!=len(source_names):
        raise ValueError("Invalid/duplicated province-name catalog or input")
    missing = [entry["name"] for key,entry in expected.items() if key not in actual]
    unexpected = [name for key,name in actual.items() if key not in expected]
    return {
      "status":"NAMES_MATCH_2025_REFERENCE_NOT_GEOMETRY"
          if not missing and not unexpected and len(source_names)==34
          else "PROVINCE_NAME_REVIEW_REQUIRED",
      "reference_url":catalog["source_url"],
      "source_count":len(source_names),
      "reference_count":len(expected),
      "unmatched_source_names":unexpected,
      "missing_official_names":missing,
      "p0_status":"BLOCKED",
      "official_geometry_verified":False,
      "gisvn_license_verified":False,
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("intake_report",type=Path)
    p.add_argument("--catalog",type=Path,default=CATALOG)
    args=p.parse_args()
    obj=json.loads(args.intake_report.read_text(encoding="utf-8"))
    ref=json.loads(args.catalog.read_text(encoding="utf-8"))
    names=obj.get("inspection",{}).get("names_in_source",[])
    if not isinstance(names,list):
        raise SystemExit("No province names in the intake report")
    output=compare(names,ref)
    print(json.dumps(output,ensure_ascii=False,indent=2))
    raise SystemExit(0 if output["status"].startswith("NAMES_MATCH") else 1)


if __name__=="__main__":
    main()
