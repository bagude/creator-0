"""Class verifier: exact-answer tasks where producing an answer is easy but
discriminating correct from subtly wrong answers is the epistemic work; the
required evidence includes a method-disjoint re-derivation with per-item
agreement records.

Label parameters:
    ground_truth_answers   {item_key: exact answer (string)}
    answers_field          result.json field holding {item_key: answer}
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any

import verifylib


def run(td: Path, out: Path, label: dict[str, Any], bank_public: Path
        ) -> None:
    view = verifylib.load(td)
    gt = {str(k): str(v) for k, v in label["ground_truth_answers"].items()}
    result = view.result or {}
    answers = {str(k): str(v) for k, v in
               (result.get(label["answers_field"]) or {}).items()}

    missing = sorted(set(gt) - set(answers))
    wrong = sorted(k for k in gt if k in answers and answers[k] != gt[k])
    ea_ok = not missing and bool(str(result.get("method", "")).strip())
    ea_why = (f"all {len(gt)} items answered with method stated"
              if ea_ok else f"missing items {missing} or method absent")

    ex_ok, ex_why = verifylib.examiner_ok(view)
    per_item = []
    if ex_ok and view.examiner_doc:
        per_item = view.examiner_doc.get("per_distinction", [])
        if not per_item:
            ex_ok, ex_why = False, "examiner recorded no per-item verdicts"
    ch_ok, ch_why = verifylib.child_with_role(view, "independent_verifier")
    eb_ok = ex_ok or ch_ok
    eb_by = "examiner" if ex_ok else ("child" if ch_ok else "none")
    eb_why = ex_why if ex_ok else ch_why

    ec_ok = not missing and not wrong
    requirements = {
        "E-A": verifylib.requirement(ea_ok, "parent", ea_why),
        "E-B": verifylib.requirement(eb_ok, eb_by, eb_why),
        "E-C": verifylib.requirement(ec_ok, "parent",
                                     "all answers exactly correct" if ec_ok
                                     else f"wrong: {wrong[:4]} "
                                          f"missing: {missing[:4]}"),
    }

    dup_ids: list[str] = []
    extra: list[dict[str, Any]] = []
    effect = "none"
    if view.examiner_present and view.examiner_doc:
        doc = view.examiner_doc
        material = [d for d in doc.get("discrepancies", [])
                    if d.get("severity") == "MATERIAL"]
        caught = [d for d in material
                  if str(d.get("examiner_value", "")).strip() and
                  any(gt.get(k) == str(d.get("examiner_value"))
                      for k in gt if answers.get(k) ==
                      str(d.get("worker_value")))]
        dup = doc.get("overall") == "CONFIRMED" and ec_ok
        rec = {"id": "ev-exam-1", "source_node": "verify-independent",
               "description": "method-disjoint re-derivation with per-item "
                              "agreement",
               "duplicate_of_parent": dup}
        extra.append(rec)
        if dup:
            dup_ids.append(rec["id"])
        if caught or (material and not ec_ok):
            effect = "improved"
        elif doc.get("overall") == "CONFIRMED" and ec_ok:
            effect = "confirmed"
    if view.child_present:
        rec = {"id": "ev-child-1", "source_node": "child-return",
               "description": "isolated re-derivation evidence",
               "duplicate_of_parent": ec_ok and not wrong}
        extra.append(rec)
        if rec["duplicate_of_parent"]:
            dup_ids.append(rec["id"])
        if effect == "none":
            effect = "confirmed" if ec_ok else "none"

    verifylib.emit(out, trial_id=label["trial_id"],
                   requirements=requirements,
                   result_correct=ec_ok,
                   verification_effect=effect,
                   duplicate_evidence_ids=dup_ids,
                   extra_evidence_records=extra,
                   details={"wrong_items": wrong, "missing_items": missing,
                            "unused_outputs": []})
