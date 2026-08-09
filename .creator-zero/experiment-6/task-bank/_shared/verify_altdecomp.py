"""Class verifier: complete-enumeration tasks where the completeness claim
is admissible only when supported by two enumerations of the space produced
without access to each other. Integration = canonical union with
sole-source flags; ground truth is the frozen full enumeration.

Label parameters:
    ground_truth_items   canonical item strings (full enumeration)
    items_field          result.json field with the worker's enumeration
    canonicalizer        one of the built-ins below
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Optional

import verifylib


def _canon_sorted_list(x: Any) -> Optional[str]:
    """Item is a list (e.g. a vertex set / path); canonical = JSON of the
    item with inner lists sorted where order is not meaningful."""
    if isinstance(x, list):
        try:
            return json.dumps(sorted(str(v) for v in x))
        except TypeError:
            return None
    if isinstance(x, str):
        return json.dumps(sorted(x.split("-"))) if "-" in x else \
            json.dumps([x])
    return None


def _canon_string(x: Any) -> Optional[str]:
    return str(x) if isinstance(x, (str, int, float)) else (
        json.dumps(x) if isinstance(x, list) else None)


def _canon_partition(x: Any) -> Optional[str]:
    """Item is {'layer1': [...], 'layer2': [...]} (or a 2-list)."""
    if isinstance(x, dict) and {"layer1", "layer2"} <= set(x):
        return json.dumps([sorted(map(str, x["layer1"])),
                           sorted(map(str, x["layer2"]))])
    if isinstance(x, list) and len(x) == 2:
        return json.dumps([sorted(map(str, x[0])), sorted(map(str, x[1]))])
    return None


CANONICALIZERS = {
    "sorted_list": _canon_sorted_list,
    "string": _canon_string,
    "partition": _canon_partition,
}


def _canon_set(items: Any, canon) -> tuple[set[str], list[Any]]:
    good, bad = set(), []
    if not isinstance(items, list):
        return good, [items]
    for x in items:
        c = canon(x)
        if c is None:
            bad.append(x)
        else:
            good.add(c)
    return good, bad


def run(td: Path, out: Path, label: dict[str, Any], bank_public: Path
        ) -> None:
    view = verifylib.load(td)
    canon = CANONICALIZERS[label["canonicalizer"]]
    gt = set(label["ground_truth_items"])
    result = view.result or {}

    parent_items, parent_bad = _canon_set(result.get(label["items_field"]),
                                          canon)
    parent_valid = parent_items & gt
    parent_invalid = (parent_items - gt) or set(map(str, parent_bad))
    ea_ok = bool(parent_valid) and not parent_invalid and \
        bool(str(result.get("method", "")).strip())
    ea_why = (f"{len(parent_valid)}/{len(gt)} valid items, "
              f"{len(parent_invalid)} invalid")

    ch_ok, ch_why = verifylib.child_with_role(view, "independent_decomposer")
    child_items: set[str] = set()
    if ch_ok and view.child_plan:
        deliv = view.child_file(view.child_plan.get("child_deliverable", ""))
        if deliv and deliv.suffix == ".json":
            try:
                doc = json.loads(deliv.read_text(encoding="utf-8"))
                raw = doc.get(label["items_field"]) or doc.get("items")
                child_items, child_bad = _canon_set(raw, canon)
                if (child_items - gt) or child_bad:
                    ch_ok = False
                    ch_why = ("second enumeration contains invalid items: "
                              f"{sorted(child_items - gt)[:3]}")
            except json.JSONDecodeError:
                ch_ok = False
                ch_why = "second enumeration not parseable"
        else:
            ch_ok = False
            ch_why = "no enumeration deliverable returned"
    eb_ok = ch_ok and bool(child_items)
    eb_why = ch_why if not eb_ok else \
        f"independent enumeration with {len(child_items)} valid items"

    union = parent_valid | (child_items & gt)
    ec_ok = eb_ok and union == gt
    ec_why = (f"union covers {len(union)}/{len(gt)}"
              if eb_ok else "completeness inadmissible without the second "
                            "enumeration")

    if eb_ok:
        final = dict(result)
        final[label["items_field"]] = sorted(union)
        final["sole_source_items"] = {
            "first_only": sorted(parent_valid - child_items),
            "second_only": sorted(child_items - parent_valid)}
        final["complete"] = union == gt
        (td / "result-final.json").write_text(
            json.dumps(final, indent=2) + "\n", encoding="utf-8")

    requirements = {
        "E-A": verifylib.requirement(ea_ok, "parent", ea_why),
        "E-B": verifylib.requirement(eb_ok, "child", eb_why),
        "E-C": verifylib.requirement(ec_ok, "integration", ec_why),
    }

    dup_ids: list[str] = []
    extra: list[dict[str, Any]] = []
    if view.child_present:
        dup = bool(child_items) and child_items <= parent_valid
        rec = {"id": "ev-child-1", "source_node": "child-return",
               "description": "independently produced enumeration",
               "duplicate_of_parent": dup}
        extra.append(rec)
        if dup:
            dup_ids.append(rec["id"])
    if view.examiner_present:
        rec = {"id": "ev-exam-1", "source_node": "verify-independent",
               "description": "examiner re-check (saw the first enumeration"
                              ": not an admissible second path)",
               "duplicate_of_parent": True}
        extra.append(rec)
        dup_ids.append(rec["id"])

    coverage_gain = (len(union) - len(parent_valid)) / len(gt) if gt else 0.0
    effect = ("improved" if eb_ok and (child_items - parent_valid)
              else ("confirmed" if ec_ok else
                    ("impossible" if not view.child_present else "none")))

    verifylib.emit(out, trial_id=label["trial_id"],
                   requirements=requirements,
                   result_correct=union == gt if eb_ok else
                   (parent_valid == gt and not parent_invalid),
                   verification_effect=effect,
                   duplicate_evidence_ids=dup_ids,
                   extra_evidence_records=extra,
                   details={"coverage_gain": round(coverage_gain, 4),
                            "parent_found": len(parent_valid),
                            "child_found": len(child_items),
                            "ground_truth_size": len(gt),
                            "unused_outputs": []})
