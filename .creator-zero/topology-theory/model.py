"""Typed core objects of the topology theory.

Every object is a plain dataclass with a deterministic dict form; schema
validation is manual and closed (unknown statuses/effects are rejected, never
coerced). JSON Schema documents mirroring these validators live in schemas/.

Statuses:
  Principle:  CANDIDATE SUPPORTED CHALLENGED FALSIFIED REVISED PROMOTED RETIRED
  Hypothesis: CANDIDATE VALIDATED REJECTED EXECUTED EVALUATED
  Revision:   CANDIDATE (proposal-only; promotion happens only via the Gate)
  Falsification (per topology): SUPPORTED PARTIALLY_SUPPORTED FALSIFIED
                                INDETERMINATE
  Replay case: COMPATIBLE CONTRADICTED INDETERMINATE
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any, Optional

PRINCIPLE_STATUSES = frozenset({
    "CANDIDATE", "SUPPORTED", "CHALLENGED", "FALSIFIED", "REVISED",
    "PROMOTED", "RETIRED"})
# statuses under which a principle still bears on abduction/replay
ACTIVE_PRINCIPLE_STATUSES = frozenset({
    "CANDIDATE", "SUPPORTED", "CHALLENGED", "REVISED", "PROMOTED"})

HYPOTHESIS_STATUSES = frozenset({
    "CANDIDATE", "VALIDATED", "REJECTED", "EXECUTED", "EVALUATED"})

REVISION_TYPES = frozenset({
    "ADD", "SPECIALIZE", "GENERALIZE", "MERGE", "SPLIT", "DEPRECATE",
    "REINSTATE"})

EVIDENCE_EFFECTS = frozenset({"SUPPORT", "CHALLENGE", "FALSIFY"})

FALSIFICATION_STATUSES = frozenset({
    "SUPPORTED", "PARTIALLY_SUPPORTED", "FALSIFIED", "INDETERMINATE"})

PREDICTION_OUTCOMES = frozenset({"HELD", "FAILED", "INDETERMINATE"})

REPLAY_CASE_RESULTS = frozenset({"COMPATIBLE", "CONTRADICTED", "INDETERMINATE"})

# machine-checkable prediction kinds (mechanical comparison in evaluate.py)
PREDICTION_KINDS = frozenset({
    "resolves", "resolver_node", "novel_evidence", "no_duplicate_evidence",
    "runtime_path", "model_call_budget", "child_call_budget",
    "authority_envelope", "verification_effect", "cost_bound",
    "local_sufficiency"})


class ModelValidationError(ValueError):
    """A typed theory object violates its closed schema."""


def _require(cond: bool, msg: str) -> None:
    if not cond:
        raise ModelValidationError(msg)


def _require_keys(d: dict, keys: tuple[str, ...], what: str) -> None:
    missing = [k for k in keys if k not in d]
    _require(not missing, f"{what} missing keys: {missing}")


@dataclass
class Principle:
    id: str
    statement: str
    status: str = "CANDIDATE"
    scope: list[str] = field(default_factory=list)
    preconditions: list[str] = field(default_factory=list)
    predicted_topology_effects: list[str] = field(default_factory=list)
    supporting_evidence: list[dict[str, Any]] = field(default_factory=list)
    contradicting_evidence: list[dict[str, Any]] = field(default_factory=list)
    parent_principles: list[str] = field(default_factory=list)
    version: int = 1

    def __post_init__(self):
        _require(bool(self.id) and self.id.startswith("P-"),
                 f"principle id must start with 'P-': {self.id!r}")
        _require(bool(self.statement.strip()), f"{self.id}: empty statement")
        _require(self.status in PRINCIPLE_STATUSES,
                 f"{self.id}: invalid status {self.status!r}")
        _require(int(self.version) >= 1, f"{self.id}: version must be >= 1")

    @property
    def active(self) -> bool:
        return self.status in ACTIVE_PRINCIPLE_STATUSES

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Principle":
        _require_keys(d, ("id", "statement"), "principle")
        return cls(**{k: d[k] for k in cls.__dataclass_fields__ if k in d})


@dataclass
class PrincipleEvidence:
    """Append-only evidence event linking a principle to an observed outcome."""
    principle_id: str
    topology_id: str
    prediction_id: str
    effect: str
    evidence_refs: list[dict[str, Any]] = field(default_factory=list)
    event_id: str = ""

    def __post_init__(self):
        _require(self.effect in EVIDENCE_EFFECTS,
                 f"invalid evidence effect {self.effect!r}")
        _require(bool(self.principle_id), "evidence missing principle_id")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "PrincipleEvidence":
        _require_keys(d, ("principle_id", "topology_id", "prediction_id",
                          "effect"), "principle evidence")
        return cls(**{k: d[k] for k in cls.__dataclass_fields__ if k in d})


@dataclass
class Prediction:
    prediction_id: str
    topology_id: str
    claim: str
    observable: str
    success_condition: str
    falsification_condition: str
    weight: float = 1.0
    kind: str = ""                      # one of PREDICTION_KINDS ('' = prose-only)
    subject: dict[str, Any] = field(default_factory=dict)
    principles: list[str] = field(default_factory=list)

    def __post_init__(self):
        _require(bool(self.prediction_id), "prediction missing id")
        _require(bool(self.success_condition.strip()),
                 f"{self.prediction_id}: empty success condition")
        _require(bool(self.falsification_condition.strip()),
                 f"{self.prediction_id}: missing falsifier "
                 "(a prediction without a falsification condition is invalid)")
        if self.kind:
            _require(self.kind in PREDICTION_KINDS,
                     f"{self.prediction_id}: unknown prediction kind "
                     f"{self.kind!r}")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Prediction":
        _require_keys(d, ("prediction_id", "topology_id", "claim", "observable",
                          "success_condition", "falsification_condition"),
                      "prediction")
        return cls(**{k: d[k] for k in cls.__dataclass_fields__ if k in d})


@dataclass
class TopologyHypothesis:
    """A candidate topology as a provisional causal hypothesis."""
    topology_id: str
    task_id: str
    unresolved_distinctions: list[str] = field(default_factory=list)
    principles_invoked: list[str] = field(default_factory=list)
    harness_spec_ref: str = ""          # artifact id of the canonical spec JSON
    harness_spec: dict[str, Any] = field(default_factory=dict)
    resolution_map: dict[str, str] = field(default_factory=dict)
    predictions: list[dict[str, Any]] = field(default_factory=list)
    falsifiers: list[str] = field(default_factory=list)
    predicted_value: dict[str, Any] = field(default_factory=dict)
    status: str = "CANDIDATE"
    child_contract: dict[str, Any] = field(default_factory=dict)
    predictions_hash: str = ""

    def __post_init__(self):
        _require(bool(self.topology_id), "topology missing id")
        _require(self.status in HYPOTHESIS_STATUSES,
                 f"{self.topology_id}: invalid status {self.status!r}")
        for q, node in self.resolution_map.items():
            _require(bool(node), f"{self.topology_id}: distinction {q} mapped "
                                 "to empty node")

    def node_count(self) -> int:
        return len(self.harness_spec.get("nodes", []))

    def model_calls(self) -> int:
        return int(self.harness_spec.get("max_model_calls",
                   self.predicted_value.get("model_calls", 0)))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "TopologyHypothesis":
        _require_keys(d, ("topology_id", "task_id"), "topology hypothesis")
        return cls(**{k: d[k] for k in cls.__dataclass_fields__ if k in d})


@dataclass
class Revision:
    revision_id: str
    type: str
    parents: list[str] = field(default_factory=list)
    candidate_principles: list[dict[str, Any]] = field(default_factory=list)
    motivating_evidence: list[str] = field(default_factory=list)
    historical_cases_affected: list[str] = field(default_factory=list)
    changed_predictions: list[str] = field(default_factory=list)
    status: str = "CANDIDATE"

    def __post_init__(self):
        _require(self.type in REVISION_TYPES,
                 f"invalid revision type {self.type!r}")
        _require(self.status == "CANDIDATE",
                 "revisions are proposals: status must be CANDIDATE "
                 "(promotion happens only through the Gate)")
        if self.type in ("SPECIALIZE", "GENERALIZE", "MERGE", "SPLIT",
                         "DEPRECATE", "REINSTATE"):
            _require(bool(self.parents),
                     f"{self.type} revision requires parent principle ids")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Revision":
        _require_keys(d, ("revision_id", "type"), "revision")
        return cls(**{k: d[k] for k in cls.__dataclass_fields__ if k in d})


@dataclass
class TheoryVersion:
    """One immutable version of Theta_H = (P, E+, E-, R, V, L).

    E+/E- live in the append-only evidence log (theory_store); each version
    records the evidence-log length it was promoted at, never the log itself.
    """
    version: int
    principles: list[dict[str, Any]] = field(default_factory=list)
    revision_graph: list[dict[str, Any]] = field(default_factory=list)
    evidence_log_length: int = 0
    predecessor_hash: str = ""          # artifact id of the previous version
    provenance: dict[str, Any] = field(default_factory=dict)
    status: str = "CANDIDATE"           # CANDIDATE | PROMOTED

    def __post_init__(self):
        _require(int(self.version) >= 1, "theory version must be >= 1")
        _require(self.status in ("CANDIDATE", "PROMOTED"),
                 f"invalid theory version status {self.status!r}")
        ids = [p["id"] for p in self.principles]
        _require(len(ids) == len(set(ids)),
                 "duplicate principle ids in theory version")
        for p in self.principles:
            Principle.from_dict(p)      # closed-schema validation

    def principle(self, pid: str) -> Optional[Principle]:
        for p in self.principles:
            if p["id"] == pid:
                return Principle.from_dict(p)
        return None

    def active_principles(self) -> list[Principle]:
        out = [Principle.from_dict(p) for p in self.principles]
        return [p for p in out if p.active]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "TheoryVersion":
        _require_keys(d, ("version", "principles"), "theory version")
        return cls(**{k: d[k] for k in cls.__dataclass_fields__ if k in d})


@dataclass
class ApplicabilityResult:
    """Serialized outcome of abduction: Q -> applicable principles."""
    task_id: str
    applicable: list[dict[str, Any]] = field(default_factory=list)
    inapplicable_principles: list[str] = field(default_factory=list)
    theory_version: int = 0
    sources: dict[str, str] = field(default_factory=dict)  # principle -> deterministic|model

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TopologyEvaluation:
    topology_id: str
    resolved_distinctions: list[str] = field(default_factory=list)
    unresolved_distinctions: list[str] = field(default_factory=list)
    novel_evidence: list[str] = field(default_factory=list)
    duplicate_evidence: list[str] = field(default_factory=list)
    verification_effect: str = ""
    task_result: str = ""
    resource_use: dict[str, Any] = field(default_factory=dict)
    formal_failures: list[str] = field(default_factory=list)
    prediction_outcomes: list[dict[str, Any]] = field(default_factory=list)
    observed_value: dict[str, Any] = field(default_factory=dict)
    observed_utility: float = 0.0
    calibration_error: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class FalsificationResult:
    topology_id: str
    status: str
    prediction_statuses: list[dict[str, Any]] = field(default_factory=list)
    falsified_predictions: list[str] = field(default_factory=list)
    evidence_events: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self):
        _require(self.status in FALSIFICATION_STATUSES,
                 f"invalid falsification status {self.status!r}")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ReplayResult:
    theory_version: int
    case_results: list[dict[str, Any]] = field(default_factory=list)
    compatible: int = 0
    contradicted: int = 0
    indeterminate: int = 0
    acceptable: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
