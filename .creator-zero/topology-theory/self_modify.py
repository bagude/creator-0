"""Governed self-modification: candidate-first, Gate-only promotion.

Pipeline (every stage deterministic except the implementer's content):

    Canonical Root
    -> Self-Modification Proposal          (observable, typed)
    -> Candidate Worktree                  (sole mutation locus)
    -> Formal Verification                 (kernel checks, tests)
    -> Historical Replay                   (frozen corpus)
    -> Independent Verifier                (information-only, cannot promote)
    -> Deterministic Gate                  (sole promotion authority)
    -> Canonical Promotion

Structural guarantees enforced here:
  - candidate_only_guard: every mutated path must live inside the declared
    candidate workspace; a canonical write before gate PASS raises
    CandidateViolation;
  - protected-law check: a candidate patch may not touch frozen experiment
    trees, prior state manifests, or the root contract;
  - gate(): pure deterministic conjunction over serialized verification
    results — no model input reaches it;
  - authorize_promotion(): the only path to canonical promotion; it demands
    the Gate's own PASS. A verifier report or any other document (whatever
    its status field says) raises PromotionError.
"""
from __future__ import annotations
import hashlib
import subprocess
from pathlib import Path
from typing import Any, Optional

from .serialization import artifact_id
from .theory_store import PromotionError

PASS, FAIL = "PASS", "FAIL"

PROTECTED_PREFIXES = (
    ".creator-zero/experiment-3/",
    ".creator-zero/experiment-4/",
    ".creator-zero/experiment-4c/",
    ".creator-zero/experiment-5/",
    ".creator-zero/experiment-6/",
)
PROTECTED_FILES = (
    ".creator-zero/state/experiment-2.json",
    ".creator-zero/state/experiment-3.json",
    ".creator-zero/state/experiment-4.json",
    ".creator-zero/state/experiment-4c.json",
    ".creator-zero/state/experiment-5.json",
    ".creator-zero/state/experiment-6.json",
    ".creator-zero/state/formal-semantics-v0.1.json",
    ".creator-zero/contracts/root_contract.json",
)

REQUIRED_GATE_INPUTS = (
    "attenuation", "refinement", "tests_existing", "tests_new",
    "historical_replay", "protected_laws", "frozen_trees",
    "independent_verifier", "patch_manifest",
)


class CandidateViolation(RuntimeError):
    """A self-modification write escaped the candidate workspace."""


def candidate_only_guard(mutated_paths: list[str | Path],
                         candidate_root: str | Path) -> list[str]:
    """Every mutated path must resolve inside the candidate workspace."""
    root = Path(candidate_root).resolve()
    out = []
    for p in mutated_paths:
        rp = Path(p).resolve()
        if not (rp == root or str(rp).startswith(str(root) + "/")):
            raise CandidateViolation(
                f"self-modification wrote outside the candidate workspace: "
                f"{rp} (candidate root: {root})")
        out.append(str(rp))
    return out


def check_protected_laws(patch_paths: list[str]) -> dict[str, Any]:
    """A candidate patch may not modify protected historical/governance
    paths. Paths are repo-relative."""
    violations = []
    for p in sorted(patch_paths):
        norm = p[2:] if p.startswith("./") else p
        if any(norm.startswith(pref) for pref in PROTECTED_PREFIXES) \
                or norm in PROTECTED_FILES:
            violations.append(p)
    return {
        "check": "protected_laws",
        "status": FAIL if violations else PASS,
        "protected_prefixes": list(PROTECTED_PREFIXES),
        "protected_files": list(PROTECTED_FILES),
        "violations": violations,
    }


