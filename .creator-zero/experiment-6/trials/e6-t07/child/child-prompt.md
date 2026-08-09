# Child task e6-t07-child — clean-room implementation of a text-rendering specification

You are an isolated, terminal worker session governed by `child-contract.json`
(tools: Read and Write only; you may not create, delegate, or launch
anything). Your entire evidential world is the `inputs/` directory. Work only
inside your workspace using the Read and Write tools.

## Your task

`inputs/render.md` specifies a small placeholder-substitution language and a
function contract. Implement that specification — exactly, completely, and
using nothing but what `inputs/render.md` states — as a Python file.

## Deliverable

Write a file named **`render_clean.py`** in your workspace root. It must:

- be valid Python 3, importable as a module with no side effects on import;
- expose a top-level function **`render(p)`** matching the function contract
  given in `inputs/render.md`;
- implement every clause of the specification faithfully. Where the
  specification fixes a behavior, your code must produce exactly that
  behavior; do not add features, transformations, or normalizations the
  specification does not state.

Your implementation will be evaluated mechanically by calling `render(p)`,
so the file must run as-is with only the Python standard library.

## Node order (from `child-harness.json`)

1. **observe-inputs** — read every file in `inputs/`.
2. **produce-evidence** — author `render_clean.py`.
3. **self-check** — re-read `render_clean.py` against every clause of
   `inputs/render.md`; note the outcome (non-authoritative).
4. **return-result** — write `result.json`:

```json
{
  "deliverable": "render_clean.py",
  "summary": "<one-paragraph description of what you implemented>",
  "files_produced": ["render_clean.py", "result.json", "execution-ledger.jsonl"],
  "model_calls_spent": 0
}
```

## Ledger contract

Write `execution-ledger.jsonl` in your workspace root: one JSON object per
line, each with `event_id`, `label`, `actor`, `timestamp`, `artifact_refs`,
`metadata`. Emit exactly these node-execution events, in this order, each
with `metadata.completes_node` set to the node id and `artifact_refs`
listing the files that node authored:

1. `{"label": "observe",  "actor": "node:observe-inputs", ...}`
2. `{"label": "propose",  "actor": "node:produce-evidence", "artifact_refs": ["render_clean.py"], ...}`
3. `{"label": "verify",   "actor": "node:self-check", ...}`
4. `{"label": "return",   "actor": "node:return-result", "artifact_refs": ["result.json"], ...}`

Finish with a terminal event `{"label": "complete", "actor": "child", ...}`
(no `completes_node`). Optional extra non-authority events with actor
`child` are permitted.
