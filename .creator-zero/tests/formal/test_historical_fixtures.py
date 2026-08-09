"""Preregistered historical regression outcomes (Experiments 3, 4, 4B).

Historical experiment artifacts are immutable inputs: their sha256 digests are
pinned here, and the expected formal outcomes are encoded exactly as
preregistered in the Formal Semantics Kernel v0.1 specification:

    Experiment 3 runtime                      -> refinement PASS
    Experiment 4 C1 process execution         -> deviation exposed
    Experiment 4 state-mediated continuation  -> weak bisimulation PASS
    Original E4 K3 attestation                -> closure FAIL (CreatorCapable)
    E4B corrected K3 attestation              -> closure PASS
    Synthetic authority-escalating child      -> attenuation FAIL
    Synthetic Actor canonical write           -> refinement FAIL
"""
from __future__ import annotations
import hashlib
import json
import subprocess
import sys
import unittest

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parent))
import _bootstrap  # noqa: F401,E402
from _bootstrap import CZROOT, FIXTURES  # noqa: F401,E402
from formal.adapters import (adapt_experiment3_ledger,
                             adapt_experiment4_c1_ledger,
                             truncate_at_raw_event)
from formal.attenuation import check_attenuation
from formal.bisimulation import strong_bisimilar, weak_bisimilar
from formal.creator_closure import check_creator_closure
from formal.refinement import check_refinement
from formal.semantics import compile_harness_spec
from formal.serialization import lts_from_json
from formal.synthesis_fixedpoint import CLOSED, classify_synthesis
from formal.trace import parse_runtime_ledger

# Immutability pins: modifying any historical artifact fails this suite.
HISTORICAL_SHA256 = {
    "experiment-3/execution-ledger.jsonl":
        "bb561f728cc7e991266c9a33865894cfa528051dd825f4bcce40ceff415f3446",
    "experiment-3/final-harness.json":
        "6a8eec1bb5bc999d57e93c6d2f37c2ee53c2d90f58e940e713f12f9772a73fd0",
    "experiment-4/c1/execution-ledger.jsonl":
        "53657a2c59c4efa7e477c1aa751218225f419f5e22fc1e248e022e5eb206edec",
    "experiment-4/c1/final-harness.json":
        "9d00267fcbbd4aef4aee8732f3222605b9475897d41a63872ee9716430a33a19",
    "experiment-4/c2/creator-capability-attestation.json":
        "2d97e54597431fe1db13d1bec3cb57a1553f3793397832628e453f2364445359",
    "experiment-4/closure-correction/corrected-k3-attestation.json":
        "5ff1a8502cdd7e325d21c00af14e50f1579492219a08d08136d1bf603213e92a",
    "experiment-4/root-contract.json":
        "17bb0c888c1366d2ef49f884743027afec179c6fbed8b67cbf4e701fc1f4f382",
    "experiment-4/child-1-contract.json":
        "4a0d935115089ff5d77abdb225f25e1d11ed32a3fdc26dc9aa0bf153c905f90c",
    "experiment-4/child-2-contract.json":
        "4f6865fec22eada3eb73ed537ca23a0a1461abdb095501230fc75d7a883d04d9",
}


def load(p):
    return json.loads((CZROOT / p).read_text(encoding="utf-8"))


class TestImmutability(unittest.TestCase):
    def test_historical_artifacts_unmodified(self):
        for rel, expect in HISTORICAL_SHA256.items():
            got = hashlib.sha256((CZROOT / rel).read_bytes()).hexdigest()
            self.assertEqual(got, expect, f"historical artifact modified: {rel}")

    def test_original_attestation_hash_matches_creation_ledger_record(self):
        # the creation ledger historically pinned this exact digest
        ledger = (CZROOT / "experiment-4/creation-ledger.jsonl").read_text()
        self.assertIn(HISTORICAL_SHA256[
            "experiment-4/c2/creator-capability-attestation.json"], ledger)


class TestExperiment3(unittest.TestCase):
    def test_runtime_refinement_pass(self):
        spec = load("experiment-3/final-harness.json")
        contract = load("contracts/root_contract.json")
        lts = compile_harness_spec(spec, contract)
        trace, mapping = adapt_experiment3_ledger(
            CZROOT / "experiment-3/execution-ledger.jsonl", spec)
        self.assertEqual(trace.unmapped_events, [])
        r = check_refinement(trace, lts)
        self.assertEqual(r.status, "PASS")

    def test_adapter_output_matches_committed_fixture(self):
        spec = load("experiment-3/final-harness.json")
        trace, _ = adapt_experiment3_ledger(
            CZROOT / "experiment-3/execution-ledger.jsonl", spec)
        regenerated = [json.dumps(e.to_dict(), sort_keys=True) for e in trace.events]
        committed = [l for l in (FIXTURES / "experiment3-normalized-ledger.jsonl")
                     .read_text().splitlines() if l.strip()]
        self.assertEqual(regenerated, committed)

    def test_synthesis_closure_classified_closed(self):
        # round 0 opened Q1-Q7; synthesis closed with no unresolved distinctions
        first = json.loads((CZROOT / "experiment-3/execution-ledger.jsonl")
                           .read_text().splitlines()[0])
        r = classify_synthesis(first["unresolved"], [])
        self.assertEqual(r.detail["classification"], CLOSED)


