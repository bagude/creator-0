"""Typed lineage objects: immutable checkpoint + verification result."""
from __future__ import annotations
import hashlib
import json
from dataclasses import dataclass, field, asdict
from typing import Any, Optional

SCHEMA_VERSION = "lineage-checkpoint-v1"

FAILURE_CODES = (
    "COMMIT_MISMATCH", "TREE_MISMATCH", "THEORY_MISMATCH",
    "EVIDENCE_HEAD_MISMATCH", "ROOT_CONTRACT_MISMATCH",
    "FORMAL_KERNEL_MISMATCH", "EXPERIMENT_STATE_MISMATCH",
    "PROTECTED_MANIFEST_MISMATCH", "EVIDENCE_SOURCE_MISMATCH",
)


class LineageError(RuntimeError):
    """Lineage invariant violation (malformed checkpoint, refused resume)."""


def canonical_dumps(obj: Any) -> str:
    return json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def checkpoint_id_for(body: dict[str, Any]) -> str:
    """Deterministic checkpoint identity over the body without its own id."""
    d = {k: v for k, v in body.items() if k != "checkpoint_id"}
    return "sha256:" + hashlib.sha256(
        (json.dumps(d, sort_keys=True, separators=(",", ":"))
         + "\x00creator-0/lineage/checkpoint").encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class LineageCheckpoint:
    schema_version: str
    checkpoint_id: str

    commit_sha: str
    tree_sha: str
    source_branch: str

    theory_version: int
    theory_artifact_id: str
    theory_status: str

    evidence_length: int
    evidence_head_hash: str

    root_contract_sha256: str
    formal_kernel_state_artifact_id: str
    protected_manifest_sha256: str
    protected_manifest: dict[str, Any] = field(default_factory=dict)

    experiment_id: str = ""
    experiment_state_path: str = ""
    experiment_state_sha256: str = ""
    experiment_result: str = ""

    parent_checkpoint_id: Optional[str] = None
    provenance: dict[str, Any] = field(default_factory=dict)
    artifact: str = ""

    def __post_init__(self):
        if self.schema_version != SCHEMA_VERSION:
            raise LineageError(
                f"unsupported checkpoint schema {self.schema_version!r}")
        for name in ("commit_sha", "tree_sha", "source_branch",
                     "theory_artifact_id"):
            if not getattr(self, name):
                raise LineageError(f"checkpoint missing {name}")
        expected = checkpoint_id_for(self.to_dict())
        if self.checkpoint_id != expected:
            raise LineageError(
                f"checkpoint_id does not match content: {self.checkpoint_id} "
                f"!= {expected} (checkpoints are immutable; a drifted id "
                "means the body was edited after creation)")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "LineageCheckpoint":
        known = {k: d[k] for k in cls.__dataclass_fields__ if k in d}
        unknown = set(d) - set(cls.__dataclass_fields__)
        if unknown:
            raise LineageError(
                f"checkpoint document carries unknown fields {sorted(unknown)}"
                " (closed schema; nothing is silently dropped)")
        return cls(**known)

    def serialize(self) -> str:
        return canonical_dumps(self.to_dict())


@dataclass
class CheckpointResult:
    checkpoint_id: str
    status: str                      # PASS | FAIL
    checks: dict[str, dict[str, Any]] = field(default_factory=dict)
    failed: list[str] = field(default_factory=list)
    failure_codes: list[str] = field(default_factory=list)
    result: Optional[str] = None     # LINEAGE_RESUME_FAIL on failure

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
