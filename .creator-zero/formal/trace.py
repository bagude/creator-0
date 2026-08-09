"""RuntimeLedger -> Trace parser for the normalized formal event schema.

Every observed governed action must carry: label, actor, and (where
applicable) source/target and artifact/evidence pointers. Unknown or
malformed governed events are never silently ignored: parsing returns a
formal parse error or records an explicit unmapped-event entry.

Timestamps are evidentiary metadata only; causal ordering is trace position.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any

from .labels import ALL_LABELS
from .model import RuntimeEvent, Trace


class TraceParseError(ValueError):
    """The ledger cannot be parsed into a governed transition structure."""


REQUIRED_KEYS = ("label", "actor")


def parse_event(obj: dict[str, Any], index: int) -> RuntimeEvent:
    if not isinstance(obj, dict):
        raise TraceParseError(f"event {index}: not an object")
    missing = [k for k in REQUIRED_KEYS if k not in obj]
    if missing:
        raise TraceParseError(f"event {index}: missing keys {missing}")
    label = obj["label"]
    if label not in ALL_LABELS:
        raise TraceParseError(f"event {index}: unmapped label {label!r}")
    md = obj.get("metadata", {})
    if not isinstance(md, dict):
        raise TraceParseError(f"event {index}: metadata must be an object")
    return RuntimeEvent(
        event_id=str(obj.get("event_id", f"e{index}")),
        label=label,
        actor=str(obj["actor"]),
        source=str(obj.get("source", "")),
        target=str(obj.get("target", "")),
        timestamp=str(obj.get("timestamp", "")),
        artifact_refs=tuple(obj.get("artifact_refs", []) or []),
        contract_id=str(obj.get("contract_id", "")),
        metadata=tuple(sorted(md.items())),
    )


def parse_runtime_ledger(path: str | Path, strict: bool = True) -> Trace:
    """Parse a JSONL ledger of normalized formal events into a Trace.

    strict=True: any malformed/unmapped line raises TraceParseError.
    strict=False: malformed/unmapped lines are collected in
    trace.unmapped_events (explicit unmapped-event result, never silent).
    """
    p = Path(path)
    if not p.exists():
        raise TraceParseError(f"ledger not found: {p}")
    events: list[RuntimeEvent] = []
    unmapped: list[dict[str, Any]] = []
    for i, line in enumerate(p.read_text(encoding="utf-8").splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as e:
            if strict:
                raise TraceParseError(f"event {i}: invalid JSON: {e}")
            unmapped.append({"index": i, "raw": line, "reason": f"invalid JSON: {e}"})
            continue
        try:
            events.append(parse_event(obj, i))
        except TraceParseError as e:
            if strict:
                raise
            unmapped.append({"index": i, "raw": obj, "reason": str(e)})
    return Trace(events=events, origin=str(p), unmapped_events=unmapped)
