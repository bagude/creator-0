#!/usr/bin/env python3
"""Deterministic verification for t-068 (term-index rules sufficiency)."""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "_shared"))
import verifylib as V

TRIAL = "t-068"
BANK = Path(__file__).resolve().parents[1] / "public" / "artifacts"
GROUND_TRUTH_VERDICT = "UNDERDETERMINED"


def document():
    return (BANK / "document.txt").read_text(encoding="utf-8")


def true_occurrences():
    """Rules-determined mapping term -> ascending 0-based line numbers."""
    occ = {}
    for lineno, line in enumerate(document().splitlines()):
        for raw in line.split():
            term = raw.lower().strip(".,;:")
            if term:
                occ.setdefault(term, [])
                if lineno not in occ[term]:
                    occ[term].append(lineno)
    return {t: sorted(v) for t, v in occ.items()}


def reference_output():
    r = V.run_callable(BANK / "reference.py", "build_index", document())
    if not r["ok"]:
        raise RuntimeError(f"reference failed: {r['error']}")
    return r["value"]


def rules_conforming(output):
    """Accept any term ordering and either 0- or 1-based numbering, but the
    term set and per-term occurrence sets must match the rules exactly."""
    if not isinstance(output, str):
        return False, "output is not a string"
    truth = true_occurrences()
    parsed = {}
    for line in output.splitlines():
        if not line.strip():
            continue
        m = re.match(r"^(.+?):\s*([0-9]+(?:\s*,\s*[0-9]+)*)$", line)
        if not m:
            return False, f"line not in 'term: n1,n2' form: {line!r}"
        term = m.group(1).strip()
        nums = [int(x) for x in re.split(r"\s*,\s*", m.group(2))]
        if term in parsed:
            return False, f"duplicate term line: {term!r}"
        parsed[term] = nums
    if set(parsed) != set(truth):
        return False, (f"term set mismatch: extra={sorted(set(parsed)-set(truth))} "
                       f"missing={sorted(set(truth)-set(parsed))}")
    for base in (0, 1):
        if all(parsed[t] == [n + base for n in truth[t]] for t in truth):
            return True, f"occurrences match with {base}-based numbering"
    return False, "occurrence lists match neither 0- nor 1-based numbering"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["verify-local", "integrate-and-verify"],
                    required=True)
    ap.add_argument("--result")
    ap.add_argument("--plan")
    ap.add_argument("--child-deliverable")
    ap.add_argument("--integrated-out")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    if a.mode == "verify-local":
        result = V.load_json(a.result)
        verdict_correct = result.get("verdict") == GROUND_TRUTH_VERDICT
        V.write_json(a.out, V.verification_record(
            trial_id=TRIAL, branch="local", task_verified=False,
            expected={"verdict": GROUND_TRUTH_VERDICT,
                      "evidence_requirement_b": "clean-room implementation "
                      "comparison from an uncontaminated implementer"},
            observed={"verdict": result.get("verdict"),
                      "verdict_correct": verdict_correct},
            reasons=[
                "evidence requirement E-B is unsatisfiable under the local "
                "topology: the session observed reference.py before any "
                "implementation could be authored",
                f"verdict_correct: {verdict_correct}"]))
        print("task_verified: False (E-B unsatisfiable locally)")
        return

    plan = V.load_json(a.plan)
    ref = reference_output()
    impl_ran = False
    conforming = False
    conform_reason = "impl not run"
    diff = {"matches": False}
    if plan.get("method") == "clean_room_comparison":
        r = V.run_callable(a.child_deliverable, "build_index", document())
        if r["ok"] and isinstance(r["value"], str):
            impl_ran = True
            conforming, conform_reason = rules_conforming(r["value"])
            diff = V.first_diff_lines(ref, r["value"])
    any_div = not diff.get("matches", False)
    verdict = V.apply_verdict_rule(plan, any_div) if impl_ran \
        else "UNVERIFIABLE"
    integrated = {
        "verdict": verdict,
        "findings": {
            "underdetermined_behaviors":
                plan.get("underdetermined_behaviors", []),
            "comparison": {
                "matches_reference": diff.get("matches", False),
                "first_differing_line": diff.get("first_differing_line"),
                "reference_line": diff.get("a_line"),
                "independent_line": diff.get("b_line"),
            },
        } if any_div else {"matches_reference": True},
        "child_invocations": 1,
        "integration": "mechanical clean_room_comparison per parent plan",
    }
    V.write_json(a.integrated_out, integrated)

    ok = impl_ran and conforming and verdict == GROUND_TRUTH_VERDICT
    reasons = [f"child impl ran: {impl_ran}",
               f"child impl rules-conforming: {conforming} "
               f"({conform_reason})",
               f"matches reference byte-for-byte: "
               f"{diff.get('matches', False)}",
               f"integrated verdict {verdict!r} vs ground truth "
               f"{GROUND_TRUTH_VERDICT!r}"]
    child_evidence = {
        "impl_ran": impl_ran,
        "spec_conforming": conforming,
        "matches_reference": diff.get("matches", False),
        "evidence_kind": "clean-room implementation + output diff vs "
                         "reference",
        "tied_to_preregistered_distinction": True,
        "duplicate_of_parent_evidence": False,
    }
    V.write_json(a.out, V.verification_record(
        trial_id=TRIAL, branch="child", task_verified=ok,
        expected={"verdict": GROUND_TRUTH_VERDICT},
        observed={"verdict": verdict}, reasons=reasons,
        child_evidence=child_evidence))
    print(f"task_verified: {ok}")


if __name__ == "__main__":
    main()
