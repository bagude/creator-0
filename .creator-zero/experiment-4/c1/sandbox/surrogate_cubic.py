"""Q6 false-positive control: a legitimate, fresh polynomial solve().

Authored fresh from docs/solver_spec.md (not copied from src/solver.py).
Same certification strategy the spec's R6 naturally suggests, but the inner
optimum uses an O(m^2) linear-scan-predecessor DP instead of bisect, making
the whole thing a higher-degree polynomial (~O(n^3)..O(n^4) on dense
instances) that must still PASS any justified R8 discriminator: R8 permits
any polynomial degree.
"""


def _validate(jobs):
    if not isinstance(jobs, list):
        raise ValueError("jobs must be a list")
    for job in jobs:
        if not isinstance(job, (tuple, list)) or len(job) != 3:
            raise ValueError("each job must be a (start, end, weight) triple")
        for v in (job[0], job[1], job[2]):
            if type(v) is not int:
                raise ValueError("start, end, and weight must be int")
        if job[1] <= job[0]:
            raise ValueError("job interval must satisfy end > start")
        if job[2] <= 0:
            raise ValueError("job weight must be positive")


def _ok(a, b):
    return a[1] <= b[0] or b[1] <= a[0]


def _best_weight(indices, jobs):
    """Max weight of a pairwise-compatible subset of indices, O(m^2)."""
    order = sorted(indices, key=lambda j: (jobs[j][1], jobs[j][0]))
    m = len(order)
    dp = [0] * (m + 1)
    for k in range(1, m + 1):
        j = order[k - 1]
        s, w = jobs[j][0], jobs[j][2]
        p = 0
        for t in range(k - 1):          # linear scan, ends are ascending
            if jobs[order[t]][1] <= s:
                p = t + 1
        dp[k] = max(dp[k - 1], dp[p] + w)
    return dp[m]


def solve(jobs):
    _validate(jobs)
    n = len(jobs)
    if n == 0:
        return (0, [])
    total = _best_weight(range(n), jobs)
    chosen = []
    weight = 0
    for i in range(n):
        if any(not _ok(jobs[c], jobs[i]) for c in chosen):
            continue
        rest = [
            j for j in range(i + 1, n)
            if _ok(jobs[i], jobs[j]) and all(_ok(jobs[c], jobs[j]) for c in chosen)
        ]
        if weight + jobs[i][2] + _best_weight(rest, jobs) == total:
            chosen.append(i)
            weight += jobs[i][2]
    return (total, chosen)
