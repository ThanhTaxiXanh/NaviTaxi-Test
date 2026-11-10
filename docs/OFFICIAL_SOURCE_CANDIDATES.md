# Official Vietnamese GIS reference candidates (research intake)

Reviewed on 2026-11-10. These links are **candidates for authoritative comparison**, not cleared vector data or proof of P0 compliance.

| Candidate | Official/public role | Intended validation use | Clearance required |
| --- | --- | --- | --- |
| https://thongtin.diagioi.gov.vn/ | Vietnamese administrative boundary database portal, with island references and online maps | Compare Vietnamese toponyms and administrative depiction at published scales | Confirm current dataset vintage, API availability and redistribution terms |
| https://vnsdi.monre.gov.vn/home | National spatial data infrastructure portal cited in 2025 publication of updated 34-province map | Acquire/review current official administrative map, if provided | Confirm download/API terms, geographic scope, coordinate reference system and version |
| https://sapnhap.bando.com.vn/ | Public administrative map presented by Nhà xuất bản Tài nguyên, Môi trường và Bản đồ Việt Nam; page references a 2026 publication | Cross-check 34 administrative units and island references | Confirm which geometries are official, licensed and complete, not just an online viewer |

Public information:

- https://baochinhphu.vn/se-cung-cap-mien-phi-ban-do-hanh-chinh-chi-tiet-34-tinh-thanh-moi-tren-moi-truong-mang-102250612194642216.htm (2025-06-12)
- https://moc.gov.vn/vn/Pages/chitiettin.aspx?ChuyenmucID=1273&IDNews=86281 (2025-06-27)

## Ingestion rules

1. Check the publisher, publication number, dataset date, national CRS and actual source coverage, including maritime/archipelago areas.
2. Establish the applicable license and reproduction permission **before** downloading/redistributing tiles or geometries.
3. Download only licensed data; store original source SHA-256, metadata, attribution, transform commands, review report and approval ID.
4. Compare topology/labels against vetted sources without inventing territorial polygon or EEZ boundaries.
5. Do not assume a public online basemap grants the right to scrape vector tiles, render offline or replace its labels.
6. Keep the staging style blocked until independent source-level, decoded-vector, offline and Android visual tests pass.

Community GIS compilations are useful as leads but cannot independently substitute for official reference material.
