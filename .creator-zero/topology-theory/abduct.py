"""Abduction: task + unresolved distinctions -> applicable principles.

    abduce(task, distinctions, evidence, contract, theory) -> ApplicabilityResult

Distinctions are typed records:
    {"id": "Q1", "question": "...", "features": {"locally_resolvable": true,
     "requires_isolation": false, "contamination": false,
     "capability_bearing_artifact": false, "spans_sessions": false, ...}}

Deterministic core: a principle applies to a distinction iff one of its
`feature:<name>` preconditions matches a true feature; `always` principles
apply to the whole task; `topology:*` preconditions are structural and bind
at generation time, so they are reported as applicable-if-structural.

Model-mediated applicability is allowed only through `model_applicability`
— a pre-serialized document {"principle_id": [distinction ids...]}. Its
entries are merged with source="model", validated against the theory (an
unknown or inactive principle is rejected deterministically), and the whole
result is serialized before candidate generation. Model input can add
applicability hypotheses; it cannot remove deterministic matches or revive
falsified principles.
"""
from __future__ import annotations
from typing import Any, Optional

from .model import ApplicabilityResult, ModelValidationError, TheoryVersion


def _distinction_features(d: dict[str, Any]) -> dict[str, bool]:
    feats = d.get("features", {})
    if not isinstance(feats, dict):
        raise ModelValidationError(
            f"distinction {d.get('id')!r}: features must be an object")
    return {k: bool(v) for k, v in feats.items()}


def abduce(task: dict[str, Any],
           distinctions: list[dict[str, Any]],
           evidence: Optional[list[dict[str, Any]]] = None,
           contract: Optional[dict[str, Any]] = None,
           theory: Optional[TheoryVersion] = None,
           model_applicability: Optional[dict[str, list[str]]] = None,
           ) -> ApplicabilityResult:
    if theory is None:
        raise ModelValidationError("abduce requires a theory version")
    for d in distinctions:
        if "id" not in d:
            raise ModelValidationError("distinction missing id")

    applicable: list[dict[str, Any]] = []
    sources: dict[str, str] = {}
    inapplicable: list[str] = []
    active = {p.id: p for p in theory.active_principles()}

    for pid in sorted(active):
        p = active[pid]
        matched: list[str] = []
        structural: list[str] = []
        for pre in p.preconditions:
            if pre == "always":
                matched.extend(d["id"] for d in distinctions)
            elif pre.startswith("feature:"):
                feat = pre.split(":", 1)[1]
                matched.extend(d["id"] for d in distinctions
                               if _distinction_features(d).get(feat, False))
            elif pre.startswith("topology:"):
                structural.append(pre.split(":", 1)[1])
        matched = sorted(set(matched))
        if matched or structural:
            applicable.append({
                "principle_id": pid,
                "distinction_ids": matched,
                "structural_preconditions": sorted(set(structural)),
                "predicted_topology_effects": list(
                    p.predicted_topology_effects),
            })
            sources[pid] = "deterministic"
        else:
            inapplicable.append(pid)

    # model-mediated additions: serialized, validated, never authoritative
    if model_applicability:
        known_q = {d["id"] for d in distinctions}
        for pid in sorted(model_applicability):
            qids = model_applicability[pid]
            if pid not in active:
                raise ModelValidationError(
                    f"model applicability names unknown or inactive "
                    f"principle {pid!r}; deterministic rejection")
            bad = sorted(set(qids) - known_q)
            if bad:
                raise ModelValidationError(
                    f"model applicability for {pid} names unknown "
                    f"distinctions {bad}; deterministic rejection")
            existing = next((a for a in applicable
                             if a["principle_id"] == pid), None)
            if existing is None:
                applicable.append({
                    "principle_id": pid,
                    "distinction_ids": sorted(set(qids)),
                    "structural_preconditions": [],
                    "predicted_topology_effects": list(
                        active[pid].predicted_topology_effects),
                })
                sources[pid] = "model"
                if pid in inapplicable:
                    inapplicable.remove(pid)
            else:
                merged = sorted(set(existing["distinction_ids"]) | set(qids))
                if merged != existing["distinction_ids"]:
                    existing["distinction_ids"] = merged
                    sources[pid] = "deterministic+model"

    applicable.sort(key=lambda a: a["principle_id"])
    return ApplicabilityResult(
        task_id=str(task.get("task_id", task.get("id", ""))),
        applicable=applicable,
        inapplicable_principles=sorted(inapplicable),
        theory_version=theory.version,
        sources=sources,
    )
