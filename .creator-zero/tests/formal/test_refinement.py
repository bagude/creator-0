from __future__ import annotations
import json
import unittest

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parent))
import _bootstrap  # noqa: F401,E402
from _bootstrap import CZROOT, FIXTURES  # noqa: F401,E402
from formal.model import RuntimeEvent, Trace
from formal.refinement import check_refinement
from formal.semantics import compile_harness_spec
from formal.trace import parse_runtime_ledger


def load(p):
    return json.loads((CZROOT / p).read_text(encoding="utf-8"))


def ev(i, label, actor, completes=None):
    md = {"completes_node": completes} if completes else {}
    return RuntimeEvent(event_id=f"t{i}", label=label, actor=actor,
                        metadata=tuple(sorted(md.items())))


class TestRefinement(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = load("experiment-3/final-harness.json")
        cls.contract = load("contracts/root_contract.json")
        cls.lts = compile_harness_spec(cls.spec, cls.contract)

    def test_legal_trace_passes(self):
        t = parse_runtime_ledger(FIXTURES / "experiment3-normalized-ledger.jsonl")
        r = check_refinement(t, self.lts)
        self.assertEqual(r.status, "PASS")

    def test_undeclared_transition_fails(self):
        t = Trace(events=[ev(0, "delegate", "node:report")], origin="synthetic")
        r = check_refinement(t, self.lts)
        self.assertEqual(r.status, "FAIL")
        self.assertEqual(r.counterexample["violation"], "REFINEMENT_VIOLATION")
        self.assertIn("expected_allowed_labels", r.counterexample)

    def test_actor_canonical_mutation_fails(self):
        t = parse_runtime_ledger(FIXTURES / "synthetic-actor-canonical-write.jsonl")
        r = check_refinement(t, self.lts)
        self.assertEqual(r.status, "FAIL")
        off = r.counterexample["offending_transition"]
        self.assertEqual(off["label"], "promote")
        self.assertEqual(off["actor"], "node:act-candidate-test")
        # counterexample carries the observable prefix leading to the violation
        self.assertEqual(len(r.counterexample["trace_prefix"]), 2)

    def test_gate_promotion_before_verification_fails(self):
        t = Trace(events=[
            ev(0, "observe", "node:evidence-gap-and-derivation",
               "evidence-gap-and-derivation"),
            ev(1, "promote", "gate")], origin="synthetic")
        r = check_refinement(t, self.lts)
        self.assertEqual(r.status, "FAIL")

    def test_node_execution_out_of_dependency_order_fails(self):
        t = Trace(events=[ev(0, "act_candidate", "node:act-candidate-test",
                             "act-candidate-test")], origin="synthetic")
        r = check_refinement(t, self.lts)
        self.assertEqual(r.status, "FAIL")

    def test_unmapped_events_yield_indeterminate(self):
        t = Trace(events=[ev(0, "observe", "anyone")],
                  origin="synthetic",
                  unmapped_events=[{"index": 3, "reason": "unmapped"}])
        r = check_refinement(t, self.lts)
        self.assertEqual(r.status, "INDETERMINATE")
        self.assertTrue(r.unmapped_events)

    def test_require_completion_flags_premature_termination(self):
        t = Trace(events=[ev(0, "observe", "node:evidence-gap-and-derivation",
                             "evidence-gap-and-derivation")], origin="synthetic")
        r = check_refinement(t, self.lts, require_completion=True)
        self.assertEqual(r.status, "INDETERMINATE")
        self.assertIn("premature", r.detail["reason"])

    def test_tau_events_are_silent(self):
        t = Trace(events=[ev(0, "tau", "anyone"), ev(1, "tau", "anyone")],
                  origin="synthetic")
        r = check_refinement(t, self.lts)
        self.assertEqual(r.status, "PASS")
        self.assertEqual(r.detail["matched_steps"], 0)


if __name__ == "__main__":
    unittest.main()
