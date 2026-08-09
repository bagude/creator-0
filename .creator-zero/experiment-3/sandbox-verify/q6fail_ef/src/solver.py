"""Surrogate A ("ef_dp_backtrack"): realistic reconstruction-order family.

Earliest-finish-sorted weighted-interval DP with the standard textbook
backtracking (skip job k when dp[k] == dp[k-1], else take it and jump to
p(k)). Satisfies R1-R5, R7, R8 by construction; does NOT lexicographically
minimize the returned index sequence (R6 violation family).
"""

import bisect


def solve(jobs):
    _validate(jobs)
    n = len(jobs)
    if n == 0:
        return (0, [])
    order = sorted(range(n), key=lambda j: (jobs[j][1], jobs[j][0]))
    ends = [jobs[j][1] for j in order]
    dp = [0] * (n + 1)
    ps = [0] * (n + 1)
    for k in range(1, n + 1):
        j = order[k - 1]
        start, _end, weight = jobs[j]
        p = bisect.bisect_right(ends, start, 0, k - 1)
        ps[k] = p
        dp[k] = max(dp[k - 1], dp[p] + weight)
    sel = []
    k = n
    while k > 0:
        if dp[k] == dp[k - 1]:
            k -= 1
        else:
            sel.append(order[k - 1])
            k = ps[k]
    return (dp[n], sorted(sel))


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