class TestExperiment4C1(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = load("experiment-4/c1/final-harness.json")
        cls.k1 = load("experiment-4/child-1-contract.json")
        cls.lts = compile_harness_spec(cls.spec, cls.k1)
        cls.trace, _ = adapt_experiment4_c1_ledger(
            CZROOT / "experiment-4/c1/execution-ledger.jsonl", cls.spec)

    def test_process_execution_deviation_exposed(self):
        # the process-level trace ends at c1_pending_on_c2 without a governed
        # complete transition: the known premature-exit deviation
        proc = truncate_at_raw_event(self.trace, "c1_pending_on_c2")
        r = check_refinement(proc, self.lts, require_completion=True)
        self.assertEqual(r.status, "INDETERMINATE")
        self.assertIn("premature", r.detail["reason"])

    def test_state_mediated_continuation_refines_to_completion(self):
        r = check_refinement(self.trace, self.lts, require_completion=True)
        self.assertEqual(r.status, "PASS")
        self.assertIn("complete=1", r.detail["final_state"])

    def test_session_equivalence_weak_bisimulation_pass(self):
        a = lts_from_json((FIXTURES / "e4-c1-inprocess-lts.json").read_text())
        b = lts_from_json((FIXTURES / "e4-c1-continuation-lts.json").read_text())
        self.assertEqual(weak_bisimilar(a, b).status, "PASS")

    def test_process_identity_distinguished_from_behavioral_equivalence(self):
        # strong bisimulation separates the two sessions (process identity);
        # weak bisimulation identifies them (governed behavioral equivalence)
        a = lts_from_json((FIXTURES / "e4-c1-inprocess-lts.json").read_text())
        b = lts_from_json((FIXTURES / "e4-c1-continuation-lts.json").read_text())
        self.assertEqual(strong_bisimilar(a, b).status, "FAIL")

    def test_no_promotion_authority_in_c1_semantics(self):
        self.assertFalse(any(t.label == "promote" for t in self.lts.transitions))


class TestClosureHistory(unittest.TestCase):
    def test_original_k3_fails_corrected_passes(self):
        k2 = load("experiment-4/child-2-contract.json")
        orig = load("experiment-4/c2/creator-capability-attestation.json")
        corr = load("experiment-4/closure-correction/corrected-k3-attestation.json")
        ro = check_creator_closure(k2, orig)
        self.assertEqual(ro.status, "FAIL")
        self.assertEqual(ro.counterexample["failed_clauses"], ["CreatorCapable"])
        self.assertEqual(check_creator_closure(k2, corr).status, "PASS")


class TestContractLineage(unittest.TestCase):
    def test_historical_attenuation_chain_holds(self):
        k0 = load("experiment-4/root-contract.json")
        k1 = load("experiment-4/child-1-contract.json")
        k2 = load("experiment-4/child-2-contract.json")
        self.assertEqual(check_attenuation(k0, k1).status, "PASS")
        self.assertEqual(check_attenuation(k1, k2).status, "PASS")

    def test_synthetic_escalating_child_fails(self):
        k1 = load("experiment-4/child-1-contract.json")
        bad = json.loads((FIXTURES / "escalating-child-contract.json").read_text())
        r = check_attenuation(k1, bad)
        self.assertEqual(r.status, "FAIL")
        escalated = {f["dimension"] for f in
                     r.counterexample["escalating_dimensions"]}
        for d in ("allowed_tools", "max_model_calls", "max_children",
                  "filesystem_write_scope", "canonical_write_authority"):
            self.assertIn(d, escalated)


class TestSyntheticActorCanonicalWrite(unittest.TestCase):
    def test_refinement_violation(self):
        spec = load("experiment-3/final-harness.json")
        contract = load("contracts/root_contract.json")
        lts = compile_harness_spec(spec, contract)
        trace = parse_runtime_ledger(FIXTURES / "synthetic-actor-canonical-write.jsonl")
        r = check_refinement(trace, lts)
        self.assertEqual(r.status, "FAIL")
        self.assertEqual(r.counterexample["violation"], "REFINEMENT_VIOLATION")
        self.assertEqual(r.counterexample["offending_transition"]["actor"],
                         "node:act-candidate-test")


class TestCLIExitCodes(unittest.TestCase):
    def run_cz(self, *args):
        return subprocess.run(
            [sys.executable, str(CZROOT / "cz.py"), *args],
            capture_output=True, text=True, cwd=str(CZROOT))

    def test_closure_exit_codes(self):
        r_fail = self.run_cz("closure",
                             "experiment-4/child-2-contract.json",
                             "experiment-4/c2/creator-capability-attestation.json")
        self.assertEqual(r_fail.returncode, 2)
        r_pass = self.run_cz(
            "closure", "experiment-4/child-2-contract.json",
            "experiment-4/closure-correction/corrected-k3-attestation.json")
        self.assertEqual(r_pass.returncode, 0)

    def test_check_runtime_and_bisim_and_parse_error(self):
        r = self.run_cz("check-runtime", "experiment-3/final-harness.json",
                        "experiment-3/execution-ledger.jsonl",
                        "--adapter", "experiment3")
        self.assertEqual(r.returncode, 0)
        r2 = self.run_cz("bisim",
                         "tests/formal/fixtures/e4-c1-inprocess-lts.json",
                         "tests/formal/fixtures/e4-c1-continuation-lts.json",
                         "--mode", "weak")
        self.assertEqual(r2.returncode, 0)
        r3 = self.run_cz("bisim",
                         "tests/formal/fixtures/e4-c1-inprocess-lts.json",
                         "tests/formal/fixtures/e4-c1-continuation-lts.json",
                         "--mode", "strong")
        self.assertEqual(r3.returncode, 2)
        r4 = self.run_cz("attenuation", "contracts/root_contract.json",
                         "/nonexistent.json")
        self.assertEqual(r4.returncode, 4)


if __name__ == "__main__":
    unittest.main()
