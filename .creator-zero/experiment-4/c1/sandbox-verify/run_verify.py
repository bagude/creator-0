"""verify-candidate node driver (deterministic script, causally distinct).

Re-derives every check from docs/solver_spec.md + oracle enumeration; reuses
NOTHING from c1/sandbox/ except reading the recorded bound/schedule to check
the candidate implements its own specification. Writes only under
c1/sandbox-verify/. Emits verify-verdict.json (sole Gate input).
"""

import importlib.util
import itertools
import json
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.abspath(os.path.dirname(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
CAND = os.path.join(ROOT, ".creator-zero", "experiment-4", "c1", "candidate", "test_solver.py")


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


oracle = load("v_oracle", os.path.join(ROOT, ".creator-zero", "harness", "oracle.py"))
exp_mask = load("v_exp_mask", os.path.join(HERE, "exp_mask.py"))
poly_alt = load("v_poly_alt", os.path.join(HERE, "poly_alt.py"))

checks = {}


def stage(src_solver_path, tag):
    d = os.path.join(HERE, "stage-" + tag)
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(os.path.join(d, "src"))
    os.makedirs(os.path.join(d, "tests"))
    shutil.copyfile(src_solver_path, os.path.join(d, "src", "solver.py"))
    shutil.copyfile(CAND, os.path.join(d, "tests", "test_solver.py"))
    return d


def run_suite(d, timeout):
    p = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
                       cwd=d, capture_output=True, text=True, timeout=timeout)
    ran = len(re.findall(r"^test_\w+ \(", p.stderr, re.M))
    failed = re.findall(r"^(?:FAIL|ERROR): (test_\w+)", p.stderr, re.M)
    return p.returncode, ran, failed, p.stderr.strip().splitlines()[-1]


# (0) fresh-surrogate admissibility: both re-derived implementations must agree
# with oracle enumeration (R5 + R6) on a bounded exhaustive grid, and reject
# invalid inputs per R1.
mism = {"exp_mask": 0, "poly_alt": 0}
checked = 0
coords = [0, 1, 2, 3]
jobset = [(s, e, w) for s in coords for e in coords if e > s for w in (1, 2)]
for n in (0, 1, 2, 3):
    for combo in ([()] if n == 0 else itertools.product(jobset, repeat=n)):
        jobs = list(combo)
        want = oracle.oracle_solve(jobs)
        want = (want[0], want[1])
        if exp_mask.solve(list(jobs)) != want:
            mism["exp_mask"] += 1
        if poly_alt.solve(list(jobs)) != want:
            mism["poly_alt"] += 1
        checked += 1
bad_inputs = [((0, 1, 1),), [(2, 2, 1)], [(0, 1, 0)], [(False, True, 3)], [(0, 1.5, 1)], [5], None, [(3, 1, 1)]]
rej = {"exp_mask": 0, "poly_alt": 0}
for b in bad_inputs:
    for tag, mod in (("exp_mask", exp_mask), ("poly_alt", poly_alt)):
        try:
            mod.solve(b)
        except ValueError:
            rej[tag] += 1
        except Exception:
            pass
checks["fresh_surrogate_admissibility"] = {
    "pass": mism["exp_mask"] == 0 and mism["poly_alt"] == 0
            and rej["exp_mask"] == len(bad_inputs) and rej["poly_alt"] == len(bad_inputs),
    "instances": checked, "mismatches": mism,
    "r1_rejections": {k: "%d/%d" % (v, len(bad_inputs)) for k, v in rej.items()},
}

# (i) candidate staged with canonical solver: 14/14 PASS.
d = stage(os.path.join(ROOT, "src", "solver.py"), "canonical")
code, ran, failed, tail = run_suite(d, 300)
checks["candidate_with_canonical_14_14"] = {
    "pass": code == 0 and ran == 14 and not failed,
    "exit": code, "tests_run": ran, "failures": failed, "tail": tail,
}

# (ii) fresh exponential surrogate: independent capped-schedule instrumentation
# must exceed the candidate's recorded bound at every doubling...
def count_ops(fn, jobs):
    c = [0]
    def tracer(frame, event, arg):
        c[0] += 1
        return tracer
    old = sys.gettrace()
    sys.settrace(tracer)
    try:
        fn(jobs)
    finally:
        sys.settrace(old)
    return c[0]

def inst(n):
    return [(3 * i, 3 * i + 2, 1 + (i % 3)) for i in range(n)]

BOUND = 32           # re-read below from candidate source to confirm identity
CAP_SCHEDULE = [6, 8, 12, 16]   # capped: 2^n work beyond ~16 is intractable by
                                 # construction of the violation class itself;
                                 # polynomial ratios are degree-bounded at every
                                 # n, so small-n doublings lose no discrimination
counts = {n: count_ops(exp_mask.solve, inst(n)) for n in CAP_SCHEDULE}
counts2 = {n: count_ops(exp_mask.solve, inst(n)) for n in CAP_SCHEDULE}
ratios = {"%d->%d" % (a, b): counts[b] / counts[a]
          for a, b in [(6, 12), (8, 16)]}
checks["fresh_exponential_exceeds_bound"] = {
    "pass": all(r > BOUND for r in ratios.values()) and counts == counts2,
    "counts": counts, "ratios": {k: round(v, 1) for k, v in ratios.items()},
    "bound": BOUND, "reproducible": counts == counts2,
    "schedule_cap_rationale": "2^n trace events at the candidate's n=64 cannot execute; per-doubling ratios of any polynomial are bounded (~2^degree) at every n, so exceeding the bound at n<=16 doublings is the same discrimination the full schedule would give",
}

# (ii-supplementary) run the staged candidate suite directly against the fresh
# exponential surrogate: incremental per-doubling assertions must make the new
# test FAIL cleanly at n=16 without hanging (subprocess timeout as safety net).
d = stage(os.path.join(HERE, "exp_mask.py"), "expmask")
try:
    code, ran, failed, tail = run_suite(d, 240)
    checks["candidate_fails_fresh_exponential"] = {
        "pass": code != 0 and failed == ["test_r8_operation_growth_is_polynomial"],
        "exit": code, "tests_run": ran, "failures": failed, "tail": tail,
        "note": "failure identity must be exactly the new test; all 13 pre-existing tests still pass on this R1-R7-preserving surrogate",
    }
except subprocess.TimeoutExpired:
    checks["candidate_fails_fresh_exponential"] = {"pass": False, "exit": None,
                                                    "note": "TIMEOUT: candidate hung against exponential surrogate"}

# (iii) fresh legitimate polynomial reimplementation: candidate must PASS (no
# false positive on a higher-degree polynomial).
d = stage(os.path.join(HERE, "poly_alt.py"), "polyalt")
code, ran, failed, tail = run_suite(d, 300)
checks["candidate_passes_fresh_polynomial"] = {
    "pass": code == 0 and ran == 14 and not failed,
    "exit": code, "tests_run": ran, "failures": failed, "tail": tail,
}

# (iv) diff-scope audit + canonical tree untouched + baselines.
cand_src = open(CAND).read()
canon_src = open(os.path.join(ROOT, "tests", "test_solver.py")).read()
added = cand_src.replace(canon_src.rstrip("\n").replace('if __name__ == "__main__":\n    unittest.main()', ""), "")
diff_lines = open(os.path.join(ROOT, ".creator-zero", "experiment-4", "c1", "candidate", "candidate.diff")).read().splitlines()
plus = [l for l in diff_lines if l.startswith("+") and not l.startswith("+++")]
minus = [l for l in diff_lines if l.startswith("-") and not l.startswith("---")]
new_methods = re.findall(r"def (test_\w+)", "\n".join(plus))
git = subprocess.run(["git", "diff", "--stat", "HEAD", "--", "src/", "docs/", "tests/"],
                     cwd=ROOT, capture_output=True, text=True)
p_canon = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"],
                         cwd=ROOT, capture_output=True, text=True, timeout=300)
