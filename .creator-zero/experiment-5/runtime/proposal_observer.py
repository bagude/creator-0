"""Capability-bearing proposal observability checker (Experiment 5 hardening 1).

Any generated artifact later used as evidence of Creator capability (child
contracts, HarnessSpecs, Creator witnesses, delegation plans, candidate
topologies, topology decisions) must cross an explicit observable `propose`
transition:

    C_n --propose(a)--> S'

A later `return` may transport the artifact, but `return` cannot substitute
for `propose`. The Formal Semantics Kernel already treats `propose` as
observable (it is in OBSERVABLE_LABELS and is never tau), so this check is a
deterministic trace predicate over parsed runtime ledgers — no kernel change
is required or made.

Results:
    PASS          — the artifact appears under an observable `propose` event,
                    and no `return` transports it before its first `propose`.
    FAIL          — CAPABILITY_OBSERVABILITY_FAIL: the artifact appears in
                    the trace only under non-propose labels (e.g. constructed
                    silently and shipped inside `return`), or is transported
                    by `return` before any `propose`.
    INDETERMINATE — the artifact is never referenced anywhere in the trace:
                    there is no observation either way.
"""
from __future__ import annotations
import posixpath
import sys
from pathlib import Path
from typing import Any

_CZROOT = Path(__file__).resolve().parents[2]
if str(_CZROOT) not in sys.path:
    sys.path.insert(0, str(_CZROOT))

from formal.labels import Label
from formal.model import FAIL, INDETERMINATE, PASS, FormalResult, Trace

CHECK = "capability_proposal_observability"
RELATION = "capability artifact in observable propose"
VIOLATION = "CAPABILITY_OBSERVABILITY_FAIL"

_ASSUMPTIONS = [
    "Causal order is ledger position; timestamps are evidentiary metadata only.",
    "An artifact reference matches by exact string or by final path component "
    "(basename); the matching mode used is recorded in evidence.",
    "propose is an observable label in the kernel alphabet (never tau); this "
    "check adds no new label and modifies no kernel semantics.",
    "Instrumentation completeness of the runtime ledger is assumed, not "
    "proven: an unlogged construction cannot be detected here and is governed "
    "by the topology guard and session audit instead.",
]


def _ref_matches(ref: str, artifact_id: str) -> str | None:
    """Deterministic reference match. Returns the mode used or None."""
    if ref == artifact_id:
        return "exact"
    if posixpath.basename(ref.rstrip("/")) == posixpath.basename(
            artifact_id.rstrip("/")) and posixpath.basename(ref.rstrip("/")):
        return "basename"
    return None


def _hits(trace: Trace, artifact_id: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for idx, ev in enumerate(trace.events):
        for ref in ev.artifact_refs:
            mode = _ref_matches(str(ref), artifact_id)
            if mode is not None:
                out.append({"index": idx, "event_id": ev.event_id,
                            "label": ev.label, "actor": ev.actor,
                            "ref": str(ref), "match_mode": mode})
                break
    return out


def check_capability_observability(trace: Trace,
                                   artifact_id: str) -> FormalResult:
    """PASS iff `artifact_id` crosses an observable propose transition
    no later than any return transporting it."""
    hits = _hits(trace, artifact_id)
    evidence = [f"trace origin: {trace.origin}",
                f"artifact_id: {artifact_id}",
                f"reference hits: {len(hits)}"]

    if not hits:
        return FormalResult(
            check=CHECK, status=INDETERMINATE, formal_relation=RELATION,
            evidence=evidence, assumptions=_ASSUMPTIONS,
            detail={"artifact_id": artifact_id,
                    "reason": "artifact never referenced in the trace; no "
                              "observation either way"})

    proposes = [h for h in hits if h["label"] == Label.PROPOSE.value]
    returns = [h for h in hits if h["label"] == Label.RETURN.value]

    if not proposes:
        return FormalResult(
            check=CHECK, status=FAIL, formal_relation=RELATION,
            counterexample={
                "violation": VIOLATION,
                "artifact_id": artifact_id,
                "reason": "artifact appears in the trace but never under an "
                          "observable propose transition; return cannot "
                          "substitute for propose",
                "labels_referencing_artifact": sorted({h["label"] for h in hits}),
                "first_reference": hits[0],
            },
            evidence=evidence, assumptions=_ASSUMPTIONS,
            detail={"artifact_id": artifact_id})

    first_propose = proposes[0]["index"]
    if returns and returns[0]["index"] < first_propose:
        return FormalResult(
            check=CHECK, status=FAIL, formal_relation=RELATION,
            counterexample={
                "violation": VIOLATION,
                "artifact_id": artifact_id,
                "reason": "artifact transported by return before any "
                          "observable propose; capability construction "
                          "escaped observation",
                "first_return": returns[0],
                "first_propose": proposes[0],
            },
            evidence=evidence, assumptions=_ASSUMPTIONS,
            detail={"artifact_id": artifact_id})

    evidence.append(f"first observable propose: event index {first_propose} "
                    f"({proposes[0]['event_id']}, actor {proposes[0]['actor']}, "
                    f"match {proposes[0]['match_mode']})")
    return FormalResult(
        check=CHECK, status=PASS, formal_relation=RELATION,
        evidence=evidence, assumptions=_ASSUMPTIONS,
        detail={"artifact_id": artifact_id,
                "first_propose_index": first_propose,
                "propose_events": proposes,
                "return_events": returns})


def check_all_capability_artifacts(trace: Trace,
                                   artifact_ids: list[str]) -> FormalResult:
    """Aggregate: PASS iff every listed capability-bearing artifact passes.
    Any FAIL dominates; otherwise any INDETERMINATE dominates."""
    per: dict[str, FormalResult] = {
        a: check_capability_observability(trace, a) for a in artifact_ids}
    statuses = {a: r.status for a, r in per.items()}
    if any(s == FAIL for s in statuses.values()):
        agg = FAIL
    elif any(s == INDETERMINATE for s in statuses.values()):
        agg = INDETERMINATE
    else:
        agg = PASS
    failing = {a: per[a].counterexample for a, s in statuses.items()
               if s == FAIL}
    return FormalResult(
        check=CHECK + "_all", status=agg, formal_relation=RELATION,
        counterexample=({"violation": VIOLATION, "artifacts": failing}
                        if failing else None),
        evidence=[f"trace origin: {trace.origin}",
                  f"artifacts checked: {len(artifact_ids)}"],
        assumptions=_ASSUMPTIONS,
        detail={"per_artifact": {a: r.to_dict() for a, r in per.items()}})
