"""Prediction falsifiers, formal validation rejection, deterministic utility."""
from __future__ import annotations
import json
import unittest

import _bootstrap
from _bootstrap import CZROOT, TT

CONTRACT = json.loads(
    (CZROOT / "contracts/root_contract.json").read_text(encoding="utf-8"))
TASK = {"task_id": "t-val"}
D_ISO = [{"id": "Q1", "question": "clean-room divergence?",
          "features": {"requires_isolation": True}}]
D_LOCAL = [{"id": "Q1", "question": "local check",
            "features": {"locally_resolvable": True}}]


def make_candidates(dist):
    theory = TT.build_seed_theory()
    app = TT.abduce(TASK, dist, contract=CONTRACT, theory=theory)
    return TT.generate_candidates(TASK, dist, app, CONTRACT)


class PredictionTest(unittest.TestCase):
    def test_prediction_requires_falsifier(self):
        with self.assertRaises(TT.ModelValidationError):
            TT.Prediction(prediction_id="p", topology_id="t", claim="c",
                          observable="o", success_condition="s",
                          falsification_condition="   ")

    def test_frozen_coverage_requires_falsifiable_resolution(self):
        cand = make_candidates(D_LOCAL)[0]
        preds = TT.freeze_predictions(cand, D_LOCAL)
        self.assertTrue(cand.predictions_hash.startswith("sha256:"))
        # a resolution claim with no covering prediction is invalid
        cand.resolution_map["Q-uncovered"] = "resolve-local"
        with self.assertRaises(TT.PredictionError):
            TT.predict.validate_frozen_coverage(cand, preds)

    def test_frozen_hash_is_deterministic(self):
        c1 = make_candidates(D_LOCAL)[0]
        c2 = make_candidates(D_LOCAL)[0]
        TT.freeze_predictions(c1, D_LOCAL)
        TT.freeze_predictions(c2, D_LOCAL)
        self.assertEqual(c1.predictions_hash, c2.predictions_hash)


class ValidationTest(unittest.TestCase):
    def test_good_candidates_pass(self):
        for cand in make_candidates(D_ISO):
            res = TT.validate_topology(cand, CONTRACT)
            self.assertEqual(res.status, "PASS", res.counterexample)

    def test_authority_escalation_rejected(self):
        cand = next(c for c in make_candidates(D_ISO)
                    if "isolated-child" in c.topology_id)
        cand.child_contract = dict(CONTRACT)
        cand.child_contract["allowed_tools"] = list(
            CONTRACT["allowed_tools"]) + ["WebFetch"]      # escalation
        cand.child_contract["max_model_calls"] = 999       # escalation
        res = TT.validate_topology(cand, CONTRACT)
        self.assertEqual(res.status, "FAIL")
        self.assertIn("attenuation", res.counterexample["failed_checks"])

    def test_unreachable_evidence_path_rejected(self):
        cand = next(c for c in make_candidates(D_ISO)
                    if "isolated-child" in c.topology_id)
        spec = cand.harness_spec
        # sever the child's causal return path: child evidence can no longer
        # reach the parent boundary
        spec["nodes"] = [n for n in spec["nodes"]
                         if n["id"] not in ("child-return",
                                            "verify-integration",
                                            "return-result")]
        spec["edges"] = [e for e in spec["edges"]
                         if e["source"] not in ("create-child", "child-return",
                                                "verify-integration")
                         and e["target"] not in ("child-return",
                                                 "verify-integration",
                                                 "return-result")]
        res = TT.validate_topology(cand, CONTRACT)
        self.assertEqual(res.status, "FAIL")
        self.assertIn("reachability", res.counterexample["failed_checks"])

    def test_budget_violation_rejected(self):
        cand = make_candidates(D_LOCAL)[0]
        cand.harness_spec["max_model_calls"] = \
            int(CONTRACT["max_model_calls"]) + 1
        res = TT.validate_topology(cand, CONTRACT)
        self.assertEqual(res.status, "FAIL")
        self.assertIn("budget", res.counterexample["failed_checks"])

    def test_missing_freshness_declaration_rejected(self):
        cand = next(c for c in make_candidates(D_ISO)
                    if "isolated-child" in c.topology_id)
        cand.harness_spec.pop("freshness", None)
        res = TT.validate_topology(cand, CONTRACT)
        self.assertEqual(res.status, "FAIL")
        self.assertIn("freshness", res.counterexample["failed_checks"])


class UtilityTest(unittest.TestCase):
    def test_config_defaults(self):
        cfg = TT.load_utility_config()
        self.assertEqual(cfg, {"lambda_cost": 1.0, "mu_redundancy": 1.0,
                               "nu_governance": 2.0})

    def test_deterministic_utility_value(self):
        cfg = {"lambda_cost": 1.0, "mu_redundancy": 1.0, "nu_governance": 2.0}
        v = {"delta_e": 0.8, "cost": 0.3, "redundancy": 0.1,
             "governance_risk": 0.1}
        self.assertEqual(TT.utility.utility(v, cfg), 0.8 - 0.3 - 0.1 - 0.2)
        self.assertEqual(TT.utility.utility(v, cfg),
                         TT.utility.utility(dict(v), dict(cfg)))

    def test_unnormalized_component_rejected(self):
        cfg = TT.load_utility_config()
        with self.assertRaises(TT.ModelValidationError):
            TT.utility.utility({"delta_e": 1.5, "cost": 0, "redundancy": 0,
                                "governance_risk": 0}, cfg)

    def _hyp(self, tid, nodes, calls, value):
        spec = {"task_id": "t", "nodes": [
            {"id": f"n{i}", "primitive": "observe", "tools": [],
             "can_create": False} for i in range(nodes)],
            "edges": [], "max_depth": 0, "max_model_calls": calls}
        return TT.TopologyHypothesis(
            topology_id=tid, task_id="t", harness_spec=spec,
            predicted_value=value)

    def test_deterministic_tie_break(self):
        v = {"delta_e": 0.5, "cost": 0.2, "redundancy": 0.0,
             "governance_risk": 0.0}
        # equal utility: fewer nodes wins; then fewer calls; then lex id
        a = self._hyp("H-b", nodes=3, calls=2, value=v)
        b = self._hyp("H-a", nodes=2, calls=2, value=v)
        c = self._hyp("H-c", nodes=2, calls=1, value=v)
        d = self._hyp("H-d", nodes=2, calls=1, value=v)
        ranked = TT.rank_candidates([a, b, c, d])
        self.assertEqual([r["topology_id"] for r in ranked],
                         ["H-c", "H-d", "H-a", "H-b"])
        # permutation invariance (full determinism)
        ranked2 = TT.rank_candidates([d, c, b, a])
        self.assertEqual([r["topology_id"] for r in ranked2],
                         [r["topology_id"] for r in ranked])

    def test_higher_utility_dominates_structure(self):
        lo = {"delta_e": 0.4, "cost": 0.2, "redundancy": 0.0,
              "governance_risk": 0.0}
        hi = {"delta_e": 0.9, "cost": 0.2, "redundancy": 0.0,
              "governance_risk": 0.0}
        big = self._hyp("H-big", nodes=9, calls=9, value=hi)
        small = self._hyp("H-small", nodes=1, calls=1, value=lo)
        ranked = TT.rank_candidates([small, big])
        self.assertEqual(ranked[0]["topology_id"], "H-big")


if __name__ == "__main__":
    unittest.main()
