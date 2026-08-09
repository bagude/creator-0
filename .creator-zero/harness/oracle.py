"""Independent brute-force oracle derived solely from docs/solver_spec.md.

Deliberately shares no code or algorithmic structure with src/solver.py:
it enumerates every subset (exponential), so it is only usable for small n,
but its correctness is transparent against requirements R1-R7.
"""

from itertools import combinations

MAX_N = 14


def spec_validate(jobs):
    """Return None if input is valid per R1, else the reason string."""
    if not isinstance(jobs, list):
        return "jobs must be a list"
    for job in jobs:
        if not isinstance(job, (tuple, list)) or len(job) != 3:
            return "job must be a triple"
        for v in job:
            if type(v) is not int:
                return "fields must be int (bool rejected)"
        start, end, weight = job
        if end <= start:
            return "end must exceed start"
        if weight <= 0:
            return "weight must be positive"
    return None


def compatible(a, b):
    # R2: half-open intervals, touching allowed.
    return a[1] <= b[0] or b[1] <= a[0]


def oracle_solve(jobs):
    """Exhaustive reference answer: (W, S) per R3-R7."""
    assert spec_validate(jobs) is None
    n = len(jobs)
    assert n <= MAX_N, "oracle is exponential; refuse large instances"
    best_w = 0
    best_s = []
    for size in range(1, n + 1):
        for subset in combinations(range(n), size):
            if all(
                compatible(jobs[a], jobs[b])
                for a, b in combinations(subset, 2)
            ):
                w = sum(jobs[i][2] for i in subset)
                s = list(subset)
                if w > best_w or (w == best_w and s < best_s):
                    best_w, best_s = w, s
    return (best_w, best_s)
