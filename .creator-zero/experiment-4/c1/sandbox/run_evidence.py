"""evidence-and-discriminator node driver (deterministic script).

Writes .creator-zero/experiment-4/c1/sandbox/evidence-round-0.json resolving
Q1-Q7 of the final harness. Zero writes outside c1/sandbox/.
"""

import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.abspath(os.path.dirname(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, HERE)

from opcount import count_ops, disjoint_instance  # noqa: E402


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


oracle = load_module("oracle", os.path.join(ROOT, ".creator-zero", "harness", "oracle.py"))
canonical = load_module("canonical_solver", os.path.join(ROOT, "src", "solver.py"))
exp_mod = load_module("surrogate_exp", os.path.join(HERE, "surrogate_exp.py"))
cubic_mod = load_module("surrogate_cubic", os.path.join(HERE, "surrogate_cubic.py"))

ev = {}

# ---------------- Q1: what does R8's runtime clause commit to ----------------
spec_text = open(os.path.join(ROOT, "docs", "solver_spec.md")).read()
r8_block = spec_text[spec_text.index("### R8"):]
ev["q1_reading"] = {
    "r8_verbatim": r8_block.strip(),
    "clauses": ["no argument mutation", "determinism (identical input -> identical result)",
                "runtime polynomial in len(jobs), parenthetical: 'exhaustive subset enumeration is not acceptable'"],
    "reading": "NARROW",
    "basis": (
        "The runtime sentence anchors itself to a concrete forbidden implementation class via the "
        "parenthetical: 'Runtime MUST be polynomial in len(jobs) (exhaustive subset enumeration is not "
        "acceptable).' The parenthetical names exhaustive subset enumeration as the canonical violation, "
        "giving the clause an operational target; nothing in R8 or elsewhere in the spec demands a proof "
        "of a particular polynomial degree, and no degree bound is stated. The clause is therefore read as: "
        "the implementation must be polynomial-time, with exhaustive-enumeration-style exponential blowup "
        "the named, concrete violation any verification must at minimum exclude. The sentence does not "
        "support two materially different readings: both the general clause and the parenthetical forbid "
        "the same class of behavior at different levels of abstraction, so reading=NARROW, not AMBIGUOUS."
    ),
    "classification": "model_judgment",
}

# ---------------- Q2: finite testability of asymptotic claim -----------------
ev["q2_note"] = {
    "note": (
        "No finite set of timed or counted executions can certify 'runtime is polynomial in n' for all n: "
        "any finite observation table is consistent both with a polynomial and with a super-polynomial "
        "function that diverges beyond the tested range (e.g. K*1.02**n is exponential yet numerically tiny "
        "at every tested n<=400). Conversely a huge-constant polynomial can look explosive at small n. "
        "Therefore 'mechanically testable' for R8's runtime clause can only mean: deterministically "
        "discriminates concrete violation classes — first of all the class R8 itself names (exhaustive "
        "subset enumeration, per-element branching factor >= 2) — not: proves the asymptotic claim. "
        "The task-level conclusion must scope any coverage verdict to that named class."
    ),
    "classification": "deterministic",
    "kind": "fixed logical argument (standard limit-of-testing result), independent of any execution",
}

# ---------------- Q3: do current tests exercise runtime ----------------------
test_src = open(os.path.join(ROOT, "tests", "test_solver.py")).read()
methods = re.findall(r"def (test_\w+)\(self\):(.*?)(?=\n    def |\nif __name__|\Z)", test_src, re.S)
enum = {}
for name, body in methods:
    asserts = re.findall(r"self\.assert\w+", body)
    n_used = re.findall(r"solve\(\[?([^)]*)", body)
    enum[name] = {"assertions": asserts, "n_assertions": len(asserts)}
timing_tokens = ["time", "perf_counter", "clock", "settrace", "setprofile", "timeit",
                 "timeout", "duration", "elapsed", "range(2", "scaling", "cProfile"]
token_hits = {t: len(re.findall(re.escape(t), test_src)) for t in timing_tokens}
max_instance = 8  # classic instance; verified below
sizes = [len(re.findall(r"\(-?\d+,\s*-?\d+,\s*-?\d+\)", body)) for _, body in methods]
ev["q3_enumeration"] = {
    "test_methods": enum,
    "method_count": len(methods),
    "timing_token_scan": token_hits,
    "timing_token_hits_total": sum(token_hits.values()),
    "largest_literal_instance_size": max(sizes),
    "negative_finding": (
        "All 13 methods assert exact (weight, schedule) values or ValueError raising on fixed literal "
        "instances (largest: 8 jobs). Zero occurrences of any timing/instrumentation/scaling token; no test "
        "varies len(jobs) programmatically, counts operations, or measures growth."
    ),
    "classification": "deterministic",
}
assert len(methods) == 13, "expected 13 test methods, found %d" % len(methods)
assert sum(token_hits.values()) == 0

# ---------------- Q4a: what does unittest discover collect -------------------
p = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
                   cwd=ROOT, capture_output=True, text=True, timeout=300)
