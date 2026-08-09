# Child task: enumerate all parses of an ambiguous expression

You are a terminal worker session governed by `child-contract.json` and
executing `child-harness.json`. Your only tools are **Read** and **Write**;
you have exactly one model call and may not create, delegate, or launch
anything. Work only inside your workspace.

## Inputs

Your workspace contains an `inputs/` directory with exactly two files:

- `inputs/grammar.md` — an expression grammar
- `inputs/expression.txt` — one expression

Read both. They are your only sources; derive everything from them alone.

## Task

Enumerate **ALL** distinct parses of the expression in
`inputs/expression.txt` under the grammar in `inputs/grammar.md`. The
grammar defines no precedence and no associativity, so every way of fully
parenthesizing the expression is a distinct parse.

Write each parse as a **fully parenthesized form with no spaces**: every
application of `E op E` is wrapped in exactly one pair of parentheses and
numbers appear bare. For example, for a hypothetical expression
`1 - 2 ^ 3`, one of its fully parenthesized forms would be `(1-(2^3))` and
another `((1-2)^3)`.

Completeness is the deliverable: a missed parse is a wrong answer. State
the method you used and why it covers the whole parse space.

## Deliverable

Write `enumeration.json` at your workspace root:

```json
{
  "items": ["<fully parenthesized string>", "..."],
  "method": "<how the enumeration was produced and why it is complete>"
}
```

- `items` must contain every distinct parse, each with no spaces, with no
  duplicates, **sorted ascending** (plain code-point/lexicographic order).
- `method` must state the enumeration procedure and the completeness
  argument.

Then write `result.json` at your workspace root:

```json
{
  "deliverable": "enumeration.json",
  "files_produced": ["enumeration.json", "result.json", "execution-ledger.jsonl"],
  "model_calls_spent": 0
}
```

## Ledger

Maintain `execution-ledger.jsonl` at your workspace root: one JSON object
per line, each with `event_id`, `label`, `actor`, `timestamp`,
`artifact_refs`, `metadata`. Execute the four harness nodes in order and
give each exactly one event with `metadata.completes_node` set:

1. `{"label": "observe", "actor": "node:observe-inputs", ...}` — after reading `inputs/`.
2. `{"label": "propose", "actor": "node:produce-evidence", "artifact_refs": ["enumeration.json"], ...}` — at the moment you author `enumeration.json`.
3. `{"label": "verify", "actor": "node:self-check", ...}` — after re-reading the deliverable against this prompt's requirements (non-authoritative; record the structural outcome in `metadata`).
4. `{"label": "return", "actor": "node:return-result", "artifact_refs": ["result.json"], ...}` — when you write `result.json`.

Finish the ledger with a terminal line `{"label": "complete", "actor": "child", ...}`.
