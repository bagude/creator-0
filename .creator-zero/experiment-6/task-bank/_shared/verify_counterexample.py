"""Class verifier: claim audits where a plausible answer exists but the
truth turns on finding (or excluding) a violating input. The violating
input is self-certifying: the verifier re-executes the property check on
the reported witness mechanically, whatever path produced it.

Label parameters:
    checker            one of the built-in property checkers below
    verdict            ground truth HOLDS | VIOLATED
    witness_field      result.json field carrying the violating input
    analysis_patterns  regex groups for E-A
"""
from __future__ import annotations
import json
import re
from pathlib import Path
from typing import Any, Optional

import verifylib


# ---------------------------------------------------------------- checkers
def _check_interval_merge(witness: Any, bank_public: Path) -> tuple[bool, str]:
    """True iff the witness violates: merged output has no two intervals
    i<j with intervals[i][1] >= intervals[j][0] (post-sort)."""
    fn = verifylib.load_py_function(bank_public / "artifacts" / "merge.py",
                                    "merge")
    try:
        ivs = [[int(a), int(b)] for a, b in witness]
    except (TypeError, ValueError):
        return False, "witness is not a list of integer pairs"
    out = fn(ivs)
    out_sorted = sorted(out)
    for i in range(len(out_sorted) - 1):
        if out_sorted[i][1] >= out_sorted[i + 1][0]:
            return True, (f"merge({ivs}) = {out}: intervals "
                          f"{out_sorted[i]} and {out_sorted[i+1]} touch or "
                          "overlap")
    return False, f"merge({ivs}) = {out}: property holds on this input"


def _check_discount(witness: Any, bank_public: Path) -> tuple[bool, str]:
    """True iff the witness cart's total discount exceeds 40% under the
    frozen rule semantics of rules.md."""
    if not isinstance(witness, dict):
        return False, "witness cart is not an object"
    qty = int(witness.get("quantity", 0))
    loyalty = bool(witness.get("loyalty_member", False))
    category = str(witness.get("category", ""))
    coupon = bool(witness.get("coupon_code_applied", False))
    factor = 1.0
    if qty >= 5:
        factor *= 0.90
    if loyalty:
        factor *= 0.85
    if category == "outdoor":
        factor *= 0.80
    if coupon:
        factor *= 0.95
    discount = 1.0 - factor
    return (discount > 0.40 + 1e-12,
            f"cart {witness}: total discount {discount:.4%}")


def _check_dateadd(witness: Any, bank_public: Path) -> tuple[bool, str]:
    """True iff add_days(d, n) differs from the true Gregorian result."""
    import datetime as _dt
    fn = verifylib.load_py_function(bank_public / "artifacts" / "dateadd.py",
                                    "add_days")
    try:
        d, n = witness
        base = _dt.date.fromisoformat(str(d))
        n = int(n)
    except (TypeError, ValueError):
        return False, "witness is not [iso-date, n]"
    if not (2023 <= base.year <= 2025 and 0 <= n <= 60):
        return False, "witness outside the claimed domain"
    truth = (base + _dt.timedelta(days=n)).isoformat()
    got = fn(str(d), n)
    return (got != truth,
            f"add_days({d}, {n}) = {got}, Gregorian truth {truth}")


def _check_tokenizer(witness: Any, bank_public: Path) -> tuple[bool, str]:
    """True iff tokenize(detokenize(ts)) != ts for the witness token list
    inside the claimed domain."""
    tok = verifylib.load_py_function(bank_public / "artifacts" / "tok.py",
                                     "tokenize")
    detok = verifylib.load_py_function(bank_public / "artifacts" / "tok.py",
                                       "detokenize")
    if not (isinstance(witness, list) and
            1 <= len(witness) <= 3 and
            all(isinstance(t, str) and 1 <= len(t) <= 3 and
                all(c in 'ab"\\' for c in t) for t in witness)):
        return False, "witness outside the claimed domain"
    s = detok(witness)
    back = tok(s)
    return (back != witness,
            f"detokenize({witness!r}) = {s!r}; tokenize -> {back!r}")


CHECKERS = {
    "interval_merge": _check_interval_merge,
    "discount": _check_discount,
    "dateadd": _check_dateadd,
    "tokenizer": _check_tokenizer,
}


