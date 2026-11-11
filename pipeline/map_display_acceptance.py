#!/usr/bin/env python3
"""Risk-based territorial display evidence, not a P0 release authorizer.

Allows reasonable cartographic generalization and documented exceptions;
does not demand a 100% polygon match or all name-points inside polygons.
Never sets P0 PASS or activates source tiles, even on full attestation.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "assets/manifests/map_display_acceptance_policy.json"
REPORT_PATH = ROOT / "docs/audits/2026-11-11-tt33-183-island-point-screen.json"
HASH = re.compile(r"^[a-f0-9]{64}$")
EXPECTED_LABELS = ["Hoàng Sa", "Trường Sa", "Biển Đông"]
PRIORITY_ISLANDS = {"B48", "C123", "B15", "B3"}
DISPOSITIONS = {
    "generalization_justified", "verified_non_land_feature",
    "region_label_point", "source_geometry_corrected",
}


class EvidenceError(ValueError):
    pass


def has_trace(value: object) -> bool:
    return (isinstance(value, dict)
            and isinstance(value.get("reviewer"), str)
            and bool(value["reviewer"].strip())
            and isinstance(value.get("source_url"), str)
            and value["source_url"].startswith("https://")
            and isinstance(value.get("evidence_sha256"), str)
            and HASH.fullmatch(value["evidence_sha256"]) is not None)


def review_status(policy: dict, screening: dict,
                  review: dict | None = None) -> dict:
    if not isinstance(policy, dict) or not isinstance(screening, dict):
        raise EvidenceError("Malformed policy or screening")
    if (policy.get("schema_version") != 1
            or policy.get("policy_id") != "NAVITAXI_VI_TERRITORY_VISUAL_ACCEPTANCE_1"
            or policy.get("exact_polygon_match_required") is not False
            or policy.get("all_point_names_must_be_inside_source_polygon") is not False
            or policy.get("point_outliers_require_documented_review") is not True
            or policy.get("mandatory_labels") != EXPECTED_LABELS
            or set(policy.get("critical_island_reference_ids", [])) != PRIORITY_ISLANDS
            or set(policy.get("allowed_outlier_dispositions", [])) != DISPOSITIONS
            or policy.get("no_unauthorized_maritime_lines") is not True
            or policy.get("no_unapproved_foreign_admin_labels") is not True
            or policy.get("road_navigation_sign_and_speed_gate_separate") is not True
            or policy.get("p0_pass") is not False
            or policy.get("maplibre_activation_allowed") is not False):
        raise EvidenceError("Unrecognized or unsafe map display policy")
    if (screening.get("points_checked") != 183
            or screening.get("source_reference_pdf_sha256") != policy["official_pdf_sha256"]
            or screening.get("user_zip_sha256") != policy["user_zip_sha256"]
            or screening.get("p0_pass") is not False
            or screening.get("maplibre_activation_allowed") is not False):
        raise EvidenceError("Official coordinate screening identity not verified")
    flagged = screening.get("review_candidates_over_5km", [])
    if (not isinstance(flagged, list)
            or len(flagged) != screening.get("outside_5km")
            or len(flagged) != 14):
        raise EvidenceError("Official outlier inventory is incomplete")
    ids = [item.get("reference_id") for item in flagged if isinstance(item, dict)]
    if len(ids) != 14 or len(set(ids)) != 14 or not PRIORITY_ISLANDS.issubset(ids):
        raise EvidenceError("Missing/duplicated high-priority island reference")
    views = policy.get("mandatory_visuals")
    if not isinstance(views, list) or len(views) < 8 or len(set(views)) != len(views):
        raise EvidenceError("Mandatory visual review list incomplete")

    review = {} if review is None else review
    if (not isinstance(review, dict)
            or review.get("p0_pass") is True
            or review.get("maplibre_activation_allowed") is True
            or (review and review.get("schema_version") != 1)):
        raise EvidenceError("Review evidence cannot assert P0 approval")
    entries = review.get("outlier_dispositions", [])
    if not isinstance(entries, list):
        raise EvidenceError("Invalid disposition list")
    cleared = set()
    errors = []
    for row in entries:
        if not isinstance(row, dict) or not isinstance(row.get("reference_id"), str):
            errors.append("Malformed outlier disposition")
            continue
        reference_id = row["reference_id"]
        if reference_id in cleared or reference_id not in ids:
            errors.append("Duplicate/unknown island outlier " + reference_id)
            continue
        if row.get("disposition") not in DISPOSITIONS or not has_trace(row):
            errors.append("No documented source review for " + reference_id)
            continue
        if reference_id in PRIORITY_ISLANDS and row["disposition"] in {
            "verified_non_land_feature", "region_label_point"
        }:
            errors.append("Named island cannot be waived as reef/label " + reference_id)
            continue
        cleared.add(reference_id)

    labels = review.get("label_checks", {})
    visuals = review.get("visual_checks", {})
    if not isinstance(labels, dict) or not isinstance(visuals, dict):
        raise EvidenceError("Malformed label or screenshot evidence")
    missing_labels = [x for x in EXPECTED_LABELS if not has_trace(labels.get(x))]
    missing_visuals = [
        x for x in views
        if not has_trace(visuals.get(x))
        or visuals[x].get("result") != "pass"
    ]
    required_reviews = [
        "source_rights", "no_prohibited_claims", "marine_line_review",
        "human_reviewer_signoff",
    ]
    missing_reviews = [
        x for x in required_reviews if not has_trace(review.get(x))
    ]
    missing_ids = sorted(set(ids) - cleared)
    blockers = errors[:]
    if missing_ids:
        blockers.append(str(len(missing_ids)) + " island/reef outliers pending")
    if missing_labels:
        blockers.append("Missing label evidence")
    if missing_visuals:
        blockers.append("Missing rendered visual evidence")
    if missing_reviews:
        blockers.append("Missing source/claim/approval reviews")
    return {
        "schema_version": 1,
        "status": ("READY_FOR_INDEPENDENT_HUMAN_P0_REVIEW_NOT_APPROVED"
                   if not blockers else "TERRITORIAL_REVIEW_INCOMPLETE_NOT_P0"),
        "exact_polygon_match_required": False,
        "screened_reference_points": 183,
        "outliers_recorded": 14,
        "outliers_cleared_with_trace": len(cleared),
        "outlier_ids_pending": missing_ids,
        "mandatory_labels_pending": missing_labels,
        "visual_checks_pending": missing_visuals,
        "additional_reviews_pending": missing_reviews,
        "blockers": blockers,
        "routing_speed_signs": "SEPARATE_UNVERIFIED",
        "p0_pass": False,
        "maplibre_activation_allowed": False,
        "note": "Self-reported evidence cannot authorize release; actual GIS/style/device and rights review required",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", type=Path, default=POLICY_PATH)
    parser.add_argument("--screening", type=Path, default=REPORT_PATH)
    parser.add_argument("--review-evidence", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        policy = json.loads(args.policy.read_text(encoding="utf-8"))
        screen = json.loads(args.screening.read_text(encoding="utf-8"))
        review = (json.loads(args.review_evidence.read_text(encoding="utf-8"))
                  if args.review_evidence else None)
        data = review_status(policy, screen, review)
        exit_code = 0
    except (OSError, ValueError, TypeError, KeyError) as exc:
        data = {"status": "REVIEW_CHECK_FAILED", "p0_pass": False,
                "maplibre_activation_allowed": False, "error": str(exc)}
        exit_code = 1
    rendered = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
