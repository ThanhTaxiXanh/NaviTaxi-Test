#!/usr/bin/env python3
"""Use a public, visible GeoJSON button on GIS.vn, no authentication bypass.

A single browser click on the source site's province-34 GeoJSON export.
Temporary data is audited on the CI runner and discarded; only a metadata
report is uploaded until the publisher's redistribution terms are confirmed.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import re
import sys
from tempfile import TemporaryDirectory
from zipfile import ZipFile, BadZipFile

from playwright.sync_api import sync_playwright, TimeoutError as BrowserTimeoutError

PAGE = "https://gis.vn/don-vi-hanh-chinh-viet-nam"
SELECTOR = (
    'button[onclick*="taigeojson_tong_tuheader_SAUSAPNHAP"]'
    '[onclick*="TONG_VN_TINHTHANH"]'
)
OUTPUT = Path("build/gisvn_public_export")
MAX_BYTES = 120 * 1024 * 1024


def inspect_bytes(payload: bytes, filename: str):
    if len(payload) > MAX_BYTES:
        return {"status": "FILE_OVER_SIZE_LIMIT", "bytes": len(payload)}
    try:
        if payload.startswith(b"PK"):
            with ZipFile(__import__("io").BytesIO(payload)) as source:
                members = [
                    item for item in source.infolist()
                    if not item.is_dir()
                    and item.filename.lower().endswith((".geojson", ".json"))
                ]
                if len(members) != 1 or members[0].file_size > MAX_BYTES:
                    return {"status": "ZIP_NOT_SINGLE_GEOJSON", "members": len(members)}
                data = source.read(members[0])
                inside = members[0].filename
        else:
            data = payload
            inside = filename
        doc = json.loads(data)
        if not isinstance(doc, dict) or doc.get("type") != "FeatureCollection":
            return {"status": "NOT_GEOJSON_FEATURECOLLECTION",
                    "document_type": str(doc.get("type")) if isinstance(doc,dict) else "unknown"}
        feats = doc.get("features")
        if not isinstance(feats, list):
            return {"status": "NO_FEATURE_ARRAY"}
        shapes = {}
        property_keys = set()
        for feat in feats:
            geometry = feat.get("geometry") or {}
            shape = geometry.get("type","null")
            shapes[shape] = shapes.get(shape, 0) + 1
            property_keys.update((feat.get("properties") or {}).keys())
        return {
            "status": "GEOJSON_STRUCTURAL_PREVIEW_NOT_P0",
            "feature_count": len(feats),
            "geometry_types": shapes,
            "property_field_names": sorted(map(str,property_keys))[:70],
            "inner_geojson_filename": inside,
            "inner_geojson_sha256": hashlib.sha256(data).hexdigest(),
        }
    except (ValueError, BadZipFile, KeyError, TypeError, RuntimeError) as exc:
        return {"status":"DATA_PARSE_FAILED", "error_type": type(exc).__name__,
                "message": str(exc)[:190]}


def run():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    result = {
        "status": "BROWSER_EXPORT_NOT_CONFIRMED",
        "source_url": PAGE,
        "export_level": "TONG_VN_TINHTHANH",
        "requested_administrative_version": "34 provinces after mergers",
        "license_for_redistribution_verified": False,
        "maplibre_activation_allowed": False,
        "p0_pass": False,
        "raw_vendor_data_uploaded_to_artifact": False,
    }
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = browser.new_context(accept_downloads=True, locale="vi-VN")
        page = context.new_page()
        network = []
        def record(response):
            if len(network) >= 50:
                return
            if re.search("geojson|export|download|diahinh|dihanh|tinht|zip",response.url,re.I):
                network.append({
                    "url": response.url.split("?")[0][:240],
                    "status": response.status,
                    "content_type": response.headers.get("content-type", "")[:100],
                })
        page.on("response", record)
        try:
            navigation = page.goto(PAGE,wait_until="domcontentloaded",timeout=60000)
            page.wait_for_timeout(6000)
            result["page_http_status"] = navigation.status if navigation else None
            result["final_url"] = page.url
            result["page_title"] = page.title()[:150]
            result["button_count"] = page.locator("button").count()
            result["page_source_has_export_handler"] = "taigeojson_tong_tuheader_SAUSAPNHAP" in page.content()
            result["frame_urls"] = [frame.url[:180] for frame in page.frames]
            result["body_preview"] = (page.locator("body").inner_text(timeout=5000)[:240]) if page.locator("body").count() else ""
            button = page.locator(SELECTOR)
            result["matching_34_province_geojson_buttons"] = button.count()
            if button.count()!=1:
                result["status"]="BUTTON_NOT_UNIQUELY_FOUND"
            else:
                result["public_button_visible"] = button.is_visible()
                result["handler_type"] = page.evaluate(
                    "typeof window.taigeojson_tong_tuheader_SAUSAPNHAP"
                )
                try:
                    with page.expect_download(timeout=60000) as download_info:
                        button.click(timeout=20000)
                    download=download_info.value
                    result["suggested_filename"] = download.suggested_filename
                    with TemporaryDirectory() as temporary:
                        target = Path(temporary)/"download.bin"
                        download.save_as(target)
                        length = target.stat().st_size
                        result["download_bytes"] = length
                        if length<=MAX_BYTES:
                            payload=target.read_bytes()
                            result["download_sha256"]=hashlib.sha256(payload).hexdigest()
                            result["geometry_preview"]=inspect_bytes(
                                payload, download.suggested_filename
                            )
                            result["status"]="DOWNLOAD_INSPECTED_NOT_LICENSED"
                        else:
                            result["status"]="TOO_LARGE_TO_INSPECT"
                except BrowserTimeoutError:
                    result["status"]="NO_BROWSER_DOWNLOAD_WITHIN_TIMEOUT"
                    messages=page.locator(".swal2-container:visible").all_text_contents()
                    result["visible_dialog_preview"] = [
                        text.strip()[:220] for text in messages[:3]
                    ]
        except Exception as exc:
            result["status"]="BROWSER_FAILURE"
            result["error_type"]=type(exc).__name__
            result["error_message"]=str(exc)[:250]
        finally:
            result["observed_download_related_requests"] = network
            browser.close()
    (OUTPUT/"inspection.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0


if __name__=="__main__":
    sys.exit(run())
