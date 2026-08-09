# Solver Specification — Weighted Interval Scheduling

This document is the authoritative behavioral specification for
`src/solver.py`. Where implementation, tests, and this document disagree,
this document governs.

## Function

```python
solve(jobs: list) -> tuple[int, list[int]]
```

`jobs` is a list of jobs. Each job is a tuple or list of exactly three
values `(start, end, weight)`.

## Requirements

### R1 — Input validation

`solve` MUST raise `ValueError` if any of the following holds for any job:

- the job is not a tuple or list of exactly 3 elements;
- `start`, `end`, or `weight` is not of type `int` (`bool` is rejected,
  despite being a subclass of `int`);
- `end <= start` (zero-length and inverted intervals are invalid);
- `weight <= 0`.

`jobs` itself MUST be a list; otherwise raise `ValueError`.
Validation errors MUST be raised before any scheduling work is observable.

### R2 — Interval semantics

Intervals are half-open: job `a` occupies `[a.start, a.end)`.
Two jobs are **compatible** if and only if they do not overlap:

```
a.end <= b.start  or  b.end <= a.start
```

In particular, a job ending at time `t` is compatible with a job starting
at time `t` (touching is allowed). Starts may be negative.

### R3 — Output form

`solve` returns a tuple `(W, S)` where:

- `W` is an `int`: the maximum achievable total weight;
- `S` is a list of `int` indices into the original `jobs` list,
  sorted in strictly ascending order, with no duplicates.

### R4 — Feasibility

The jobs referenced by `S` MUST be pairwise compatible under R2.

### R5 — Optimality

`sum(jobs[i].weight for i in S) == W`, and no subset of pairwise-compatible
jobs has total weight greater than `W`.

### R6 — Canonical tie-break

Among all subsets achieving the optimum `W`, `S` MUST be the
lexicographically smallest ascending index sequence. (Sequences are
compared element-wise; because all weights are positive, no optimal subset
is a proper prefix of another.)

### R7 — Trivial input

`solve([])` returns `(0, [])`.

### R8 — Purity and determinism

`solve` MUST NOT mutate its argument and MUST be deterministic: identical
input yields an identical result. Runtime MUST be polynomial in
`len(jobs)` (exhaustive subset enumeration is not acceptable).
