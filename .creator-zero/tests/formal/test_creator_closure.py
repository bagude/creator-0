from __future__ import annotations
import json
import unittest

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parent))
import _bootstrap  # noqa: F401,E402
from _bootstrap import CZROOT, FIXTURES  # noqa: F401,E402
from formal.creator_closure import check_creator_closure


def load(p):
    return json.loads((CZROOT / p).read_text(encoding="utf-8"))


class TestClosure(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.k2 = load("experiment-4/child-2-contract.json")
        cls.original = load("experiment-4/c2/creator-capability-attestation.json")
        cls.corrected = load(
            "experiment-4/closure-correction/corrected-k3-attestation.json")

    def clone(self, d):
        return json.loads(json.dumps(d))

    def test_original_terminal_k3_fails(self):
        r = check_creator_closure(self.k2, self.original)
        self.assertEqual(r.status, "FAIL")
        self.assertEqual(r.counterexample["failed_clauses"], ["CreatorCapable"])

    def test_corrected_bounded_creator_k3_passes(self):
        r = check_creator_closure(self.k2, self.corrected)
        self.assertEqual(r.status, "PASS")
        self.assertTrue(all(r.detail["clauses"].values()))

    def test_realization_enabled_escalation_fails(self):
        a = self.clone(self.corrected)
        a["draft_child_contract_K3"]["may_realize_creation"] = True
        r = check_creator_closure(self.k2, a)
        self.assertEqual(r.status, "FAIL")
        self.assertIn("ExternalStopOnly", r.counterexample["failed_clauses"])
        # re-escalating realization against a parent with false also breaks attenuation
        self.assertIn("Attenuated", r.counterexample["failed_clauses"])

    def test_missing_creation_command_fails(self):
        a = self.clone(self.corrected)
        del a["exact_creation_command_NOT_EXECUTED"]
        r = check_creator_closure(self.k2, a)
        self.assertEqual(r.status, "FAIL")
        self.assertIn("CreationMechanismValid", r.counterexample["failed_clauses"])

    def test_missing_child_contract_indeterminate(self):
        r = check_creator_closure(self.k2, {"note": "no draft here"})
        self.assertEqual(r.status, "INDETERMINATE")

    def test_invalid_child_contract_fails_valid_clause(self):
        a = self.clone(self.corrected)
        del a["draft_child_contract_K3"]["max_model_calls"]
        r = check_creator_closure(self.k2, a)
        self.assertEqual(r.status, "FAIL")
        self.assertIn("Valid", r.counterexample["failed_clauses"])

    def test_nonzero_children_budget_fails_external_stop(self):
        a = self.clone(self.corrected)
        a["draft_child_contract_K3"]["max_children"] = 1
        r = check_creator_closure(self.k2, a)
        self.assertEqual(r.status, "FAIL")
        self.assertIn("ExternalStopOnly", r.counterexample["failed_clauses"])


if __name__ == "__main__":
    unittest.main()
