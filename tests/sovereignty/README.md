# Sovereignty P0 test plan (not yet certified)

`python3 -m unittest discover -s tests/sovereignty -v` tests the correctness of the **preflight tools**, not the sovereignty of actual rendered tiles.

Required future coverage:

A. Island presence with approved authoritative geometry and AOIs.
B. Hoàng Sa / Trường Sa source and rendered label correctness at target zooms.
C. Biển Đông label.
D. Prohibited claims and management names detected via actual decoded MVT features, geometry and spatial scope (not substring alone).
E. Style source/layer and collision constraints.
F. Complete offline archive with no Internet and fully loaded glyphs/sprites.
G. Android screenshots compared to human-approved baselines.
H. Malicious/synthetic tile changes rejected.
I. Cache version revocation, fallback and rollback.
J. Nationwide overview displays/reaches island and sea info.

**No coordinates invented** in tests. Human-reviewed reference GeoJSON, source versions and reproducible screenshots must be committed as controlled evidence when licensed. The release CLI exits nonzero until these checks exist and pass.
