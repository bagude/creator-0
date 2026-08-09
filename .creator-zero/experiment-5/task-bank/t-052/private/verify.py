#!/usr/bin/env python3
"""Deterministic verification for t-052 (dependency-order audit)."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "_shared"))
import verifylib as V

TRIAL = "t-052"
BANK = Path(__file__).resolve().parents[1] / "public" / "artifacts"


def expected():
    plan = V.load_json(BANK / "plan.json")["tasks"]
    log = V.load_json(BANK / "log.json")["executions"]
    done = set()
    for i, t in enumerate(log):
        unmet = sorted(set(plan[t]["deps"]) - done)
        if unmet:
            return {"verdict": "MISORDERED", "first_misordered_index": i,
                    "task": t, "unmet_dependencies": unmet}
        done.add(t)
    return {"verdict": "WELL_ORDERED"}


def check_result(result):
    exp = expected()
    reasons = []
    ok = result.get("verdict") == exp["verdict"]
    if not ok:
        reasons.append(f"verdict {result.get('verdict')!r} != "
                       f"{exp['verdict']!r}")
    f = result.get("findings") or {}
    got = {}
    if exp["verdict"] == "MISORDERED":
        for k in ("first_misordered_index", "task", "unmet_dependencies"):
            got[k] = f.get(k)
            want = exp[k]
            gv = sorted(got[k]) if k == "unmet_dependencies" and \
                isinstance(got[k], list) else got[k]
            if gv != want:
                ok = False
                reasons.append(f"findings.{k} {got[k]!r} != {want!r}")
    if ok:
        reasons.append("verdict and misorder findings match the simulation")
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
