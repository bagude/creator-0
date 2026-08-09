"""Post-execution evaluation: mechanical comparison of frozen predictions
against the observed runtime record.

    evaluate_topology(predictions, runtime, evidence) -> TopologyEvaluation

`runtime` is the typed execution record:
    {"topology_id": ..., "predictions_hash": ...,
     "resolved_distinctions": [{"id": "Q1", "resolved_by": "node", ...}],
     "unresolved_distinctions": ["Q2", ...],
     "node_completion_order": ["observe-evidence", ...],
     "resource_use": {"model_calls": 1, "child_calls": 0, ...},
     "formal_failures": ["FRESHNESS_FAIL", ...],
     "authority_violations": [...],
     "verification_effect": "verified|failed|impossible",
     "task_result": "correct|incorrect|unverified",
     "child_launches": 0}

`evidence` is a list of typed evidence records:
    {"id": "...", "source_node": "...", "duplicate_of_parent": false}

Prediction outcomes are decided mechanically per prediction kind; prose-only
predictions (kind == "") are INDETERMINATE — never silently HELD. The frozen
predictions_hash must match the runtime's recorded hash; retrospective
prediction edits raise PredictionIntegrityError.
"""
from __future__ import annotations
from typing import Any, Optional

from .model import Prediction, TopologyEvaluation
from .predict import predictions_hash
from .utility import calibration_error, load_utility_config, observed_utility

HELD, FAILED, INDET = "HELD", "FAILED", "INDETERMINATE"


class PredictionIntegrityError(RuntimeError):
    """The frozen predictions were edited after freezing."""


def _outcome(p: Prediction, runtime: dict[str, Any],
             evidence: list[dict[str, Any]]) -> tuple[str, str]:
    resolved = {r["id"]: r for r in runtime.get("resolved_distinctions", [])}
    unresolved = set(runtime.get("unresolved_distinctions", []))
    kind = p.kind
    if kind == "resolves":
        q = p.subject.get("distinction_id")
        node = p.subject.get("node")
        if q in resolved:
            by = resolved[q].get("resolved_by", "")
            if by == node:
                return HELD, f"{q} resolved by predicted node {node}"
            return FAILED, (f"{q} resolved by {by!r}, not predicted "
                            f"node {node!r}")
        if q in unresolved:
            return FAILED, f"{q} remained unresolved"
        return INDET, f"no record for distinction {q}"
    if kind == "runtime_path":
        order = runtime.get("node_completion_order")
        if order is None:
            return INDET, "no node completion order recorded"
        expected = p.subject.get("expected_order", [])
        realized = [n for n in expected if n in order]
        if [n for n in order if n in set(expected)] == realized \
                and "REFINEMENT_VIOLATION" not in runtime.get(
                    "formal_failures", []):
            return HELD, "completion order consistent with declared causal order"
        return FAILED, "completion order violates the declared causal order"
    if kind == "model_call_budget":
        calls = runtime.get("resource_use", {}).get("model_calls")
        if calls is None:
            return INDET, "model calls not recorded"
        mx = int(p.subject.get("max", 0))
        return (HELD, f"{calls} <= {mx}") if int(calls) <= mx else \
               (FAILED, f"{calls} > {mx}")
    if kind == "child_call_budget":
        calls = runtime.get("resource_use", {}).get("child_calls")
        if calls is None:
            return INDET, "child calls not recorded"
        mx = int(p.subject.get("max", 0))
        return (HELD, f"{calls} <= {mx}") if int(calls) <= mx else \
               (FAILED, f"{calls} > {mx}")
    if kind == "authority_envelope":
        if runtime.get("authority_violations") or any(
                "ATTENUATION" in f or "REFINEMENT" in f
                for f in runtime.get("formal_failures", [])):
            return FAILED, "authority/refinement/attenuation failure observed"
        return HELD, "no authority violation observed"
    if kind == "novel_evidence":
        child_ev = [e for e in evidence
                    if e.get("source_node") in ("child-return", "create-child",
                                                "child")]
        if not child_ev:
            return (INDET, "no child evidence recorded") \
                if runtime.get("child_launches", 0) == 0 else \
                (FAILED, "child launched but returned no evidence")
        novel = [e for e in child_ev if not e.get("duplicate_of_parent")]
        if novel:
            return HELD, f"{len(novel)} novel child evidence record(s)"
        return FAILED, "every child evidence record duplicates parent evidence"
    if kind == "no_duplicate_evidence":
        dups = [e for e in evidence if e.get("duplicate_of_parent")]
        return (HELD, "no duplicate evidence") if not dups else \
               (FAILED, f"{len(dups)} duplicate evidence record(s)")
    if kind == "verification_effect":
        fails = [f for f in runtime.get("formal_failures", [])
                 if any(c.upper() in f.upper()
                        for c in p.subject.get("checks", []))]
        if fails:
            return FAILED, f"verification failures: {fails}"
        eff = runtime.get("verification_effect")
        if eff is None:
            return INDET, "verification effect not recorded"
        return HELD, f"verification effect: {eff}"
    if kind == "cost_bound":
        cost = runtime.get("resource_use", {}).get("normalized_cost")
        if cost is None:
            return INDET, "cost not recorded"
        mx = float(p.subject.get("max", 1.0))
        return (HELD, f"{cost} <= {mx}") if float(cost) <= mx else \
               (FAILED, f"{cost} > {mx}")
    if kind == "local_sufficiency":
        if runtime.get("child_launches", 0):
            return FAILED, "a descendant was launched"
        eff = runtime.get("verification_effect")
        if eff == "impossible":
            return FAILED, "verification impossible from local evidence"
        if eff is None:
            return INDET, "verification effect not recorded"
        return HELD, "resolved and verified with zero descendants"
    return INDET, f"prose-only prediction (kind={kind!r}) is not mechanically decidable"


