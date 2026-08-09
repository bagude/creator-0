# Examiner charge — e6-t08 (verify-independent)

You are the root-launched independent examiner for task e6-t08. You did not
author the provisional answer; your search and argument are what makes
evidence requirement E-B admissible. Re-derive everything below from
`package/artifacts/merge.py` and `package/task.json` yourself; do not treat
the worker's conclusions as given.

## Provisional answer under examination

- Verdict: **VIOLATED**.
- Claimed violating input: `[[0, 1], [1, 2]]`.
- Claimed mechanism: line 8 of merge.py uses the strict comparison
  `s < out[-1][1]`, so an interval whose start equals the previous output
  interval's end is appended unmerged; the claim forbids `i.end >= j.start`
  in the sorted output, and equality then occurs.

## Answer components whose failure would change the deliverable

Attack each of these specifically; refuting any one flips or invalidates
the verdict:

1. **Claim reading.** Confirm the claim in package/task.json really uses
   `>=` (so touching output intervals count as violations). If the claim
   only forbade strict overlap (`>`), the verdict would be HOLDS — check
   whether any in-domain input can make merge emit a pair with
   `i.end > j.start` (the worker argues it cannot, because line 8 merges
   all strict overlaps).
2. **Domain membership.** Verify `[[0,1],[1,2]]` satisfies: at most 6
   intervals, integer endpoints in [-10, 10], start <= end for each.
3. **Mechanical trace.** Execute merge.py's logic by hand on
   `[[0,1],[1,2]]`: sorting, `out = [[0,1]]`, the test `1 < 1`, the append,
   and the returned value. Confirm the sorted output contains a pair
   i before j with `i.end >= j.start`. If the trace instead merges the
   intervals (i.e. if line 8 were actually `<=`), the demonstration fails
   and the verdict must be re-derived from scratch.

## Required independent search (E-B)

Carry out your own systematic search of the domain, not a replay of the
worker's example:

- Enumerate the boundary classes structurally: touching pairs
  (`[a,b],[b,c]`), zero-width intervals (`[a,a]` alone, duplicated, and
  touching a wider interval), nested intervals, duplicates, proper
  overlaps, empty and singleton lists, negative endpoints, and unsorted
  presentations of each.
- For each class, decide from the code whether merge's output can contain a
  forbidden pair, and record at least one concrete in-domain witness for
  every class you find violating (do not reuse `[[0,1],[1,2]]` as your only
  witness; e.g. check a zero-width case and a negative-endpoint case too).
- If you conclude no violating input exists in the domain, you must instead
  produce the E-B argument for that: a case analysis over the loop
  invariant of merge.py showing every reachable output satisfies
  `i.end < j.start` for consecutive pairs — and then explain the
  discrepancy with the worker's trace explicitly.

## Checking method and report

Work read-only. Use hand execution / symbolic tracing of the actual code
text (no idealized merge). Report, in your session's output: (a) PASS/FAIL
per numbered component above, (b) your independent search record by class
with witnesses, (c) your final independent verdict HOLDS/VIOLATED, and
(d) whether the deliverable in result.json should stand unchanged.
Deterministic root verification, not this charge, decides promotion.