discovered = re.findall(r"^(test_\w+) \(", p.stderr, re.M)
ev["q4a_discovery"] = {
    "command": "python -m unittest discover -s tests -v (cwd=repo root)",
    "exit_code": p.returncode,
    "discovered_tests": sorted(discovered),
    "count": len(discovered),
    "tail": p.stderr.strip().splitlines()[-1],
    "probe_functions_collected": [x for x in ("r8_scaling", "r8_no_mutation", "r8_determinism") if x in p.stderr],
    "finding": "probes.py is outside tests/ and none of its probes are collected by unittest discovery; suite runtime protection cannot be credited to probes.py.",
    "classification": "deterministic",
}
assert p.returncode == 0 and len(discovered) == 13
assert not ev["q4a_discovery"]["probe_functions_collected"]

# ---------------- Q4b: does r8_scaling catch a mild regression ---------------
mild = load_module("solver", os.path.join(HERE, "surrogate_mild.py"))  # registers as 'solver'
sys.modules["solver"] = mild  # import shim: probes.py's `from solver import solve` hits this
probes = load_module("probes_shimmed", os.path.join(ROOT, ".creator-zero", "harness", "probes.py"))
scaling = [r for r in probes.results if "scaling" in r[0]][0]
all_pass = all(ok for _, ok, _ in probes.results)
del sys.modules["solver"]
ev["q4b_probe_check"] = {
    "surrogate": "surrogate_mild.py = canonical solve + busy-loop of int(3000 * 1.02**n) iterations (genuinely exponential, base 1.02; ~8.3e6 iterations at n=400)",
    "shape_rationale": "chosen so the added cost is provably super-polynomial yet numerically small at the probe's largest n=400, keeping the whole check under a minute",
    "r8_scaling_result": {"name": scaling[0], "ok": scaling[1], "detail": scaling[2]},
    "full_probe_matrix_pass": all_pass,
    "probe_count": len(probes.results),
    "finding": (
        "r8_scaling reports ok=%s for the mild exponential surrogate: the 30s wall-clock cap at n<=400 "
        "does not discriminate this super-polynomial regression. Even if probes.py were part of the suite "
        "(it is not, per q4a), its wall-clock threshold form would not protect R8's runtime clause against "
        "mild-base exponential regressions." % scaling[1]
    ),
    "classification": "deterministic",
}
assert scaling[1] is True, "expected the mild surrogate to PASS r8_scaling"

# ---------------- Q5: exponential surrogate passes the full suite ------------
# Admissibility first: R5+R6 agreement with oracle on bounded exhaustive grid.
import itertools
def small_instances():
    yield []
    coords = [0, 1, 2, 3]
    for n in (1, 2, 3):
        for jobs in itertools.product(
                [(s, e, w) for s in coords for e in coords if e > s for w in (1, 2)],
                repeat=n):
            yield list(jobs)

checked = 0
mismatch = 0
for jobs in small_instances():
    got = exp_mod.solve(list(jobs))
    want = oracle.oracle_solve(jobs)
    if got != (want[0], want[1]):
        mismatch += 1
    checked += 1
