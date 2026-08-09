"""Class verifier: tasks whose evidence requirements are all satisfiable
from the package inside one governed session. Ground truth is frozen in the
private label as the exact canonical deliverable. Each requirement maps to
a set of deliverable fields; satisfaction = deep equality on those fields.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any

import verifylib


def _norm(x: Any) -> Any:
    if isinstance(x, float):
        return round(x, 6)
    if isinstance(x, list):
        return [_norm(v) for v in x]
    if isinstance(x, dict):
        return {k: _norm(v) for k, v in sorted(x.items())}
    return x


def run(td: Path, out: Path, label: dict[str, Any]) -> None:
    view = verifylib.load(td)
    gt = label["ground_truth"]
    result = view.result or {}

    def fields_ok(fields: list[str]) -> tuple[bool, str]:
        bad = []
        for f in fields:
            if _norm(result.get(f)) != _norm(gt.get(f)):
                bad.append(f)
        return (not bad,
                "fields exact" if not bad else f"mismatch on {bad}")

    requirements = {}
    for rid, fields in label["requirement_fields"].items():
        ok, why = fields_ok(fields)
        requirements[rid] = verifylib.requirement(ok, "parent", why)

    all_ok = all(_norm(result.get(f)) == _norm(v) for f, v in gt.items())

    # duplicates: any extra path on a locally sufficient task re-derives
    # parent-derivable content unless it disagrees materially
    dup_ids: list[str] = []
    extra: list[dict[str, Any]] = []
    effect = "none"
    if view.examiner_present and view.examiner_doc:
        doc = view.examiner_doc
        material = [d for d in doc.get("discrepancies", [])
                    if d.get("severity") == "MATERIAL"]
        rec = {"id": "ev-exam-1", "source_node": "verify-independent",
               "description": f"independent examiner: {doc.get('overall')}",
               "duplicate_of_parent": doc.get("overall") == "CONFIRMED"
               and not material}
        extra.append(rec)
        if rec["duplicate_of_parent"]:
            dup_ids.append(rec["id"])
        effect = "confirmed" if doc.get("overall") == "CONFIRMED" else \
            ("improved" if material and not all_ok else "none")
    if view.child_present:
        rec = {"id": "ev-child-1", "source_node": "child-return",
               "description": "child deliverable on a locally sufficient "
                              "task",
               "duplicate_of_parent": True}
        extra.append(rec)
        dup_ids.append(rec["id"])

    if effect == "none" and all_ok:
        effect = "confirmed" if view.examiner_present else "none"

    verifylib.emit(out, trial_id=label["trial_id"],
                   requirements=requirements, result_correct=all_ok,
                   verification_effect=effect,
                   duplicate_evidence_ids=dup_ids,
                   extra_evidence_records=extra,
                   details={"ground_truth_fields": sorted(gt),
                            "mismatched_fields": sorted(
                                f for f in gt
                                if _norm(result.get(f)) != _norm(gt[f]))})
