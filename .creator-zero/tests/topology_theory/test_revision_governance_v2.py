"""Revision engine v2, governance taxonomy v2, two-stage gate
(spec §20.6-20.7, NC9-NC14, NC17)."""
from __future__ import annotations
import json
import tempfile
import unittest

import _bootstrap
from _bootstrap import CZROOT, TT

G = TT.governance
TG = TT.theory_gate


def _theory():
    return TT.build_seed_theory()


def _ev(pid, kind, effect, i, run="primary"):
    ctx = ({"context_status": "OK", "admissibility_kind": kind,
            "latent_class": "X"} if kind else
           {"context_status": "UNKNOWN"})
    return {"principle_id": pid, "topology_id": f"H-t{i}-x",
            "prediction_id": f"H-t{i}-x-pr01", "effect": effect,
            "event_id": f"ev-{pid}-{i}", "trial_id": f"t{i}", "run": run,
            "context": ctx}


def _mixed_contextual_events():
    events = []
    i = 0
    for _ in range(6):
        i += 1
        events.append(_ev("P-INDEPENDENCE", "CLEAN_ROOM_AUTHORSHIP",
                          "SUPPORT", i))
    for eff in ("SUPPORT", "SUPPORT", "FALSIFY", "FALSIFY", "FALSIFY"):
        i += 1
        events.append(_ev("P-INDEPENDENCE", "NON_AUTHOR_SEARCH", eff, i))
    for eff in ("SUPPORT", "FALSIFY", "FALSIFY", "FALSIFY"):
        i += 1
        events.append(_ev("P-INDEPENDENCE", "METHOD_DISJOINT_VERIFICATION",
                          eff, i))
    for eff in ("SUPPORT", "SUPPORT", "FALSIFY", "FALSIFY"):
        i += 1
        events.append(_ev("P-INDEPENDENCE", "INDEPENDENT_DECOMPOSITION",
                          eff, i))
    return events


class RevisionV2Test(unittest.TestCase):
    def test_old_specialize_behavior_preserved(self):
        theory = _theory()
        events = [
            {"principle_id": "P-LOCALITY", "topology_id": "H-a-local",
             "prediction_id": "p1", "effect": "SUPPORT", "event_id": "e1"},
            {"principle_id": "P-LOCALITY", "topology_id": "H-a-local",
             "prediction_id": "p2", "effect": "FALSIFY", "event_id": "e2"},
        ]
        rev = TT.propose_revision(theory, events)
        self.assertEqual(rev.type, "SPECIALIZE")
        self.assertEqual(rev.parents, ["P-LOCALITY"])

    def test_contextual_mixed_evidence_produces_split(self):
        theory = _theory()
        doc = TT.propose_revision_v2(theory, _mixed_contextual_events())
        self.assertTrue(doc["split_trigger"]["eligible"],
                        doc["split_trigger"])
        self.assertEqual(doc["selected"], "SPLIT", doc["scores"])
        rev = TT.Revision.from_dict(doc["candidates"]["SPLIT"])
        self.assertEqual(rev.parents, ["P-INDEPENDENCE"])
        ids = {c["id"] for c in rev.candidate_principles}
        self.assertEqual(ids, {"P-AUTHORSHIP-INDEPENDENCE",
                               "P-NONAUTHOR-SEARCH",
                               "P-INDEPENDENT-DECOMPOSITION",
                               "P-METHOD-DISJOINT-VERIFICATION"})
        for c in rev.candidate_principles:
            self.assertEqual(c["parent_principles"], ["P-INDEPENDENCE"])
            self.assertTrue(c["supporting_evidence"])
            self.assertTrue(str(c.get("falsifier", "")).strip())
        self.assertEqual(rev.status, "CANDIDATE")
        self.assertTrue(rev.context_partition)

    def test_no_split_without_context(self):
        theory = _theory()
        events = [_ev("P-INDEPENDENCE", None, "SUPPORT", 1),
                  _ev("P-INDEPENDENCE", None, "FALSIFY", 2)]
        doc = TT.propose_revision_v2(theory, events)
        self.assertFalse(doc["split_trigger"]["eligible"])
        self.assertNotIn("SPLIT", doc["scores"])

    def test_no_change_supported_when_all_support(self):
        theory = _theory()
        events = [_ev("P-INDEPENDENCE", "CLEAN_ROOM_AUTHORSHIP",
                      "SUPPORT", i) for i in range(1, 9)]
        doc = TT.propose_revision_v2(theory, events)
        self.assertEqual(doc["selected"], "no-change")

    def test_apply_split_marks_parent_revised_and_keeps_it_active(self):
        theory = _theory()
        doc = TT.propose_revision_v2(theory, _mixed_contextual_events())
        rev = TT.Revision.from_dict(doc["candidates"]["SPLIT"])
        succ = TT.revise.apply_revision(theory, rev, "sha256:predecessor")
        self.assertEqual(succ.version, theory.version + 1)
        self.assertEqual(succ.status, "CANDIDATE")
        parent = succ.principle("P-INDEPENDENCE")
        self.assertEqual(parent.status, "REVISED")
        self.assertTrue(parent.active)
        self.assertIsNotNone(succ.principle("P-NONAUTHOR-SEARCH"))

    def test_candidate_cannot_promote_directly(self):
        # NC13: no direct promotion without a Gate-issued PASS
        theory = _theory()
        doc = TT.propose_revision_v2(theory, _mixed_contextual_events())
        rev = TT.Revision.from_dict(doc["candidates"]["SPLIT"])
        succ = TT.revise.apply_revision(theory, rev, "sha256:x")
        store = TT.TheoryStore(tempfile.mkdtemp())
        with self.assertRaises(TT.PromotionError):
            store.promote(succ, rev.to_dict())
        with self.assertRaises(TT.PromotionError):
            store.promote(succ, {"check": "verifier", "status": "PASS",
                                 "detail": {"issued_by": "verifier"}})

    def test_replay_rejects_deprecating_split(self):
        # a bad revision that RETIRES the parent contradicts frozen history
        theory = _theory()
        rev = TT.Revision(
            revision_id="rev-bad", type="DEPRECATE",
            parents=["P-INDEPENDENCE"], motivating_evidence=["x"])
        succ = TT.revise.apply_revision(theory, rev, "sha256:x")
        res = TT.replay(succ)
        self.assertGreater(res.contradicted, 0)
        self.assertFalse(res.acceptable)

    def test_split_survives_replay_including_e6_cases(self):
        theory = _theory()
        doc = TT.propose_revision_v2(theory, _mixed_contextual_events())
        rev = TT.Revision.from_dict(doc["candidates"]["SPLIT"])
        succ = TT.revise.apply_revision(theory, rev, "sha256:x")
        cases = TT.load_replay_corpus()
        cases += TT.load_replay_corpus(
            CZROOT / "topology-theory" / "replay-corpus-e6.json")
        res = TT.replay(succ, cases, repo_root=CZROOT)
        self.assertEqual(res.contradicted, 0, res.to_dict())
        self.assertEqual(res.indeterminate, 0, res.to_dict())


