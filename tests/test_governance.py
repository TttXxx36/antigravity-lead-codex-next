"""Negative and positive cases for the advisory governance checker."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('check_governance', ROOT / 'scripts/check_governance.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class GovernanceTests(unittest.TestCase):
    def setUp(self):
        self.actual = json.loads((ROOT / 'docs/EXECUTION_STATUS.json').read_text(encoding='utf-8'))
        self.data = copy.deepcopy(self.actual)
        # Mutations below use a fixed D05-ready fixture, not downstream active cards.
        for card in self.data['cards'][6:]:
            card.update(status='PROPOSED',approval=None,pr=None,accepted=False,merged=False,checks=[])
            card.pop('candidate',None)

    def test_current_ledger(self):
        self.assertEqual(mod.validate(self.actual), [])

    def test_missing_card(self):
        self.data['cards'].pop()
        self.assertTrue(mod.validate(self.data))

    def test_duplicate_card(self):
        self.data['cards'].append(copy.deepcopy(self.data['cards'][0]))
        self.assertTrue(mod.validate(self.data))

    def test_permission_escalation(self):
        self.data['permissions']['automatic_merge'] = True
        self.assertTrue(mod.validate(self.data))

    def test_unknown_state(self):
        self.data['cards'][0]['status'] = 'FINISHED'
        self.assertTrue(mod.validate(self.data))

    def test_no_approval(self):
        self.data['cards'][2]['approval'] = None
        self.assertTrue(mod.validate(self.data))

    def test_blocked_dependency(self):
        self.data['cards'][3].update(status='IN_PROGRESS', approval='test approval')
        self.assertTrue(mod.validate(self.data))

    def test_candidate_dependency_only_for_development(self):
        d05 = self.data['cards'][5]
        d06 = self.data['cards'][6]
        d06.update(status='IN_PROGRESS', approval='test')
        self.assertEqual(mod.validate(self.data), [])
        d06.update(status='DONE', accepted=True, merged=True, pr=999,
                   checks=[{'name':'test','status':'PASS','ref':'test'}])
        self.assertTrue(any('dependency' in error for error in mod.validate(self.data)))

    def test_candidate_without_matching_ci_evidence_rejected(self):
        self.data['cards'][6].update(status='IN_PROGRESS', approval='test')
        self.data['cards'][5]['candidate']['tested_commit'] = '0'*40
        self.assertTrue(any('dependency' in error for error in mod.validate(self.data)))

    def test_candidate_failure_rejected(self):
        self.data['cards'][6].update(status='IN_PROGRESS', approval='test')
        self.data['cards'][5]['checks'].append({'name':'failure','status':'FAIL','ref':'test'})
        self.assertTrue(any('dependency' in error for error in mod.validate(self.data)))

    def test_done_without_human_acceptance(self):
        self.data['cards'][0]['accepted'] = False
        self.assertTrue(mod.validate(self.data))

    def test_done_with_failed_check(self):
        self.data['cards'][0]['checks'][0]['status'] = 'FAIL'
        self.assertTrue(mod.validate(self.data))

    def test_done_with_not_run(self):
        self.data['cards'][0]['checks'][0]['status'] = 'NOT_RUN'
        self.assertTrue(mod.validate(self.data))

    def test_review_missing_evidence(self):
        self.data['cards'][2]['checks'] = []
        self.assertTrue(mod.validate(self.data))

    def test_review_no_pr(self):
        self.data['cards'][2]['pr'] = None
        self.assertTrue(mod.validate(self.data))

    def test_dependency_cycle_or_future(self):
        self.data['cards'][0]['depends'] = ['D22']
        self.assertTrue(mod.validate(self.data))

    def test_proposed_implementation_metadata(self):
        self.data['cards'][22]['pr'] = 99
        self.assertTrue(mod.validate(self.data))

    def test_malformed_input(self):
        self.assertTrue(mod.validate(None))
        self.data['cards'][2]['depends'] = [[]]
        self.assertTrue(mod.validate(self.data))


if __name__ == '__main__':
    unittest.main()
