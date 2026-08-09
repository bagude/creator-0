"""Experiment 5 limitation repairs: branching completion, freshness v0.2,
stable artifact identity."""
from __future__ import annotations
import json
import unittest

import _bootstrap
from _bootstrap import CZROOT, TT

from formal.model import RuntimeEvent, Trace
from formal.refinement import check_refinement
from formal.semantics import compile_harness_spec
from formal.freshness import check_freshness

CONTRACT = json.loads(
    (CZROOT / "contracts/root_contract.json").read_text(encoding="utf-8"))


def ev(i, label, actor, node=None, **meta):
    if node:
        meta["completes_node"] = node
    return RuntimeEvent(event_id=f"e{i}", label=label, actor=actor,
                        metadata=tuple(sorted(meta.items())))


def branching_spec():
    """Minimal branching topology per the v0.1 target semantics:
    LOCAL:  decision -> local -> verify -> complete
    CREATE: decision -> propose-child -> validate-child -> create
            -> child-return -> integrate -> verify -> complete"""
    text = (CZROOT / "experiment-5/harness-template.json").read_text(
        encoding="utf-8").replace("__TRIAL_ID__", "branch-test")
    return json.loads(text)


class BranchingCompletionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lts = compile_harness_spec(branching_spec(), CONTRACT)

    def test_complete_states_exist(self):
        finals = [s for s in self.lts.states if "complete=1" in s]
        self.assertEqual(len(finals), 2)   # one per legal branch

    def test_local_branch_completion(self):
        trace = Trace(events=[
            ev(1, "observe", "node:observe-package", "observe-package"),
            ev(2, "propose", "node:decide-topology", "decide-topology"),
            ev(3, "propose", "node:local-resolve", "local-resolve"),
            ev(4, "verify", "node:self-check-local", "self-check-local"),
            ev(5, "return", "node:return-local", "return-local"),
            ev(6, "verify", "node:verify-trial-local", "verify-trial-local"),
            ev(7, "complete", "root"),
        ], origin="local-branch")
        r = check_refinement(trace, self.lts, require_completion=True)
        self.assertEqual(r.status, "PASS", r.counterexample or r.detail)
        self.assertIn("complete=1", r.detail["final_state"])

    def test_create_branch_completion(self):
        trace = Trace(events=[
            ev(1, "observe", "node:observe-package", "observe-package"),
            ev(2, "propose", "node:decide-topology", "decide-topology"),
            ev(3, "propose", "node:propose-child", "propose-child"),
            ev(4, "verify", "node:self-check-proposal", "self-check-proposal"),
            ev(5, "return", "node:return-proposal", "return-proposal"),
            ev(6, "verify", "node:validate-child", "validate-child"),
            ev(7, "create", "node:create-child", "create-child"),
            ev(8, "return", "node:child-return", "child-return"),
            ev(9, "verify", "node:verify-trial-child", "verify-trial-child"),
            ev(10, "complete", "root"),
        ], origin="create-branch")
        r = check_refinement(trace, self.lts, require_completion=True)
        self.assertEqual(r.status, "PASS", r.counterexample or r.detail)
        self.assertIn("complete=1", r.detail["final_state"])

    def test_cross_branch_execution_rejected(self):
        # after committing to the local branch, a create-branch node
        # execution must have no enabled transition
        trace = Trace(events=[
            ev(1, "observe", "node:observe-package", "observe-package"),
            ev(2, "propose", "node:decide-topology", "decide-topology"),
            ev(3, "propose", "node:local-resolve", "local-resolve"),
            ev(4, "propose", "node:propose-child", "propose-child"),
        ], origin="cross-branch")
        r = check_refinement(trace, self.lts)
        self.assertEqual(r.status, "FAIL")
        self.assertEqual(r.counterexample["violation"],
                         "REFINEMENT_VIOLATION")

    def test_incomplete_branch_does_not_complete(self):
        trace = Trace(events=[
            ev(1, "observe", "node:observe-package", "observe-package"),
            ev(2, "propose", "node:decide-topology", "decide-topology"),
            ev(3, "propose", "node:local-resolve", "local-resolve"),
        ], origin="incomplete")
        r = check_refinement(trace, self.lts, require_completion=True)
        self.assertEqual(r.status, "INDETERMINATE")

    def test_non_branching_spec_unchanged(self):
        # linear specs keep the historical rule: complete iff all nodes done
        spec = json.loads((CZROOT / "experiment-3/final-harness.json")
                          .read_text(encoding="utf-8"))
        lts = compile_harness_spec(spec, CONTRACT)
        self.assertFalse(lts.metadata["branches"])
        n_nodes = len(spec["nodes"])
        for s in lts.states:
            if "complete=1" in s:
                done = s.split("done={")[1].split("}")[0]
                self.assertEqual(len(done.split(",")), n_nodes)


