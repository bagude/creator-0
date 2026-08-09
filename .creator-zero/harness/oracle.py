"""Brute-force oracle for docs/solver_spec.md (n <= 10 only).

Enumerates ALL subsets of job indices, keeps those pairwise compatible per
R2 half-open semantics (a.end <= b.start or b.end <= a.start), finds max
total weight W, and among subsets achieving W returns the lexicographically
smallest ascending index sequence (R6).
"""

from itertools import combinations


def _compat(a, b):
    return a[1] <= b[0] or b[1] <= a[0]


def oracle_solve(jobs):
    n = len(jobs)
    assert n <= 10, "oracle limited to n <= 10"
    best_w = 0
    best_seqs = [()]
    for k in range(1, n + 1):
        for subset in combinations(range(n), k):
            ok = True
            for x in range(k):
                for y in range(x + 1, k):
                    if not _compat(jobs[subset[x]], jobs[subset[y]]):
                        ok = False
                        break
                if not ok:
                    break
            if not ok:
                continue
            w = sum(jobs[i][2] for i in subset)
            if w > best_w:
                best_w = w
                best_seqs = [subset]
            elif w == best_w:
                best_seqs.append(subset)
    return (best_w, list(min(best_seqs)))
