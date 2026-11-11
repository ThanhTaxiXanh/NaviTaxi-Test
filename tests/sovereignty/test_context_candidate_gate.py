"""Fail-closed checks for physical GIS candidates, no official approval."""
import json
import tempfile
import unittest
from pathlib import Path

from pipeline.verify_physical_context import validate

ROOT = Path(__file__).resolve().parents[2]
INVENTORY = ROOT / 'assets/geo/physical_context_candidate_manifest.json'


class CandidateContextTests(unittest.TestCase):
    def test_pinned_inventory_never_authorizes_release(self):
        record = json.loads(INVENTORY.read_text(encoding='utf-8'))
        self.assertEqual(record['source_version'], '2.0.0')
        self.assertIn('GSHHG 2.3.6', record['source_original_version'])
        self.assertEqual(record['status'], 'quarantine')
        self.assertIs(record['p0_pass'], False)
        self.assertIs(record['ui_activation_allowed'], False)
        self.assertIs(record['official_vietnam_reference_verified'], False)
        self.assertIs(record['license_clearance_complete'], False)
        self.assertEqual(len(record['layers']), 5)
        self.assertTrue(all(item['release_allowed'] is False
                            for item in record['layers']))

    def test_missing_gis_files_rejected_even_if_manifest_claims_quarantine(self):
        with tempfile.TemporaryDirectory() as root:
            p = Path(root)
            (p / 'manifest.json').write_text(
                INVENTORY.read_text(encoding='utf-8'), encoding='utf-8',
            )
            result = validate(p, check_topology=False, expected_manifest=INVENTORY)
            self.assertEqual(result['status'], 'FAILED')
            self.assertFalse(result['p0_pass'])
            self.assertGreater(len(result['errors']), 0)

    def test_forged_approval_is_rejected_before_geometry_processing(self):
        with tempfile.TemporaryDirectory() as root:
            p = Path(root)
            data = json.loads(INVENTORY.read_text())
            data['p0_pass'] = True
            data['ui_activation_allowed'] = True
            data['official_vietnam_reference_verified'] = True
            (p / 'manifest.json').write_text(json.dumps(data))
            result = validate(p, check_topology=False, expected_manifest=INVENTORY)
            self.assertEqual(result['status'], 'FAILED')
            self.assertFalse(result['p0_pass'])
            self.assertTrue(any('approval' in x or 'sovereignty' in x
                                for x in result['errors']))

    def test_existing_reference_still_pending(self):
        ref = json.loads((ROOT / 'assets/geo/approved_reference.json').read_text())
        self.assertEqual(ref['status'], 'pending')
        self.assertEqual(ref['features'], [])


if __name__ == '__main__':
    unittest.main()
