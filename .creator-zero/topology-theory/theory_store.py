"""Persistent theory store: immutable versions + append-only evidence.

Layout (default root `.creator-zero/state/topology-theory/`):
    theta-v<N>.json      — one file per theory version; write-once
    evidence.jsonl       — append-only principle-evidence log
    evidence-heads.jsonl — append-only chain of (length, running-hash) heads

Invariants enforced here (deterministically, not by convention):
  - a version file is never overwritten (write-once; TheoryStoreError);
  - promoted versions are immutable: promotion writes a new file and links
    the predecessor by artifact id, never edits in place;
  - evidence is append-only: every append extends a running hash chain and
    verify_append_only() detects any rewrite/truncation of the prefix;
  - promotion demands a Gate-issued PASS: models, verifiers, and revision
    proposals cannot promote (PromotionError).
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from typing import Any, Optional

from .model import PrincipleEvidence, TheoryVersion, ModelValidationError
from .serialization import canonical_dumps, object_artifact_id


class TheoryStoreError(RuntimeError):
    """Store invariant violation (overwrite, rewrite, missing lineage)."""


class PromotionError(RuntimeError):
    """Promotion attempted by anything other than a Gate-issued PASS."""


def _running_hash(prev: str, line: str) -> str:
    return hashlib.sha256((prev + "\n" + line).encode("utf-8")).hexdigest()


class TheoryStore:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.evidence_path = self.root / "evidence.jsonl"
        self.heads_path = self.root / "evidence-heads.jsonl"

    # ---- versions ---------------------------------------------------------
    def version_path(self, version: int) -> Path:
        return self.root / f"theta-v{int(version)}.json"

    def versions(self) -> list[int]:
        out = []
        for p in self.root.glob("theta-v*.json"):
            try:
                out.append(int(p.stem.split("theta-v")[1]))
            except (IndexError, ValueError):
                continue
        return sorted(out)

    def load(self, version: Optional[int] = None) -> TheoryVersion:
        vs = self.versions()
        if not vs:
            raise TheoryStoreError("no theory versions in store")
        v = vs[-1] if version is None else int(version)
        p = self.version_path(v)
        if not p.exists():
            raise TheoryStoreError(f"theory version {v} not found")
        return TheoryVersion.from_dict(json.loads(p.read_text(encoding="utf-8")))

    def version_hash(self, version: int) -> str:
        doc = json.loads(self.version_path(version).read_text(encoding="utf-8"))
        return object_artifact_id(doc, f"creator-0/topology-theory/theta-v{version}")

    def write_version(self, theory: TheoryVersion) -> Path:
        """Write-once persistence of a version document."""
        p = self.version_path(theory.version)
        if p.exists():
            raise TheoryStoreError(
                f"refusing to overwrite existing theory version file: {p.name} "
                "(promoted theory versions are immutable)")
        if theory.version > 1:
            if not theory.predecessor_hash:
                raise TheoryStoreError(
                    f"theory v{theory.version} missing predecessor_hash lineage")
            prev = theory.version - 1
            if not self.version_path(prev).exists():
                raise TheoryStoreError(
                    f"theory v{theory.version} has no stored predecessor v{prev}")
            actual = self.version_hash(prev)
            if actual != theory.predecessor_hash:
                raise TheoryStoreError(
                    f"predecessor_hash mismatch for v{theory.version}: "
                    f"declared {theory.predecessor_hash} != stored {actual}")
        p.write_text(canonical_dumps(theory.to_dict()), encoding="utf-8")
        return p

    def promote(self, candidate: TheoryVersion,
                gate_result: dict[str, Any]) -> Path:
        """Persist a candidate version as PROMOTED. Gate-issued PASS only.

        `gate_result` must be the deterministic Gate's own FormalResult dict:
        check == "gate", status == "PASS", detail.issued_by == "gate". A
        verifier report, a revision proposal, or any model-authored document
        does not satisfy this and raises PromotionError.
        """
        if not isinstance(gate_result, dict):
            raise PromotionError("gate result must be a serialized FormalResult")
        if gate_result.get("check") != "gate":
            raise PromotionError(
                f"promotion requires the Gate's own result; got check="
                f"{gate_result.get('check')!r}")
        if gate_result.get("status") != "PASS":
            raise PromotionError(
                f"gate status is {gate_result.get('status')!r}, not PASS")
        if gate_result.get("detail", {}).get("issued_by") != "gate":
            raise PromotionError(
                "gate result not issued by the gate actor "
                f"(issued_by={gate_result.get('detail', {}).get('issued_by')!r})")
        promoted = TheoryVersion.from_dict(
            {**candidate.to_dict(), "status": "PROMOTED"})
        return self.write_version(promoted)

    # ---- append-only evidence --------------------------------------------
    def evidence_head(self) -> tuple[int, str]:
        """(length, running hash) of the current evidence log."""
        if not self.heads_path.exists():
            return 0, ""
        lines = [l for l in self.heads_path.read_text(
            encoding="utf-8").splitlines() if l.strip()]
        if not lines:
            return 0, ""
        head = json.loads(lines[-1])
        return int(head["length"]), str(head["hash"])

    def append_evidence(self, event: PrincipleEvidence | dict[str, Any]) -> int:
        if isinstance(event, dict):
            event = PrincipleEvidence.from_dict(event)
        length, prev = self.evidence_head()
        line = json.dumps(event.to_dict(), sort_keys=True,
                          separators=(",", ":"))
        new_hash = _running_hash(prev, line)
        with self.evidence_path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
        with self.heads_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"length": length + 1, "hash": new_hash},
                               sort_keys=True, separators=(",", ":")) + "\n")
        return length + 1

    def read_evidence(self) -> list[PrincipleEvidence]:
        if not self.evidence_path.exists():
            return []
        out = []
        for i, line in enumerate(self.evidence_path.read_text(
                encoding="utf-8").splitlines()):
            if not line.strip():
                continue
            try:
                out.append(PrincipleEvidence.from_dict(json.loads(line)))
            except (json.JSONDecodeError, ModelValidationError) as e:
                raise TheoryStoreError(f"evidence line {i} corrupt: {e}")
        return out

    def verify_append_only(self) -> dict[str, Any]:
        """Recompute the hash chain over the log; any prefix rewrite fails."""
        lines = []
        if self.evidence_path.exists():
            lines = [l for l in self.evidence_path.read_text(
                encoding="utf-8").splitlines() if l.strip()]
        running = ""
        for line in lines:
            running = _running_hash(running, line)
        length, head = self.evidence_head()
        ok = (len(lines) == length) and (running == head or length == 0)
        return {"append_only_intact": ok, "log_length": len(lines),
                "recorded_length": length,
                "recomputed_hash": running, "recorded_hash": head}
