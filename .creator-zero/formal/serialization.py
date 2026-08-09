"""Deterministic JSON serialization for formal objects.

All emitted JSON is canonical: sorted keys, sorted state/transition lists,
newline-terminated. Byte-identical output for identical inputs.
"""
from __future__ import annotations
import json
from typing import Any

from .model import LTS, Transition, FormalResult


def canonical_dumps(obj: Any) -> str:
    return json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def lts_to_dict(lts: LTS) -> dict[str, Any]:
    return {
        "formal_object": "lts",
        "version": "0.1",
        "initial": lts.initial,
        "states": sorted(lts.states),
        "labels": sorted(lts.labels),
        "transitions": [t.to_dict() for t in sorted(lts.transitions)],
        "metadata": lts.metadata,
    }


def lts_to_json(lts: LTS) -> str:
    return canonical_dumps(lts_to_dict(lts))


def lts_from_dict(d: dict[str, Any]) -> LTS:
    required = {"initial", "states", "transitions"}
    missing = required - set(d)
    if missing:
        raise ValueError(f"LTS document missing keys: {sorted(missing)}")
    transitions = frozenset(
        Transition(source=t["source"], label=t["label"], target=t["target"],
                   actor=t.get("actor", "*"))
        for t in d["transitions"])
    states = frozenset(d["states"])
    labels = frozenset(d.get("labels") or sorted({t.label for t in transitions}) or ["tau"])
    return LTS(states=states, labels=labels, transitions=transitions,
               initial=d["initial"], metadata=d.get("metadata", {}))


def lts_from_json(text: str) -> LTS:
    return lts_from_dict(json.loads(text))


def result_to_json(result: FormalResult) -> str:
    return canonical_dumps(result.to_dict())
