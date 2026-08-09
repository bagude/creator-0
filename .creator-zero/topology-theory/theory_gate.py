"""Two-stage theory promotion gating (Experiment 7 semantics).

Stage 1 — evaluation_authorization(): deterministic conjunction that
authorizes a CANDIDATE theory to enter held-out validation. Its result is
deliberately NOT gate-shaped (check='evaluation_authorization',
issued_by='evaluation_authorization'): TheoryStore.promote refuses it, so
authorization can never promote (NC17).

Stage 2 — theory_gate(): the final deterministic theory Gate. It is the
only producer of the {"check":"gate","status":"PASS","detail":
{"issued_by":"gate"}} shape the store demands, and it requires every
stage-1 input PLUS held-out thresholds, paired improvement, governance,
and historical immutability. There is no second promotion API: promotion
still flows only through TheoryStore.promote(candidate, gate_result).
"""
from __future__ import annotations
from typing import Any

from .self_modify import PASS, FAIL, _input_status

REQUIRED_EVAL_INPUTS = (
    "candidate_schema", "evidence_provenance", "historical_replay",
    "protected_laws", "tests_existing", "tests_new", "independent_verifier",
)

REQUIRED_THEORY_GATE_INPUTS = REQUIRED_EVAL_INPUTS + (
    "evaluation_authorization", "heldout_thresholds", "paired_improvement",
    "governance", "historical_immutability",
)


def _conjunction(required: tuple[str, ...], inputs: dict[str, Any]
                 ) -> tuple[str, dict[str, str], list[str]]:
    clauses: dict[str, str] = {}
    for k in required:
        clauses[k] = "MISSING" if k not in inputs else _input_status(
            inputs[k])
    failed = sorted(k for k, v in clauses.items() if v != PASS)
    return (PASS if not failed else FAIL), clauses, failed


def evaluation_authorization(inputs: dict[str, Any]) -> dict[str, Any]:
    status, clauses, failed = _conjunction(REQUIRED_EVAL_INPUTS, inputs)
    return {
        "check": "evaluation_authorization",
        "status": status,
        "formal_relation": "conjunction over stage-1 verification inputs; "
                           "authorizes held-out evaluation only — this "
                           "result cannot promote a theory",
        "counterexample": ({"violation": "EVALUATION_AUTHORIZATION_FAIL",
                            "failed_or_missing_inputs": failed}
                           if failed else None),
        "evidence": [f"{k}: {v}" for k, v in sorted(clauses.items())],
        "detail": {"issued_by": "evaluation_authorization",
                   "clauses": clauses},
    }


def theory_gate(inputs: dict[str, Any]) -> dict[str, Any]:
    """Final deterministic theory Gate. Pure conjunction; no model input."""
    status, clauses, failed = _conjunction(REQUIRED_THEORY_GATE_INPUTS,
                                           inputs)
    return {
        "check": "gate",
        "status": status,
        "formal_relation": "conjunction of stage-1 inputs + held-out "
                           "thresholds + paired improvement + governance + "
                           "historical immutability",
        "counterexample": ({"violation": "THEORY_GATE_FAIL",
                            "failed_or_missing_inputs": failed}
                           if failed else None),
        "evidence": [f"{k}: {v}" for k, v in sorted(clauses.items())],
        "assumptions": [
            "The gate decides only over the serialized verification inputs "
            "listed; it re-checks nothing and re-runs nothing.",
            "Held-out threshold and paired-improvement inputs were computed "
            "by the preregistered deterministic scorers.",
        ],
        "detail": {"issued_by": "gate", "clauses": clauses},
    }
