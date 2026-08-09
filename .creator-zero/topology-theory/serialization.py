"""Canonical serialization and exact stable artifact identity.

ArtifactID = "sha256:" + hex(sha256(content_bytes || 0x00 || provenance_utf8))

The 0x00 separator makes the (content, provenance) split unambiguous. The
provenance identity names the governed origin of the artifact (for example
"creator-0/topology-theory/candidate/H-t1-local"), never a filesystem path.
Path/basename is non-authoritative metadata carried alongside the id: two
artifacts with the same basename but different content have distinct ids,
and moving a file never changes its id.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from typing import Any

ID_PREFIX = "sha256:"


def canonical_dumps(obj: Any) -> str:
    """Deterministic JSON: sorted keys, 2-space indent, newline-terminated."""
    return json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def canonical_bytes(obj: Any) -> bytes:
    return canonical_dumps(obj).encode("utf-8")


def artifact_id(content: bytes | str, provenance_identity: str) -> str:
    if isinstance(content, str):
        content = content.encode("utf-8")
    h = hashlib.sha256()
    h.update(content)
    h.update(b"\x00")
    h.update(provenance_identity.encode("utf-8"))
    return ID_PREFIX + h.hexdigest()


def object_artifact_id(obj: Any, provenance_identity: str) -> str:
    """Artifact id of a JSON-serializable object via its canonical bytes."""
    return artifact_id(canonical_bytes(obj), provenance_identity)


def file_artifact_id(path: str | Path, provenance_identity: str) -> str:
    return artifact_id(Path(path).read_bytes(), provenance_identity)


def artifact_ref(path: str | Path, provenance_identity: str) -> dict[str, str]:
    """Reference for formal events: authoritative id + non-authoritative path."""
    return {
        "artifact_id": file_artifact_id(path, provenance_identity),
        "provenance_identity": provenance_identity,
        "path": str(path),          # metadata only, never identity
    }


def sha256_file(path: str | Path) -> str:
    """Bare content hash (no provenance), for pinning frozen artifacts."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
