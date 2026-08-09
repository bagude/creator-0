"""Deterministic evidence driver for node evidence-gap-and-derivation.

Runs Q2 (surrogate admissibility differential), Q3 (full tie enumeration),
Q4 (minimality search), Q5 (oracle-first derivation), and prepares data for
Q1 (suite runs, executed by run_suites.sh and merged by finalize.py).

Writes q_results.json (intermediate). All randomness is seeded; every step
is reproducible.
"""

import copy
import importlib.util
import itertools
import json
import os
import random
import sys

ROOT = "/home/user/creator-0"
SANDBOX = os.path.join(ROOT, ".creator-zero", "experiment-3", "sandbox")
sys.path.insert(0, os.path.join(ROOT, ".creator-zero", "harness"))

from oracle import oracle_solve, _compat  # noqa: E402


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


surrogate_ef = load_module(
    "surrogate_ef", os.path.join(SANDBOX, "surrogates", "surrogate_ef.py"))
surrogate_hi = load_module(
    "surrogate_hi", os.path.join(SANDBOX, "surrogates", "surrogate_hi.py"))
canonical = load_module("canonical_solver", os.path.join(ROOT, "src", "solver.py"))

SURROGATES = [
    ("ef_dp_backtrack", surrogate_ef.solve),
    ("prefer_higher_index", surrogate_hi.solve),
]


def all_optimal_sequences(jobs):
    """Oracle-style full subset enumeration: return (W, [all optimal seqs])."""
    n = len(jobs)
    best_w = 0
    best_seqs = [()]
    for k in range(1, n + 1):
        for subset in itertools.combinations(range(n), k):
            ok = True
            for x in range(k):
                for y in range(x + 1, k):
                    if not _compat(jobs[subset[x]], jobs[subset[y]]):
                        ok = False
                        break
                if not ok:
                    break
            if not ok:
                continue
            w = sum(jobs[i][2] for i in subset)
            if w > best_w:
                best_w = w
                best_seqs = [subset]
            elif w == best_w:
                best_seqs.append(subset)
    return best_w, sorted(list(s) for s in best_seqs)


# ---------------------------------------------------------------- Q2 cases
def q2_cases():
    """Bounded exhaustive + seeded random differential grid, n <= 8.

    Exhaustive: all ORDERED job tuples (index order matters for R6) of
    length 1..4 over universe starts in [-1..2], lengths {1,2}, weights
    {1,2}.  Random: 2000 seeded instances, n in 5..8, starts [-3..5],
    lengths 1..4, weights 1..3 (many equal weights to stress ties).
    """
    universe = []
    for s in range(-1, 3):
        for ln in (1, 2):
            for w in (1, 2):
                universe.append((s, s + ln, w))
    for k in (1, 2, 3, 4):
        for combo in itertools.product(universe, repeat=k):
            yield ("exhaustive", list(combo))
    rng = random.Random(20260809)
    for _ in range(2000):
        n = rng.randint(5, 8)
        jobs = []
        for _ in range(n):
            s = rng.randint(-3, 5)
            jobs.append((s, s + rng.randint(1, 4), rng.randint(1, 3)))
        yield ("random", jobs)


def run_q2():
    stats = {
        name: {
            "instances": 0,
            "exhaustive_instances": 0,
            "random_instances": 0,
            "weight_matches_oracle": 0,
            "weight_mismatches": 0,
            "sequence_differs_from_lex_min": 0,
            "mutation_detected": 0,
            "first_r6_violation_example": None,
        }
        for name, _ in SURROGATES
    }
    for tag, jobs in q2_cases():
        arg = [tuple(j) for j in jobs]
        expected = oracle_solve(list(arg))
        for name, fn in SURROGATES:
            st = stats[name]
            snap = copy.deepcopy(arg)
            got = fn(list(arg))
            st["instances"] += 1
            st["%s_instances" % tag] += 1
            if arg != snap:
                st["mutation_detected"] += 1
            if got[0] == expected[0]:
                st["weight_matches_oracle"] += 1
            else:
                st["weight_mismatches"] += 1
            if got[1] != expected[1]:
                st["sequence_differs_from_lex_min"] += 1
                if st["first_r6_violation_example"] is None:
                    st["first_r6_violation_example"] = {
                        "jobs": [list(j) for j in arg],
                        "oracle": [expected[0], expected[1]],
                        "surrogate": [got[0], list(got[1])],
                    }
    admissible = {}
    for name, _ in SURROGATES:
        st = stats[name]
        st["admissible"] = (
            st["weight_mismatches"] == 0
            and st["mutation_detected"] == 0
            and st["sequence_differs_from_lex_min"] >= 1
        )
        admissible[name] = st["admissible"]
    return stats, admissible


