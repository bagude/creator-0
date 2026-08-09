"""Deterministic tests for capability-bearing proposal observability
(Experiment 5 hardening 1)."""
from __future__ import annotations
import json
import tempfile
import unittest
from pathlib import Path

import _bootstrap  # noqa: F401

from formal.trace import parse_runtime_ledger

# The experiment-5 directory is hyphenated (not an importable package name):
# runtime modules self-bootstrap sys.path and are loaded by file path.
import importlib.util


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(
        name, _bootstrap.E5 / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class ProposalObserverTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.po = _load("e5_proposal_observer", "runtime/proposal_observer.py")

    def _trace(self, events):
        tmp = Path(tempfile.mkdtemp()) / "ledger.jsonl"
        tmp.write_text("\n".join(json.dumps(e) for e in events) + "\n",
                       encoding="utf-8")
        return parse_runtime_ledger(tmp, strict=True)

    @staticmethod
    def _ev(label, refs, actor="creator", **meta):
        return {"label": label, "actor": actor, "artifact_refs": refs,
                "metadata": meta}

    def test_pass_propose_then_return(self):
        trace = self._trace([
            self._ev("observe", ["inputs/"]),
            self._ev("propose", ["child-contract.json"],
                     artifact_type="child_contract"),
            self._ev("return", ["child-contract.json", "result.json"]),
        ])
        res = self.po.check_capability_observability(trace,
                                                     "child-contract.json")
        self.assertEqual(res.status, "PASS")
        self.assertEqual(res.detail["first_propose_index"], 1)

    def test_fail_only_inside_return(self):
        # Negative control B shape: witness emitted only inside return.
        trace = self._trace([
            self._ev("observe", ["inputs/"]),
            self._ev("return", ["child-contract.json"]),
        ])
        res = self.po.check_capability_observability(trace,
                                                     "child-contract.json")
        self.assertEqual(res.status, "FAIL")
        self.assertEqual(res.counterexample["violation"],
                         "CAPABILITY_OBSERVABILITY_FAIL")

    def test_fail_return_before_propose(self):
        trace = self._trace([
            self._ev("return", ["witness.json"]),
            self._ev("propose", ["witness.json"]),
        ])
        res = self.po.check_capability_observability(trace, "witness.json")
        self.assertEqual(res.status, "FAIL")
        self.assertIn("before any", res.counterexample["reason"])

    def test_indeterminate_when_never_referenced(self):
        trace = self._trace([self._ev("observe", ["inputs/"])])
        res = self.po.check_capability_observability(trace, "ghost.json")
        self.assertEqual(res.status, "INDETERMINATE")

    def test_basename_matching_recorded(self):
        trace = self._trace([
            self._ev("propose", ["workspace/out/harness.json"]),
        ])
        res = self.po.check_capability_observability(
            trace, "trials/t-001/child/harness.json")
        self.assertEqual(res.status, "PASS")
        self.assertEqual(res.detail["propose_events"][0]["match_mode"],
                         "basename")

    def test_persist_does_not_substitute_for_propose(self):
        trace = self._trace([
            self._ev("persist", ["decision.json"]),
            self._ev("verify", ["decision.json"]),
        ])
        res = self.po.check_capability_observability(trace, "decision.json")
        self.assertEqual(res.status, "FAIL")
        self.assertIn("persist",
                      res.counterexample["labels_referencing_artifact"])

    def test_aggregate_fail_dominates(self):
        trace = self._trace([
            self._ev("propose", ["a.json"]),
            self._ev("return", ["b.json"]),
        ])
        res = self.po.check_all_capability_artifacts(trace,
                                                     ["a.json", "b.json"])
        self.assertEqual(res.status, "FAIL")
        self.assertIn("b.json", res.counterexample["artifacts"])

    def test_aggregate_all_pass(self):
        trace = self._trace([
            self._ev("propose", ["a.json", "b.json"]),
        ])
        res = self.po.check_all_capability_artifacts(trace,
                                                     ["a.json", "b.json"])
        self.assertEqual(res.status, "PASS")


if __name__ == "__main__":
    unittest.main()