def _witness_from(view: verifylib.TrialView, field: str
                  ) -> tuple[Optional[Any], str]:
    r = view.result or {}
    w = r.get(field)
    if w not in (None, "PENDING-INTEGRATION"):
        return w, "parent"
    # child search report
    if view.child_plan:
        deliv = view.child_file(view.child_plan.get("child_deliverable", ""))
        if deliv and deliv.suffix == ".json":
            try:
                doc = json.loads(deliv.read_text(encoding="utf-8"))
                w = doc.get(field) or doc.get("witness") or \
                    doc.get("violating_input")
                if w is not None:
                    return w, "child"
            except json.JSONDecodeError:
                pass
    if view.examiner_doc:
        for d in view.examiner_doc.get("discrepancies", []):
            ev = d.get("evidence")
            if isinstance(ev, (list, dict)):
                return ev, "examiner"
    return None, "none"


def run(td: Path, out: Path, label: dict[str, Any], bank_public: Path
        ) -> None:
    view = verifylib.load(td)
    checker = CHECKERS[label["checker"]]
    result = view.result or {}

    text = verifylib.findings_text(view)
    groups = label["analysis_patterns"]
    hit = [any(re.search(p, text, re.IGNORECASE) for p in g) for g in groups]
    ea_ok = all(hit)

    # E-B: a distinct search path (examiner, or child in adversarial role)
    ex_ok, ex_why = verifylib.examiner_ok(view)
    ch_ok, ch_why = verifylib.child_with_role(view, "adversarial_searcher")
    eb_ok = ex_ok or ch_ok
    eb_by = "examiner" if ex_ok else ("child" if ch_ok else "none")
    eb_why = ex_why if ex_ok else ch_why

    # E-C: verdict + mechanically validated witness
    verdict = result.get("verdict")
    witness, source = _witness_from(view, label["witness_field"])
    violated, check_why = (checker(witness, bank_public)
                           if witness is not None else
                           (False, "no violating input reported"))
    gt = label["verdict"]
    if gt == "VIOLATED":
        ec_ok = (verdict == "VIOLATED" and violated)
    else:
        ec_ok = (verdict == "HOLDS" and witness is None)
    ec_by = source if (ec_ok and source != "none") else \
        ("parent" if ec_ok else "none")
    ec_why = f"verdict {verdict} vs ground truth {gt}; {check_why}"

    requirements = {
        "E-A": verifylib.requirement(ea_ok, "parent",
                                     f"{sum(hit)}/{len(groups)} seeded "
                                     "input classes identified"),
        "E-B": verifylib.requirement(eb_ok, eb_by, eb_why),
        "E-C": verifylib.requirement(ec_ok, ec_by, ec_why),
    }

    dup_ids: list[str] = []
    extra: list[dict[str, Any]] = []
    parent_had = (result.get(label["witness_field"])
                  not in (None, "PENDING-INTEGRATION")) and violated \
        and source == "parent"
    if view.examiner_present and view.examiner_doc:
        adds = source == "examiner" or \
            view.examiner_doc.get("overall") == "DISPUTED"
        rec = {"id": "ev-exam-1", "source_node": "verify-independent",
               "description": "distinct search over the claim",
               "duplicate_of_parent": bool(parent_had and not adds)}
        extra.append(rec)
        if rec["duplicate_of_parent"]:
            dup_ids.append(rec["id"])
    if view.child_present:
        adds = source == "child"
        rec = {"id": "ev-child-1", "source_node": "child-return",
               "description": "isolated adversarial search evidence",
               "duplicate_of_parent": bool(parent_had and not adds)}
        extra.append(rec)
        if rec["duplicate_of_parent"]:
            dup_ids.append(rec["id"])

    if ec_ok and source in ("child", "examiner"):
        effect = "improved"
    elif ec_ok and eb_ok:
        effect = "confirmed"
    elif ec_ok:
        effect = "none"
    else:
        effect = "none"

    verifylib.emit(out, trial_id=label["trial_id"],
                   requirements=requirements,
                   result_correct=ec_ok,
                   verification_effect=effect,
                   duplicate_evidence_ids=dup_ids,
                   extra_evidence_records=extra,
                   details={"witness": witness, "witness_source": source,
                            "witness_check": check_why,
                            "unused_outputs": []})