def evaluate_topology(predictions: list[Prediction] | list[dict[str, Any]],
                      runtime: dict[str, Any],
                      evidence: Optional[list[dict[str, Any]]] = None,
                      config: Optional[dict[str, float]] = None,
                      predicted_value: Optional[dict[str, Any]] = None,
                      ) -> TopologyEvaluation:
    evidence = evidence or []
    preds = [p if isinstance(p, Prediction) else Prediction.from_dict(p)
             for p in predictions]
    if not preds:
        raise PredictionIntegrityError("no predictions to evaluate")
    tid = preds[0].topology_id

    # frozen-hash integrity: retrospective edits are inadmissible
    recorded = runtime.get("predictions_hash", "")
    if recorded:
        actual = predictions_hash(tid, [p.to_dict() for p in preds])
        if actual != recorded:
            raise PredictionIntegrityError(
                f"predictions hash mismatch for {tid}: frozen {recorded} != "
                f"recomputed {actual} (retrospective edit detected)")

    outcomes = []
    for p in preds:
        outcome, why = _outcome(p, runtime, evidence)
        outcomes.append({"prediction_id": p.prediction_id, "kind": p.kind,
                         "outcome": outcome, "why": why,
                         "weight": p.weight,
                         "principles": list(p.principles)})

    resolved = [r["id"] for r in runtime.get("resolved_distinctions", [])]
    unresolved = list(runtime.get("unresolved_distinctions", []))
    novel = sorted(e["id"] for e in evidence
                   if not e.get("duplicate_of_parent"))
    dup = sorted(e["id"] for e in evidence if e.get("duplicate_of_parent"))

    # observed value components, normalized [0,1]
    total_q = len(resolved) + len(unresolved)
    delta_e = 0.0
    if total_q:
        delta_e = len(resolved) / total_q
    if evidence:
        delta_e = round(min(1.0, 0.5 * delta_e +
                            0.5 * (len(novel) / len(evidence))), 4)
    else:
        delta_e = round(delta_e, 4)
    ru = runtime.get("resource_use", {})
    budget = max(1, int(ru.get("model_call_budget",
                               ru.get("model_calls", 1) or 1)))
    cost = round(min(1.0, (int(ru.get("model_calls", 0))
                           + int(ru.get("child_calls", 0))) / (budget + 1)), 4)
    redundancy = round(len(dup) / len(evidence), 4) if evidence else 0.0
    governance = round(min(1.0, 0.25 * len(
        runtime.get("formal_failures", []))), 4)
    observed_value = {"delta_e": delta_e, "cost": cost,
                      "redundancy": redundancy, "governance_risk": governance}

    cfg = config or load_utility_config()
    obs_u = observed_utility(observed_value, cfg)
    calib = (calibration_error(predicted_value, observed_value, cfg)
             if predicted_value else {})

    return TopologyEvaluation(
        topology_id=tid,
        resolved_distinctions=resolved,
        unresolved_distinctions=unresolved,
        novel_evidence=novel,
        duplicate_evidence=dup,
        verification_effect=str(runtime.get("verification_effect", "")),
        task_result=str(runtime.get("task_result", "")),
        resource_use=dict(ru),
        formal_failures=list(runtime.get("formal_failures", [])),
        prediction_outcomes=outcomes,
        observed_value=observed_value,
        observed_utility=obs_u,
        calibration_error=calib,
    )
