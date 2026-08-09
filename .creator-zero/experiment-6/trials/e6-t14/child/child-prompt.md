# Child task e6-t14-child — amount formatting by digit-string tie inspection

You are an isolated worker session governed by `child-contract.json` and
executing `child-harness.json`. Your only tools are Read and Write. You may
not create, delegate, or launch anything. Work only inside your workspace.

## Inputs

Your workspace's `inputs/` directory contains exactly two files:

- `inputs/format-spec.md` — the formatting specification.
- `inputs/amounts.json` — a JSON array of 12 decimal amount strings.

Read both first (node `observe-inputs`). They are your only evidence
sources.

## Task

For each of the 12 amount strings, derive the formatted string mandated by
`inputs/format-spec.md`: exactly two decimal places with ties rounded to
the even neighbor, comma grouping of the integer part every three digits,
and negative amounts rendered unsigned inside parentheses.

## Mandatory method: pure digit-string tie inspection

You MUST derive every answer with the following lexical procedure, working
directly on each input's character string. Do NOT parse any input into a
binary floating-point number, and do NOT use scaled-integer arithmetic
(e.g. multiplying by 100 and comparing a remainder). Every decision must
come from inspecting digits of the string.

For each input string:

1. Note and remove a leading `-` if present.
2. Split at the decimal point into integer digits `I` and fraction digits
   `F` (`F` is empty if there is no point).
3. Conceptually extend `F` with trailing zeros so it has at least 3
   digits. The first two fraction digits `d1 d2` are the candidate
   decimals.
4. Inspect the third fraction digit `d3` and the tail `T` (all fraction
   digits after `d3`):
   - `d3` in 0–4: keep `d1 d2` unchanged.
   - `d3` in 6–9, or `d3 = 5` with any nonzero digit in `T`: round up.
   - `d3 = 5` and `T` all zeros (or empty): exact tie — round up only if
     `d2` is odd; if `d2` is even, keep `d1 d2` unchanged.
5. "Round up" means string increment with carry: add 1 to `d2`; if it was
   9 it becomes 0 and the carry moves left through `d1` and then through
   the digits of `I`, prepending a `1` if the carry runs off the left end.
6. Render `I` (after any carry) grouped with commas every three digits
   from the right, then `.`, then the two decimals.
7. If the original string had a `-`, wrap the result in parentheses and
   omit the sign; otherwise output it as is.

State this method in your deliverable's `method` field in your own words.

## Deliverable

At node `produce-evidence`, write `child-answers.json` in your workspace
root:

```json
{
  "answers": {
    "<input string exactly as it appears in inputs/amounts.json>": "<formatted string>",
    "... one entry per input, all 12, in the array's order ...": "..."
  },
  "method": "<statement of the digit-string tie-inspection method used>"
}
```

Keys must be the input strings verbatim; values must be the exact
formatted output strings, nothing else.

At node `return-result`, write `result.json`:

```json
{
  "deliverable": "child-answers.json",
  "files_produced": ["child-answers.json", "result.json", "execution-ledger.jsonl"],
  "model_calls_spent": 0
}
```

## Ledger

Maintain `execution-ledger.jsonl` in your workspace root per the
`ledger_contract` in `child-harness.json`: one JSON object per line with
`event_id`, `label`, `actor`, `timestamp`, `artifact_refs`, `metadata`.
Emit exactly one event per harness node in dependency order —
`observe` (actor `node:observe-inputs`), `propose` (actor
`node:produce-evidence`, with `child-answers.json` in `artifact_refs`),
`verify` (actor `node:self-check`), `return` (actor `node:return-result`)
— each carrying `metadata.completes_node`, then a terminal
`complete` event with actor `child`.
