# Child task e6-t17-child — independent parse enumeration

You are a terminal worker in a fresh, governed session under
`child-contract.json` (K-E6-child-t17). Your only tools are **Read** and
**Write**; you may not create, delegate, or launch anything. Work only
inside your workspace. Execute the four nodes of `child-harness.json` in
order: observe-inputs, produce-evidence, self-check, return-result.

## Inputs

Your workspace contains exactly these input files:

- `inputs/grammar.md` — an expression grammar
- `inputs/expression.txt` — one expression

Read both at `observe-inputs` before producing anything.

## Task

Enumerate **ALL distinct parses** of the expression in
`inputs/expression.txt` under the grammar in `inputs/grammar.md`. The
grammar defines no precedence and no associativity, so every way of fully
parenthesizing the expression is a distinct parse. Completeness is the
deliverable: a missed item is a wrong answer, and an invented item (one not
derivable from the grammar over the exact token sequence) is also a wrong
answer. Derive everything from the two input files alone.

## Deliverable format

At `produce-evidence`, write `enumeration.json` in your workspace root:

```json
{
  "items": ["...", "..."],
  "method": "how the enumeration was produced",
  "count": <number of items>
}
```

- Each item is one complete parse written as a **fully parenthesized form
  with no spaces**: numbers are bare leaves, and every binary operator
  application is wrapped in exactly one pair of parentheses, including the
  outermost one. Example of the format (for some expression): a parse might
  look like `((8-2)^(2-1))`.
- `items` must contain every distinct parse exactly once, **sorted in
  ascending lexicographic (byte) order**.
- `method` must state explicitly and precisely how you enumerated the space
  and why the enumeration is complete.

At `self-check`, re-read `enumeration.json` and confirm: item format
(fully parenthesized, no spaces), no duplicates, sorted order, and that the
count matches the number of parses the grammar admits for the token
sequence. This check is non-authoritative; record its outcome in the
ledger event's metadata.

At `return-result`, write `result.json`:

```json
{
  "summary": "one-sentence description of what was produced",
  "files_produced": ["enumeration.json", "result.json", "execution-ledger.jsonl"],
  "model_calls_spent": 0
}
```

## Ledger contract

Maintain `execution-ledger.jsonl` in your workspace root: one JSON object
per line, each with `event_id`, `label`, `actor`, `timestamp`,
`artifact_refs`, `metadata`. Emit exactly one event per executed node, in
dependency order, with `metadata.completes_node` set to the node id:

1. `{"label": "observe",  "actor": "node:observe-inputs",  ...}` — refs the input files
2. `{"label": "propose",  "actor": "node:produce-evidence", ...}` — refs `enumeration.json`, emitted at authoring time
3. `{"label": "verify",   "actor": "node:self-check",       ...}` — metadata records the structural check outcome
4. `{"label": "return",   "actor": "node:return-result",    ...}` — refs `result.json`

Finish with a terminal event `{"label": "complete", "actor": "child", ...}`
(no `completes_node`). Do not emit events for anything you did not do.
