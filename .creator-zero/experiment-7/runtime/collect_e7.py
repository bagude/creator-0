"""Closed validators for E7 blinded-session outputs (condition B v2 shapes;
condition A reuses the frozen E6 validators verbatim)."""
from __future__ import annotations
import re
from typing import Any

from .common import e6_runtime

FEATURES_V2 = ("locally_resolvable", "requires_isolation", "contamination",
               "capability_bearing_artifact", "spans_sessions",
               "requires_clean_room_authorship", "requires_nonauthor_search",
               "requires_independent_decomposition",
               "requires_method_disjoint_verification")
TYPED = FEATURES_V2[5:]


class OutputValidationError(ValueError):
    pass


def _req(cond: bool, msg: str) -> None:
    if not cond:
        raise OutputValidationError(msg)


def validate_distinctions_a(doc, task_id, req_ids) -> None:
    e6_runtime("collect").validate_distinctions(doc, task_id, req_ids)


def validate_value_estimates_a(doc, task_id) -> None:
    e6_runtime("collect").validate_value_estimates(doc, task_id)


def validate_resolution(doc, task_id, qids) -> None:
    e6_runtime("collect").validate_resolution(doc, task_id, qids)


def validate_evidence(doc) -> None:
    e6_runtime("collect").validate_evidence(doc)


def validate_distinctions_b(doc: Any, task_id: str,
                            evidence_requirement_ids: list[str]) -> None:
    _req(isinstance(doc, dict), "distinctions: not an object")
    _req(set(doc) == {"task_id", "unresolved_distinctions"},
         f"distinctions: keys {sorted(doc)}")
    _req(doc["task_id"] == task_id, "distinctions: wrong task_id")
    uds = doc["unresolved_distinctions"]
    _req(isinstance(uds, list) and 1 <= len(uds) <= 8,
         "distinctions: need 1..8 entries")
    ids, referenced = set(), set()
    for d in uds:
        required = {"id", "question", "why_unresolved", "required_evidence",
                    "admissibility_constraints", "dependencies", "features",
                    "evidence_requirement_refs"}
        _req(isinstance(d, dict) and set(d) == required,
             f"distinction keys {sorted(d) if isinstance(d, dict) else d}")
        _req(re.fullmatch(r"Q[0-9]+", d["id"]) is not None,
             f"bad distinction id {d.get('id')!r}")
        _req(d["id"] not in ids, f"duplicate distinction id {d['id']}")
        ids.add(d["id"])
        for k in ("question", "why_unresolved", "required_evidence"):
            _req(isinstance(d[k], str) and len(d[k]) >= 10,
                 f"{d['id']}.{k}: string >= 10 chars required")
        _req(isinstance(d["admissibility_constraints"], list),
             f"{d['id']}.admissibility_constraints")
        _req(isinstance(d["dependencies"], list),
             f"{d['id']}.dependencies")
        _req(isinstance(d["evidence_requirement_refs"], list)
             and d["evidence_requirement_refs"],
             f"{d['id']}.evidence_requirement_refs")
        for r in d["evidence_requirement_refs"]:
            _req(r in evidence_requirement_ids,
                 f"{d['id']}: unknown evidence requirement {r!r}")
            referenced.add(r)
        f = d["features"]
        _req(isinstance(f, dict) and set(f) == set(FEATURES_V2),
             f"{d['id']}.features: exactly the 9 v2 features required "
             f"(got {sorted(f) if isinstance(f, dict) else f})")
        _req(all(isinstance(v, bool) for v in f.values()),
             f"{d['id']}.features: booleans required")
        typed_on = [t for t in TYPED if f[t]]
        _req(len(typed_on) <= 1,
             f"{d['id']}: multiple typed relation features set: {typed_on}")
    for d in uds:
        for dep in d["dependencies"]:
            _req(dep in ids, f"{d['id']}: dependency {dep} not defined")
    missing = sorted(set(evidence_requirement_ids) - referenced)
    _req(not missing, f"evidence requirements never referenced: {missing}")


def validate_value_estimates_b(doc: Any, task_id: str,
                               distinction_ids: list[str]) -> None:
    _req(isinstance(doc, dict), "value-estimates: not an object")
    _req(set(doc) == {"task_id", "estimates"},
         f"value-estimates: keys {sorted(doc) if isinstance(doc, dict) else doc}")
    _req(doc["task_id"] == task_id, "value-estimates: wrong task_id")
    est = doc["estimates"]
    _req(isinstance(est, dict) and set(est) == set(distinction_ids),
         f"value-estimates: must cover exactly the distinction ids "
         f"(got {sorted(est) if isinstance(est, dict) else est}, "
         f"want {sorted(distinction_ids)})")
    for q, e in est.items():
        _req(isinstance(e, dict) and set(e) == {"value", "rationale"},
             f"estimate {q}: bad keys")
        v = e["value"]
        _req(isinstance(v, (int, float)) and 0.0 <= float(v) <= 1.0,
             f"estimate {q}.value: number in [0,1] required")
        _req(isinstance(e["rationale"], str) and len(e["rationale"]) >= 10,
             f"estimate {q}.rationale: string >= 10 chars")
