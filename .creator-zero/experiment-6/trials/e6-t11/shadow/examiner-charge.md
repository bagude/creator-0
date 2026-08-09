# Examiner charge — e6-t11 (verify-independent)

You are the independent, information-only examiner for task e6-t11. You are
not the author of the provisional answer. Re-derive the following from
`package/artifacts/dateadd.py` and `package/task.json` alone before reading
the worker's artifacts, then compare.

## Provisional answer under examination

- Verdict: **VIOLATED** over the domain (ISO dates in 2023-2025, 0 <= n <= 60).
- Witness: `add_days("2023-08-30", 1)` returns `"2023-09-01"`; the true
  Gregorian date one day after 2023-08-30 is `"2023-08-31"`.
- Root cause claimed: `DAYS` table entry for August (index 7) is 30; the
  true length of August is 31. All other table entries, the leap-year
  branch, and the rollover logic are claimed correct.

## Answer components whose failure would change the deliverable

1. **The August table entry.** If `DAYS[7]` is in fact 31 (i.e. the worker
   misread the source), the witness trace collapses and the verdict is no
   longer supported — the whole deliverable would need re-derivation.
2. **The witness trace.** If `add_days("2023-08-30", 1)` actually returns
   `"2023-08-31"`, the cited input is not violating; a different witness
   (or verdict HOLDS) would be required.
3. **Domain membership.** If the witness date or n were outside
   2023-2025 x [0, 60], the evidence would be inadmissible per E-C.

## Checking method

1. **Table audit (attack component 1).** Read `dateadd.py` line 1 and
   compare each of the 12 `DAYS` entries against the true Gregorian month
   lengths (31,28,31,30,31,30,31,31,30,31,30,31). Sum the table: a correct
   non-leap table sums to 365. Record every discrepancy you find, not just
   the claimed one.
2. **Mechanical re-trace (attack component 2).** Hand-execute
   `add_days("2023-08-30", 1)` statement by statement: parse (y=2023, m=8,
   d=30); one loop iteration; the `_dim(2023, 8)` call path (m != 2, so
   `DAYS[7]`); the rollover comparison; the formatted return. State the
   exact returned string and compare with the true date.
3. **Domain check (attack component 3).** Confirm 2023-08-30 is a valid ISO
   date in 2023-2025 and 0 <= 1 <= 60.
4. **Systematic search over the input classes (E-B).** Independently of the
   worker's witness, search the domain structured by classes: n=0 identity;
   within-month spans; last-day-of-month + 1 for each month Jan-Dec in a
   leap year (2024) and a non-leap year (2023 or 2025); (last-day - 1) + 1
   for each month (no-roll direction — this is where an understated table
   entry surfaces); Feb 28/29 transitions in 2024 vs Feb 28 in 2023/2025;
   Dec 31 -> Jan 1 for each year; and at least one multi-month span with
   n near 60 crossing two boundaries. For each probe, hand-compute the
   code's output and the true date. Report every violating pair found and
   whether the worker's classes (input-class-analysis.md, C1-C7) omit any
   class on which the claim's truth could turn.
5. **Deliverable-shape check.** Confirm `result.json` matches the shape in
   `package/task.json` -> `deliverable` and that `resolution.json` conforms
   to `resolution-schema.json`.

Your output is information-only; you have no write or promotion authority.
Report agreement or disagreement per component, with your own traces as
evidence. Your systematic search record, being of distinct process origin
from the provisional answer's author, is the intended admissible evidence
for distinction Q3 (requirement E-B).
