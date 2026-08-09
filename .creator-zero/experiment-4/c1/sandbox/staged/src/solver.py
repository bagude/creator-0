"""Q5 surrogate: exhaustive-enumeration solve() — plausible R8 regression.

Preserves R1-R7 semantics (validation, half-open compatibility, max weight,
lexicographically smallest optimal ascending index sequence, purity,
determinism) but replaces the polynomial DP with unmemoized include/exclude
recursion over all feasible subsets: Theta(2^n) recursion nodes. This is the
violation class R8 names: "exhaustive subset enumeration is not acceptable".

Include-first DFS visits complete ascending index sequences in lexicographic
order, so keeping the FIRST subset that strictly improves the best weight
yields the lex-smallest optimal sequence (R6); no optimal subset is a proper
prefix of another because all weights are positive.
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


def _compat(a, b):
    return a[1] <= b[0] or b[1] <= a[0]


def solve(jobs):
    _validate(jobs)
    n = len(jobs)
    best = {"w": 0, "seq": ()}

    def rec(i, chosen, weight):
        if i == n:
            if weight > best["w"]:
                best["w"] = weight
                best["seq"] = chosen
            return
        if all(_compat(jobs[c], jobs[i]) for c in chosen):
            rec(i + 1, chosen + (i,), weight + jobs[i][2])
        rec(i + 1, chosen, weight)

    rec(0, (), 0)
    return (best["w"], list(best["seq"]))