# spot-check R1 rejections mirror canonical
rejects = [((0, 0, 1),), [(0, 0, 1)], [(2, 2, 1)], [(0, 1, 0)], [(False, True, 3)], [(0, 1.5, 1)], [5], None]
reject_ok = 0
for bad in rejects:
    try:
        exp_mod.solve(bad)
    except ValueError:
        reject_ok += 1
    except Exception:
        pass

staged = os.path.join(HERE, "staged")
shutil.rmtree(staged, ignore_errors=True)
os.makedirs(os.path.join(staged, "src"))
os.makedirs(os.path.join(staged, "tests"))
shutil.copyfile(os.path.join(HERE, "surrogate_exp.py"), os.path.join(staged, "src", "solver.py"))
shutil.copyfile(os.path.join(ROOT, "tests", "test_solver.py"), os.path.join(staged, "tests", "test_solver.py"))
p5 = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
                    cwd=staged, capture_output=True, text=True, timeout=300)
ran = re.findall(r"^(test_\w+) \(", p5.stderr, re.M)
failed = re.findall(r"^(?:FAIL|ERROR): (test_\w+)", p5.stderr, re.M)
ev["q5_gap_demo"] = {
    "surrogate": "surrogate_exp.py: unmemoized include/exclude recursion, Theta(2^n) nodes — the violation class R8 names",
    "admissibility": {
        "oracle_differential_instances": checked,
        "weight_or_sequence_mismatches": mismatch,
        "r1_rejection_spot_checks_passed": "%d/%d" % (reject_ok, len(rejects)),
    },
    "staged_suite_run": {
        "command": "python -m unittest discover -s tests -v (cwd=c1/sandbox/staged, src/solver.py = exponential surrogate)",
        "exit_code": p5.returncode,
        "tests_run": len(ran),
        "failures": failed,
        "tail": p5.stderr.strip().splitlines()[-1],
    },
    "finding": (
        "The exponential surrogate passes the entire canonical 13-test suite unmodified (%d/13, exit %d): "
        "an implementation in exactly the violation class R8 names is indistinguishable from the canonical "
        "solver by tests/. Executable H1 witness." % (len(ran), p5.returncode)
    ),
    "classification": "deterministic",
}
assert mismatch == 0 and reject_ok == len(rejects)
assert p5.returncode == 0 and len(ran) == 13 and not failed

# ---------------- Q6: discriminator construction + FP/FN checks --------------
BOUND = 32  # per-doubling trace-event growth-ratio bound: admits any polynomial of degree <= 5
POLY_SCHEDULE = [8, 16, 32, 64]
EXP_SCHEDULE = [6, 8, 12, 16]  # doublings: 6->12, 8->16

def growth(mod, schedule):
    counts = {}
    for n in schedule:
        c1, _ = count_ops(mod.solve, disjoint_instance(n))
        c2, _ = count_ops(mod.solve, disjoint_instance(n))
        assert c1 == c2, "trace counts not reproducible for n=%d" % n
        counts[n] = c1
    ratios = {"%d->%d" % (a, b): round(counts[b] / counts[a], 2)
              for a, b in zip(schedule, schedule[1:]) if b == 2 * a}
    for a in schedule:
        for b in schedule:
            if b == 2 * a:
                ratios["%d->%d" % (a, b)] = round(counts[b] / counts[a], 2)
    return counts, ratios

can_counts, can_ratios = growth(canonical, POLY_SCHEDULE)
cub_counts, cub_ratios = growth(cubic_mod, POLY_SCHEDULE)
exp_counts, exp_ratios = growth(exp_mod, EXP_SCHEDULE)

# cubic surrogate admissibility (it must be a *legitimate* implementation)
cub_checked = cub_mism = 0
for jobs in small_instances():
    if cub_mism == 0:
        want = oracle.oracle_solve(jobs)
        if cubic_mod.solve(list(jobs)) != (want[0], want[1]):
            cub_mism += 1
        cub_checked += 1

grep_targets = {
    "canonical src/solver.py": open(os.path.join(ROOT, "src", "solver.py")).read(),
    "surrogate_exp.py": open(os.path.join(HERE, "surrogate_exp.py")).read(),
}
patterns = ["itertools.combinations", "itertools.permutations", "itertools.product",
            "range(2 **", "range(2**", "combinations(", "def rec", "lru_cache", "memo"]
