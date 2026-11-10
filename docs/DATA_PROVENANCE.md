# Source provenance — intake status

Date: 2026-11-10. This file records only inspection of user-supplied archives; it is not an assertion of source authenticity, license clearance or territorial validity.

| Local upload | Byte length | SHA-256 | source-layer | min/max zoom |
| --- | ---: | --- | --- | --- |
| hotosm_vnm_roads_osm.pmtiles | 249894089 | ca575f95bc708ec1fb39e0c3b3f5ee4a3f1596e75e5a0b1f6e50f85e8a28bedd | roads | 0/13 |
| hotosm_vnm_buildings_osm.pmtiles | 75340271 | 8c6f129a2bf2237215d90be72a52475cb6f0f528ac41dfabc5434d832ca37b6f | buildings | 0/14 |
| hotosm_vnm_points_of_interest_osm.pmtiles | 15966991 | dda5a9de8412e8d6bdc73ae62d4fa2c3f8ef017bcbc0c833bc2a9e441be87763 | points_of_interest | 0/12 |

PMTiles version 3, tile type MVT. Header and gzip JSON metadata successfully decoded locally. Metadata `antimeridian_adjusted_bounds`:

- roads: 102.127251,8.421970,109.461296,23.399686
- buildings: 102.159032,8.427456,109.449674,23.383397
- POIs: 102.164762,8.429519,109.458161,23.383397

**Quarantine**: longitude maxima near 109.46°E do not establish coverage for Hoàng Sa, Trường Sa or the wider Biển Đông. No sea polygon, marine administrative line or basemap tiles are supplied in these archives. Also verify origin, license, attribution and redistribution rights with a reliable publication reference before shipping.

Do not add the PMTiles archives to Git; handle via versioned artifact storage after clearance. Original archives reside outside this repository.

## Missing evidence / blockers

1. Official Vietnamese cartographic reference and exact version/date for island topology, coastlines and territorial labeling.
2. Reviewed geospatial features plus coordinates/geometry and documentary authority.
3. Full MVT/PBF feature scan for **Roads and Buildings**, authoritative prohibited-claim geometry verification and online/offline equivalent checks. All 4,209 POI index entries have undergone a structural/WGS84-envelope scan only.
4. Approved Android screenshots at all required cameras/zooms/themes/network conditions.
5. Data origin/attribution/license and distribution approval.
6. Offline manifest, update/rollback and post-install checksum audit.

Release gate currently fails by design.

## Decoded MVT geometry and geographic envelopes

A deterministic local **128-directory-entry sample per archive** has been decoded to individual WGS84 feature envelopes. See [spatial scan procedure](SPATIAL_AUDIT.md) and the [machine-readable quarantine report](audits/2026-11-10-feature-spatial-sample.json). This does not provide approved sea/island boundaries or validate legal geometry. P0 remains blocked.

## POI completed structural scan

The POI archive's **4,209 of 4,209 index entries** were structurally scanned and rechecked by merging two contiguous ranges. Full scanned geometry contains 357,628 features and 1,120,681 decoded vertices. Two *name fields at one viewpoint* contain an English term for the South China Sea, retained as manual-review candidates rather than interpreted as a displayed maritime claim. See [full POI diagnostic report](audits/2026-11-10-poi-full-index-spatial.json). Source legitimacy and P0 correctness remain unverified.
