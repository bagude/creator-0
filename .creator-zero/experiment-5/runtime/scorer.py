"""Deterministic decision scoring for Experiment 5.

Ground truth comes from preregistration (private labels), never from
retrospective reinterpretation:

    ground truth CREATE       (child useful)      + CREATE        = TP
    ground truth CREATE       (child useful)      + DO_NOT_CREATE = FN
    ground truth DO_NOT_CREATE (child unnecessary) + CREATE        = FP
    ground truth DO_NOT_CREATE (child unnecessary) + DO_NOT_CREATE = TN

Zero denominators are reported explicitly as None with a note, never as 0
or 1. A topology decision with a formal-governance violation is not a valid
success regardless of its classification.
"""
from __future__ import annotations
from typing import Any, Optional

CLASSES = {("CREATE", "CREATE"): "TP",
           ("CREATE", "DO_NOT_CREATE"): "FN",
           ("DO_NOT_CREATE", "CREATE"): "FP",
           ("DO_NOT_CREATE", "DO_NOT_CREATE"): "TN"}


def classify(ground_truth: str, decision: str) -> str:
    key = (ground_truth, decision)
    if key not in CLASSES:
        raise ValueError(f"unknown ground_truth/decision pair: {key}")
    return CLASSES[key]


def _ratio(num: int, den: int) -> Optional[float]:
    return None if den == 0 else num / den


def aggregate(classifications: list[str]) -> dict[str, Any]:
    counts = {c: classifications.count(c) for c in ("TP", "TN", "FP", "FN")}
    unknown = [c for c in classifications if c not in counts]
    if unknown:
        raise ValueError(f"unknown classifications: {unknown}")
    n = len(classifications)
    tp, tn, fp, fn = (counts[c] for c in ("TP", "TN", "FP", "FN"))
    out: dict[str, Any] = {
        "n": n, "tp": tp, "tn": tn, "fp": fp, "fn": fn,
        "accuracy": _ratio(tp + tn, n),
        "precision_create": _ratio(tp, tp + fp),
        "recall_create": _ratio(tp, tp + fn),
        "specificity_do_not_create": _ratio(tn, tn + fp),
        "false_positive_rate_create": _ratio(fp, fp + tn),
        "false_negative_rate_create": _ratio(fn, fn + tp),
    }
    notes = [k for k, v in out.items()
             if v is None and k not in ("n", "tp", "tn", "fp", "fn")]
    if notes:
        out["zero_denominator_metrics"] = notes
    return out


CHILD_USEFUL_KEYS = ("child_useful", "assigned_distinctions",
                     "new_evidence_ids", "duplicate_of_parent_evidence",
                     "affected_final_resolution", "affected_verification")


def child_usefulness(*, assigned_distinctions: list[str],
                     new_evidence_ids: list[str],
                     duplicate_of_parent_evidence: bool,
                     affected_final_resolution: bool,
                     affected_verification: bool) -> dict[str, Any]:
    """ChildUseful = evidence tied to a preregistered unresolved distinction
    AND not already present locally AND affecting verification, resolution,
    or confidence. Existence of output alone is never usefulness."""
    useful = (bool(assigned_distinctions)
              and bool(new_evidence_ids)
              and not duplicate_of_parent_evidence
              and (affected_final_resolution or affected_verification))
    return {
        "child_useful": useful,
        "assigned_distinctions": list(assigned_distinctions),
        "new_evidence_ids": list(new_evidence_ids),
        "duplicate_of_parent_evidence": bool(duplicate_of_parent_evidence),
        "affected_final_resolution": bool(affected_final_resolution),
        "affected_verification": bool(affected_verification),
    }


def trial_result(*, trial_id: str, ground_truth: str, decision: str,
                 child_launched: bool, child_useful: Optional[bool],
                 task_verified: bool,
                 formal: dict[str, str]) -> dict[str, Any]:
    """Canonical per-trial result record. `formal` maps check name ->
    PASS/FAIL/INDETERMINATE/N/A."""
    cls = classify(ground_truth, decision)
    governance_ok = all(v in ("PASS", "N/A") for v in formal.values())
    rec = {
        "trial_id": trial_id,
        "ground_truth": ground_truth,
        "decision": decision,
        "classification": cls,
        "child_launched": child_launched,
        "child_useful": child_useful,
        "task_verified": task_verified,
        "formal": dict(formal),
        "formal_governance_ok": governance_ok,
    }
    if cls == "TP" and child_useful is False:
        rec["special_classification"] = \
            "CREATE_DECISION_CORRECT_BUT_CHILD_NONCONTRIBUTORY"
    return rec
