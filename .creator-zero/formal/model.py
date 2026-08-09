"""Core formal objects: LTS, Transition, RuntimeEvent, Trace, FormalResult.

L = (S, Lambda, ->, s0) over externally reconstructible governed states only.
Hidden chain-of-thought and inaccessible model internals are outside the model.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Iterable, Optional

from .labels import ALL_LABELS, Label

# Actor wildcard: matches any runtime actor. Used only for non-authority labels.
ANY_ACTOR = "*"


@dataclass(frozen=True, order=True)
class Transition:
    source: str
    label: str
    target: str
    actor: str = ANY_ACTOR

    def __post_init__(self):
        if self.label not in ALL_LABELS:
            raise ValueError(f"transition label not in closed alphabet: {self.label!r}")

    def to_dict(self) -> dict[str, str]:
        return {"source": self.source, "label": self.label,
                "target": self.target, "actor": self.actor}


@dataclass
class LTS:
    states: frozenset[str]
    labels: frozenset[str]
    transitions: frozenset[Transition]
    initial: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.initial not in self.states:
            raise ValueError(f"initial state {self.initial!r} not in state set")
        for t in self.transitions:
            if t.source not in self.states or t.target not in self.states:
                raise ValueError(f"transition references unknown state: {t}")
            if t.label not in self.labels:
                raise ValueError(f"transition label outside declared alphabet: {t}")

    def outgoing(self, state: str) -> list[Transition]:
        return sorted(t for t in self.transitions if t.source == state)

    def enabled(self, state: str, label: str, actor: Optional[str] = None) -> list[Transition]:
        """Transitions from `state` with `label` whose actor pattern admits `actor`."""
        out = []
        for t in self.outgoing(state):
            if t.label != label:
                continue
            if actor is None or t.actor == ANY_ACTOR or t.actor == actor:
                out.append(t)
        return out

    def allowed_labels(self, state: str) -> list[str]:
        return sorted({t.label for t in self.transitions if t.source == state})


@dataclass(frozen=True)
class RuntimeEvent:
    """Normalized governed runtime event (formal event schema)."""
    event_id: str
    label: str
    actor: str
    source: str = ""
    target: str = ""
    timestamp: str = ""          # evidentiary metadata; causal order is trace position
    artifact_refs: tuple[str, ...] = ()
    contract_id: str = ""
    metadata: tuple[tuple[str, Any], ...] = ()

    def meta(self) -> dict[str, Any]:
        return dict(self.metadata)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id, "source": self.source, "label": self.label,
            "target": self.target, "actor": self.actor, "timestamp": self.timestamp,
            "artifact_refs": list(self.artifact_refs), "contract_id": self.contract_id,
            "metadata": self.meta(),
        }


@dataclass
class Trace:
    """A sequential runtime transition structure parsed from an execution ledger."""
    events: list[RuntimeEvent]
    origin: str = ""
    unmapped_events: list[dict[str, Any]] = field(default_factory=list)

    def observable(self) -> list[RuntimeEvent]:
        return [e for e in self.events if e.label != Label.TAU.value]


PASS, FAIL, INDETERMINATE = "PASS", "FAIL", "INDETERMINATE"


@dataclass
class FormalResult:
    check: str
    status: str                     # PASS | FAIL | INDETERMINATE
    formal_relation: str
    counterexample: Optional[dict[str, Any]] = None
    evidence: list[Any] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    unmapped_events: list[Any] = field(default_factory=list)
    detail: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.status not in (PASS, FAIL, INDETERMINATE):
            raise ValueError(f"invalid status {self.status!r}")

    def to_dict(self) -> dict[str, Any]:
        d = {
            "check": self.check, "status": self.status,
            "formal_relation": self.formal_relation,
            "counterexample": self.counterexample,
            "evidence": self.evidence, "assumptions": self.assumptions,
            "unmapped_events": self.unmapped_events,
        }
        if self.detail:
            d["detail"] = self.detail
        return d

    @property
    def exit_code(self) -> int:
        return {PASS: 0, FAIL: 2, INDETERMINATE: 3}[self.status]


def make_lts(transitions: Iterable[Transition], initial: str,
             extra_states: Iterable[str] = (), metadata: Optional[dict] = None) -> LTS:
    ts = frozenset(transitions)
    states = set(extra_states) | {initial}
    labels = set()
    for t in ts:
        states.add(t.source); states.add(t.target); labels.add(t.label)
    return LTS(states=frozenset(states), labels=frozenset(labels) or frozenset({Label.TAU.value}),
               transitions=ts, initial=initial, metadata=metadata or {})
