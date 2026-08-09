"""Resume: realize a new causal trajectory from a verified checkpoint.

    resume_from_checkpoint(repo_root, cp, destination, branch_name=None)

Creates a git worktree rooted at exactly the checkpoint commit. The source
branch is never moved, and resume refuses to run at all unless
verify_checkpoint passes first (Resume(L,X)=⊥ on any mismatch). A resumed
worktree is Branch(X_n, Δ_{n+1}): a descendant trajectory, not a restart
and not hidden-state continuity.
"""
from __future__ import annotations
from pathlib import Path
from typing import Any, Optional

from ._common import git
from .model import LineageCheckpoint, LineageError
from .verify import verify_checkpoint


def resume_from_checkpoint(repo_root: str | Path,
                           cp: LineageCheckpoint | dict[str, Any],
                           destination: str | Path,
                           branch_name: Optional[str] = None,
                           ) -> dict[str, Any]:
    if isinstance(cp, dict):
        cp = LineageCheckpoint.from_dict(cp)
    root = Path(repo_root)
    dest = Path(destination)
    if dest.exists():
        raise LineageError(f"resume destination already exists: {dest}")

    verification = verify_checkpoint(root, cp)
    if verification.status != "PASS":
        raise LineageError(
            "LINEAGE_RESUME_FAIL: checkpoint verification failed "
            f"({verification.failure_codes}); resume refused")

    source_tip_before = git(root, "rev-parse", cp.commit_sha)
    args = ["worktree", "add"]
    if branch_name:
        args += ["-b", branch_name]
    args += [str(dest), cp.commit_sha]
    git(root, *args)

    head = git(dest, "rev-parse", "HEAD")
    tree = git(dest, "rev-parse", "HEAD^{tree}")
    if head != cp.commit_sha or tree != cp.tree_sha:
        raise LineageError(
            f"resumed worktree does not sit at the checkpoint: head={head} "
            f"tree={tree}")
    source_tip_after = git(root, "rev-parse", cp.commit_sha)
    if source_tip_before != source_tip_after:
        raise LineageError("source commit moved during resume")

    return {
        "artifact": "lineage resume record",
        "checkpoint_id": cp.checkpoint_id,
        "destination": str(dest),
        "branch": branch_name or "(detached)",
        "head": head,
        "tree": tree,
        "verification": verification.to_dict(),
        "source_branch_unmodified": True,
    }
