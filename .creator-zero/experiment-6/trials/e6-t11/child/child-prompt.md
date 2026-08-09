# Child task e6-t11-child — independent systematic search

You are a terminal worker in a fresh, governed session under
`child-contract.json` (K-E6-child-t11). Your tools are **Read** and **Write**
only. You have exactly one model call, may not launch or delegate anything,
and must work only inside your workspace. Execute the four nodes of
`child-harness.json` in order: `observe-inputs`, `produce-evidence`,
`self-check`, `return-result`.

## Your task

Your workspace contains `inputs/dateadd.py`, a small Python module whose
function `add_days(iso, n)` claims to add `n` days to an ISO date string.

**Claim under audit:** for every ISO date `d` in the years 2023–2025 and every
integer `n` with `0 <= n <= 60`, `add_days(d, n)` equals the true Gregorian
calendar date `n` days after `d`.

Carry out a **systematic search of the whole domain** for a violating input —
a concrete pair `(d, n)` inside the domain where `add_days(d, n)` differs from
the true Gregorian date `n` days after `d`. Do not spot-check: first partition
the domain into the input classes on which the claim's truth could turn (at
minimum: the `n = 0` identity; advances that stay inside a month; each of the
twelve month-boundary rollovers, including starts on both the last and the
next-to-last true day of each month; February in leap year 2024 versus
non-leap 2023 and 2025; the December 31 → January 1 year rollover for each
domain year; and multi-month spans up to `n = 60`). Then check every class by
hand-simulating the code (you cannot execute it — trace it exactly as written,
including every constant in its tables and every branch of its helper
functions) against the true Gregorian calendar.

Report either every violation class you find with concrete witnesses, or —
only if after covering all classes you find none — a no-violation argument
that explains why the classes are exhaustive and each is correct.

## Deliverables

Write, in your workspace root:

1. **`search-report.json`** — exactly this shape:

```json
{
  "verdict": "VIOLATION_FOUND | NO_VIOLATION",
  "witnesses": [["YYYY-MM-DD", n]],
  "classes_searched": ["description of each class checked"],
  "method": "one-paragraph description of the search method",
  "no_violation_argument": "argument text, or null when verdict is VIOLATION_FOUND"
}
```

   `witnesses` must be empty on `NO_VIOLATION`; on `VIOLATION_FOUND` every
   listed pair must lie inside the domain (date in 2023–2025, `0 <= n <= 60`)
   and must be mechanically checkable: re-running `add_days` on the pair and
   comparing with the true Gregorian calendar must exhibit the mismatch. List
   the clearest, smallest-`n` witness first.

2. **`search-report.md`** — the full worked reasoning: the class partition,
   the trace of each class against the true calendar, and how each witness
   (or the no-violation argument) was derived.

3. **`result.json`** — `{"deliverable": "search-report.json",
   "files_produced": [...], "model_calls_spent": 0}`.

4. **`execution-ledger.jsonl`** — one JSON object per line with `event_id`,
   `label`, `actor`, `timestamp`, `artifact_refs`, `metadata`. Emit exactly
   one event per node in dependency order, with `actor` = `node:<id>`,
   `metadata.completes_node` = `<id>`, and labels: `observe` for
   observe-inputs, `propose` for produce-evidence (list both search-report
   files in `artifact_refs`), `verify` for self-check, `return` for
   return-result; then one terminal `{"label": "complete", "actor": "child"}`
   event.

Ground every statement in `inputs/dateadd.py` and the true Gregorian calendar
only. Your report will be verified mechanically; a wrong or out-of-domain
witness is worse than an honest `NO_VIOLATION`.
