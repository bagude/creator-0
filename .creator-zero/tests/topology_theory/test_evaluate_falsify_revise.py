"""Evaluation, prediction-specific falsification, revision, replay."""
from __future__ import annotations
import json
import tempfile
import unittest
from pathlib import Path

import _bootstrap
from _bootstrap import CZROOT, TT

CONTRACT = json.loads(
    (CZROOT / "contracts/root_contract.json").read_text(encoding="utf-8"))
TASK = {"task_id": "t-ev"}
D_ISO = [{"id": "Q1", "question": "clean-room divergence?",
          "features": {"requires_isolation": True}}]
D_LOCAL = [{"id": "Q1", "question": "local check",
            "features": {"locally_resolvable": True}}]


def frozen_candidate(dist, key):
    theory = TT.build_seed_theory()
    app = TT.abduce(TASK, dist, contract=CONTRACT, theory=theory)
    cands = TT.generate_candidates(TASK, dist, app, CONTRACT)
    cand = next(c for c in cands if key in c.topology_id)
    preds = TT.freeze_predictions(cand, dist)
    return cand, preds


def runtime_for(cand, resolved_by=None, **over):
    spec = cand.harness_spec
    order = TT.predict._expected_path(spec)
    rt = {
        "topology_id": cand.topology_id,
        "predictions_hash": cand.predictions_hash,
        "resolved_distinctions": [
            {"id": q, "resolved_by": resolved_by or node}
            for q, node in cand.resolution_map.items()],
        "unresolved_distinctions": [],
        "node_completion_order": order,
        "resource_use": {"model_calls": spec["max_model_calls"],
                          "child_calls": 0,
                          "model_call_budget": spec["max_model_calls"]},
        "formal_failures": [],
        "authority_violations": [],
        "verification_effect": "verified",
        "task_result": "correct",
        "child_launches": 1 if any(n["primitive"] == "create"
                                    for n in spec["nodes"]) else 0,
    }
    rt.update(over)
    return rt


class EvaluationTest(unittest.TestCase):
    def test_all_held_supported(self):
        cand, preds = frozen_candidate(D_ISO, "isolated-child")
        rt = runtime_for(cand)
        ev = [{"id": "e1", "source_node": "child-return",
               "duplicate_of_parent": False}]
        evaluation = TT.evaluate_topology(preds, rt, ev,
                                          predicted_value=cand.predicted_value)
        fr = TT.falsify(preds, evaluation)
        self.assertEqual(fr.status, "SUPPORTED")
        self.assertIn("mean_component_error", evaluation.calibration_error)
        self.assertIsInstance(evaluation.observed_utility, float)

    def test_retrospective_edit_detected(self):
        cand, preds = frozen_candidate(D_ISO, "isolated-child")
        rt = runtime_for(cand)
        preds[0].claim = "edited after freezing"
        with self.assertRaises(TT.PredictionIntegrityError):
            TT.evaluate_topology(preds, rt, [])

    def test_duplicate_child_falsification(self):
        cand, preds = frozen_candidate(D_ISO, "isolated-child")
        rt = runtime_for(cand)
        # the child returned only duplicates of parent evidence
        ev = [{"id": "e1", "source_node": "child-return",
               "duplicate_of_parent": True},
              {"id": "e2", "source_node": "child-return",
               "duplicate_of_parent": True}]
        evaluation = TT.evaluate_topology(preds, rt, ev)
        fr = TT.falsify(preds, evaluation)
        self.assertIn(fr.status, ("PARTIALLY_SUPPORTED", "FALSIFIED"))
        novel = next(p for p in preds if p.kind == "novel_evidence")
        self.assertIn(novel.prediction_id, fr.falsified_predictions)
        # P-INDEPENDENCE receives a FALSIFY evidence event
        effects = {(e["principle_id"], e["effect"])
                   for e in fr.evidence_events}
        self.assertIn(("P-INDEPENDENCE", "FALSIFY"), effects)

    def test_local_insufficiency_falsification(self):
        cand, preds = frozen_candidate(D_LOCAL, "H-t-ev-local")
        rt = runtime_for(cand,
                         resolved_by=None,
                         verification_effect="impossible",
                         resolved_distinctions=[],
                         unresolved_distinctions=["Q1"])
        evaluation = TT.evaluate_topology(preds, rt, [])
        fr = TT.falsify(preds, evaluation)
        self.assertIn(fr.status, ("PARTIALLY_SUPPORTED", "FALSIFIED"))
        loc = next(p for p in preds if p.kind == "local_sufficiency")
        self.assertIn(loc.prediction_id, fr.falsified_predictions)
        effects = {(e["principle_id"], e["effect"])
                   for e in fr.evidence_events}
        self.assertIn(("P-LOCALITY", "FALSIFY"), effects)

    def test_task_success_does_not_imply_topology_support(self):
        cand, preds = frozen_candidate(D_LOCAL, "H-t-ev-local")
        # task verified correct, but a hidden child ran: local-sufficiency
        # prediction is falsified even though the answer was right
        rt = runtime_for(cand, child_launches=1)
        evaluation = TT.evaluate_topology(preds, rt, [])
        fr = TT.falsify(preds, evaluation)
        self.assertEqual(rt["task_result"], "correct")
        self.assertIn(fr.status, ("PARTIALLY_SUPPORTED", "FALSIFIED"))


