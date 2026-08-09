"""Creator-0 lineage subsystem: externally reconstructible checkpoints.

A LineageCheckpoint is evidence about inherited state, not hidden-state
continuity: the successor session reconstructs governed state from pinned
artifacts (X_{n+1,0} ~=_Lambda_O X_{n,checkpoint}), never from process
memory (Z_{n+1} != Z_n is expected and irrelevant).

    create_checkpoint(repo_root, ...)       -> LineageCheckpoint
    verify_checkpoint(repo_root, cp)        -> CheckpointResult (idempotent)
    resume_from_checkpoint(repo_root, cp, destination) -> resume record

Verification is a deterministic conjunction with typed failure codes; any
critical mismatch maps to LINEAGE_RESUME_FAIL in the caller. No model input
reaches any check. The package directory is importable directly (no hyphen).
"""
from .model import (LineageCheckpoint, CheckpointResult, LineageError,
                    FAILURE_CODES)
from .checkpoint import create_checkpoint
from .verify import verify_checkpoint
from .resume import resume_from_checkpoint

__all__ = ["LineageCheckpoint", "CheckpointResult", "LineageError",
           "FAILURE_CODES", "create_checkpoint", "verify_checkpoint",
           "resume_from_checkpoint"]
