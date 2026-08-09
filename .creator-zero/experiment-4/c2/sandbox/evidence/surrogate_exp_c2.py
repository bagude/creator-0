"""C2's independent exponential surrogate (Q2) — R8-runtime violation witness.

Construction chosen to be structurally DISTINCT from both of C1's:
- C1 evidence surrogate (.../c1/sandbox/surrogate_exp.py): unmemoized
  include/exclude RECURSION, include-first DFS, first-improvement lex rule.
- C1 verify surrogate (.../c1/sandbox-verify/exp_mask.py): iterative bitmask
  enumerator.
This one: size-stratified itertools.combinations enumeration with explicit
lex-min tie tracking. Theta(2^n) subsets visited — exactly the class R8's
parenthetical names. R1-R7 semantics re-derived from docs/solver_spec.md,
not copied from C1.
"""

from itertools import combinations


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
    best_w = 0
    best_seq = ()
    for k in range(1, n + 1):
        for subset in combinations(range(n), k):
            feasible = True
            for x in range(k):
                for y in range(x + 1, k):
                    if not _compatible(jobs[subset[x]], jobs[subset[y]]):
                        feasible = False
                        break
                if not feasible:
                    break
            if not feasible:
                continue
            w = 0
            for i in subset:
                w += jobs[i][2]
            if w > best_w or (w == best_w and subset < best_seq):
                best_w = w
                best_seq = subset
    return (best_w, list(best_seq))
