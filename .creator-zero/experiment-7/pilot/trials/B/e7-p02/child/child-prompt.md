# Child task: implement the list joining format from its specification

You are a terminal worker session governed by `child-contract.json` and executing
`child-harness.json` in your workspace. Your only tools are **Read** and **Write**.
You may not create, delegate, or launch anything, and you may not attempt to access
any file outside your workspace. Your entire input is the file listed below — do not
assume the existence of any other material.

## Your input

- `inputs/joinspec.md` — a short specification of a list joining format.

This is the ONLY substantive input you have. Work solely from what this
specification states.

## Your task

1. **observe-inputs** — Read `inputs/joinspec.md`.
2. **produce-evidence** — Write `impl.py` at your workspace root. It must expose a
   function `join_items(items)` that implements exactly the behavior the
   specification states — nothing more, nothing less. Requirements:
   - Plain Python, standard library only (no imports should be needed).
   - `join_items` must be a pure function of its argument: no I/O, no printing, no
     global state, no side effects on `items`.
   - Do not add behavior the specification does not state (no trimming, no
     de-duplication, no sorting, no special-casing beyond what the spec says).
   - Where the specification is explicit, follow it literally. Do not invent
     handling for cases the specification does not describe.
3. **self-check** — Re-read `impl.py` against the specification, clause by clause,
   and confirm each stated clause is honored. This check is non-authoritative;
   record its outcome in your result summary.
4. **return-result** — Write `result.json` at your workspace root:

   ```json
   {
     "deliverable": "impl.py",
     "files_produced": ["impl.py", "result.json", "execution-ledger.jsonl"],
     "summary": "<one paragraph: what you implemented and the self-check outcome>",
     "model_calls_spent": 0
   }
   ```

## Ledger contract

Write `execution-ledger.jsonl` at your workspace root: one JSON object per line,
each with `event_id`, `label`, `actor`, `timestamp`, `artifact_refs`, `metadata`.
Emit exactly one event per harness node, in this order, each carrying
`metadata.completes_node` set to the node id:

1. `{"label": "observe",  "actor": "node:observe-inputs", ...}`
2. `{"label": "propose",  "actor": "node:produce-evidence", "artifact_refs": ["impl.py"], ...}`
3. `{"label": "verify",   "actor": "node:self-check", ...}`
4. `{"label": "return",   "actor": "node:return-result", "artifact_refs": ["result.json"], ...}`

Finish with one terminal event: `{"label": "complete", "actor": "child", ...}`.

## Deliverable summary

Your deliverable is `impl.py` exposing `join_items(items)`, faithful to
`inputs/joinspec.md` alone, plus `result.json` and `execution-ledger.jsonl`.
