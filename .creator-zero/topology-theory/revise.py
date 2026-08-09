"""Reverse-ITP principle revision: evidence -> candidate theory change.

    propose_revision(theory, evidence_events) -> Revision

Deterministic proposal rules over the append-only evidence log (candidate
principle *wording* may be model-mediated, but it enters only as serialized
candidate_principles content inside the returned CANDIDATE revision):

    FALSIFY evidence, no SUPPORT          -> DEPRECATE the principle
    FALSIFY and SUPPORT evidence mixed    -> SPECIALIZE (narrow preconditions
                                             to the supported context)
    CHALLENGE evidence only               -> SPECIALIZE
    SUPPORT for a RETIRED principle       -> REINSTATE

Promotion is not part of this function: the returned Revision is always
status=CANDIDATE, and TheoryStore.promote refuses anything that is not a
Gate-issued PASS. A model cannot self-promote a theory change.
"""
from __future__ import annotations
from typing import Any, Optional

from .model import (PrincipleEvidence, Revision, TheoryVersion)


def _collect(evidence_events: list[PrincipleEvidence] | list[dict[str, Any]]
             ) -> dict[str, dict[str, list[str]]]:
    by: dict[str, dict[str, list[str]]] = {}
    for e in evidence_events:
        d = e.to_dict() if isinstance(e, PrincipleEvidence) else dict(e)
        slot = by.setdefault(d["principle_id"],
                             {"SUPPORT": [], "CHALLENGE": [], "FALSIFY": []})
        slot[d["effect"]].append(d.get("event_id") or d["prediction_id"])
    return by


def propose_revision(theory: TheoryVersion,
                     evidence_events: list[Any],
                     revision_id: Optional[str] = None,
                     ) -> Optional[Revision]:
    """Propose at most one revision from the strongest evidence signal.

    Returns None when the evidence motivates no change (all SUPPORT)."""
    by = _collect(evidence_events)
    principle_ids = {p["id"] for p in theory.principles}

    # strongest signal first: falsified-without-support, then challenged
    deprecate, specialize, reinstate = [], [], []
    for pid in sorted(by):
        if pid not in principle_ids:
            continue
        eff = by[pid]
        p = theory.principle(pid)
        if p is not None and p.status == "RETIRED" and eff["SUPPORT"]:
            reinstate.append(pid)
        elif eff["FALSIFY"] and not eff["SUPPORT"]:
            deprecate.append(pid)
        elif eff["FALSIFY"] or eff["CHALLENGE"]:
            specialize.append(pid)

    if deprecate:
        pid = deprecate[0]
        eff = by[pid]
        return Revision(
            revision_id=revision_id or f"rev-deprecate-{pid.lower()}",
            type="DEPRECATE",
            parents=[pid],
            candidate_principles=[],
            motivating_evidence=sorted(eff["FALSIFY"]),
            historical_cases_affected=[],
            changed_predictions=[],
            status="CANDIDATE")
    if specialize:
        pid = specialize[0]
        eff = by[pid]
        parent = theory.principle(pid)
        narrowed = dict(parent.to_dict()) if parent else {"id": pid}
        narrowed.update({
            "id": f"{pid}-SPECIALIZED",
            "status": "CANDIDATE",
            "parent_principles": [pid],
            "version": 1,
            "statement": (parent.statement if parent else "") +
                         " [SPECIALIZED: preconditions narrowed to the "
                         "contexts in which the principle's predictions "
                         "held; see motivating evidence]",
        })
        return Revision(
            revision_id=revision_id or f"rev-specialize-{pid.lower()}",
            type="SPECIALIZE",
            parents=[pid],
            candidate_principles=[narrowed],
            motivating_evidence=sorted(eff["FALSIFY"] + eff["CHALLENGE"]),
            historical_cases_affected=[],
            changed_predictions=[],
            status="CANDIDATE")
    if reinstate:
        pid = reinstate[0]
        return Revision(
            revision_id=revision_id or f"rev-reinstate-{pid.lower()}",
            type="REINSTATE",
            parents=[pid],
            candidate_principles=[],
            motivating_evidence=sorted(by[pid]["SUPPORT"]),
            historical_cases_affected=[],
            changed_predictions=[],
            status="CANDIDATE")
    return None


def apply_revision(theory: TheoryVersion, revision: Revision,
                   predecessor_hash: str) -> TheoryVersion:
    """Build the CANDIDATE successor theory version for a revision.

    This constructs a document only. It performs no store writes and no
    promotion; the result must pass historical replay, independent
    verification, and the Gate before TheoryStore.promote persists it."""
    principles = [dict(p) for p in theory.principles]
    by_id = {p["id"]: p for p in principles}
    if revision.type == "DEPRECATE":
        for pid in revision.parents:
            if pid in by_id:
                by_id[pid]["status"] = "RETIRED"
    elif revision.type == "REINSTATE":
        for pid in revision.parents:
            if pid in by_id:
                by_id[pid]["status"] = "SUPPORTED"
    elif revision.type in ("SPECIALIZE", "GENERALIZE", "SPLIT", "MERGE"):
        for pid in revision.parents:
            if pid in by_id:
                by_id[pid]["status"] = "REVISED"
        principles.extend(dict(cp) for cp in revision.candidate_principles)
    elif revision.type == "ADD":
        principles.extend(dict(cp) for cp in revision.candidate_principles)
    return TheoryVersion(
        version=theory.version + 1,
        principles=principles,
        revision_graph=list(theory.revision_graph) + [revision.to_dict()],
        evidence_log_length=theory.evidence_log_length,
        predecessor_hash=predecessor_hash,
        provenance={"revised_from": theory.version,
                    "revision_id": revision.revision_id},
        status="CANDIDATE")
