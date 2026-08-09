"""Checkpoint creation: pin every governed identity of the current state."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Optional

from ._common import (CZROOT, git, protected_manifest_sha256, sha256_file,
                      tt_mod)
from .model import (LineageCheckpoint, LineageError, SCHEMA_VERSION,
                    checkpoint_id_for)


def create_checkpoint(repo_root: str | Path, *,
                      commit_sha: str,
                      source_branch: str,
                      experiment_id: str,
                      experiment_state_path: str,
                      experiment_result: str,
                      protected_manifest: dict[str, Any],
                      theory_version: Optional[int] = None,
                      parent_checkpoint_id: Optional[str] = None,
                      provenance: Optional[dict[str, Any]] = None,
                      artifact_label: str = "lineage checkpoint",
                      ) -> LineageCheckpoint:
    """Build an immutable checkpoint of the repo's governed state.

    Every identity is computed from the repository, never accepted from a
    caller-supplied claim (the caller names WHAT to pin; the values are
    measured)."""
    root = Path(repo_root)
    czroot = root / ".creator-zero"
    if not czroot.is_dir():
        raise LineageError(f"{root} is not a Creator-0 repository root")

    tree_sha = git(root, "rev-parse", f"{commit_sha}^{{tree}}")

    store_mod = tt_mod("theory_store")
    store = store_mod.TheoryStore(czroot / "state" / "topology-theory")
    versions = store.versions()
    if not versions:
        raise LineageError("no theory versions to checkpoint")
    tv = versions[-1] if theory_version is None else int(theory_version)
    theory = store.load(tv)
    length, head = store.evidence_head()
    chain = store.verify_append_only()
    if not chain["append_only_intact"]:
        raise LineageError("refusing to checkpoint a store whose evidence "
                           "chain is not intact")

    body: dict[str, Any] = {
        "artifact": artifact_label,
        "schema_version": SCHEMA_VERSION,
        "commit_sha": commit_sha,
        "tree_sha": tree_sha,
        "source_branch": source_branch,
        "theory_version": theory.version,
        "theory_artifact_id": store.version_hash(theory.version),
        "theory_status": theory.status,
        "evidence_length": length,
        "evidence_head_hash": head,
        "root_contract_sha256": sha256_file(
            czroot / "contracts" / "root_contract.json"),
        "formal_kernel_state_artifact_id": sha256_file(
            czroot / "state" / "formal-semantics-v0.1.json"),
        "protected_manifest_sha256": protected_manifest_sha256(
            protected_manifest),
        "protected_manifest": dict(protected_manifest),
        "experiment_id": experiment_id,
        "experiment_state_path": experiment_state_path,
        "experiment_state_sha256": sha256_file(root / experiment_state_path),
        "experiment_result": experiment_result,
        "parent_checkpoint_id": parent_checkpoint_id,
        "provenance": dict(provenance or {}),
    }
    body["checkpoint_id"] = checkpoint_id_for(body)
    return LineageCheckpoint.from_dict(body)


def write_checkpoint(cp: LineageCheckpoint, path: str | Path) -> Path:
    """Write-once persistence: an existing checkpoint file is never
    overwritten (checkpoints are immutable)."""
    p = Path(path)
    if p.exists():
        raise LineageError(f"refusing to overwrite existing checkpoint {p}")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(cp.serialize(), encoding="utf-8")
    return p


def load_checkpoint(path: str | Path) -> LineageCheckpoint:
    return LineageCheckpoint.from_dict(
        json.loads(Path(path).read_text(encoding="utf-8")))
