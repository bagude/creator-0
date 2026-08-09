"""Verifier's OWN legitimate polynomial reimplementation — authored fresh.

Different internals from both src/solver.py (bisect prefix DP) and the
evidence node's cubic control (end-sorted linear-scan prefix DP): this one
uses a START-sorted suffix DP with an O(n) linear predecessor scan, giving a
higher-degree but plainly polynomial implementation (~O(n^3) overall). The
candidate R8 test MUST pass on it: R8 admits any polynomial degree.
Reconstruction: ascending-index greedy certification, which yields the
lex-smallest optimal sequence (R6) because an index is kept iff keeping it
still permits reaching the global optimum.
"""


def _valid(jobs):
    if not isinstance(jobs, list):
        raise ValueError("jobs must be a list")
    for job in jobs:
        if not isinstance(job, (tuple, list)) or len(job) != 3:
            raise ValueError("each job must be a (start, end, weight) triple")
        if any(type(v) is not int for v in (job[0], job[1], job[2])):
            raise ValueError("start, end, and weight must be int")
        if job[1] <= job[0]:
            raise ValueError("job interval must satisfy end > start")
        if job[2] <= 0:
            raise ValueError("job weight must be positive")


def _max_weight(pool, jobs):
    """Suffix DP over start-sorted pool; O(m^2)."""
    order = sorted(pool, key=lambda j: (jobs[j][0], jobs[j][1]))
    m = len(order)
    suffix = [0] * (m + 1)
    for k in range(m - 1, -1, -1):
        j = order[k]
        end_j, w = jobs[j][1], jobs[j][2]
        nxt = m
        for t in range(k + 1, m):
            if jobs[order[t]][0] >= end_j:
                nxt = t
                break
        take = w + suffix[nxt]
        suffix[k] = take if take > suffix[k + 1] else suffix[k + 1]
    return suffix[0]


def solve(jobs):
    _valid(jobs)
    n = len(jobs)
    if n == 0:
        return (0, [])
    goal = _max_weight(list(range(n)), jobs)
    picked = []
    got = 0
    for i in range(n):
        clash = False
        for c in picked:
            if not (jobs[c][1] <= jobs[i][0] or jobs[i][1] <= jobs[c][0]):
                clash = True
                break
        if clash:
            continue
        pool = []
        for j in range(i + 1, n):
            if not (jobs[i][1] <= jobs[j][0] or jobs[j][1] <= jobs[i][0]):
                continue
            if all(jobs[c][1] <= jobs[j][0] or jobs[j][1] <= jobs[c][0] for c in picked):
                pool.append(j)
        if got + jobs[i][2] + _max_weight(pool, jobs) == goal:
            picked.append(i)
            got += jobs[i][2]
    return (goal, picked)
