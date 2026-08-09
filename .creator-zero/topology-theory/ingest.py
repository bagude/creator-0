"""Evidence import layer: pinned source, deterministic enrichment,
idempotent append into the append-only theory store.

    verify_source_pin(path, pin)               -> typed PASS/FAIL record
    enrich_e6_events(raw_events, pins, ...)    -> v2 evidence dicts
    ingest_evidence(store, events, ...)        -> import manifest

Idempotence contract (per event e):
    e.event_id not in store                       -> append
    same id, identical normalized content         -> skip
    same id, different content                    -> EVIDENCE_ID_CONFLICT
No previously written evidence line is ever rewritten; the running hash
chain remains the tamper-evidence.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from typing import Any, Optional

from .admissibility import E6_CLASS_TO_KIND
from .model import ModelValidationError, PrincipleEvidence
from .serialization import file_artifact_id


class EvidenceImportError(RuntimeError):
    """Typed import failure (source pin mismatch, id conflict)."""


def normalized_event_hash(d: dict[str, Any]) -> str:
    """Content hash over the closed canonical form of an evidence event."""
    canon = PrincipleEvidence.from_dict(d).to_dict()
    return hashlib.sha256(json.dumps(canon, sort_keys=True,
                          separators=(",", ":")).encode("utf-8")).hexdigest()


def load_source_events(path: str | Path) -> list[dict[str, Any]]:
    out = []
    for i, line in enumerate(Path(path).read_text(
            encoding="utf-8").splitlines()):
        if not line.strip():
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError as e:
            raise EvidenceImportError(f"source line {i} unparseable: {e}")
    return out


def verify_source_pin(path: str | Path, pin: dict[str, Any]
                      ) -> dict[str, Any]:
    """The import source must byte-match its Phase A pin."""
    p = Path(path)
    got = hashlib.sha256(p.read_bytes()).hexdigest()
    events = load_source_events(p)
    ids = [e.get("event_id") for e in events]
    checks = {
        "sha256": got == pin["sha256"],
        "event_count": len(events) == int(pin["expected_event_count"]),
        "unique_event_ids": len(set(ids)) ==
        int(pin["expected_unique_event_ids"]),
    }
    ok = all(checks.values())
    return {"check": "evidence_source_pin",
            "status": "PASS" if ok else "FAIL",
            "failure_code": None if ok else "EVIDENCE_SOURCE_MISMATCH",
            "observed": {"sha256": got, "event_count": len(events),
                         "unique_event_ids": len(set(ids))},
            "pinned": {k: pin[k] for k in ("sha256", "expected_event_count",
                                           "expected_unique_event_ids")},
            "clauses": checks}


def enrich_e6_events(raw_events: list[dict[str, Any]],
                     labels_by_trial: dict[str, dict[str, Any]],
                     *, source_commit: str, source_path: str,
                     source_artifact_id: str,
                     ) -> list[dict[str, Any]]:
    """Deterministic enrichment of frozen E6 events with provenance/context.

    The join is trial_id -> frozen private label -> admissibility kind. The
    frozen labels are truth artifacts: nothing here rewrites them, and an
    event whose join fails gets context_status=UNKNOWN (it cannot support a
    context-conditioned split dimension)."""
    out = []
    for raw in raw_events:
        e = dict(raw)
        e.setdefault("source_experiment", "experiment-6")
        e.setdefault("source_commit", source_commit)
        e.setdefault("source_artifact_id", source_artifact_id)
        trial = e.get("trial_id", "")
        label = labels_by_trial.get(trial)
        if label is not None and label.get("latent_class") in \
                E6_CLASS_TO_KIND:
            cls = label["latent_class"]
            e["context"] = {
                "context_status": "OK",
                "latent_class": cls,
                "admissibility_kind": E6_CLASS_TO_KIND[cls],
                "join_source": {
                    "path": f".creator-zero/experiment-6/task-bank/{trial}/"
                            "private/label.json",
                    "join_key": "trial_id",
                    "source_path": source_path,
                },
            }
        else:
            e["context"] = {"context_status": "UNKNOWN"}
        # closed-schema validation: unknown fields fail loudly, nothing is
        # silently stripped (NC6)
        out.append(PrincipleEvidence.from_dict(e).to_dict())
    return out


def ingest_evidence(store, events: list[dict[str, Any]],
                    import_manifest: Optional[dict[str, Any]] = None,
                    ) -> dict[str, Any]:
    """Idempotent append of validated evidence events into the store."""
    head_before = store.evidence_head()
    existing: dict[str, str] = {}
    for ev in store.read_evidence():
        d = ev.to_dict()
        existing[d["event_id"]] = normalized_event_hash(d)

    imported, skipped, conflicts = [], [], []
    for e in events:
        try:
            canon = PrincipleEvidence.from_dict(e).to_dict()
        except ModelValidationError as exc:
            raise EvidenceImportError(f"invalid evidence event "
                                      f"{e.get('event_id')!r}: {exc}")
        eid = canon["event_id"]
        h = normalized_event_hash(canon)
        if eid in existing:
            if existing[eid] == h:
                skipped.append(eid)
                continue
            conflicts.append(eid)
            raise EvidenceImportError(
                f"EVIDENCE_ID_CONFLICT: event {eid!r} already stored with "
                "different content; append-only history cannot be rewritten")
        store.append_evidence(canon)
        existing[eid] = h
        imported.append(eid)

    head_after = store.evidence_head()
    chain = store.verify_append_only()
    doc = {
        "artifact": "evidence import manifest",
        "imported": len(imported),
        "skipped_identical": len(skipped),
        "conflicts": len(conflicts),
        "evidence_head_before": {"length": head_before[0],
                                 "hash": head_before[1]},
        "evidence_head_after": {"length": head_after[0],
                                "hash": head_after[1]},
        "append_only_intact": chain["append_only_intact"],
        "imported_event_ids_sha256": hashlib.sha256(
            json.dumps(imported, separators=(",", ":")).encode()
        ).hexdigest(),
    }
    if import_manifest:
        doc.update({k: v for k, v in import_manifest.items()
                    if k not in doc})
    return doc


def pin_source_artifact(path: str | Path, provenance: str) -> dict[str, Any]:
    p = Path(path)
    return {
        "path": str(path),
        "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
        "artifact_id": file_artifact_id(p, provenance),
    }
