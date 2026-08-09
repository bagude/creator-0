"""Runtime <= Spec simulation/refinement checking.

Every externally governed runtime transition must be permitted by the declared
HarnessSpec semantics. This checks actual transition behavior against the
compiled LTS, not mere node appearance in the ledger.

Matching is deterministic:
  - tau events are silent and consume no spec transition;
  - an event whose metadata carries completes_node=<id> must match the node
    execution transition for <id> (label + actor + enabledness);
  - any other event must match an enabled transition with the same label whose
    actor pattern admits the event actor; state-moving matches are preferred
    over self-loops, and among moves the lexicographically smallest target is
    taken (spec moves are deterministic per (state,label,actor) by
    construction, so this tie-break is stable).

Failure returns REFINEMENT_VIOLATION with the shortest useful counterexample:
the offending transition, the reconstructed source state, the labels the spec
allows there, and the observable trace prefix that led to it.
"""
from __future__ import annotations
from typing import Any, Optional

from .labels import Label
from .model import FAIL, INDETERMINATE, PASS, FormalResult, LTS, Trace

RELATION = "Runtime <= Spec"


def _prefix(events, upto: int, limit: int = 12) -> list[dict[str, Any]]:
    obs = [e.to_dict() for e in events[:upto] if e.label != Label.TAU.value]
    return obs[-limit:]


def check_refinement(trace: Trace, spec_lts: LTS,
                     require_completion: bool = False) -> FormalResult:
    assumptions = [
        "Causal order is ledger position; timestamps are evidentiary metadata only.",
        "Only explicitly modeled governed events are checked; instrumentation "
        "completeness of the runtime is assumed, not proven.",
    ]
    if trace.unmapped_events:
        return FormalResult(
            check="runtime_refinement", status=INDETERMINATE,
            formal_relation=RELATION,
            counterexample=None,
            evidence=[f"trace origin: {trace.origin}"],
            assumptions=assumptions,
            unmapped_events=list(trace.unmapped_events),
            detail={"reason": "unmapped governed events present; refinement "
                              "cannot be decided over an incomplete mapping"})

    state = spec_lts.initial
    steps: list[dict[str, Any]] = []
    for idx, ev in enumerate(trace.events):
        if ev.label == Label.TAU.value:
            continue
        candidates = spec_lts.enabled(state, ev.label, ev.actor)
        completes = ev.meta().get("completes_node")
        if completes is not None:
            # must be the execution move for that node: a state-changing
            # transition by actor node:<id>
            candidates = [t for t in candidates
                          if t.target != t.source and t.actor == f"node:{completes}"]
        if not candidates:
            return FormalResult(
                check="runtime_refinement", status=FAIL,
                formal_relation=RELATION,
                counterexample={
                    "violation": "REFINEMENT_VIOLATION",
                    "offending_transition": ev.to_dict(),
                    "event_index": idx,
                    "source_state": state,
                    "expected_allowed_labels": spec_lts.allowed_labels(state),
                    "trace_prefix": _prefix(trace.events, idx),
                },
                evidence=[f"trace origin: {trace.origin}"],
                assumptions=assumptions)
        moves = sorted((t for t in candidates if t.target != t.source),
                       key=lambda t: t.target)
        chosen = moves[0] if moves else candidates[0]
        steps.append({"event": ev.event_id, "label": ev.label,
                      "actor": ev.actor, "state": chosen.target})
        state = chosen.target

    if require_completion and "complete=1" not in state:
        return FormalResult(
            check="runtime_refinement", status=INDETERMINATE,
            formal_relation=RELATION,
            counterexample=None,
            evidence=[f"trace origin: {trace.origin}",
                      f"final reconstructed state: {state}"],
            assumptions=assumptions,
            detail={"reason": "trace ends before a governed complete "
                              "transition: premature termination / externalized "
                              "continuation required",
                    "final_state": state})

    return FormalResult(
        check="runtime_refinement", status=PASS,
        formal_relation=RELATION,
        evidence=[f"trace origin: {trace.origin}",
                  f"observable events matched: {len(steps)}",
                  f"final reconstructed state: {state}"],
        assumptions=assumptions,
        detail={"final_state": state, "matched_steps": len(steps)})