class RevisionReplayTest(unittest.TestCase):
    def setUp(self):
        self.theory = TT.build_seed_theory()

    def test_all_support_proposes_nothing(self):
        events = [TT.PrincipleEvidence(
            principle_id="P-LOCALITY", topology_id="H", prediction_id="p1",
            effect="SUPPORT", event_id="e1")]
        self.assertIsNone(TT.propose_revision(self.theory, events))

    def test_falsify_without_support_proposes_deprecate(self):
        events = [TT.PrincipleEvidence(
            principle_id="P-INDEPENDENCE", topology_id="H",
            prediction_id="p1", effect="FALSIFY", event_id="e1")]
        rev = TT.propose_revision(self.theory, events)
        self.assertEqual(rev.type, "DEPRECATE")
        self.assertEqual(rev.parents, ["P-INDEPENDENCE"])
        self.assertEqual(rev.status, "CANDIDATE")

    def test_mixed_evidence_proposes_specialize(self):
        events = [
            TT.PrincipleEvidence(principle_id="P-INDEPENDENCE",
                                 topology_id="H", prediction_id="p1",
                                 effect="FALSIFY", event_id="e1"),
            TT.PrincipleEvidence(principle_id="P-INDEPENDENCE",
                                 topology_id="H2", prediction_id="p2",
                                 effect="SUPPORT", event_id="e2")]
        rev = TT.propose_revision(self.theory, events)
        self.assertEqual(rev.type, "SPECIALIZE")
        self.assertEqual(rev.candidate_principles[0]["parent_principles"],
                         ["P-INDEPENDENCE"])

    def test_revision_status_is_forced_candidate(self):
        with self.assertRaises(TT.ModelValidationError):
            TT.Revision(revision_id="r", type="DEPRECATE",
                        parents=["P-X"], status="PROMOTED")

    def test_revision_cannot_self_promote(self):
        store = TT.TheoryStore(Path(tempfile.mkdtemp()))
        store.write_version(self.theory)
        events = [TT.PrincipleEvidence(
            principle_id="P-INDEPENDENCE", topology_id="H",
            prediction_id="p1", effect="FALSIFY", event_id="e1")]
        rev = TT.propose_revision(self.theory, events)
        candidate = TT.revise.apply_revision(self.theory, rev,
                                             store.version_hash(1))
        # the revision itself is not a gate result
        with self.assertRaises(TT.PromotionError):
            store.promote(candidate, rev.to_dict())
        # nor is a verifier report, whatever its status claims
        verifier_report = {"check": "independent_verifier", "status": "PASS",
                           "detail": {"issued_by": "verifier"}}
        with self.assertRaises(TT.PromotionError):
            store.promote(candidate, verifier_report)

    def test_seed_theory_replays_compatible(self):
        res = TT.replay(self.theory, repo_root=CZROOT)
        self.assertEqual(res.contradicted, 0)
        self.assertEqual(res.indeterminate, 0)
        self.assertTrue(res.acceptable)
        self.assertEqual(res.compatible, 5)

    def test_historical_replay_detects_bad_revision(self):
        # deprecating P-INDEPENDENCE contradicts the frozen E5 contamination
        # case (an isolated child demonstrably added novel verified evidence)
        rev = TT.Revision(revision_id="r-bad", type="DEPRECATE",
                          parents=["P-INDEPENDENCE"])
        candidate = TT.revise.apply_revision(self.theory, rev, "sha256:x")
        res = TT.replay(candidate, repo_root=CZROOT)
        self.assertFalse(res.acceptable)
        bad = [c for c in res.case_results if c["result"] == "CONTRADICTED"]
        self.assertTrue(any(c["case_id"] == "E5-contamination" for c in bad))


if __name__ == "__main__":
    unittest.main()
