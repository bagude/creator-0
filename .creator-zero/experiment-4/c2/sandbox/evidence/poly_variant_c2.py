"""C2's legitimate polynomial variant (Q3) — false-positive probe.

A spec-conforming R1-R7 implementation structurally DISTINCT from canonical
src/solver.py (which uses bisect over end-times, O(n log n) opt) and from
C1's controls (end-sorted prefix DP / start-sorted suffix DP): this one
precomputes a full pairwise compatibility matrix and computes opt() with a
reversed LINEAR-SCAN predecessor search (no bisect), giving O(n^2) per opt
call and O(n^3) overall — a legitimately polynomial rewrite of higher degree
and different structure than the canonical implementation. If C1's
discriminator (per-doubling trace-event ratio bound 32) is overfit to
src/solver.py's structure, this variant should expose it.
"""


def _validate(jobs):
    if not isinstance(jobs, list):
        raise ValueError("jobs must be a list")
    for job in jobs:
        if not isinstance(job, (tuple, list)) or len(job) != 3:
            raise ValueError("each job must be a (start, end, weight) triple")
        s, e, w = job[0], job[1], job[2]
        for v in (s, e, w):
            if type(v) is not int:
                raise ValueError("start, end, and weight must be int")
        if e <= s:
            raise ValueError("job interval must satisfy end > start")
        if w <= 0:
            raise ValueError("job weight must be positive")


def _compatible(a, b):
    return a[1] <= b[0] or b[1] <= a[0]


def solve(jobs):
    _validate(jobs)
    n = len(jobs)
    if n == 0:
        return (0, [])

    compat = [[_compatible(jobs[i], jobs[j]) for j in range(n)] for i in range(n)]

    def opt(indices):
        order = sorted(indices, key=lambda j: (jobs[j][1], jobs[j][0]))
        m = len(order)
        dp = [0] * (m + 1)
        for k in range(1, m + 1):
            j = order[k - 1]
            s = jobs[j][0]
            w = jobs[j][2]
            p = 0
            for t in range(k - 1, 0, -1):
                if jobs[order[t - 1]][1] <= s:
                    p = t
                    break
            dp[k] = max(dp[k - 1], dp[p] + w)
        return dp[m]

    total = opt(range(n))
    chosen = []
    chosen_weight = 0
    for i in range(n):
        if any(not compat[c][i] for c in chosen):
            continue
        pool = [
            j
            for j in range(i + 1, n)
            if compat[i][j] and all(compat[c][j] for c in chosen)
        ]
        if chosen_weight + jobs[i][2] + opt(pool) == total:
            chosen.append(i)
            chosen_weight += jobs[i][2]
    return (total, chosen)
