# Child task: format decimal amounts by exact scaled-integer arithmetic

You are a terminal worker process in a fresh session. Your workspace contains
an `inputs/` directory with exactly two files:

- `inputs/format-spec.md` — the formatting specification
- `inputs/amounts.json` — a JSON array of amount strings

You have only the Read and Write tools. You may not create, delegate, or
launch anything. Work entirely inside your workspace.

## Task

For every amount string in `inputs/amounts.json`, derive the formatted string
`format(x)` mandated by `inputs/format-spec.md`, and deliver all answers in
`child-answers.json`.

Every answer must be exactly right. The inputs are chosen so that careless
methods (in particular anything that touches binary floating point, and any
rounding mode other than the one the spec states) produce wrong answers.

## Required method — exact scaled-integer arithmetic (mandatory)

You MUST derive every answer with pure integer arithmetic, as follows. Do not
reason about the decimal digit string's tail directly, and never parse any
amount as a binary floating-point value.

For each amount string `s`:

1. `negative` = whether `s` begins with `-`; remove the sign.
2. Let `d` = the number of digits after the decimal point (0 if there is no
   point). Let `N` = the exact non-negative integer formed by concatenating
   the integer digits and the fractional digits (e.g. `"999999.995"` →
   `N = 999999995`, `d = 3`). `N` represents the amount in units of `10^-d`.
3. Scale to hundredths:
   - If `d <= 2`: `M = N * 10^(2-d)`. No rounding occurs.
   - If `d > 2`: let `k = 10^(d-2)`, `q = N div k` (integer division),
     `r = N mod k`, `half = 5 * 10^(d-3)`.
     - if `r < half`: `M = q`
     - if `r > half`: `M = q + 1`
     - if `r = half` (exact tie): `M = q` when `q` is even, else `M = q + 1`
       (ties to the even neighbor, per the spec).
4. `M` is the rounded amount in whole hundredths. Integer part
   `I = M div 100`; cents `C = M mod 100`, rendered as exactly two digits.
5. Render `I` in decimal with commas grouping every three digits from the
   right; append `.` and the two cent digits.
6. If `negative`, wrap the whole unsigned string in parentheses; otherwise
   output it as is.

Carry out every step per item explicitly (show `N`, `d`, `q`, `r`, `half`,
`M` in your working notes inside the deliverable's method description or a
brief derivation table in `child-derivation.md` if you produce one).

## Deliverable

Write `child-answers.json` in your workspace root, with exactly this shape:

```json
{
  "answers": {"<input string exactly as it appears in amounts.json>": "<formatted string>"},
  "method": "<a precise statement of the scaled-integer derivation you performed>"
}
```

`answers` must contain one entry for every element of `inputs/amounts.json`,
keyed by the input string verbatim.

Then write `result.json`: `{"summary": "<one sentence>", "files_produced":
[...], "model_calls_spent": 0}`.

## Ledger contract

Maintain `execution-ledger.jsonl` in your workspace root: one JSON object per
line — `{"event_id", "label", "actor", "timestamp", "artifact_refs",
"metadata"}`. Emit, in order:

1. `{"label": "observe", "actor": "node:observe-inputs", ..., "metadata": {"completes_node": "observe-inputs"}}` after reading `inputs/`.
2. `{"label": "propose", "actor": "node:produce-evidence", "artifact_refs": ["child-answers.json", ...], "metadata": {"completes_node": "produce-evidence"}}` when authoring the deliverable.
3. `{"label": "verify", "actor": "node:self-check", ..., "metadata": {"completes_node": "self-check"}}` after re-checking the deliverable's shape and coverage (non-authoritative).
4. `{"label": "return", "actor": "node:return-result", "artifact_refs": ["result.json"], "metadata": {"completes_node": "return-result"}}`.
5. A terminal `{"label": "complete", "actor": "child", ...}` line.