structural = {k: {pat: len(re.findall(re.escape(pat), v)) for pat in patterns}
              for k, v in grep_targets.items()}

poly_ok = all(r <= BOUND for r in list(can_ratios.values()) + list(cub_ratios.values()))
exp_flagged = all(r > BOUND for r in exp_ratios.values())

ev["q6_discriminator"] = {
    "form": "deterministic operation counting: sys.settrace event count (call+line+return+exception) of solve() on the disjoint instance family [(3i,3i+2,1+i%3)], compared per doubling of n",
    "bound": {"per_doubling_ratio": BOUND, "rationale": (
        "A degree-d polynomial's trace-event count grows by ~2^d per doubling of n; bound 32 = 2^5 admits "
        "every polynomial of degree <= 5 with wide margin over the canonical solver (measured <= %.1f) and "
        "the degree-3/4 control (measured <= %.1f), while any per-element branching enumeration grows by "
        ">= 2^n/2^(n/2) per doubling — measured >= %.0f already at the capped schedule. The bound derives "
        "from asymptotic form, not from the current implementation's constants; it is scale-invariant: "
        "multiplying any implementation's work by a constant K leaves every ratio unchanged."
        % (max(can_ratios.values()), max(cub_ratios.values()), min(exp_ratios.values())))},
    "schedules": {
        "canonical_and_cubic": POLY_SCHEDULE,
        "exponential_surrogate": EXP_SCHEDULE,
    },
    "exp_schedule_cap": (
        "The exponential surrogate runs on its own capped schedule (max n=16) purely because Theta(2^n) "
        "work at n=64 (let alone 160) cannot execute in any realistic time. This does not weaken the "
        "discrimination claim: a polynomial implementation's per-doubling ratio is bounded by ~2^degree at "
        "EVERY n including small n, while an exhaustive enumerator's ratio is ~2^(n/2) per doubling at the "
        "capped points already (measured %s vs bound %d) and diverges further with n."
        % (exp_ratios, BOUND)),
    "measurements": {
        "canonical": {"counts": can_counts, "per_doubling_ratios": can_ratios, "reproducible": True},
        "cubic_control": {"counts": cub_counts, "per_doubling_ratios": cub_ratios, "reproducible": True,
                           "oracle_differential": {"instances": cub_checked, "mismatches": cub_mism}},
        "exponential_surrogate": {"counts": exp_counts, "per_doubling_ratios": exp_ratios, "reproducible": True},
    },
    "false_positive_check": {"pass": poly_ok, "detail": "canonical and fresh degree-3/4 control both stay under the bound at every doubling"},
    "false_negative_check": {"pass": exp_flagged, "detail": "exponential surrogate exceeds the bound at every doubling of its capped schedule"},
    "structural_check": {
        "patterns": structural,
        "finding": "canonical solver contains no combinatorial-enumeration pattern; the surrogate's marker is unmemoized recursion (def rec present, no cache/memo). Execution-free corroboration only; not the primary discriminator.",
    },
    "constant_evasion_note": {
        "note": (
            "Growth-ratio methodology is immune to multiplicative-constant evasion (ratios are scale-"
            "invariant), so a 'large hidden constant' violation is caught iff its growth base shows at "
            "tested sizes. A super-polynomial with base close to 1 (e.g. the q4b 1.02**n surrogate) stays "
            "under any fixed ratio bound at finite n — by q2 this is unavoidable for EVERY finite test, "
            "wall-clock or counted. The discriminator therefore claims coverage of the violation class R8 "
            "names (per-element branching factor >= 2, ratio >= 2^(n/2) per doubling), not of all "
            "super-polynomial functions. Work executed entirely inside C extensions is a further recorded "
            "blind spot (no trace events); implausible for a hand-written scheduling regression."),
        "classification": "model_judgment",
    },
    "wall_clock_comparison": (
        "Versus timing thresholds: trace counts are exactly reproducible run-to-run (asserted above), "
        "machine-independent for fixed CPython semantics, and need no environment-tuned constant. Counts "
        "may differ across CPython versions, but the assertion is on RATIOS, which track asymptotic order, "
        "not absolute cost — so no implementation-specific or environment-specific threshold is encoded."),
    "justified": bool(poly_ok and exp_flagged),
    "classification": "deterministic",
}
assert ev["q6_discriminator"]["justified"]