class GovernanceV2Test(unittest.TestCase):
    def test_unauthorized_capability_tool_is_fatal(self):
        evs = G.classify_session_audit(
            {"disallowed_tool_uses": [{"tool": "Bash", "id": "x"}]}, "s1")
        self.assertEqual(evs[0]["category"], "capability_violation")
        self.assertTrue(evs[0]["fatal"])

    def test_meta_tool_observation_is_not_capability_violation(self):
        # NC9/NC10
        evs = G.classify_session_audit(
            {"disallowed_tool_uses": [{"tool": "ToolSearch", "id": "x"},
                                      {"tool": "ToolSearch", "id": "y"}]},
            "s1")
        self.assertTrue(all(e["category"] == "meta_tool_observation"
                            for e in evs))
        s = G.summarize(evs)
        self.assertEqual(s["capability_violations"], 0)
        self.assertEqual(s["fatal_events"], 0)
        self.assertEqual(s["meta_tool_observations"], 2)
        self.assertEqual(s["observed_governance_risk"], 0.0)

    def test_hidden_child_is_fatal(self):
        # NC11
        evs = G.classify_session_audit(
            {"spawn_capable_tool_uses": [{"tool": "Agent", "id": "x"}]},
            "s1")
        self.assertEqual(evs[0]["code"], "HIDDEN_CHILD_RISK")
        self.assertTrue(evs[0]["fatal"])

    def test_invalid_ledger_label_is_instrumentation(self):
        evs = G.classify_ledger_labels(["unknown label 'proposeX'"], "s1")
        self.assertEqual(evs[0]["category"], "instrumentation_violation")
        self.assertFalse(evs[0]["fatal"])
        s = G.summarize(evs)
        self.assertEqual(s["observed_governance_risk"], 0.1)

    def test_e6_mutation_is_protected_law_failure(self):
        # NC14
        res = TT.self_modify.check_protected_laws(
            [".creator-zero/experiment-6/report.md"])
        self.assertEqual(res["status"], "FAIL")
        res = TT.self_modify.check_protected_laws(
            [".creator-zero/state/experiment-6.json"])
        self.assertEqual(res["status"], "FAIL")
        res = TT.self_modify.check_protected_laws(
            [".creator-zero/experiment-7/report.md"])
        self.assertEqual(res["status"], "PASS")


class TwoStageGateTest(unittest.TestCase):
    def _eval_inputs(self, **over):
        base = {k: {"status": "PASS"} for k in TG.REQUIRED_EVAL_INPUTS}
        base.update(over)
        return base

    def test_stage1_authorizes_but_cannot_promote(self):
        auth = TG.evaluation_authorization(self._eval_inputs())
        self.assertEqual(auth["status"], "PASS")
        self.assertNotEqual(auth["check"], "gate")
        store = TT.TheoryStore(tempfile.mkdtemp())
        succ = _theory()
        with self.assertRaises(TT.PromotionError):
            store.promote(succ, auth)          # NC17

    def test_stage1_fails_on_missing_input(self):
        inputs = self._eval_inputs()
        del inputs["independent_verifier"]
        auth = TG.evaluation_authorization(inputs)
        self.assertEqual(auth["status"], "FAIL")

    def test_theory_gate_requires_heldout_and_paired(self):
        inputs = self._eval_inputs()
        inputs["evaluation_authorization"] = \
            TG.evaluation_authorization(self._eval_inputs())
        gate = TG.theory_gate(inputs)          # missing held-out inputs
        self.assertEqual(gate["status"], "FAIL")
        inputs.update({
            "heldout_thresholds": {"status": "PASS"},
            "paired_improvement": {"status": "PASS"},
            "governance": {"status": "PASS"},
            "historical_immutability": {"status": "PASS"},
        })
        gate = TG.theory_gate(inputs)
        self.assertEqual(gate["status"], "PASS")
        self.assertEqual(gate["check"], "gate")
        self.assertEqual(gate["detail"]["issued_by"], "gate")


if __name__ == "__main__":
    unittest.main()