class FreshnessV2Test(unittest.TestCase):
    def _prov(self, executed, confirmed, **over):
        p = {
            "artifact": "fresh-child launch provenance",
            "fresh": True,
            "session_id": "11111111-2222-3333-4444-555555555555",
            "environment_sanitization": {
                "removed_variables": ["CLAUDE_CODE_SESSION_ID"],
                "residual_continuity_variables": [],
                "session_id_reuse": False,
            },
            "executed": executed,
            "session_id_confirmed": confirmed,
        }
        p.update(over)
        return p

    def test_executed_confirmed_passes(self):
        r = check_freshness(self._prov(True, True))
        self.assertEqual(r.status, "PASS")

    def test_executed_unconfirmed_none_fails(self):
        # the tightened rule: executed sessions demand stream confirmation
        r = check_freshness(self._prov(True, None))
        self.assertEqual(r.status, "FAIL")
        self.assertIn("session_id_confirmed_rule",
                      r.counterexample["failed_clauses"])

    def test_executed_wrong_session_fails(self):
        r = check_freshness(self._prov(True, False))
        self.assertEqual(r.status, "FAIL")

    def test_dry_run_none_allowed(self):
        r = check_freshness(self._prov(False, None, dry_run=True))
        self.assertEqual(r.status, "PASS")

    def test_missing_executed_field_fails(self):
        p = self._prov(True, True)
        del p["executed"]
        r = check_freshness(p)
        self.assertEqual(r.status, "FAIL")
        self.assertIn("executed_recorded",
                      r.counterexample["failed_clauses"])

    def test_frozen_e5_provenance_passes_tightened_rule(self):
        # historical evidence is untouched AND satisfies the harder rule
        prov = json.loads((CZROOT / "experiment-5/trials/t-031/child/"
                           "launch-provenance.json").read_text())
        r = check_freshness(prov)
        self.assertEqual(r.status, "PASS", r.counterexample)


class ArtifactIdentityTest(unittest.TestCase):
    def test_same_basename_different_content_distinct_ids(self):
        prov = "creator-0/test/report.json"
        a = TT.artifact_id(b'{"x": 1}', prov)
        b = TT.artifact_id(b'{"x": 2}', prov)
        self.assertNotEqual(a, b)
        self.assertTrue(a.startswith("sha256:") and b.startswith("sha256:"))

    def test_identity_is_content_plus_provenance(self):
        content = b'{"x": 1}'
        a = TT.artifact_id(content, "creator-0/roleA/report.json")
        b = TT.artifact_id(content, "creator-0/roleB/report.json")
        self.assertNotEqual(a, b)
        self.assertEqual(a, TT.artifact_id(content,
                                           "creator-0/roleA/report.json"))

    def test_path_is_metadata_not_identity(self):
        import tempfile
        from pathlib import Path
        d = Path(tempfile.mkdtemp())
        p1, p2 = d / "a" / "report.json", d / "b" / "report.json"
        for p in (p1, p2):
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(b'{"same": "content"}')
        prov = "creator-0/test/report"
        r1 = TT.serialization.artifact_ref(p1, prov)
        r2 = TT.serialization.artifact_ref(p2, prov)
        # same content + provenance => same id, whatever the path says
        self.assertEqual(r1["artifact_id"], r2["artifact_id"])
        self.assertNotEqual(r1["path"], r2["path"])

    def test_separator_prevents_boundary_ambiguity(self):
        self.assertNotEqual(TT.artifact_id(b"ab", "c"),
                            TT.artifact_id(b"a", "bc"))


if __name__ == "__main__":
    unittest.main()
