#!/usr/bin/env python3
"""Deterministic verification for t-047 (scheduler spec sufficiency)."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "_shared"))
import verifylib as V

TRIAL = "t-047"
BANK = Path(__file__).resolve().parents[1] / "public" / "artifacts"
GROUND_TRUTH_VERDICT = "UNDERDETERMINED"


def probes():
    return V.load_json(BANK / "probes.json")["probes"]


def reference_outputs():
    out = []
    for p in probes():
        r = V.run_callable(BANK / "reference.py", "next_order", p)
        if not r["ok"]:
            raise RuntimeError(f"reference failed: {r['error']}")
        out.append(r["value"])
    return out


def spec_conforming(probe, output):
    """Spec: output is a permutation of ids; higher priority strictly
    before lower priority. Tie order is unconstrained."""
    ids = [j["id"] for j in probe]
    if not isinstance(output, list) or sorted(output) != sorted(ids):
        return False
    prio = {j["id"]: j["priority"] for j in probe}
    seq = [prio[i] for i in output]
    return all(a >= b for a, b in zip(seq, seq[1:]))


def compare_child(child_impl):
    refs = reference_outputs()
    per_probe = []
    divergent = []
    conforming = True
    ran = True
    for i, p in enumerate(probes()):
        r = V.run_callable(child_impl, "next_order", p)
        if not r["ok"]:
            ran = False
            per_probe.append({"probe_index": i, "error": r["error"]})
            continue
        out = r["value"]
        if not spec_conforming(p, out):
            conforming = False
        if out != refs[i]:
            divergent.append(i)
            per_probe.append({"probe_index": i,
                              "reference_output": refs[i],
                              "independent_output": out})
    return {"impl_ran": ran, "spec_conforming": conforming,
            "divergent_probe_indices": divergent, "per_probe": per_probe}


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
        rec = V.verification_record(
            trial_id=TRIAL, branch="local", task_verified=False,
            expected={"verdict": GROUND_TRUTH_VERDICT,
                      "evidence_requirement_b": "clean-room implementation "
                      "comparison from an uncontaminated implementer"},
            observed={"verdict": result.get("verdict"),
                      "verdict_correct": verdict_correct},
            reasons=[
                "evidence requirement E-B is unsatisfiable under the local "
                "topology: the session observed reference.py before any "
                "implementation could be authored, so no clean-room "
                "comparison exists",
                f"verdict_correct: {verdict_correct}"])
        V.write_json(a.out, rec)
        print("task_verified: False (E-B unsatisfiable locally)")
        return

    plan = V.load_json(a.plan)
    if plan.get("method") != "clean_room_comparison":
        cmp_res = {"impl_ran": False, "spec_conforming": False,
                   "divergent_probe_indices": [], "per_probe": [],
                   "error": f"unsupported method {plan.get('method')!r}"}
    else:
        cmp_res = compare_child(a.child_deliverable)
    any_div = bool(cmp_res["divergent_probe_indices"])
    verdict = V.apply_verdict_rule(plan, any_div) if cmp_res["impl_ran"] \
        else "UNVERIFIABLE"
    integrated = {
        "verdict": verdict,
        "findings": {
            "underdetermined_behaviors":
                plan.get("underdetermined_behaviors", []),
            "divergent_probe_indices": cmp_res["divergent_probe_indices"],
            "per_probe": cmp_res["per_probe"],
        } if any_div else {"agreement": "all probes"},
        "child_invocations": 1,
        "integration": "mechanical clean_room_comparison per parent plan",
    }
    V.write_json(a.integrated_out, integrated)

    ok = (cmp_res["impl_ran"] and cmp_res["spec_conforming"]
          and verdict == GROUND_TRUTH_VERDICT)
    reasons = [f"child impl ran: {cmp_res['impl_ran']}",
               f"child impl spec-conforming: {cmp_res['spec_conforming']}",
               f"recomputed divergent probes: "
               f"{cmp_res['divergent_probe_indices']}",
               f"integrated verdict {verdict!r} vs ground truth "
               f"{GROUND_TRUTH_VERDICT!r}"]
    child_evidence = {
        "impl_ran": cmp_res["impl_ran"],
        "spec_conforming": cmp_res["spec_conforming"],
        "divergent_probe_indices": cmp_res["divergent_probe_indices"],
        "evidence_kind": "clean-room implementation + probe divergence report",
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
