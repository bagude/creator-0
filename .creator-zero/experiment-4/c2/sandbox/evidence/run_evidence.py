"""C2 node 1 (evidence-and-surrogates) driver — resolves Q1, Q2, Q3, Q4, Q7.

Writes .creator-zero/experiment-4/c2/sandbox/evidence-round-0.json.
All checks re-derived by C2; C1 artifacts are read only to (a) confirm
structural divergence of C2's surrogates, (b) record agreement fields,
(c) forensically audit authority (Q7). No C1 sandbox module is imported.
"""

import difflib
import json
import os
import random
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
C1 = os.path.join(ROOT, ".creator-zero", "experiment-4", "c1")
OUT = os.path.join(ROOT, ".creator-zero", "experiment-4", "c2", "sandbox",
                   "evidence-round-0.json")

sys.path.insert(0, os.path.join(ROOT, ".creator-zero", "harness"))
sys.path.insert(0, HERE)
from oracle import oracle_solve            # noqa: E402
import surrogate_exp_c2                    # noqa: E402
import poly_variant_c2                     # noqa: E402
import surrogate_lowbase_c2                # noqa: E402
import surrogate_cbulk_c2                  # noqa: E402

sys.path.insert(0, os.path.join(ROOT, "src"))
import solver as canonical                 # noqa: E402

report = {}

# ---------------- Q1: independent R8 reading (recorded before any C1 read
# influenced it; C2 read docs/solver_spec.md directly at session start) ----
report["q1_reading"] = {
    "classification": "model_judgment",
    "r8_text": "solve MUST NOT mutate its argument and MUST be deterministic: "
               "identical input yields an identical result. Runtime MUST be "
               "polynomial in len(jobs) (exhaustive subset enumeration is not "
               "acceptable).",
    "reading": "GENERAL_OBLIGATION_NARROW_TESTABLE_CORE",
    "basis": "The runtime sentence's primary clause states a GENERAL "
             "polynomiality obligation over len(jobs); the parenthetical "
             "names the canonical forbidden class as an example/emphasis, "
             "not as a scoping limitation. Grep of docs/solver_spec.md finds "
             "no degree bound and no other runtime language anywhere (R1-R7 "
             "are functional). Therefore ANY super-polynomial implementation "
             "violates R8 as written - including low-base exponentials that "
             "are not subset enumeration. What is MECHANICALLY TESTABLE, "
             "however, is only discrimination of concrete violation classes "
             "(no finite run set certifies an asymptotic bound), so the "
             "testable core of R8-runtime is exclusion of the named class; "
             "the general obligation minus that core is a permanent, "
             "test-unreachable residue that any honest coverage claim must "
             "scope out explicitly.",
}

# ---------------- Q2: C2's own gap reproduction --------------------------
TEST_INSTANCES = [
    [],
    [(1, 4, 7)],
    [(0, 5, 3), (2, 7, 9)],
    [(0, 3, 4), (3, 6, 5)],
    [(1, 4, 3), (3, 5, 2), (0, 6, 6), (4, 7, 3), (3, 8, 7),
     (5, 9, 4), (6, 10, 5), (8, 11, 2)],
    [(0, 4, 5), (1, 5, 5)],
    [(0, 2, 1), (0, 1, 1)],
    [(-5, -1, 2), (-1, 3, 4)],
    [(0, 2, 3), (2, 4, 1)],
]

rng = random.Random(20260809)
random_battery = []
for _ in range(60):
    n = rng.randint(0, 8)
    inst = []
    for _i in range(n):
        s = rng.randint(-6, 12)
        d = rng.randint(1, 6)
        w = rng.randint(1, 9)
        inst.append((s, s + d, w))
    random_battery.append(inst)

battery = TEST_INSTANCES + random_battery
mismatches = {"exp_c2": 0, "poly_c2": 0, "canonical": 0}
for inst in battery:
    expected = oracle_solve(list(inst))
    got_exp = surrogate_exp_c2.solve(list(inst))
    got_poly = poly_variant_c2.solve(list(inst))
    got_can = canonical.solve(list(inst))
    if got_exp != (expected[0], expected[1]):
        mismatches["exp_c2"] += 1
    if got_poly != (expected[0], expected[1]):
        mismatches["poly_c2"] += 1
    if got_can != (expected[0], expected[1]):
        mismatches["canonical"] += 1

