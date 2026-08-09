# Child Task e6-t16-child — Session C-E6

You are **C-E6**, a terminal worker in a fresh, governed session under
`child-contract.json`. Your session grants only the tools **Read** and
**Write**, a single model call, and no ability to create, delegate, or
launch anything. Work only inside your workspace. Your only input material
is the file listed below; derive everything from it alone.

## Input

- `inputs/modules.json` — a list of software modules and their dependency
  edges. A dependency entry `{"from": "a", "to": "b"}` means **a depends
  on b**.

## Task

Enumerate **ALL** valid foundation/application splits of the modules in
`inputs/modules.json`. A split assigns every module to exactly one of
`layer1` (foundation) or `layer2` (application), with **both layers
non-empty**, such that **no module in layer1 depends on a module in
layer2**. (Modules in layer2 may freely depend on modules in layer1 or on
each other.)

Completeness is the deliverable: a missed split is a wrong answer, and so
is an invalid or duplicated split. Use a systematic method that provably
covers the whole space (for example: exhaustive enumeration of all subsets
as candidate layer1 sets with an explicit validity check, or enumeration of
all dependency-closed subsets), and state the method you used.

## Deliverable

Write `enumeration-2.json` in your workspace root, with exactly this shape:

```json
{
  "items": [
    {"layer1": ["..."], "layer2": ["..."]}
  ],
  "method": "how the enumeration was produced, stated precisely",
  "complete": true
}
```

- Within each item, sort `layer1` and `layer2` alphabetically.
- Sort `items` lexicographically by the `layer1` array.
- Set `complete` to `true` only if your method exhaustively covered the
  space; otherwise set it to `false` and say why in `method`.

Then write `result.json`:

```json
{
  "summary": "<one-sentence description of what was produced>",
  "files_produced": ["enumeration-2.json", "result.json", "execution-ledger.jsonl"],
  "model_calls_spent": 0
}
```

## Execution order and ledger

Execute the four nodes of `child-harness.json` in order: `observe-inputs`,
`produce-evidence`, `self-check`, `return-result`. Record
`execution-ledger.jsonl` in your workspace root: one JSON object per line
with fields `event_id`, `label`, `actor`, `timestamp`, `artifact_refs`,
`metadata`. Emit exactly one event per node, in this order:

1. `{"label": "observe", "actor": "node:observe-inputs", ..., "metadata": {"completes_node": "observe-inputs"}}` — `artifact_refs` lists the input files read.
2. `{"label": "propose", "actor": "node:produce-evidence", ..., "metadata": {"completes_node": "produce-evidence"}}` — `artifact_refs` lists `enumeration-2.json`, emitted at authoring time.
3. `{"label": "verify", "actor": "node:self-check", ..., "metadata": {"completes_node": "self-check"}}` — re-check `enumeration-2.json` against the task requirements (every module in exactly one layer, both layers non-empty, no layer1→layer2 dependency, sorted, no duplicates); record the outcome in `metadata`. This check is non-authoritative.
4. `{"label": "return", "actor": "node:return-result", ..., "metadata": {"completes_node": "return-result"}}` — `artifact_refs` lists `result.json`.

Finish the ledger with a terminal line
`{"label": "complete", "actor": "child", ...}`.
