from __future__ import annotations
import json
import unittest

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parent))
import _bootstrap  # noqa: F401,E402
from _bootstrap import CZROOT, FIXTURES  # noqa: F401,E402
from formal.labels import Label
from formal.semantics import (GATE_ACTOR, SemanticsError, compile_harness_spec,
                              state_id)
from formal.serialization import lts_to_json


def load(p):
    return json.loads((CZROOT / p).read_text(encoding="utf-8"))


class TestCompile(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec3 = load("experiment-3/final-harness.json")
        cls.root = load("contracts/root_contract.json")
        cls.k1 = load("experiment-4/child-1-contract.json")
        cls.spec_c1 = load("experiment-4/c1/final-harness.json")

    def test_deterministic_compilation(self):
        a = lts_to_json(compile_harness_spec(self.spec3, self.root))
        b = lts_to_json(compile_harness_spec(self.spec3, self.root))
        self.assertEqual(a, b)

    def test_legal_authorize_path(self):
        lts = compile_harness_spec(self.spec3, self.root)
        s0 = lts.initial
        # act node is not executable before its authorizing dependency
        self.assertFalse(lts.enabled(s0, "act_candidate", "node:act-candidate-test"))
        s1 = state_id(frozenset({"evidence-gap-and-derivation"}), False, False)
        self.assertTrue(lts.enabled(s1, "act_candidate", "node:act-candidate-test"))
        # after source completion the authorize interaction label exists
        self.assertTrue(lts.enabled(s1, "authorize", "node:evidence-gap-and-derivation"))
        self.assertFalse(lts.enabled(s0, "authorize", "node:evidence-gap-and-derivation"))

    def test_candidate_only_actor_cannot_promote(self):
        lts = compile_harness_spec(self.spec3, self.root)
        for t in lts.transitions:
            if t.label == Label.PROMOTE.value:
                self.assertEqual(t.actor, GATE_ACTOR)

    def test_gate_promotion_requires_verify_completion(self):
        lts = compile_harness_spec(self.spec3, self.root)
        for t in lts.transitions:
            if t.label == Label.PROMOTE.value:
                self.assertIn("verify-candidate", t.source)

    def test_promotion_absent_under_canonical_none_contract(self):
        # K1 denies canonical write without naming the gate: no promote at all
        lts = compile_harness_spec(self.spec_c1, self.k1)
        self.assertFalse(any(t.label == Label.PROMOTE.value
                             for t in lts.transitions))
        self.assertFalse(lts.metadata["allow_promote"])

    def test_create_bounded_by_contract(self):
        spec = json.loads(json.dumps(self.spec3))
        spec["nodes"].append({"id": "kid", "primitive": "create", "tools": [],
                              "can_create": True})
        contract = json.loads(json.dumps(self.root))
        contract["may_create_creator"] = False
        with self.assertRaises(SemanticsError):
            compile_harness_spec(spec, contract)

    def test_create_transition_present_iff_contract_grants(self):
        lts = compile_harness_spec(self.spec3, self.root)
        self.assertTrue(any(t.label == Label.CREATE.value for t in lts.transitions))
        denied = json.loads(json.dumps(self.root))
        denied["may_create_creator"] = False
        lts2 = compile_harness_spec(self.spec3, denied)
        self.assertFalse(any(t.label == Label.CREATE.value for t in lts2.transitions))

    def test_illegal_transitions_absent_by_construction(self):
        lts = compile_harness_spec(self.spec_c1, self.k1)
        # no state admits act_candidate by any actor other than the act node
        for t in lts.transitions:
            if t.label == Label.ACT_CANDIDATE.value:
                self.assertEqual(t.actor, "node:act-candidate-test")

    def test_unmapped_primitive_rejected(self):
        spec = json.loads(json.dumps(self.spec3))
        spec["nodes"][0]["primitive"] = "telepathy"
        with self.assertRaises(Exception):
            compile_harness_spec(spec, self.root)


if __name__ == "__main__":
    unittest.main()