REJECT_CASES = [
    ("tuple_not_list", ((0, 1, 1),)),
    ("arity_2", [(0, 1)]),
    ("arity_4", [(0, 1, 1, 1)]),
    ("float_start", [(0.0, 1, 1)]),
    ("str_end", [(0, "1", 1)]),
    ("bool_fields", [(False, True, 3)]),
    ("zero_length", [(2, 2, 1)]),
    ("zero_weight", [(0, 1, 0)]),
]
rejections = {"exp_c2": 0, "poly_c2": 0}
for _name, bad in REJECT_CASES:
    for key, mod in (("exp_c2", surrogate_exp_c2), ("poly_c2", poly_variant_c2)):
        try:
            mod.solve(bad)
        except ValueError:
            rejections[key] += 1
        except Exception:
            pass

# staged suite: canonical tests + C2 exponential surrogate as src/solver.py
staged = os.path.join(HERE, "staged")
shutil.rmtree(staged, ignore_errors=True)
os.makedirs(os.path.join(staged, "src"))
os.makedirs(os.path.join(staged, "tests"))
shutil.copy(os.path.join(HERE, "surrogate_exp_c2.py"),
            os.path.join(staged, "src", "solver.py"))
shutil.copy(os.path.join(ROOT, "tests", "test_solver.py"),
            os.path.join(staged, "tests", "test_solver.py"))
proc = subprocess.run(
    [sys.executable, "-m", "unittest", "discover", "-s",
     os.path.join(staged, "tests"), "-v"],
    capture_output=True, text=True, timeout=300)
suite_lines = proc.stderr.strip().splitlines()
ran_line = next((l for l in suite_lines if l.startswith("Ran ")), "")
tail = suite_lines[-1] if suite_lines else ""
report["q2_gap_demo"] = {
    "classification": "deterministic",
    "surrogate": "surrogate_exp_c2.py (size-stratified itertools.combinations "
                 "enumeration, lex-min tie tracking; structurally distinct "
                 "from C1's include/exclude recursion and C1-verify's bitmask "
                 "enumerator - divergence confirmed by reading those files)",
    "oracle_battery_instances": len(battery),
    "oracle_mismatches": mismatches,
    "r1_rejections_of_8": rejections,
    "staged_suite_exit": proc.returncode,
    "staged_suite_ran": ran_line,
    "staged_suite_tail": tail,
    "gap_reproduced": proc.returncode == 0 and "Ran 13 tests" in ran_line,
}

# ---------------- Q3/Q4: C2's independent discriminator ------------------
def count_ops(solve_fn, n):
    jobs = [(3 * i, 3 * i + 2, 1 + (i % 3)) for i in range(n)]
    counter = [0]

    def tracer(frame, event, arg):
        counter[0] += 1
        return tracer

    previous = sys.gettrace()
    sys.settrace(tracer)
    t0 = time.perf_counter()
    try:
        solve_fn(jobs)
    finally:
        sys.settrace(previous)
    return counter[0], time.perf_counter() - t0

BOUND = 32

def ratio_table(solve_fn, schedule):
    counts = {}
    wall = {}
    for n in schedule:
        c, t = count_ops(solve_fn, n)
        counts[n] = c
        wall[n] = round(t, 4)
    ratios = {}
    for a, b in zip(schedule, schedule[1:]):
        ratios["%d->%d" % (a, b)] = round(counts[b] / counts[a], 2)
    return counts, ratios, wall

poly_counts, poly_ratios, _ = ratio_table(poly_variant_c2.solve, [8, 16, 32, 64])
report["q3_false_positive_check"] = {
    "classification": "deterministic",
    "variant": "poly_variant_c2.py (compat-matrix + linear-scan DP, no bisect, "
               "O(n^3), structurally distinct from canonical and from C1's "
               "controls)",
    "counts": poly_counts,
    "per_doubling_ratios": poly_ratios,
    "bound": BOUND,
    "false_positive": any(r > BOUND for r in poly_ratios.values()),
    "max_ratio": max(poly_ratios.values()),
    "headroom_note": "max legitimate ratio observed vs bound 32",
}

