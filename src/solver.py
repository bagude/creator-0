"""Weighted interval scheduling solver.

Governing specification: docs/solver_spec.md
"""

import bisect


def solve(jobs):
    """Return (W, S): maximum total weight and the canonical optimal schedule.

    S is the lexicographically smallest ascending list of job indices among
    all optimal pairwise-compatible subsets.
    """
    _validate(jobs)
    n = len(jobs)
    if n == 0:
        return (0, [])

    total = _opt_weight(range(n), jobs)

    chosen = []
    chosen_weight = 0
    for i in range(n):
        if any(not _compatible(jobs[c], jobs[i]) for c in chosen):
            continue
        pool = [
            j
            for j in range(i + 1, n)
            if _compatible(jobs[i], jobs[j])
            and all(_compatible(jobs[c], jobs[j]) for c in chosen)
        ]
        if chosen_weight + jobs[i][2] + _opt_weight(pool, jobs) == total:
            chosen.append(i)
            chosen_weight += jobs[i][2]

    return (total, chosen)


def _validate(jobs):
    if not isinstance(jobs, list):
        raise ValueError("jobs must be a list")
    for job in jobs:
        if not isinstance(job, (tuple, list)) or len(job) != 3:
            raise ValueError("each job must be a (start, end, weight) triple")
        start, end, weight = job
        for v in (start, end, weight):
            if type(v) is not int:
                raise ValueError("start, end, and weight must be int")
        if end <= start:
            raise ValueError("job interval must satisfy end > start")
        if weight <= 0:
            raise ValueError("job weight must be positive")


def _compatible(a, b):
    return a[1] <= b[0] or b[1] <= a[0]


def _opt_weight(indices, jobs):
    """Max total weight of a pairwise-compatible subset of `indices`."""
    order = sorted(indices, key=lambda j: (jobs[j][1], jobs[j][0]))
    if not order:
        return 0
    ends = [jobs[j][1] for j in order]
    dp = [0] * (len(order) + 1)
    for k, j in enumerate(order, start=1):
        start, _end, weight = jobs[j]
        p = bisect.bisect_right(ends, start, 0, k - 1)
        dp[k] = max(dp[k - 1], dp[p] + weight)
    return dp[-1]
