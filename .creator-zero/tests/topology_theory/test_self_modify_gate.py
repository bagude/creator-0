"""Self-modification governance: candidate-only, verifier != promoter,
Gate monopoly, protected laws."""
from __future__ import annotations
import tempfile
import unittest
from pathlib import Path

import _bootstrap
from _bootstrap import TT

SM = TT.self_modify


def pass_inputs():
    return {
        "attenuation": {"status": "PASS"},
        "refinement": {"status": "PASS"},
        "tests_existing": {"status": "PASS"},
        "tests_new": {"status": "PASS"},
        "historical_replay": {"acceptable": True},
        "protected_laws": {"status": "PASS"},
        "frozen_trees": {"status": "PASS"},
        "independent_verifier": {"status": "PASS"},
        "patch_manifest": {"file_count": 3},
    }


class CandidateOnlyTest(unittest.TestCase):
    def test_candidate_only_self_modification(self):
        root = Path(tempfile.mkdtemp())
        inside = root / "pkg" / "file.py"
        SM.candidate_only_guard([inside], root)          # no raise
        outside = Path(tempfile.mkdtemp()) / "canonical.py"
        with self.assertRaises(SM.CandidateViolation):
            SM.candidate_only_guard([inside, outside], root)

    def test_protected_laws_reject_historical_mutation(self):
        res = SM.check_protected_laws(
            [".creator-zero/topology-theory/model.py",
             ".creator-zero/experiment-5/report.md"])
        self.assertEqual(res["status"], "FAIL")
        self.assertEqual(res["violations"],
                         [".creator-zero/experiment-5/report.md"])
        ok = SM.check_protected_laws(
            [".creator-zero/topology-theory/model.py",
             ".creator-zero/formal/freshness.py"])
        self.assertEqual(ok["status"], "PASS")

    def test_root_contract_is_protected(self):
        res = SM.check_protected_laws(
            [".creator-zero/contracts/root_contract.json"])
        self.assertEqual(res["status"], "FAIL")


class GateTest(unittest.TestCase):
    def test_gate_passes_on_complete_pass_inputs(self):
        res = SM.gate(pass_inputs())
        self.assertEqual(res["status"], "PASS")
        self.assertEqual(res["detail"]["issued_by"], "gate")

    def test_gate_fails_on_missing_input(self):
        inputs = pass_inputs()
        del inputs["independent_verifier"]
        res = SM.gate(inputs)
        self.assertEqual(res["status"], "FAIL")
        self.assertIn("independent_verifier",
                      res["counterexample"]["failed_or_missing_inputs"])

    def test_gate_fails_on_failed_replay(self):
        inputs = pass_inputs()
        inputs["historical_replay"] = {"acceptable": False}
        self.assertEqual(SM.gate(inputs)["status"], "FAIL")

    def test_gate_only_promotion(self):
        gate_res = SM.gate(pass_inputs())
        auth = SM.authorize_promotion(gate_res, actor="gate")
        self.assertTrue(auth["promotion_authorized"])
        self.assertEqual(auth["authorized_by"], "gate")

    def test_verifier_cannot_promote(self):
        gate_res = SM.gate(pass_inputs())
        # right document, wrong actor
        with self.assertRaises(TT.PromotionError):
            SM.authorize_promotion(gate_res, actor="verifier")
        # right actor claim, wrong document (a verifier report)
        forged = {"check": "independent_verifier", "status": "PASS",
                  "detail": {"issued_by": "verifier"}}
        with self.assertRaises(TT.PromotionError):
            SM.authorize_promotion(forged, actor="gate")

    def test_failed_gate_cannot_authorize(self):
        inputs = pass_inputs()
        inputs["refinement"] = {"status": "FAIL"}
        gate_res = SM.gate(inputs)
        with self.assertRaises(TT.PromotionError):
            SM.authorize_promotion(gate_res, actor="gate")

    def test_model_document_cannot_impersonate_gate(self):
        # a document claiming check=gate but not issued by the gate
        forged = {"check": "gate", "status": "PASS",
                  "detail": {"issued_by": "model"}}
        with self.assertRaises(TT.PromotionError):
            SM.authorize_promotion(forged, actor="gate")


if __name__ == "__main__":
    unittest.main()
