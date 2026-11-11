#!/usr/bin/env python3
"""Public GIS.vn 34-province export discovery; no authentication or scraping.

Inspects publicly served HTML for an advertised, direct GeoJSON download.
Does NOT download/copy geodata, execute arbitrary scripts or grant use rights.
"""
from __future__ import annotations
from html.parser import HTMLParser
from urllib.request import Request, urlopen
from urllib.parse import urljoin, urlsplit
import json
import re
import sys

PAGE = "https://gis.vn/don-vi-hanh-chinh-viet-nam"
MAX_HTML = 3 * 1024 * 1024


class PublicLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.scripts = []
        self.buttons = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "script" and attrs.get("src"):
            self.scripts.append(attrs["src"])
        if tag == "a" and attrs.get("href"):
            self.links.append((attrs.get("href"), attrs.get("download")))
        if tag in ("button", "input"):
            text = " ".join(str(attrs.get(k, "")) for k in
                            ("id", "class", "onclick", "title", "value", "data-export"))
            if re.search("geojson|download|tải|xuất", text, re.I):
                self.buttons.append(text[:240])


def main():
    request = Request(PAGE, headers={
        "User-Agent": "NaviTaxi-GIS-SourceAudit/1.0 (public HTML inspection)",
        "Accept": "text/html",
    })
    try:
        with urlopen(request, timeout=35) as response:
            url = response.url
            status = response.status
            kind = response.headers.get("content-type", "")
            data = response.read(MAX_HTML + 1)
    except Exception as exc:
        print(json.dumps({"status": "UNREACHABLE", "page": PAGE,
                          "error_type": type(exc).__name__,
                          "error": str(exc)[:300]}, ensure_ascii=False))
        return 2
    if len(data) > MAX_HTML or "text/html" not in kind.lower():
        print(json.dumps({"status": "UNEXPECTED_RESPONSE", "http": status,
                          "type": kind, "bytes": len(data)}))
        return 2
    html = data.decode("utf-8", errors="replace")
    parser = PublicLinks()
    parser.feed(html)
    safe_links = [
        (urljoin(url, href), download)
        for href, download in parser.links
        if re.search(r"geojson|\.zip|shp|kml|tải|download|license|terms", href, re.I)
    ]
    snippets = []
    for match in list(re.finditer("GeoJSON", html, re.I))[:20]:
        part = re.sub(r"\s+", " ", html[max(0, match.start()-145):match.end()+165])
        snippets.append(part[:315])
    result = {
        "status": "PUBLIC_PAGE_INSPECTED", "page": url,
        "http": status, "content_type": kind, "html_bytes": len(data),
        "public_direct_download_links": safe_links[:40],
        "scripts": [urljoin(url, src) for src in parser.scripts[:50]],
        "export_buttons": parser.buttons[:30],
        "geojson_markup_snippets": snippets,
        "license_or_terms_links": [
            urljoin(url, href) for href, _ in parser.links
            if re.search(r"terms|license|điều.khoản|ban.quyen", href, re.I)
        ][:20],
        "source_data_downloaded": False,
        "gisvn_redistribution_permission_verified": False,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
