"""C2 node 2 (independent-rederivation) driver — resolves Q5, Q6, Q8, Q9.

Writes .creator-zero/experiment-4/c2/sandbox/verify-round-0.json.
Causally independent of node 1's scripts: re-derives measurements with its
own code; reads node 1's OUTPUT JSON only for the Q8 comparison against
C1's claims, never importing node 1's modules.
"""

import json
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
C1 = os.path.join(ROOT, ".creator-zero", "experiment-4", "c1")
OUT = os.path.join(ROOT, ".creator-zero", "experiment-4", "c2", "sandbox",
                   "verify-round-0.json")

report = {}

# ---------------- Q5: reproducibility ------------------------------------
sys.path.insert(0, os.path.join(ROOT, "src"))
import solver as canonical  # noqa: E402


def count_ops(n):
    jobs = [(3 * i, 3 * i + 2, 1 + (i % 3)) for i in range(n)]
    counter = [0]

    def tracer(frame, event, arg):
        counter[0] += 1
        return tracer

    previous = sys.gettrace()
    sys.settrace(tracer)
    try:
        canonical.solve(jobs)
    finally:
        sys.settrace(previous)
    return counter[0]


runs = []
for _ in range(5):
    runs.append({n: count_ops(n) for n in (8, 16, 32, 64)})
identical = all(r == runs[0] for r in runs)
ratios = {"%d->%d" % (a, b): round(runs[0][b] / runs[0][a], 2)
          for a, b in ((8, 16), (16, 32), (32, 64))}

probe_runs = []
for _ in range(5):
    p = subprocess.run([sys.executable,
                        os.path.join(ROOT, ".creator-zero", "harness",
                                     "probes.py")],
                       capture_output=True, text=True, timeout=600)
    scaling = next((l for l in p.stdout.splitlines() if "R8 empirical" in l), "")
    total = next((l for l in p.stdout.splitlines()
                  if l.startswith("PROBES total=")), "")
    probe_runs.append({"exit": p.returncode, "scaling_line": scaling,
                       "summary": total})
probe_outcomes = {(r["exit"], r["summary"]) for r in probe_runs}
scaling_ok_stable = all(r["scaling_line"].startswith("PASS")
                        for r in probe_runs)

report["q5_reproducibility"] = {
    "classification": "deterministic",
    "settrace_runs": runs,
    "settrace_bit_identical_across_5_runs": identical,
    "canonical_per_doubling_ratios": ratios,
    "probes_runs": probe_runs,
    "probes_outcome_stable": len(probe_outcomes) == 1 and scaling_ok_stable,
    "stability_verdict": ("STABLE" if identical and len(probe_outcomes) == 1
                          else "NOISY"),
    "note": "settrace counts are the candidate's actual assertion input; "
            "wall-clock r8_scaling is C1's E3 subject. Bit-identical counts "
            "mean the candidate test is deterministic given a fixed "
            "interpreter; wall-clock lines may vary in magnitude but only "
            "the ok (30s cap) outcome matters for stability.",
}

# ---------------- Q8: independence of C1's verify locus -------------------
sv = os.path.join(C1, "sandbox-verify")
import_hits = {}
for fname in ("exp_mask.py", "poly_alt.py", "run_verify.py"):
    text = open(os.path.join(sv, fname)).read()
    hits = re.findall(r"^\s*(?:from|import)\s+[^\n]*", text, re.M)
    sandbox_refs = [h for h in hits if "sandbox" in h and "sandbox-verify" not in h]
    literal_refs = "c1/sandbox/" in text.replace("\\", "/")
    import_hits[fname] = {"imports": hits, "imports_evidence_sandbox": bool(sandbox_refs),
                          "string_refs_evidence_sandbox": literal_refs}

exp_mask_src = open(os.path.join(sv, "exp_mask.py")).read()
sur_exp_src = open(os.path.join(C1, "sandbox", "surrogate_exp.py")).read()
construction_diverges = ("for mask" in exp_mask_src or "1 << " in exp_mask_src
                         or "range(1 <<" in exp_mask_src) and "def rec" in sur_exp_src

node1 = json.load(open(os.path.join(ROOT, ".creator-zero", "experiment-4",
                                    "c2", "sandbox", "evidence-round-0.json")))
vv = json.load(open(os.path.join(sv, "verify-verdict.json")))
comparison = {
    "gap_13_13": {"c1_claim": True,
                  "c2_independent": node1["q2_gap_demo"]["gap_reproduced"]},
    "no_false_positive_on_legit_polynomial": {
        "c1_claim": vv["checks"]["candidate_passes_fresh_polynomial"]["pass"],
        "c2_independent": not node1["q3_false_positive_check"]["false_positive"]},
    "exponential_flagged_by_bound": {
        "c1_claim": vv["checks"]["fresh_exponential_exceeds_bound"]["pass"],
        "c2_independent_note": "C2 did not re-run its own exp surrogate under "
                               "the counter (its class was already flagged by "
                               "C1 twice); C2's cbulk/lowbase results instead "
                               "bound the discriminator's blind spots"},
}
agreement = (comparison["gap_13_13"]["c2_independent"]
             and comparison["no_false_positive_on_legit_polynomial"]["c2_independent"])

