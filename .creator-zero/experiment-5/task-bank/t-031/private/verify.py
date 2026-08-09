#!/usr/bin/env python3
"""Deterministic verification for t-031 (codec format sufficiency)."""
import argparse
import itertools
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "_shared"))
import verifylib as V

TRIAL = "t-031"
BANK = Path(__file__).resolve().parents[1] / "public" / "artifacts"
GROUND_TRUTH_VERDICT = "UNDERDETERMINED"


def probes():
    return V.load_json(BANK / "probes.json")["probes"]


def reference_outputs():
    out = []
    for p in probes():
        r = V.run_callable(BANK / "reference.py", "encode", p)
        if not r["ok"]:
            raise RuntimeError(f"reference failed: {r['error']}")
        out.append(r["value"])
    return out


def _value_variants(s):
    """Format-conforming renderings of a value: ; and = escaping is
    mandatory; backslash escaping is unspecified (both readings allowed)."""
    mandatory = s.replace(";", "\\;").replace("=", "\\=")
    with_bs = (s.replace("\\", "\\\\").replace(";", "\\;")
                .replace("=", "\\="))
    return {mandatory, with_bs}


def format_conforming(probe, output):
    """Accept any key permutation x any allowed value-escaping reading.
    Key escaping is unspecified; probe keys contain no special chars, so
    keys render as themselves. Only checkable when variant count is small."""
    if not isinstance(output, str):
        return False
    keys = list(probe)
    variants_per_key = {k: _value_variants(probe[k]) for k in keys}
    for perm in itertools.permutations(keys):
        pools = [[f"{k}={v}" for v in sorted(variants_per_key[k])]
                 for k in perm]
        for combo in itertools.product(*pools):
            if ";".join(combo) == output:
                return True
    return False


def compare_child(child_impl):
    refs = reference_outputs()
    per_probe = []
    divergent = []
    conforming = True
    ran = True
    for i, p in enumerate(probes()):
        r = V.run_callable(child_impl, "encode", p)
        if not r["ok"]:
            ran = False
            per_probe.append({"probe_index": i, "error": r["error"]})
            continue
        out = r["value"]
        if not format_conforming(p, out):
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
               f"child impl format-conforming: {cmp_res['spec_conforming']}",
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
