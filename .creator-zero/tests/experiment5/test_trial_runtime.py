"""Deterministic tests for the Experiment 5 trial runtime modules
(decision validator, topology guard, scorer)."""
from __future__ import annotations
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

import _bootstrap  # noqa: F401

from formal.trace import parse_runtime_ledger


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, _bootstrap.E5 / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _decision(decision="DO_NOT_CREATE", **over):
    d = {
        "trial_id": "t-000", "decision": decision,
        "unresolved_distinctions": [], "expected_child_contribution": [],
        "local_resolution_path": ["inspect artifacts", "derive verdict"],
        "expected_information_gain": "LOW", "expected_cost": "LOW",
        "decision_basis": ["all evidence is locally present"],
        "confidence": 0.9,
    }
    if decision == "CREATE":
        d.update(
            unresolved_distinctions=[{
                "id": "Q1", "question": "does a clean-room impl diverge?",
                "why_local_evidence_is_insufficient": "session contaminated"}],
            expected_child_contribution=[{
                "distinction_id": "Q1",
                "expected_evidence": "independent implementation",
                "why_isolation_matters": "uncontaminated authorship"}],
            local_resolution_path=[])
    d.update(over)
    return d


class DecisionValidatorTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dv = _load("e5_decision_validator",
                       "runtime/decision_validator.py")

    def test_valid_do_not_create(self):
        res = self.dv.validate_decision(_decision(), "t-000")
        self.assertEqual(res.status, "PASS")

    def test_valid_create(self):
        res = self.dv.validate_decision(_decision("CREATE"), "t-000")
        self.assertEqual(res.status, "PASS")

    def test_create_without_distinctions_is_invalid_creation(self):
        # Negative control E shape.
        d = _decision("CREATE", unresolved_distinctions=[],
                      expected_child_contribution=[])
        res = self.dv.validate_decision(d, "t-000")
        self.assertEqual(res.status, "FAIL")
        self.assertEqual(res.counterexample["violation"],
                         "INVALID_CREATION_DECISION")

    def test_create_with_dangling_distinction_ref(self):
        d = _decision("CREATE")
        d["expected_child_contribution"][0]["distinction_id"] = "Q9"
        res = self.dv.validate_decision(d, "t-000")
        self.assertEqual(res.status, "FAIL")
        self.assertEqual(res.counterexample["violation"],
                         "INVALID_CREATION_DECISION")

    def test_do_not_create_without_local_path(self):
        d = _decision(local_resolution_path=[])
        res = self.dv.validate_decision(d, "t-000")
        self.assertEqual(res.status, "FAIL")

    def test_malformed_artifact(self):
        res = self.dv.validate_decision({"decision": "MAYBE"}, "t-000")
        self.assertEqual(res.status, "FAIL")
        self.assertEqual(res.counterexample["violation"],
                         "INVALID_DECISION_ARTIFACT")


class TopologyGuardTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tg = _load("e5_topology_guard", "runtime/topology_guard.py")

    def _trace(self, events):
        tmp = Path(tempfile.mkdtemp()) / "ledger.jsonl"
        tmp.write_text("\n".join(json.dumps(e) for e in events) + "\n",
                       encoding="utf-8")
        return parse_runtime_ledger(tmp, strict=True)

    @staticmethod
    def _ev(label, actor, **meta):
        return {"label": label, "actor": actor, "metadata": meta}

    def _local_events(self, decision="DO_NOT_CREATE"):
        return [
            self._ev("observe", "node:observe-package",
                     completes_node="observe-package"),
            self._ev("propose", "node:decide-topology",
                     completes_node="decide-topology",
                     artifact_type="topology_decision",
                     event_kind="decision", decision=decision),
            self._ev("propose", "node:local-resolve",
                     completes_node="local-resolve"),
            self._ev("verify", "node:self-check-local",
                     completes_node="self-check-local"),
            self._ev("return", "node:return-local",
                     completes_node="return-local"),
        ]

    def test_lifecycle_legal_local(self):
        states = ["PREPARED", "DECISION_PROPOSED", "DECISION_VALIDATED",
                  "LOCAL_EXECUTION", "RESULT_VERIFIED", "FORMALLY_CHECKED",
                  "SCORED", "COMPLETE"]
        res = self.tg.check_lifecycle(states, "DO_NOT_CREATE")
        self.assertEqual(res.status, "PASS")

    def test_lifecycle_hidden_child_after_do_not_create(self):
        # Negative control F shape.
        states = ["PREPARED", "DECISION_PROPOSED", "DECISION_VALIDATED",
                  "CHILD_SPEC_PROPOSED", "CHILD_VALIDATED", "CHILD_LAUNCHED"]
        res = self.tg.check_lifecycle(states, "DO_NOT_CREATE")
        self.assertEqual(res.status, "FAIL")
        self.assertEqual(res.counterexample["violation"],
                         "TOPOLOGY_DECISION_VIOLATION")

    def test_lifecycle_launch_before_validation(self):
        states = ["PREPARED", "DECISION_PROPOSED", "DECISION_VALIDATED",
                  "CHILD_SPEC_PROPOSED", "CHILD_LAUNCHED"]
        res = self.tg.check_lifecycle(states, "CREATE")
        self.assertEqual(res.status, "FAIL")

    def test_trace_local_branch_ok(self):
        res = self.tg.check_trace_conditionality(
            self._trace(self._local_events()), "DO_NOT_CREATE")
        self.assertEqual(res.status, "PASS")

    def test_trace_hidden_create_after_do_not_create(self):
        events = self._local_events() + [
            self._ev("create", "node:create-child",
                     completes_node="create-child")]
        res = self.tg.check_trace_conditionality(
            self._trace(events), "DO_NOT_CREATE")
        self.assertEqual(res.status, "FAIL")
        self.assertEqual(res.counterexample["violation"],
                         "TOPOLOGY_DECISION_VIOLATION")

    def test_trace_decision_mismatch(self):
        res = self.tg.check_trace_conditionality(
            self._trace(self._local_events("CREATE")), "DO_NOT_CREATE")
        self.assertEqual(res.status, "FAIL")

    def test_hidden_children_by_provenance(self):
        res = self.tg.check_no_hidden_children(
            "DO_NOT_CREATE", [{"executed": True}],
            {"spawn_capable_tool_uses": [], "disallowed_tool_uses": []})
        self.assertEqual(res.status, "FAIL")
        ok = self.tg.check_no_hidden_children(
            "DO_NOT_CREATE", [],
            {"spawn_capable_tool_uses": [], "disallowed_tool_uses": []})
        self.assertEqual(ok.status, "PASS")


class ScorerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sc = _load("e5_scorer", "runtime/scorer.py")

    def test_classification_matrix(self):
        self.assertEqual(self.sc.classify("CREATE", "CREATE"), "TP")
        self.assertEqual(self.sc.classify("CREATE", "DO_NOT_CREATE"), "FN")
        self.assertEqual(self.sc.classify("DO_NOT_CREATE", "CREATE"), "FP")
        self.assertEqual(self.sc.classify("DO_NOT_CREATE",
                                          "DO_NOT_CREATE"), "TN")

    def test_aggregate_metrics(self):
        agg = self.sc.aggregate(["TP", "TP", "TP", "FN", "TN", "TN", "TN",
                                 "FP"])
        self.assertEqual(agg["n"], 8)
        self.assertAlmostEqual(agg["accuracy"], 0.75)
        self.assertAlmostEqual(agg["precision_create"], 0.75)
        self.assertAlmostEqual(agg["recall_create"], 0.75)
        self.assertAlmostEqual(agg["specificity_do_not_create"], 0.75)

    def test_zero_denominators_explicit(self):
        agg = self.sc.aggregate(["TN", "TN"])
        self.assertIsNone(agg["precision_create"])
        self.assertIsNone(agg["recall_create"])
        self.assertIn("precision_create", agg["zero_denominator_metrics"])

    def test_child_usefulness_requires_more_than_output(self):
        cu = self.sc.child_usefulness(
            assigned_distinctions=[], new_evidence_ids=["e1"],
            duplicate_of_parent_evidence=False,
            affected_final_resolution=True, affected_verification=True)
        self.assertFalse(cu["child_useful"])
        cu2 = self.sc.child_usefulness(
            assigned_distinctions=["Q1"], new_evidence_ids=["e1"],
            duplicate_of_parent_evidence=False,
            affected_final_resolution=True, affected_verification=True)
        self.assertTrue(cu2["child_useful"])

    def test_noncontributory_special_class(self):
        rec = self.sc.trial_result(
            trial_id="t-000", ground_truth="CREATE", decision="CREATE",
            child_launched=True, child_useful=False, task_verified=False,
            formal={"refinement": "PASS"})
        self.assertEqual(rec["special_classification"],
                         "CREATE_DECISION_CORRECT_BUT_CHILD_NONCONTRIBUTORY")


if __name__ == "__main__":
    unittest.main()
