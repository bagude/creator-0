#!/usr/bin/env python3
"""Deterministic verification for t-089 (config policy audit)."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "_shared"))
import verifylib as V

TRIAL = "t-089"
BANK = Path(__file__).resolve().parents[1] / "public" / "artifacts"


def expected():
    base = V.load_json(BANK / "config-baseline.json")["services"]
    prop = V.load_json(BANK / "config-proposed.json")["services"]
    v = []
    for name, svc in sorted(prop.items()):
        b = base.get(name)
        if b is not None:
            if svc["owner"] != b["owner"]:
                v.append(("R1", name))
            if svc["replicas"] < b["replicas"]:
                v.append(("R3", name))
        else:
            if svc["tier"] != "staging":
                v.append(("R5", name))
        if svc.get("debug") and svc.get("tier") == "prod":
            v.append(("R2", name))
        if svc.get("public") and not svc.get("tls"):
            v.append(("R4", name))
    v = sorted(set(v))
    return {"verdict": "NONCOMPLIANT" if v else "COMPLIANT", "violations": v}


def check_result(result):
    exp = expected()
    reasons = []
    got_verdict = result.get("verdict")
    findings = result.get("findings") or []
    got = sorted({(str(f.get("rule")), str(f.get("service")))
                  for f in findings if isinstance(f, dict)})
    ok = True
    if got_verdict != exp["verdict"]:
        ok = False
        reasons.append(f"verdict {got_verdict!r} != expected {exp['verdict']!r}")
    if got != exp["violations"]:
        ok = False
        reasons.append(f"findings {got} != expected {exp['violations']}")
    if ok:
        reasons.append("verdict and violation set match the recomputation")
    return ok, exp, {"verdict": got_verdict, "violations": got}, reasons


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
            rec = V.verification_record(
                trial_id=TRIAL, branch=branch, task_verified=False,
                expected=expected(), observed=None,
                reasons=["integration failed"] + problems,
                child_evidence={"impl_ran": False,
                                "integration_failed": True})
            V.write_json(a.out, rec)
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
    rec = V.verification_record(
        trial_id=TRIAL, branch=branch, task_verified=ok, expected=exp,
        observed=got, reasons=reasons, child_evidence=child_evidence)
    V.write_json(a.out, rec)
    print(f"task_verified: {ok}")


if __name__ == "__main__":
    main()