p_probes = subprocess.run([sys.executable, ".creator-zero/harness/probes.py"],
                          cwd=ROOT, capture_output=True, text=True, timeout=600)
probes_tail = p_probes.stdout.strip().splitlines()[-1]
checks["diff_scope_and_canonical_integrity"] = {
    "pass": (minus == [] and new_methods == ["test_r8_operation_growth_is_polynomial"]
             and git.stdout.strip() == "" and git.returncode == 0
             and p_canon.returncode == 0 and "Ran 13 tests" in p_canon.stderr
             and p_probes.returncode == 0 and "total=24 pass=24 fail=0" in probes_tail),
    "diff_added_lines": len(plus), "diff_removed_lines": len(minus),
    "diff_new_methods": new_methods,
    "git_diff_canonical": git.stdout.strip() or "(empty)",
    "canonical_suite": p_canon.stderr.strip().splitlines()[-1],
    "probes": probes_tail,
}

# (v) candidate implements its recorded specification: bound 32, schedule
# 8->16->32->64, settrace mechanism, tracer save/restore, no wall-clock.
spec_ok = ("32 * prev" in cand_src and "(16, 32, 64)" in cand_src
           and "count_ops(8)" in cand_src and "sys.settrace" in cand_src
           and "sys.gettrace()" in cand_src
           and not re.search(r"time\.\w|perf_counter|monotonic|timeit|sleep\(|import time", cand_src))
checks["candidate_matches_specification"] = {
    "pass": bool(spec_ok),
    "detail": "bound=32 per doubling, schedule [8,16,32,64] incremental, settrace counting, tracer saved/restored, no wall-clock reference",
}

overall = all(c["pass"] for c in checks.values())
verdict = {
    "node": "verify-candidate",
    "overall": "ACCEPT" if overall else "REJECT",
    "checks": checks,
    "independence": ("all surrogates re-authored fresh in sandbox-verify/ (bitmask enumerator vs evidence's "
                      "recursive one; start-sorted suffix-DP polynomial vs evidence's end-sorted prefix-DP); "
                      "expectations re-derived from docs/solver_spec.md via oracle enumeration; no evidence-"
                      "sandbox module imported"),
}
out = os.path.join(HERE, "verify-verdict.json")
json.dump(verdict, open(out, "w"), indent=2)
print("WROTE", out)
print("OVERALL:", verdict["overall"])
for k, v in checks.items():
    print(("PASS " if v["pass"] else "FAIL ") + k)
