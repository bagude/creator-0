# Child task: independent ISO week-date derivation (e6-t03-child)

You are an isolated, terminal worker process. Your workspace contains:

- `inputs/dates.json` — a JSON array of 10 Gregorian calendar dates in
  `YYYY-MM-DD` form. This is your ONLY input. Do not assume access to any
  other file, and do not invent additional inputs.
- `child-harness.json` — the four-node harness you execute
  (observe-inputs, produce-evidence, self-check, return-result).
- `child-contract.json` — your governing contract. You have tools Read and
  Write only. You may not create, delegate, or launch anything.

## Task

For every date in `inputs/dates.json`, compute its ISO-8601 week-date form
`YYYY-Www-D`, where `YYYY` is the ISO week-numbering year (which can differ
from the calendar year near year boundaries), `Www` is the zero-padded week
number 01–53, and `D` is the ISO weekday, 1 = Monday .. 7 = Sunday.

## Mandatory method (use this and nothing else)

You MUST derive every answer with the ordinal-date (day-of-year) formula
method below. You MUST NOT use nearest-Thursday / "Thursday of this week" /
"count Thursdays" reasoning in any step; that reasoning style is reserved
for a different process and using it voids your evidence.

For a date with calendar year `Y`:

1. `ordinal` = the day-of-year of the date (Jan 1 = 1; account for leap
   years: `Y` is leap iff divisible by 4 and not by 100, unless divisible
   by 400).
2. `weekday` = ISO weekday 1..7 (1 = Monday). Compute it arithmetically,
   e.g. via the day-count formula of your choice (Zeller's congruence or an
   epoch day-number mod 7), not by locating Thursdays.
3. `week = floor((ordinal - weekday + 10) / 7)`.
4. Boundary rules:
   - If `week == 0`, the date belongs to the LAST week of year `Y-1`: the
     ISO year is `Y-1` and the week number is `weeks(Y-1)`.
   - If `week == 53` and year `Y` does not have 53 weeks, the ISO year is
     `Y+1` and the week number is 01.
   - Otherwise the ISO year is `Y` and the week number is `week`.
   - `weeks(y) = 53` iff Jan 1 of `y` falls on a Thursday, or `y` is a
     leap year and Jan 1 of `y` falls on a Wednesday; otherwise 52. (This
     is a lookup rule on Jan-1's weekday, not week-membership reasoning.)
5. The answer is `<ISO year>-W<zero-padded week>-<weekday>`.

Show the intermediate values (ordinal, weekday, raw week, boundary rule
applied) for each date in your method statement or working notes.

## Deliverable

Write `child-answers.json` at the workspace root, exactly this shape:

```json
{
  "answers": {"YYYY-MM-DD": "YYYY-Www-D"},
  "method": "prose statement of the ordinal-date formula method as actually applied, including per-date intermediates (ordinal, weekday, raw week, boundary rule)"
}
```

`answers` must contain exactly one entry for every date in
`inputs/dates.json` (all 10), keyed by the input date string.

Then write `result.json`:

```json
{
  "summary": "what was produced",
  "files_produced": ["child-answers.json"],
  "model_calls_spent": 0
}
```

## Ledger

Write `execution-ledger.jsonl` at the workspace root: one JSON object per
line with fields `event_id`, `label`, `actor`, `timestamp`, `artifact_refs`,
`metadata`. Emit, in order:

1. `{"label": "observe", "actor": "node:observe-inputs", "metadata": {"completes_node": "observe-inputs"}}`
2. `{"label": "propose", "actor": "node:produce-evidence", "artifact_refs": ["child-answers.json"], "metadata": {"completes_node": "produce-evidence"}}`
3. `{"label": "verify", "actor": "node:self-check", "metadata": {"completes_node": "self-check"}}`
4. `{"label": "return", "actor": "node:return-result", "artifact_refs": ["result.json"], "metadata": {"completes_node": "return-result"}}`
5. terminal `{"label": "complete", "actor": "child"}`

(each with a unique `event_id` and a timestamp; fill `artifact_refs` with
`[]` where no file was authored).

## Conduct

- Every answer must be exactly right; the dates are chosen so that sloppy
  methods get the ISO year or the 52/53/01 week number wrong. Apply the
  boundary rules literally.
- Your self-check is non-authoritative; deterministic verification happens
  outside your session.
- Do not guess or copy answers from memory of similar tables; derive each
  one with the formula above.
