"""Verifier's OWN exponential surrogate — authored fresh from docs/solver_spec.md.

Deliberately a DIFFERENT construction from the evidence node's recursive
surrogate: iterative bitmask enumeration over all 2^n subsets with mostly
inline (non-function-call) per-subset work. This also stresses the candidate
discriminator's line-event counting: a pure call-counter would undercount
this shape, a trace-event counter must not.

Semantics per spec: R1 validation, R2 half-open compatibility, R5 max weight,
R6 lex-smallest ascending optimal index sequence (ascending-index bit order +
strict improvement scan visits index sequences in lexicographic order when
masks are enumerated in an order that lists lower-index-first subsets first;
here we instead collect ALL optimal masks and take the lexicographically
smallest sequence explicitly, which is unambiguous), R7 empty input.
"""


def solve(jobs):
    if not isinstance(jobs, list):
        raise ValueError("jobs must be a list")
    for job in jobs:
        if not isinstance(job, (tuple, list)) or len(job) != 3:
            raise ValueError("each job must be a (start, end, weight) triple")
        if type(job[0]) is not int or type(job[1]) is not int or type(job[2]) is not int:
            raise ValueError("start, end, and weight must be int")
        if job[1] <= job[0]:
            raise ValueError("job interval must satisfy end > start")
        if job[2] <= 0:
            raise ValueError("job weight must be positive")
    n = len(jobs)
    best_w = 0
    best_seq = []
    for mask in range(1 << n):
        members = []
        m = mask
        while m:
            b = m & -m
            members.append(b.bit_length() - 1)
            m ^= b
        feasible = True
        w = 0
        for x in range(len(members)):
            i = members[x]
            w += jobs[i][2]
            for y in range(x + 1, len(members)):
                j = members[y]
                if not (jobs[i][1] <= jobs[j][0] or jobs[j][1] <= jobs[i][0]):
                    feasible = False
                    break
            if not feasible:
                break
        if not feasible:
            continue
        if w > best_w or (w == best_w and w > 0 and members < best_seq):
            best_w = w
            best_seq = members
    return (best_w, best_seq)