report["q8_independence_check"] = {
    "classification": "deterministic",
    "c1_verify_imports": import_hits,
    "no_evidence_sandbox_import": not any(
        v["imports_evidence_sandbox"] or v["string_refs_evidence_sandbox"]
        for v in import_hits.values()),
    "construction_divergence_bitmask_vs_recursion": construction_diverges,
    "c2_vs_c1_claim_comparison": comparison,
    "independent_agreement": agreement,
    "caveat": "artifact-level independence within C1 is real (verify re-authored "
              "its surrogates; no imports from the evidence sandbox), but ALL "
              "C1 loci share one authoring mind; the operative independence "
              "evidence is C2's own from-scratch agreement, plus the "
              "ledger-vs-artifact narrative discrepancies node 1 found "
              "(instances 13825 vs 1885; ratios 100.4-373.5 vs 149.3/660.2), "
              "which undermine the ledger narrative's precision but not the "
              "artifact-level measurements.",
}

# ---------------- Q9: candidate flakiness ---------------------------------
staged = os.path.join(HERE, "staged")
shutil.rmtree(staged, ignore_errors=True)
os.makedirs(os.path.join(staged, "src"))
os.makedirs(os.path.join(staged, "tests"))
shutil.copy(os.path.join(ROOT, "src", "solver.py"),
            os.path.join(staged, "src", "solver.py"))
shutil.copy(os.path.join(C1, "candidate", "test_solver.py"),
            os.path.join(staged, "tests", "test_solver.py"))
q9_runs = []
for _ in range(10):
    p = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s",
                        os.path.join(staged, "tests")],
                       capture_output=True, text=True, timeout=300)
    tail = p.stderr.strip().splitlines()[-1] if p.stderr.strip() else ""
    q9_runs.append({"exit": p.returncode, "tail": tail})
all_pass = all(r["exit"] == 0 and r["tail"] == "OK" for r in q9_runs)
report["q9_flakiness_check"] = {
    "classification": "deterministic",
    "runs": q9_runs,
    "all_10_pass": all_pass,
    "verdict": "NON_FLAKY" if all_pass else "FLAKY",
}

# ---------------- Q6: protection judgment (model_judgment by C2) ----------
report["q6_protection_judgment"] = {
    "classification": "model_judgment",
    "residual_uncaught_shapes": [
        "low-base exponential (e.g. 1.02^n busy work): measured MISSED at "
        "n<=64 (q4a); C1's E10(a) concedes this and it is unavoidable for "
        "any fixed finite test (E8, logically sound)",
        "super-polynomial work executed inside C-level builtins: measured "
        "INVISIBLE to the trace-event counter (q4b); C1's E10(b) concedes "
        "tracer blindness but NOT the concrete failure mode that such a "
        "regression makes the candidate test HANG at n=64 rather than fail "
        "- in CI this surfaces as a timeout, which still flags the "
        "regression operationally but not via the assertion path C1 "
        "describes",
        "legitimate polynomial of degree > 5 would false-positive the "
        "bound-32 test; C1's E10(c) concedes this; C2 measured a fresh "
        "degree-3 rewrite at max ratio 5.87 (5.4x headroom), consistent "
        "with C1's headroom claim but the degree->ratio mapping means a "
        "legitimate O(n^6+) rewrite (unusual for this problem) would be "
        "wrongly rejected",
    ],
    "judgment": "QUALIFIED_PROTECTION",
    "detail": "The candidate test genuinely discriminates the violation "
              "class R8 names (Python-level exhaustive enumeration) with "
              "reproducible, wall-clock-free counts, no observed false "
              "positive on two structurally distinct legitimate rewrites "
              "(C1's control + C2's), and fail-fast behavior on the named "
              "class. 'Protected' is fair ONLY as scoped by C1's E8/E10: "
              "protection against the named class, not general R8-runtime "
              "enforcement. The claim as recorded in C1's evidence.json IS "
              "so scoped; the scoping must survive into any promotion "
              "record. One addition C1's record lacks: the hang (not fail) "
              "mode on C-level regressions, and the test's dependence on "
              "CPython settrace semantics (a PyPy/JIT environment could "
              "change counts - though ratios, not absolute counts, are "
              "asserted, and the suite is CPython-targeted).",
}

with open(OUT, "w") as f:
    json.dump(report, f, indent=2)
print("WROTE", OUT)
print(json.dumps({"q5_stable": report["q5_reproducibility"]["stability_verdict"],
                  "settrace_identical": identical,
                  "probes_stable": report["q5_reproducibility"]["probes_outcome_stable"],
                  "q8_agreement": agreement,
                  "q8_no_sandbox_import": report["q8_independence_check"]["no_evidence_sandbox_import"],
                  "q9": report["q9_flakiness_check"]["verdict"]}, indent=1))