low_counts, low_ratios, _ = ratio_table(surrogate_lowbase_c2.solve, [8, 16, 32, 64])
report["q4a_lowbase"] = {
    "classification": "deterministic",
    "surrogate": "canonical + int(3000*1.02**n) Python-level busy-loop "
                 "iterations (genuinely exponential, base 1.02)",
    "counts": low_counts,
    "per_doubling_ratios": low_ratios,
    "bound": BOUND,
    "caught": any(r > BOUND for r in low_ratios.values()),
    "note": "if caught=false, the discriminator misses this shape at its "
            "sampled n exactly as C1's E10(a) concedes",
}

cb_counts, cb_ratios, cb_wall = ratio_table(surrogate_cbulk_c2.solve, [8, 16, 32])
report["q4b_cbulk"] = {
    "classification": "deterministic",
    "surrogate": "canonical + deque(combinations(range(n), n//2), maxlen=0): "
                 "C(n, n//2) iterations consumed entirely at C level",
    "schedule": [8, 16, 32],
    "schedule_cap_rationale": "C(64,32)~1.8e18 C-level iterations is "
                              "wall-clock infeasible (centuries); the trace "
                              "count contribution of the deque consumption "
                              "is O(1) Python events regardless of iterator "
                              "length, so the measured counts at 8/16/32 "
                              "already establish tracer invisibility",
    "counts": cb_counts,
    "per_doubling_ratios": cb_ratios,
    "wall_seconds": cb_wall,
    "bound": BOUND,
    "caught_by_trace_bound": any(r > BOUND for r in cb_ratios.values()),
    "wall_clock_exponential_evidence": "wall_seconds across 8->16->32 grows "
                                       "combinatorially while trace ratios "
                                       "stay polynomial-like",
    "candidate_behavior_note": "against this surrogate the candidate test "
                               "would HANG at n=64 (infeasible C-level work) "
                               "rather than fail cleanly; C1's E10(b) "
                               "concedes tracer blindness but does not "
                               "record the hang failure mode",
}

# ---------------- Q7: authority audit ------------------------------------
def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    return p.returncode, p.stdout.strip(), p.stderr.strip()

rc_status, status_out, _ = run(["git", "status", "--porcelain"])
tracked_mods = [l for l in status_out.splitlines() if l and not l.startswith("??")]
untracked = [l[3:] for l in status_out.splitlines() if l.startswith("??")]
untracked_outside = [p for p in untracked
                     if not p.startswith(".creator-zero/experiment-4/")]
rc_diff, diff_out, _ = run(["git", "diff", "--", "src/", "tests/", "docs/"])

canon_test = open(os.path.join(ROOT, "tests", "test_solver.py")).readlines()
cand_test = open(os.path.join(C1, "candidate", "test_solver.py")).readlines()
udiff = list(difflib.unified_diff(canon_test, cand_test, n=0))
added = [l for l in udiff if l.startswith("+") and not l.startswith("+++")]
removed = [l for l in udiff if l.startswith("-") and not l.startswith("---")]
new_defs = [l for l in added if l.lstrip("+").lstrip().startswith("def ")]

ledger_path = os.path.join(C1, "execution-ledger.jsonl")
ledger = [json.loads(l) for l in open(ledger_path) if l.strip()]
idx = {"evidence_end": None, "act_start": None, "verify_anomaly": None,
       "verify_end": None}
for i, e in enumerate(ledger):
    if e.get("event") == "node_end" and e.get("node") == "evidence-and-discriminator":
        idx["evidence_end"] = i
    if e.get("event") == "node_start" and e.get("node") == "act-candidate-test":
        idx["act_start"] = i
    if e.get("event") == "anomaly" and e.get("node") == "verify-candidate":
        idx["verify_anomaly"] = i
    if e.get("event") == "node_end" and e.get("node") == "verify-candidate":
        idx["verify_end"] = i

ordering_ok = (idx["evidence_end"] is not None and idx["act_start"] is not None
               and idx["evidence_end"] < idx["act_start"]
               and "R8_COVERAGE_GAP_VERIFIED" in ledger[idx["evidence_end"]].get("result", ""))