# ---------------- Q7: sub-clause mapping -------------------------------------
ev["q7_mapping"] = {
    "tests/test_solver.py": {
        "test_does_not_mutate_input": "R8/no-mutation (shallow snapshot)",
        "all_other_12_methods": "R1-R7 functional value/exception assertions; none touch any R8 sub-clause",
    },
    "probes.py (NOT in suite, per q4a)": {
        "r8_no_mutation": "R8/no-mutation (deep snapshot)",
        "r8_determinism": "R8/determinism (repeat calls)",
        "r8_scaling": "R8/runtime (wall-clock, 30s cap; shown non-discriminating in q4b)",
    },
    "runtime_subclause_tests_in_suite": 0,
    "determinism_subclause_tests_in_suite": 0,
    "no_mutation_subclause_tests_in_suite": 1,
    "supporting_greps": {"tests_timing_tokens": 0, "see": "q3_enumeration.timing_token_scan"},
    "finding": (
        "R8 bundles three obligations; the suite covers no-mutation (1 test), leaves determinism to the "
        "out-of-suite probes, and has ZERO runtime coverage. The verdict below is scoped strictly to the "
        "runtime sub-clause; crediting the mutation test toward runtime protection would be a category error."),
    "classification": "model_judgment supported by deterministic greps (q3) and discovery run (q4a)",
}

# ---------------- verdict ----------------------------------------------------
suite_passes_exp = ev["q5_gap_demo"]["staged_suite_run"]["exit_code"] == 0
ev["verdict"] = ("R8_COVERAGE_GAP_VERIFIED"
                  if suite_passes_exp and ev["q6_discriminator"]["justified"]
                  else "INDETERMINATE")
ev["verdict_derivation"] = (
    "q1_reading=NARROW (not AMBIGUOUS) -> coverage verdict permitted. q5: exponential surrogate in the "
    "named violation class passes 13/13 canonical tests -> gap exists. q6: justified deterministic, "
    "non-wall-clock discriminator exists (FP and FN checks both pass) -> gap is meaningfully closable -> "
    "R8_COVERAGE_GAP_VERIFIED. Scope: the named violation class; general asymptotic polynomiality is not "
    "finitely testable (q2).")

# ---------------- candidate test specification (authorizes act node) ---------
ev["candidate_test_specification"] = {
    "target_file": "tests/test_solver.py (candidate copy under .creator-zero/experiment-4/c1/candidate/)",
    "method_name": "test_r8_operation_growth_is_polynomial",
    "instance_family": "disjoint_instance(n) = [(3*i, 3*i+2, 1 + (i % 3)) for i in range(n)]",
    "schedule": POLY_SCHEDULE,
    "bound_per_doubling": BOUND,
    "mechanism": (
        "sys.settrace counter of all trace events during solve(instance(n)); assert incrementally after "
        "each doubling that count(2n) <= 32 * count(n); save and restore any pre-existing tracer. "
        "Incremental per-doubling assertion makes an exponential regression fail fast at n=16 "
        "(~1e6 events, a few seconds) instead of hanging at n=64."),
    "assertions": ["for each consecutive pair (n, 2n) in [8,16,32,64]: assertLessEqual(count(2n), 32*count(n))"],
    "must_not": "reference wall-clock time, sandbox files, or anything outside src/solver.py + stdlib",
}

out = os.path.join(HERE, "evidence-round-0.json")
json.dump(ev, open(out, "w"), indent=2)
print("WROTE", out)
print("verdict:", ev["verdict"])
print("q6 justified:", ev["q6_discriminator"]["justified"])
print("canonical ratios:", can_ratios, "cubic:", cub_ratios, "exp:", exp_ratios)
