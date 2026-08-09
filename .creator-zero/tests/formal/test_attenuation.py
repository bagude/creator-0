from __future__ import annotations
import json
import unittest

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parent))
import _bootstrap  # noqa: F401,E402
from _bootstrap import CZROOT, FIXTURES  # noqa: F401,E402
from formal.attenuation import check_attenuation


def load(p):
    return json.loads((CZROOT / p).read_text(encoding="utf-8"))


def dims(result):
    return [f["dimension"] for f in
            result.counterexample["escalating_dimensions"]]


class TestAttenuation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.k0 = load("experiment-4/root-contract.json")
        cls.k1 = load("experiment-4/child-1-contract.json")
        cls.k2 = load("experiment-4/child-2-contract.json")

    def clone(self, c):
        return json.loads(json.dumps(c))

    def test_strict_attenuation_passes(self):
        self.assertEqual(check_attenuation(self.k0, self.k1).status, "PASS")

    def test_equal_authority_passes(self):
        self.assertEqual(check_attenuation(self.k1, self.clone(self.k1)).status,
                         "PASS")

    def test_tool_escalation_fails(self):
        c = self.clone(self.k2)
        c["allowed_tools"].append("Agent")
        r = check_attenuation(self.k1, c)
        self.assertEqual(r.status, "FAIL")
        self.assertIn("allowed_tools", dims(r))
        self.assertEqual(r.counterexample["verdict"], "ATTENUATION_FAIL")

    def test_write_scope_escalation_fails(self):
        c = self.clone(self.k2)
        c["filesystem_write_scope"] = ["src/"]
        r = check_attenuation(self.k1, c)
        self.assertEqual(r.status, "FAIL")
        self.assertIn("filesystem_write_scope", dims(r))

    def test_model_call_escalation_fails(self):
        c = self.clone(self.k2)
        c["max_model_calls"] = self.k1["max_model_calls"] + 1
        r = check_attenuation(self.k1, c)
        self.assertEqual(r.status, "FAIL")
        self.assertIn("max_model_calls", dims(r))

    def test_realization_reescalation_fails(self):
        c = self.clone(self.k2)
        c["may_realize_creation"] = True
        r = check_attenuation(self.k2, c)
        self.assertEqual(r.status, "FAIL")
        self.assertIn("may_realize_creation", dims(r))

    def test_canonical_authority_escalation_fails(self):
        c = self.clone(self.k2)
        c["canonical_write_authority"] = "full"
        r = check_attenuation(self.k1, c)
        self.assertEqual(r.status, "FAIL")
        self.assertIn("canonical_write_authority", dims(r))

    def test_sibling_workspace_delegation_is_not_escalation(self):
        # the governed lineage law: c2/ under K1, c3/ under K2
        self.assertEqual(check_attenuation(self.k1, self.k2).status, "PASS")

    def test_child_missing_axis_inherits_parent(self):
        c = self.clone(self.k2)
        del c["max_model_calls"]
        self.assertEqual(check_attenuation(self.k1, c).status, "PASS")

    def test_exact_escalating_dimension_reported(self):
        c = self.clone(self.k2)
        c["max_depth"] = 99
        r = check_attenuation(self.k1, c)
        self.assertEqual(dims(r), ["max_depth"])


if __name__ == "__main__":
    unittest.main()
