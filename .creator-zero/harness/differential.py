"""Differential test: src/solver.py solve() vs brute-force oracle.

Exhaustive small grid + seeded random instances. Compares BOTH weight and
exact index sequence. Prints tallies and every counterexample as
(input, expected_from_oracle, actual_from_solve).
"""

import copy
import os
import random
import sys
from itertools import combinations_with_replacement

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
sys.path.insert(0, os.path.dirname(__file__))

from solver import solve
from oracle import oracle_solve

MAX_PRINT = 25


def run_case(jobs, tag, stats, counterexamples):
    arg = [tuple(j) for j in jobs]
    snap = copy.deepcopy(arg)
    expected = oracle_solve(arg)
    actual = solve(arg)
    stats["total"] += 1
    if arg != snap:
        stats["mutated"] += 1
        counterexamples.append((tag, "MUTATION", snap, None, arg))
    if actual == expected:
        stats["pass"] += 1
    else:
        stats["fail"] += 1
        if len(counterexamples) < 10000:
            counterexamples.append((tag, "MISMATCH", snap, expected, actual))


def grid_cases():
    """All job multisets of size 1..3 (starts/ends in [-2..4], weights {1,2}),
    plus deterministic size-4 sampling from the same universe."""
    universe = []
    for s in range(-2, 5):
        for e in range(s + 1, 5):
            for w in (1, 2):
                universe.append((s, e, w))
    # sizes 1..3 exhaustive over multisets (includes duplicate intervals,
    # touching intervals arise naturally from the range)
    for k in (1, 2, 3):
        for combo in combinations_with_replacement(universe, k):
            yield list(combo)
    # size-4 sampling, seeded
    rng = random.Random(12345)
    for _ in range(4000):
        yield [rng.choice(universe) for _ in range(4)]


def random_cases():
    rng = random.Random(987654321)
    for _ in range(2500):
        n = rng.randint(1, 10)
        jobs = []
        for _ in range(n):
            s = rng.randint(-6, 8)
            e = s + rng.randint(1, 6)
            w = rng.randint(1, 3)  # many equal weights -> stresses R6
            jobs.append((s, e, w))
        yield jobs


def main():
    stats = {"total": 0, "pass": 0, "fail": 0, "mutated": 0}
    counterexamples = []

    grid_stats = {"total": 0, "pass": 0, "fail": 0, "mutated": 0}
    for jobs in grid_cases():
        run_case(jobs, "grid", grid_stats, counterexamples)
    rand_stats = {"total": 0, "pass": 0, "fail": 0, "mutated": 0}
    for jobs in random_cases():
        run_case(jobs, "random", rand_stats, counterexamples)

    for k in stats:
        stats[k] = grid_stats[k] + rand_stats[k]

    print("GRID   total=%(total)d pass=%(pass)d fail=%(fail)d mutated=%(mutated)d" % grid_stats)
    print("RANDOM total=%(total)d pass=%(pass)d fail=%(fail)d mutated=%(mutated)d" % rand_stats)
    print("ALL    total=%(total)d pass=%(pass)d fail=%(fail)d mutated=%(mutated)d" % stats)
    print("COUNTEREXAMPLES total=%d (printing up to %d)" % (len(counterexamples), MAX_PRINT))
    for tag, kind, inp, exp, act in counterexamples[:MAX_PRINT]:
        print("  [%s/%s] input=%r expected_from_oracle=%r actual_from_solve=%r"
              % (tag, kind, inp, exp, act))
    return 1 if counterexamples else 0


if __name__ == "__main__":
    sys.exit(main())
