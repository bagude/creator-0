"""Deterministic validation of blinded-session outputs (Experiment 6).

Hand-rolled closed validators mirroring the JSON-Schema documents in
schemas/ (no external dependencies). A validation failure is a typed
rejection; model output cannot override it.
"""
from __future__ import annotations
import re
from typing import Any

FEATURES = ("locally_resolvable", "requires_isolation", "contamination",
            "capability_bearing_artifact", "spans_sessions")
FAMILIES = ("local", "local-independent-verify", "isolated-child",
            "branching")


class OutputValidationError(ValueError):
    """A session artifact violates its closed schema."""


def _req(cond: bool, msg: str) -> None:
    if not cond:
        raise OutputValidationError(msg)


def validate_distinctions(doc: Any, task_id: str,
                          evidence_requirement_ids: list[str]) -> None:
    _req(isinstance(doc, dict), "distinctions: not an object")
    _req(set(doc) == {"task_id", "unresolved_distinctions"},
         f"distinctions: keys {sorted(doc)} != [task_id, "
         "unresolved_distinctions]")
    _req(doc["task_id"] == task_id,
         f"distinctions: task_id {doc['task_id']!r} != {task_id!r}")
    uds = doc["unresolved_distinctions"]
    _req(isinstance(uds, list) and 1 <= len(uds) <= 8,
         "distinctions: need 1..8 entries")
    ids = set()
    referenced: set[str] = set()
    for d in uds:
        _req(isinstance(d, dict), "distinction: not an object")
        required = {"id", "question", "why_unresolved", "required_evidence",
                    "admissibility_constraints", "dependencies", "features",
                    "evidence_requirement_refs"}
        _req(set(d) == required,
             f"distinction keys {sorted(d)} != {sorted(required)}")
        _req(re.fullmatch(r"Q[0-9]+", d["id"]) is not None,
             f"bad distinction id {d.get('id')!r}")
        _req(d["id"] not in ids, f"duplicate distinction id {d['id']}")
        ids.add(d["id"])
        for k in ("question", "why_unresolved", "required_evidence"):
            _req(isinstance(d[k], str) and len(d[k]) >= 10,
                 f"{d['id']}.{k}: string >= 10 chars required")
        _req(isinstance(d["admissibility_constraints"], list) and
             all(isinstance(x, str) for x in d["admissibility_constraints"]),
             f"{d['id']}.admissibility_constraints: list of strings")
        _req(isinstance(d["dependencies"], list) and
             all(re.fullmatch(r"Q[0-9]+", str(x)) for x in d["dependencies"]),
             f"{d['id']}.dependencies: list of Qn ids")
        _req(isinstance(d["evidence_requirement_refs"], list) and
             d["evidence_requirement_refs"] and
             all(isinstance(x, str) for x in d["evidence_requirement_refs"]),
             f"{d['id']}.evidence_requirement_refs: non-empty string list")
        for r in d["evidence_requirement_refs"]:
            _req(r in evidence_requirement_ids,
                 f"{d['id']}: unknown evidence requirement {r!r}")
            referenced.add(r)
        f = d["features"]
        _req(isinstance(f, dict) and set(f) == set(FEATURES),
             f"{d['id']}.features: exactly {FEATURES} required")
        _req(all(isinstance(v, bool) for v in f.values()),
             f"{d['id']}.features: booleans required")
    for d in uds:
        for dep in d["dependencies"]:
            _req(dep in ids, f"{d['id']}: dependency {dep} not defined")
    missing = sorted(set(evidence_requirement_ids) - referenced)
    _req(not missing,
         f"evidence requirements never referenced by any distinction: "
         f"{missing}")


def validate_value_estimates(doc: Any, task_id: str) -> None:
    _req(isinstance(doc, dict), "value-estimates: not an object")
    _req(set(doc) == {"task_id", "estimates"},
         f"value-estimates: keys {sorted(doc)}")
    _req(doc["task_id"] == task_id,
         f"value-estimates: task_id {doc['task_id']!r} != {task_id!r}")
    est = doc["estimates"]
    _req(isinstance(est, dict) and set(est) == set(FAMILIES),
         f"value-estimates: families {sorted(est) if isinstance(est, dict) else est}")
    for fam, e in est.items():
        _req(isinstance(e, dict) and set(e) == {"delta_e", "redundancy",
                                                "governance_risk",
                                                "rationale"},
             f"estimate {fam}: bad keys")
        for k in ("delta_e", "redundancy", "governance_risk"):
            v = e[k]
            _req(isinstance(v, (int, float)) and 0.0 <= float(v) <= 1.0,
                 f"estimate {fam}.{k}: number in [0,1] required")
        _req(isinstance(e["rationale"], str) and len(e["rationale"]) >= 10,
             f"estimate {fam}.rationale: string >= 10 chars")


def validate_resolution(doc: Any, task_id: str,
                        distinction_ids: list[str]) -> None:
    _req(isinstance(doc, dict), "resolution: not an object")
    _req(set(doc) == {"task_id", "topology_id", "resolutions"},
         f"resolution: keys {sorted(doc) if isinstance(doc, dict) else doc}")
    _req(doc["task_id"] == task_id, "resolution: wrong task_id")
    rs = doc["resolutions"]
    _req(isinstance(rs, list) and rs, "resolution: non-empty list required")
    seen = set()
    for r in rs:
        required = {"id", "status", "resolved_by", "answer", "evidence_ids",
                    "evidence_requirement_refs"}
        _req(isinstance(r, dict) and set(r) == required,
             f"resolution entry keys {sorted(r) if isinstance(r, dict) else r}")
        _req(r["id"] in distinction_ids,
             f"resolution names unknown distinction {r['id']!r}")
        _req(r["id"] not in seen, f"duplicate resolution for {r['id']}")
        seen.add(r["id"])
        _req(r["status"] in ("RESOLVED", "UNRESOLVED"),
             f"{r['id']}: bad status {r['status']!r}")
        _req(isinstance(r["resolved_by"], str), f"{r['id']}: resolved_by")
        _req(isinstance(r["answer"], str), f"{r['id']}: answer")
        _req(isinstance(r["evidence_ids"], list), f"{r['id']}: evidence_ids")
        _req(isinstance(r["evidence_requirement_refs"], list),
             f"{r['id']}: evidence_requirement_refs")
    missing = sorted(set(distinction_ids) - seen)
    _req(not missing, f"resolutions missing for distinctions: {missing}")


def validate_evidence(doc: Any) -> None:
    _req(isinstance(doc, list), "evidence: list required")
    seen = set()
    for e in doc:
        _req(isinstance(e, dict) and
             {"id", "source_node", "description"} <= set(e),
             "evidence record: id, source_node, description required")
        _req(e["id"] not in seen, f"duplicate evidence id {e['id']}")
        seen.add(e["id"])
