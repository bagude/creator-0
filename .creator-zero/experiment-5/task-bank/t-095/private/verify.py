#!/usr/bin/env python3
"""Deterministic verification for t-095 (build-notes reconstruction)."""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "_shared"))
import verifylib as V

TRIAL = "t-095"
BANK = Path(__file__).resolve().parents[1] / "public" / "artifacts"
GROUND_TRUTH_VERDICT = "UNDERDETERMINED"
TOTALS = {"north": 120.50, "south": 95.25, "east": 150.00, "west": 88.75}


def notes_conforming(text):
    """The notes determine the content modulo ordering/casing/formatting:
    one line per active region, 'REGION: TOTAL', totals numerically equal."""
    lines = [l for l in text.splitlines() if l.strip()]
    if len(lines) != len(TOTALS):
        return False, f"expected {len(TOTALS)} region lines, got {len(lines)}"
    seen = {}
    for l in lines:
        m = re.match(r"^\s*([A-Za-z]+)\s*:\s*([0-9.]+)\s*$", l)
        if not m:
            return False, f"line not in REGION: TOTAL form: {l!r}"
        region = m.group(1).lower()
        try:
            total = float(m.group(2))
        except ValueError:
            return False, f"unparseable total in line: {l!r}"
        seen[region] = total
    if set(seen) != set(TOTALS):
        return False, f"regions {sorted(seen)} != {sorted(TOTALS)}"
    for r, t in TOTALS.items():
        if abs(seen[r] - t) > 1e-9:
            return False, f"total for {r}: {seen[r]} != {t}"
    return True, "content matches the notes-determined totals"


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
                      "evidence_requirement_b": "reproduction by a producer "
                      "who has never seen summary.txt"},
            observed={"verdict": result.get("verdict"),
                      "verdict_correct": verdict_correct},
            reasons=[
                "evidence requirement E-B is unsatisfiable under the local "
                "topology: the session observed summary.txt before any "
                "reproduction could be authored",
                f"verdict_correct: {verdict_correct}"]))
        print("task_verified: False (E-B unsatisfiable locally)")
        return

    plan = V.load_json(a.plan)
    target = (BANK / "summary.txt").read_text(encoding="utf-8")
    csv_text = (BANK / "records.csv").read_text(encoding="utf-8")
    impl_ran = False
    conforming = False
    conform_reason = "impl not run"
    diff = {"matches": False}
    reproduced = None
    if plan.get("method") == "clean_room_comparison":
        r = V.run_callable(a.child_deliverable, "produce_summary", csv_text)
        if r["ok"] and isinstance(r["value"], str):
            impl_ran = True
            reproduced = r["value"]
            conforming, conform_reason = notes_conforming(reproduced)
            diff = V.first_diff_lines(target, reproduced)
    any_div = not diff.get("matches", False)
    verdict = V.apply_verdict_rule(plan, any_div) if impl_ran \
        else "UNVERIFIABLE"
    integrated = {
        "verdict": verdict,
        "findings": {
            "underdetermined_aspects":
                plan.get("underdetermined_behaviors", []),
            "reproduction_diff": {
                "matches_target": diff.get("matches", False),
                "first_differing_line": diff.get("first_differing_line"),
                "target_line": diff.get("a_line"),
                "reproduced_line": diff.get("b_line"),
            },
        } if any_div else {"matches_target": True},
        "child_invocations": 1,
        "integration": "mechanical clean_room_comparison per parent plan",
    }
    V.write_json(a.integrated_out, integrated)

    ok = impl_ran and conforming and verdict == GROUND_TRUTH_VERDICT
    reasons = [f"child impl ran: {impl_ran}",
               f"child reproduction notes-conforming: {conforming} "
               f"({conform_reason})",
               f"byte-identical to target: {diff.get('matches', False)}",
               f"integrated verdict {verdict!r} vs ground truth "
               f"{GROUND_TRUTH_VERDICT!r}"]
    child_evidence = {
        "impl_ran": impl_ran,
        "spec_conforming": conforming,
        "matches_target": diff.get("matches", False),
        "evidence_kind": "clean-room reproduction + byte diff vs target",
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
