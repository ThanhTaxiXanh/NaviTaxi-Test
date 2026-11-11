"""No exact polygon threshold. Genuine island review and P0 stay independent."""
import copy
import json
from pathlib import Path
import unittest

from pipeline.map_display_acceptance import (
    POLICY_PATH, REPORT_PATH, EvidenceError, review_status
)


class MapAcceptanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        cls.report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))

    def test_real_14_outliers_are_review_tasks_not_auto_geometry_failures(self):
        result = review_status(self.policy, self.report)
        self.assertFalse(result["exact_polygon_match_required"])
        self.assertEqual(result["screened_reference_points"], 183)
        self.assertEqual(len(result["outlier_ids_pending"]), 14)
        self.assertIn("B48", result["outlier_ids_pending"])
        self.assertIn("C123", result["outlier_ids_pending"])
        self.assertEqual(len(result["mandatory_labels_pending"]), 3)
        self.assertFalse(result["p0_pass"])
        self.assertFalse(result["maplibre_activation_allowed"])

    def test_mutating_required_labels_or_precision_policy_fails(self):
        policy = copy.deepcopy(self.policy)
        policy["mandatory_labels"].remove("Trường Sa")
        with self.assertRaises(EvidenceError):
            review_status(policy, self.report)
        policy = copy.deepcopy(self.policy)
        policy["point_outliers_require_documented_review"] = False
        with self.assertRaises(EvidenceError):
            review_status(policy, self.report)

    def test_named_islands_cannot_be_dismissed_as_non_land(self):
        review = {"schema_version": 1, "outlier_dispositions": [{
            "reference_id": "B48",
            "disposition": "verified_non_land_feature",
            "reviewer": "synthetic",
            "source_url": "https://example.org/test",
            "evidence_sha256": "a"*64,
        }]}
        outcome = review_status(self.policy, self.report, review)
        self.assertIn("B48", outcome["outlier_ids_pending"])
        self.assertTrue(any("Named island" in x for x in outcome["blockers"]))

    def test_even_complete_fake_evidence_cannot_grant_p0(self):
        trail = {"reviewer": "synthetic", "source_url": "https://example.org/test",
                 "evidence_sha256": "a"*64}
        review = {
            "schema_version": 1,
            "outlier_dispositions": [
                {**trail, "reference_id": x["reference_id"],
                 "disposition": "generalization_justified"}
                for x in self.report["review_candidates_over_5km"]
            ],
            "label_checks": {x: trail for x in self.policy["mandatory_labels"]},
            "visual_checks": {
                x: {**trail, "result": "pass"}
                for x in self.policy["mandatory_visuals"]
            },
            **{x: trail for x in [
                "source_rights", "no_prohibited_claims", "marine_line_review",
                "human_reviewer_signoff",
            ]},
        }
        outcome = review_status(self.policy, self.report, review)
        self.assertEqual(outcome["blockers"], [])
        self.assertEqual(
            outcome["status"], "READY_FOR_INDEPENDENT_HUMAN_P0_REVIEW_NOT_APPROVED"
        )
        self.assertFalse(outcome["p0_pass"])
        self.assertFalse(outcome["maplibre_activation_allowed"])
        root = Path(__file__).resolve().parents[2]
        release = json.loads((root/"assets/manifests/map_release.json").read_text())
        self.assertFalse(release["p0_pass"])

    def test_invalid_source_report_or_forged_approval_fails(self):
        report = copy.deepcopy(self.report)
        report["points_checked"] = 182
        with self.assertRaises(EvidenceError):
            review_status(self.policy, report)
        with self.assertRaises(EvidenceError):
            review_status(self.policy, self.report, {"p0_pass": True})


if __name__ == "__main__":
    unittest.main()