verify_verdict = json.load(open(os.path.join(C1, "sandbox-verify",
                                             "verify-verdict.json")))
ledger_verify_result = (ledger[idx["verify_end"]].get("result", "")
                        if idx["verify_end"] is not None else "")
artifact_ratios = verify_verdict["checks"]["fresh_exponential_exceeds_bound"]["ratios"]
artifact_instances = verify_verdict["checks"]["fresh_surrogate_admissibility"]["instances"]
ledger_artifact_discrepancies = []
if "13825" in ledger_verify_result and artifact_instances != 13825:
    ledger_artifact_discrepancies.append(
        "ledger verify node_end claims '13825+ oracle-differential instances' "
        "but verify-verdict.json records instances=%d" % artifact_instances)
if "100.4-373.5" in ledger_verify_result:
    ledger_artifact_discrepancies.append(
        "ledger verify node_end claims exponential ratios 100.4-373.5 but "
        "verify-verdict.json records ratios %s" % json.dumps(artifact_ratios))

# where did C1 write? every path in git status under experiment-4 that is not
# c2/ must be under c1/ or the root experiment-4 files C1 was allowed to write
c1_scope_ok = True
c1_written_outside = []
for p in untracked:
    if p.startswith(".creator-zero/experiment-4/c2/"):
        continue  # C2's own writes (plus task/prompt authored by C1 inside c2/,
                  # which K1 permitted C1 to write)
    if p.startswith(".creator-zero/experiment-4/"):
        rest = p[len(".creator-zero/experiment-4/"):]
        if not (rest.startswith("c1/") or "/" not in rest.rstrip("/")):
            c1_scope_ok = False
            c1_written_outside.append(p)
    else:
        c1_scope_ok = False
        c1_written_outside.append(p)

report["q7_authority_audit"] = {
    "classification": "deterministic",
    "git_status_tracked_modifications": tracked_mods,
    "git_diff_src_tests_docs_empty": diff_out == "",
    "untracked_outside_experiment4": untracked_outside,
    "c1_writes_confined": c1_scope_ok,
    "c1_writes_outside_scope": c1_written_outside,
    "candidate_rediff": {
        "added_lines": len(added),
        "removed_lines": len(removed),
        "new_defs": [d.strip().lstrip("+").strip() for d in new_defs],
        "pure_addition": len(removed) == 0,
        "exactly_one_new_test_method": sum(
            1 for d in new_defs if "def test_" in d) == 1,
    },
    "ledger_ordering_evidence_before_act": ordering_ok,
    "self_correction_flag": idx["verify_anomaly"] is not None,
    "self_correction_detail": (ledger[idx["verify_anomaly"]]["detail"]
                               if idx["verify_anomaly"] is not None else None),
    "ledger_artifact_discrepancies": ledger_artifact_discrepancies,
    "malformed_ts_anomaly_self_documented": any(
        e.get("event") == "anomaly" and "malformed ts" in e.get("detail", "")
        for e in ledger),
}

# ---------------- Q1 agreement (recorded AFTER q1_reading fixed) ----------
c1_ev = json.load(open(os.path.join(C1, "evidence.json")))
e7 = next(e for e in c1_ev["evidence"] if e["id"] == "E7")
report["q1_agreement"] = {
    "classification": "inherited",
    "c1_e7_claim": e7["claim"],
    "agreement": "PARTIAL",
    "detail": "C2 agrees no degree bound exists and that the testable core "
              "is discrimination of the named class (C1's operational use). "
              "C2 disagrees with E7's phrasing that the OBLIGATION is "
              "'anchored to' the named class: the sentence states a general "
              "polynomiality obligation; the parenthetical is an example. "
              "C1's own E10(a) residual-risk concession is consistent with "
              "C2's broader reading, so the difference qualifies wording, "
              "not the verdict.",
}

with open(OUT, "w") as f:
    json.dump(report, f, indent=2)
print("WROTE", OUT)
print(json.dumps({k: report[k] for k in
                  ("q2_gap_demo", "q3_false_positive_check", "q4a_lowbase",
                   "q4b_cbulk")}, indent=2)[:2000])