# ---------------------------------------------------------------- Q3
CLASSIC_JOBS = [(1, 4, 3), (3, 5, 2), (0, 6, 6), (4, 7, 3), (3, 8, 7),
                (5, 9, 4), (6, 10, 5), (8, 11, 2)]


def run_q3(candidates):
    out = {}
    w, seqs = all_optimal_sequences(CLASSIC_JOBS)
    out["classic_instance_from_test_classic_instance"] = {
        "jobs": [list(j) for j in CLASSIC_JOBS],
        "optimal_weight": w,
        "all_optimal_sequences": seqs,
        "num_optimal_sequences": len(seqs),
        "tie_bearing": len(seqs) >= 2,
        "lex_smallest": min(seqs) if seqs else [],
    }
    out["synthetic_candidates"] = []
    for jobs in candidates:
        w, seqs = all_optimal_sequences(jobs)
        out["synthetic_candidates"].append({
            "jobs": [list(j) for j in jobs],
            "optimal_weight": w,
            "all_optimal_sequences": seqs,
            "num_optimal_sequences": len(seqs),
            "tie_bearing": len(seqs) >= 2,
            "lex_smallest": min(seqs) if seqs else [],
        })
    return out


# ---------------------------------------------------------------- Q4
def instances_at(n, span, wmax):
    """All ordered n-job instances, coords in [0..span], weights in [1..wmax]."""
    universe = []
    for s in range(0, span + 1):
        for e in range(s + 1, span + 1):
            for w in range(1, wmax + 1):
                universe.append((s, e, w))
    for combo in itertools.product(universe, repeat=n):
        yield list(combo)


def discriminates(jobs, admissible_fns, check_canonical=True):
    """Tie-bearing AND failed by every admissible surrogate
    AND (optionally) passed by canonical."""
    w, seqs = all_optimal_sequences(jobs)
    if len(seqs) < 2:
        return False, None
    lex = min(seqs)
    expected = (w, lex)
    for _name, fn in admissible_fns:
        if fn(list(jobs)) == expected:
            return False, expected
    if check_canonical and canonical.solve(list(jobs)) != expected:
        return False, expected
    return True, expected


def run_q4(admissible_fns):
    """Minimality measure (stated explicitly, lexicographic priority):
      1. fewest jobs n;
      2. smallest coordinate universe: coords drawn from [0..span],
         minimize span (coordinate placement is shift-invariant under
         R2, so [0..span] is a canonical universe);
      3. smallest weight universe: weights drawn from [1..wmax],
         minimize wmax;
      4. fewest assertions in the candidate test (1 is the floor).
    Search bound: n <= 3, span <= 4, wmax <= 2 (exhaustive within bound).
    Tie among equals broken by lexicographic order of the instance literal.
    """
    summary = {
        "measure": [
            "fewest jobs",
            "smallest coordinate universe [0..span] (minimize span)",
            "smallest weight universe [1..wmax] (minimize wmax)",
            "fewest assertions",
        ],
        "search_bounds": {"n_max": 3, "span_max": 4, "wmax_max": 2},
        "lower_bound_proof_n_lt_2": (
            "n=0: the only feasible subset is [] with W=0 -> unique optimum, "
            "no tie. n=1: weights are strictly positive (R1), so {0} with "
            "W=w0>0 strictly beats [] and is the only optimal sequence -> no "
            "instance with fewer than 2 jobs can admit an optimal tie, hence "
            "none can be tie-bearing per the Q3 criterion."
        ),
        "cells_examined": [],
        "chosen": None,
        "smaller_cells_all_negative": None,
    }
    found = None
    for n in (2, 3):
        for span in range(1, 5):
            for wmax in (1, 2):
                cell = {"n": n, "span": span, "wmax": wmax,
                        "instances_checked": 0, "discriminating": 0,
                        "first_discriminating": None}
                for jobs in instances_at(n, span, wmax):
                    cell["instances_checked"] += 1
                    ok, expected = discriminates(jobs, admissible_fns)
                    if ok:
                        cell["discriminating"] += 1
                        if cell["first_discriminating"] is None:
                            cell["first_discriminating"] = {
                                "jobs": [list(j) for j in jobs],
                                "expected": [expected[0], expected[1]],
                            }
                summary["cells_examined"].append(cell)
                if found is None and cell["discriminating"] > 0:
                    found = (n, span, wmax, cell["first_discriminating"])
            if found is not None and found[0] == n and found[1] == span:
                break
        if found is not None and found[0] == n:
            break
    if found is not None:
        n, span, wmax, first = found
        summary["chosen"] = {
            "n": n, "span": span, "wmax": wmax, "assertions": 1,
            "jobs": first["jobs"],
        }
        neg = [c for c in summary["cells_examined"]
               if (c["n"], c["span"], c["wmax"]) < (n, span, wmax)]
        summary["smaller_cells_all_negative"] = all(
            c["discriminating"] == 0 for c in neg)
    return summary, found


