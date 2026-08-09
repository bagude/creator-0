#!/usr/bin/env python3
"""Experiment 4B deterministic regression for the corrected Creator-Closure
predicate hat_kappa (gate.py: attested_creator_closure).

Governance regression only — deliberately OUTSIDE the canonical tests/ solver
suite (Ctrl(4B -> tests/) = 0). No C3 realization occurs in any case: the
predicate evaluates contract dicts; nothing is launched.

Run: python3 -m unittest discover -s .creator-zero/experiment-4/closure-correction
"""
import importlib.util
import json
import unittest
from pathlib import Path

E4 = Path(__file__).resolve().parents[1]

_spec = importlib.util.spec_from_file_location("e4gate", E4 / "gate.py")
gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gate)

K2 = json.loads((E4 / "child-2-contract.json").read_text(encoding="utf-8"))
ATT_STUB = {"exact_creation_command_NOT_EXECUTED":
            "claude -p ... (draft creation command; never executed)"}


def bounded_stop_k3() -> dict:
    """A Creator-capable K3 whose realization is denied only by an explicit
    external architectural stop — the shape the corrected predicate accepts."""
    return {
        "allowed_primitives": ["observe", "test", "verify", "create", "return"],
        "allowed_relations": ["observe", "verify", "create", "return"],
        "allowed_tools": ["Read", "Grep", "Glob", "Bash"],
        "max_children": 0,
        "max_depth": 0,
        "max_model_calls": 2,
        "may_create_creator": True,
        "creator_capability": True,
        "may_realize_creation": False,
        "filesystem_write_scope": [".creator-zero/experiment-4/c3/"],
        "git_authority": "none",
    }


class ClosurePredicateRegression(unittest.TestCase):

    def test_negative_terminal_child_fails(self):
        """Required negative case: creator_capability=false,
        may_create_creator=false must NOT satisfy Creator-Closure attestation,
        even with otherwise valid attenuation and a creation command."""
        k3 = bounded_stop_k3()
        k3["creator_capability"] = False
        k3["may_create_creator"] = False
        ok, clauses = gate.attested_creator_closure(k3, K2, ATT_STUB)
        self.assertFalse(ok)
        self.assertFalse(clauses["creator_capable"])
        self.assertTrue(clauses["attenuated_K3_le_K2"],
                        "must fail on capability alone, not on attenuation")
        self.assertTrue(clauses["creation_mechanism_valid"])
        self.assertTrue(clauses["external_stop_only"])

    def test_positive_bounded_stop_passes(self):
        """Required positive case: creator_capability=true,
        may_create_creator=true, may_realize_creation=false, max_children=0
        with valid attenuation satisfies the bounded predicate."""
        ok, clauses = gate.attested_creator_closure(bounded_stop_k3(), K2, ATT_STUB)
        self.assertTrue(ok, clauses)

    def test_original_experiment4_k3_draft_fails(self):
        """The historical Experiment 4 K3 draft (preserved unmodified) fails
        hat_kappa — the reproduced mismatch this correction exists to fix."""
        att = json.loads((E4 / "c2/creator-capability-attestation.json")
                         .read_text(encoding="utf-8"))
        k3 = gate.extract_k3(att)
        self.assertIs(k3.get("creator_capability"), False)
        self.assertIs(k3.get("may_create_creator"), False)
        ok, clauses = gate.attested_creator_closure(k3, K2, att)
        self.assertFalse(ok)
        self.assertFalse(clauses["creator_capable"])

    def test_corrected_k3_attestation_passes(self):
        """The 4B corrected attestation artifact satisfies hat_kappa."""
        att = json.loads((Path(__file__).parent / "corrected-k3-attestation.json")
                         .read_text(encoding="utf-8"))
        k3 = gate.extract_k3(att)
        ok, clauses = gate.attested_creator_closure(k3, K2, att)
        self.assertTrue(ok, clauses)

    def test_realization_escalation_fails(self):
        """Capability preservation must not smuggle in realization authority:
        may_realize_creation=true breaks the external-stop clause."""
        k3 = bounded_stop_k3()
        k3["may_realize_creation"] = True
        ok, clauses = gate.attested_creator_closure(k3, K2, ATT_STUB)
        self.assertFalse(ok)
        self.assertFalse(clauses["external_stop_only"])

    def test_authority_increase_fails(self):
        """A K3 gaining a tool K2 lacks must fail attenuation."""
        k3 = bounded_stop_k3()
        k3["allowed_tools"] = k3["allowed_tools"] + ["Edit"]
        ok, clauses = gate.attested_creator_closure(k3, K2, ATT_STUB)
        self.assertFalse(ok)
        self.assertFalse(clauses["attenuated_K3_le_K2"])

    def test_missing_creation_mechanism_fails(self):
        """No creation command in the attestation -> mechanism clause fails."""
        ok, clauses = gate.attested_creator_closure(bounded_stop_k3(), K2, {})
        self.assertFalse(ok)
        self.assertFalse(clauses["creation_mechanism_valid"])


if __name__ == "__main__":
    unittest.main()
