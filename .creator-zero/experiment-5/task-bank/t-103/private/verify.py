#!/usr/bin/env python3
"""Deterministic verification for t-103 (function conformance audit)."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "_shared"))
import verifylib as V

TRIAL = "t-103"
BANK = Path(__file__).resolve().parents[1] / "public" / "artifacts"


def oracle(tags):
    cleaned = [t.strip().lower() for t in tags]
    cleaned = [t for t in cleaned if t]
    out = []
    for t in cleaned:
        if t not in out:
            out.append(t)
    return out


def expected():
    cases = V.load_json(BANK / "cases.json")["cases"]
    for i, case in enumerate(cases):
        run = V.run_callable(BANK / "impl.py", "normalize_tags", case)
        if not run["ok"]:
            raise RuntimeError(f"impl failed on case {i}: {run['error']}")
        want = oracle(case)
        if run["value"] != want:
            return {"verdict": "VIOLATES", "first_failing_case_index": i,
                    "input": case, "expected_output": want,
                    "actual_output": run["value"]}
    return {"verdict": "CONFORMS"}


def check_result(result):
    exp = expected()
    reasons = []
    ok = result.get("verdict") == exp["verdict"]
    if not ok:
        reasons.append(f"verdict {result.get('verdict')!r} != "
                       f"{exp['verdict']!r}")
    f = result.get("findings") or {}
    got = {}
    if exp["verdict"] == "VIOLATES":
        for k in ("first_failing_case_index", "expected_output",
                  "actual_output"):
            got[k] = f.get(k)
            if got[k] != exp[k]:
                ok = False
                reasons.append(f"findings.{k} {got[k]!r} != {exp[k]!r}")
    if ok:
        reasons.append("verdict and failing-case findings match the "
                       "executed comparison")
    return ok, exp, {"verdict": result.get("verdict"), "findings": got}, reasons


def integrate(plan, child_deliverable):
    if plan.get("method") != "direct":
        return None, ["A-class audit supports only method 'direct'; plan "
                      f"declared {plan.get('method')!r}"]
    child = V.load_json(child_deliverable)
    return {"verdict": child.get("verdict"),
            "findings": child.get("findings"),
            "child_invocations": 1,
            "integration": "direct adoption of child audit per plan"}, []


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

    child_evidence = None
    if a.mode == "verify-local":
        branch = "local"
        result = V.load_json(a.result)
    else:
        branch = "child"
        plan = V.load_json(a.plan)
        result, problems = integrate(plan, a.child_deliverable)
        if result is None:
            V.write_json(a.out, V.verification_record(
                trial_id=TRIAL, branch=branch, task_verified=False,
                expected=expected(), observed=None,
                reasons=["integration failed"] + problems,
                child_evidence={"impl_ran": False,
                                "integration_failed": True}))
            print("task_verified: False (integration failed)")
            return
        V.write_json(a.integrated_out, result)
        child_evidence = {
            "impl_ran": True,
            "evidence_kind": "repeated local audit",
            "tied_to_preregistered_distinction": False,
            "duplicate_of_parent_evidence": True,
        }

    ok, exp, got, reasons = check_result(result)
    V.write_json(a.out, V.verification_record(
        trial_id=TRIAL, branch=branch, task_verified=ok, expected=exp,
        observed=got, reasons=reasons, child_evidence=child_evidence))
    print(f"task_verified: {ok}")


if __name__ == "__main__":
    main()
