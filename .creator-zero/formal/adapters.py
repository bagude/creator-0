"""Fixture adapters: historical experiment ledgers -> normalized formal events.

Historical experiment artifacts (Experiments 1-4B) are immutable evidence.
These adapters read them without modification and emit normalized events plus
an explicit mapping record so no historical evidence is silently reinterpreted.
Raw events with no deterministic mapping are returned as unmapped, never
dropped.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any

from .labels import Label, primitive_label
from .model import RuntimeEvent, Trace
from .semantics import CREATOR_ACTOR, GATE_ACTOR, node_actor

VALIDATOR_ACTOR = "validator"


def _node_labels(spec: dict[str, Any]) -> dict[str, str]:
    return {n["id"]: primitive_label(n["primitive"]).value for n in spec["nodes"]}


def _ev(i: int, label: str, actor: str, raw_event: str, ts: str = "",
        target: str = "", completes: str = "", **meta) -> RuntimeEvent:
    md: dict[str, Any] = {"raw_event": raw_event, **meta}
    if completes:
        md["completes_node"] = completes
    return RuntimeEvent(
        event_id=f"adapted-{i}", label=label, actor=actor, target=target,
        timestamp=ts, metadata=tuple(sorted(md.items())))


def adapt_experiment3_ledger(ledger_path: str | Path,
                             spec: dict[str, Any]) -> tuple[Trace, list[dict]]:
    """Adapt .creator-zero/experiment-3/execution-ledger.jsonl.

    Mapping (recorded per event):
      decomposer_round_*_complete -> propose (actor decomposer)
      composer_round_*_complete   -> propose (actor composer)
      decomposer_round_*_critique -> consult (actor decomposer)
      synthesis_closure           -> tau (internal synthesis bookkeeping)
      node_complete               -> node execution label from spec primitive,
                                     actor node:<id>, metadata.completes_node
      gate_decision(promoted)     -> promote (actor gate)
    """
    labels = _node_labels(spec)
    events: list[RuntimeEvent] = []
    mapping: list[dict] = []
    unmapped: list[dict] = []
    raw_lines = Path(ledger_path).read_text(encoding="utf-8").splitlines()
    for i, line in enumerate(raw_lines):
        if not line.strip():
            continue
        raw = json.loads(line)
        kind = raw.get("event", "")
        ts = str(raw.get("ts", ""))
        if kind.startswith("decomposer_round") and kind.endswith("_complete"):
            e = _ev(i, Label.PROPOSE.value, "decomposer", kind, ts)
        elif kind.startswith("composer_round") and kind.endswith("_complete"):
            e = _ev(i, Label.PROPOSE.value, "composer", kind, ts)
        elif kind.startswith("decomposer_round") and kind.endswith("_critique"):
            e = _ev(i, Label.CONSULT.value, "decomposer", kind, ts)
        elif kind == "synthesis_closure":
            e = _ev(i, Label.TAU.value, CREATOR_ACTOR, kind, ts)
        elif kind == "node_complete":
            nid = raw.get("node", "")
            if nid not in labels:
                unmapped.append({"index": i, "raw": raw,
                                 "reason": f"node {nid!r} not in spec"})
                continue
            e = _ev(i, labels[nid], node_actor(nid), kind, ts, completes=nid)
        elif kind == "gate_decision" and raw.get("promoted"):
            e = _ev(i, Label.PROMOTE.value, GATE_ACTOR, kind, ts)
        else:
            unmapped.append({"index": i, "raw": raw,
                             "reason": f"no deterministic mapping for event {kind!r}"})
            continue
        events.append(e)
        mapping.append({"index": i, "raw_event": kind,
                        "mapped_label": e.label, "actor": e.actor})
    trace = Trace(events=events, origin=str(ledger_path), unmapped_events=unmapped)
    return trace, mapping


# Experiment 4 C1: deterministic per-event-kind mapping. Session/phase/anomaly
# bookkeeping is hidden as tau; model synthesis calls are consult/propose;
# boundary validation is validate; node_end is the node execution; the C2
# instantiation is create; the continuation is reconstruct; C2's incorporated
# result is return. c1_complete fans out into the report node's return plus
# the governed complete transition (recorded in the mapping).
_E4C1_TAU_KINDS = {"phase_transition", "anomaly", "node_start", "c1_pending_on_c2"}
_E4C1_ROLE_ACTORS = {"decomposer": "decomposer", "composer": "composer",
                     "decomposer_critique": "decomposer"}


def adapt_experiment4_c1_ledger(ledger_path: str | Path, spec: dict[str, Any],
                                report_node: str = "report"
                                ) -> tuple[Trace, list[dict]]:
    labels = _node_labels(spec)
    events: list[RuntimeEvent] = []
    mapping: list[dict] = []
    unmapped: list[dict] = []
    raw_lines = Path(ledger_path).read_text(encoding="utf-8").splitlines()
    for i, line in enumerate(raw_lines):
        if not line.strip():
            continue
        raw = json.loads(line)
        kind = raw.get("event", "")
        ts = str(raw.get("ts", ""))
        out: list[RuntimeEvent] = []
        if kind in _E4C1_TAU_KINDS:
            out = [_ev(i, Label.TAU.value, CREATOR_ACTOR, kind, ts)]
        elif kind == "c1_session_start":
            out = [_ev(i, Label.OBSERVE.value, CREATOR_ACTOR, kind, ts)]
        elif kind == "model_invocation_start":
            if raw.get("role") == "c2_instantiation":
                out = [_ev(i, Label.CREATE.value, CREATOR_ACTOR, kind, ts,
                           target="C2")]
            else:
                out = [_ev(i, Label.CONSULT.value, CREATOR_ACTOR, kind, ts)]
        elif kind == "model_invocation_end":
            actor = _E4C1_ROLE_ACTORS.get(raw.get("role", ""), CREATOR_ACTOR)
            out = [_ev(i, Label.PROPOSE.value, actor, kind, ts)]
        elif kind == "boundary_validation":
            lab = (Label.VALIDATE if raw.get("verdict") == "VALID"
                   else Label.REJECT).value
            out = [_ev(i, lab, VALIDATOR_ACTOR, kind, ts)]
        elif kind == "node_end":
            nid = raw.get("node", "")
            if nid not in labels:
                unmapped.append({"index": i, "raw": raw,
                                 "reason": f"node {nid!r} not in spec"})
                continue
            out = [_ev(i, labels[nid], node_actor(nid), kind, ts, completes=nid)]
        elif kind == "c1_continuation_start":
            out = [_ev(i, Label.RECONSTRUCT.value, CREATOR_ACTOR, kind, ts)]
        elif kind == "c2_result_incorporated":
            out = [_ev(i, Label.RETURN.value, CREATOR_ACTOR, kind, ts,
                       target="C1")]
        elif kind == "c1_complete":
            out = [_ev(i, labels.get(report_node, Label.RETURN.value),
                       node_actor(report_node), kind, ts, completes=report_node,
                       fanout="1/2"),
                   _ev(i, Label.COMPLETE.value, CREATOR_ACTOR, kind, ts,
                       fanout="2/2")]
        else:
            unmapped.append({"index": i, "raw": raw,
                             "reason": f"no deterministic mapping for event {kind!r}"})
            continue
        for e in out:
            events.append(e)
            mapping.append({"index": i, "raw_event": kind,
                            "mapped_label": e.label, "actor": e.actor})
    trace = Trace(events=events, origin=str(ledger_path), unmapped_events=unmapped)
    return trace, mapping


def truncate_at_raw_event(trace: Trace, raw_event: str) -> Trace:
    """Prefix of the trace up to and including the first event adapted from
    the named raw ledger event (e.g. the process-level premature-exit point)."""
    cut = None
    for idx, e in enumerate(trace.events):
        if e.meta().get("raw_event") == raw_event:
            cut = idx
            break
    if cut is None:
        raise ValueError(f"raw event {raw_event!r} not present in trace")
    return Trace(events=trace.events[:cut + 1],
                 origin=trace.origin + f" [truncated at {raw_event}]",
                 unmapped_events=list(trace.unmapped_events))
