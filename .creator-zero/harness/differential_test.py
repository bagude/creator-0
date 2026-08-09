"""Deterministic differential discriminator: src/solver.py vs the oracle.

Seeded PRNG only — every run is exactly reproducible. On any divergence
from the specification, writes executable counterexample evidence to
.creator-zero/runs/experiment-1-evidence.json and exits nonzero.

Env:
    SOLVER_DIR  directory containing solver.py (default: src)
"""

import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
SOLVER_DIR = os.environ.get("SOLVER_DIR", os.path.join(REPO, "src"))
sys.path.insert(0, HERE)
sys.path.insert(0, SOLVER_DIR)

from oracle import oracle_solve, spec_validate  # noqa: E402
from solver import solve  # noqa: E402

EVIDENCE_PATH = os.path.join(REPO, ".creator-zero", "runs",
                             "experiment-1-evidence.json")

REGIMES = [
    # (name, seed, cases, n_range, coord_range, weight_range)
    ("dense_small_ties", 101, 800, (0, 8), (-4, 8), (1, 4)),
    ("touching_grid", 202, 800, (1, 9), (0, 6), (1, 5)),
    ("sparse_wide", 303, 500, (1, 10), (-50, 50), (1, 100)),
    ("duplicate_heavy", 404, 500, (2, 8), (0, 4), (1, 3)),
    ("equal_weights", 505, 400, (1, 10), (-6, 10), (7, 7)),
]

INVALID_INPUTS = [
    ("not_a_list", ((0, 1, 1),)),
    ("bad_arity", [(0, 1)]),
    ("float_field", [(0, 1, 1.0)]),
    ("bool_field", [(False, True, 3)]),
    ("zero_length", [(2, 2, 5)]),
    ("inverted", [(3, 1, 5)]),
    ("zero_weight", [(0, 1, 0)]),
    ("negative_weight", [(0, 1, -2)]),
]


def gen_case(rng, n_range, coord_range, weight_range):
    n = rng.randint(*n_range)
    jobs = []
    for _ in range(n):
        a = rng.randint(*coord_range)
        b = rng.randint(*coord_range)
        if a == b:
            b = a + 1
        s, e = min(a, b), max(a, b)
        jobs.append((s, e, rng.randint(*weight_range)))
    return jobs


def check_case(jobs):
    """Return None if solver output matches the spec on jobs, else a dict."""
    snapshot = [tuple(j) for j in jobs]
    got = solve(list(jobs))
    if [tuple(j) for j in jobs] != snapshot:
        return {"violation": "R8 purity: input mutated", "jobs": snapshot}
    expected = oracle_solve(jobs)
    if not (isinstance(got, tuple) and len(got) == 2
            and isinstance(got[0], int) and isinstance(got[1], list)
            and all(isinstance(i, int) for i in got[1])):
        return {"violation": "R3 output form", "jobs": snapshot,
                "got": repr(got)}
    if (got[0], got[1]) != expected:
        which = "R5 optimality" if got[0] != expected[0] else \
            "R3/R4/R6 schedule (feasibility, order, or tie-break)"
        return {"violation": which, "jobs": snapshot,
                "got": [got[0], got[1]],
                "expected": [expected[0], expected[1]]}
    return None


def main():
    counterexamples = []
    executed = 0

    for name, bad in INVALID_INPUTS:
        executed += 1
        try:
            solve(bad if isinstance(bad, tuple) else list(bad))
        except ValueError:
            continue
        except Exception as exc:  # noqa: BLE001
            counterexamples.append({
                "violation": "R1 wrong exception type",
                "case": name, "raised": type(exc).__name__})
            continue
        counterexamples.append({
            "violation": "R1 invalid input accepted", "case": name})

    for name, seed, cases, n_range, coord_range, weight_range in REGIMES:
        rng = random.Random(seed)
        for _ in range(cases):
            jobs = gen_case(rng, n_range, coord_range, weight_range)
            if spec_validate(jobs) is not None:
                continue
            executed += 1
            failure = check_case(jobs)
            if failure is not None:
                failure["regime"] = name
                counterexamples.append(failure)
                if len(counterexamples) >= 5:
                    break
        if len(counterexamples) >= 5:
            break

    record = {
        "tool": "differential_test",
        "solver_dir": SOLVER_DIR,
        "cases_executed": executed,
        "counterexamples": counterexamples,
        "outcome": "DIVERGENCE" if counterexamples else "AGREEMENT",
    }
    with open(EVIDENCE_PATH, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2)
        f.write("\n")
    print(json.dumps(record, indent=2))
    return 1 if counterexamples else 0


if __name__ == "__main__":
    sys.exit(main())