# ---------------------------------------------------------------- Q5
def run_q5(chosen_jobs):
    """ORACLE-FIRST: oracle enumeration + hand derivation recorded BEFORE
    the canonical solver is invoked on the chosen instance."""
    provenance = []
    w, seqs = all_optimal_sequences(chosen_jobs)
    lex = min(seqs)
    provenance.append("1_oracle_enumeration: full subset enumeration "
                      "computed W=%d, all optimal sequences=%r, "
                      "lex-min S=%r" % (w, seqs, lex))
    derivation = (
        "Hand derivation from R2/R5/R6 for jobs=%r: R2 (half-open "
        "intervals) — every pair of jobs overlaps (no pair satisfies "
        "a.end <= b.start or b.end <= a.start), so every feasible "
        "schedule contains at most one job. R5 — each singleton {i} has "
        "total weight equal to that job's weight; the maximum singleton "
        "weight is W=%d, and multiple singletons attain it, so the "
        "optimum is tied. R6 — among the tied ascending index sequences "
        "%r, the lexicographically smallest is S=%r, which the spec "
        "selects uniquely." % ([list(j) for j in chosen_jobs], w, seqs, lex)
    )
    provenance.append("2_hand_derivation_recorded")
    canonical_result = canonical.solve(list(chosen_jobs))
    provenance.append(
        "3_canonical_solver_run: src/solver.py returned %r" %
        (canonical_result,))
    return {
        "expected_W": w,
        "expected_S": lex,
        "all_optimal_sequences": seqs,
        "hand_derivation": derivation,
        "canonical_solver_result": [canonical_result[0],
                                    list(canonical_result[1])],
        "canonical_agrees_with_oracle": list(canonical_result[1]) == lex
        and canonical_result[0] == w,
        "provenance_order": provenance,
    }


def main():
    q2_stats, admissible = run_q2()
    admissible_fns = [(n, f) for n, f in SURROGATES if admissible[n]]
    discarded = [n for n, _ in SURROGATES if not admissible[n]]

    q4_summary, found = run_q4(admissible_fns)
    chosen_jobs = None
    q5 = None
    q3_candidates = []
    if found is not None:
        chosen_jobs = [tuple(j) for j in q4_summary["chosen"]["jobs"]]
        q3_candidates.append(chosen_jobs)
        # also enumerate ties for every discriminating witness cell found
        for cell in q4_summary["cells_examined"]:
            fd = cell["first_discriminating"]
            if fd and [tuple(j) for j in fd["jobs"]] != chosen_jobs:
                q3_candidates.append([tuple(j) for j in fd["jobs"]])
        q5 = run_q5(chosen_jobs)
    q3 = run_q3(q3_candidates)

    # surrogate behavior on the chosen instance (for the record)
    per_surrogate_on_chosen = {}
    if chosen_jobs is not None:
        for name, fn in SURROGATES:
            r = fn(list(chosen_jobs))
            per_surrogate_on_chosen[name] = [r[0], list(r[1])]

    out = {
        "q2_surrogate_differential": q2_stats,
        "admissible_surrogates": [n for n, _ in admissible_fns],
        "discarded_surrogates": discarded,
        "q3_tie_enumerations": q3,
        "q4_minimality_search": q4_summary,
        "q5_oracle_first_derivation": q5,
        "surrogate_results_on_chosen_instance": per_surrogate_on_chosen,
    }
    with open(os.path.join(SANDBOX, "q_results.json"), "w") as f:
        json.dump(out, f, indent=2)
    print("admissible:", [n for n, _ in admissible_fns])
    print("discarded:", discarded)
    print("chosen:", q4_summary.get("chosen"))
    if q5:
        print("expected:", q5["expected_W"], q5["expected_S"],
              "canonical_agrees:", q5["canonical_agrees_with_oracle"])


if __name__ == "__main__":
    main()
