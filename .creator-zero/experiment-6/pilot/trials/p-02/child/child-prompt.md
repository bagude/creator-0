# Child task: implement the list-joining format

You are a terminal worker session governed by `child-contract.json` and
executing `child-harness.json`. You have the tools **Read** and **Write**
only, and you work only inside your workspace. You may not create,
delegate, or launch anything.

## Your task

Your workspace contains a directory `inputs/` with a specification file,
`inputs/joinspec.md`. Read it, then author a python file that implements
exactly the format it specifies.

Deliverable: **`join_impl.py`** at the workspace root, a plain python file
exposing a top-level function

```python
def join_items(items):
    ...
```

that takes a list of strings and returns the single rendered line, exactly
as `inputs/joinspec.md` specifies — nothing more and nothing less. The file
must be importable as a module: no side effects at import time, no I/O, no
dependencies beyond the python standard library, and no code beyond what
the implementation needs.

Base the implementation solely on the text of `inputs/joinspec.md`. Do not
speculate about behaviors the spec does not mention; where the spec fixes a
behavior, follow it literally.

## Execution order (harness nodes)

1. `observe-inputs` — read every file in `inputs/`.
2. `produce-evidence` — write `join_impl.py`.
3. `self-check` — re-read `join_impl.py` against the spec's clauses and the
   deliverable requirements above; non-authoritative.
4. `return-result` — write `result.json` at the workspace root:

```json
{
  "summary": "<one sentence: what was implemented>",
  "files_produced": ["join_impl.py"],
  "model_calls_spent": 0
}
```

## Ledger contract

Write `execution-ledger.jsonl` at the workspace root: one JSON object per
line, each with `event_id`, `label`, `actor`, `timestamp`, `artifact_refs`,
`metadata`. Emit exactly one event per executed node, in order:

1. `{"label": "observe", "actor": "node:observe-inputs", "metadata": {"completes_node": "observe-inputs"}, ...}`
2. `{"label": "propose", "actor": "node:produce-evidence", "artifact_refs": ["join_impl.py"], "metadata": {"completes_node": "produce-evidence"}, ...}`
3. `{"label": "verify", "actor": "node:self-check", "metadata": {"completes_node": "self-check"}, ...}`
4. `{"label": "return", "actor": "node:return-result", "artifact_refs": ["result.json", "execution-ledger.jsonl"], "metadata": {"completes_node": "return-result"}, ...}`

Finish with a terminal event `{"label": "complete", "actor": "child", ...}`.
Fill `event_id` (e1, e2, ...) and `timestamp` (ISO 8601) on every line;
use `[]`/`{}` where a field has no content beyond what is shown.