def build_patch_manifest(candidate_root: str | Path,
                         base_ref: str, head_ref: str = "HEAD",
                         provenance: str = "creator-0/self-modification",
                         ) -> dict[str, Any]:
    """Externally reconstructible candidate patch manifest.

    Lists every file changed between base and head in the candidate worktree
    with its exact stable artifact id. Anyone with the two commits can
    reproduce every hash."""
    root = Path(candidate_root)
    diff = subprocess.run(
        ["git", "diff", "--name-status", f"{base_ref}..{head_ref}"],
        cwd=root, capture_output=True, text=True, check=True).stdout
    entries = []
    for line in sorted(diff.splitlines()):
        if not line.strip():
            continue
        status, _, path = line.partition("\t")
        entry: dict[str, Any] = {"path": path, "change": status.strip()}
        f = root / path
        if f.exists():
            content = f.read_bytes()
            entry["sha256"] = hashlib.sha256(content).hexdigest()
            entry["artifact_id"] = artifact_id(content,
                                               f"{provenance}/{path}")
        entries.append(entry)
    return {
        "artifact": "candidate patch manifest",
        "base_ref": base_ref,
        "head_ref": head_ref,
        "provenance_identity": provenance,
        "file_count": len(entries),
        "files": entries,
    }


def _input_status(doc: Any) -> str:
    """Normalize a verification input to PASS/FAIL."""
    if isinstance(doc, dict):
        if "status" in doc:
            return str(doc["status"])
        if "acceptable" in doc:          # ReplayResult
            return PASS if doc["acceptable"] else FAIL
        if "append_only_intact" in doc:
            return PASS if doc["append_only_intact"] else FAIL
        if "ok" in doc:
            return PASS if doc["ok"] else FAIL
        if "verdict" in doc:
            return PASS if str(doc["verdict"]).upper() in ("PASS", "OK") \
                else FAIL
        if "file_count" in doc:          # patch manifest: present + non-empty
            return PASS if doc["file_count"] > 0 else FAIL
    return FAIL


def gate(inputs: dict[str, Any]) -> dict[str, Any]:
    """Deterministic Gate: conjunction over required serialized inputs.

    Returns a FormalResult-shaped dict with check='gate' and
    detail.issued_by='gate'. This function contains no model-mediated step;
    a missing or failing input fails the gate, and nothing can override it."""
    clauses: dict[str, str] = {}
    for k in REQUIRED_GATE_INPUTS:
        if k not in inputs:
            clauses[k] = "MISSING"
        else:
            clauses[k] = _input_status(inputs[k])
    failed = sorted(k for k, v in clauses.items() if v != PASS)
    status = PASS if not failed else FAIL
    result = {
        "check": "gate",
        "status": status,
        "formal_relation": "conjunction of required verification inputs",
        "counterexample": ({"violation": "GATE_FAIL",
                            "failed_or_missing_inputs": failed}
                           if failed else None),
        "evidence": [f"{k}: {v}" for k, v in sorted(clauses.items())],
        "assumptions": [
            "The gate decides only over the serialized verification inputs "
            "listed; it re-checks nothing and re-runs nothing.",
            "Verification inputs were produced by the deterministic checks "
            "and the append-only evidence chain they document.",
        ],
        "detail": {"issued_by": "gate", "clauses": clauses},
    }
    return result


def authorize_promotion(gate_result: dict[str, Any],
                        actor: str = "gate") -> dict[str, Any]:
    """The only path to canonical promotion.

    Raises PromotionError unless the supplied result is the Gate's own PASS
    and the requesting actor is the gate. Verifier reports, revision
    proposals, evaluations, or any model-authored document are refused
    regardless of their status fields."""
    if actor != "gate":
        raise PromotionError(
            f"actor {actor!r} cannot promote: canonical promotion is the "
            "gate's monopoly")
    if not isinstance(gate_result, dict) or gate_result.get("check") != "gate":
        raise PromotionError(
            "promotion requires the Gate's own result document "
            f"(check='gate'); got {gate_result.get('check') if isinstance(gate_result, dict) else type(gate_result).__name__!r}")
    if gate_result.get("detail", {}).get("issued_by") != "gate":
        raise PromotionError("gate result not issued by the gate")
    if gate_result.get("status") != PASS:
        raise PromotionError(
            f"gate status {gate_result.get('status')!r} != PASS")
    return {
        "promotion_authorized": True,
        "authorized_by": "gate",
        "gate_evidence": list(gate_result.get("evidence", [])),
    }
