# Task: implement a specification (isolated worker e6-t07-child)

You are a terminal worker in a fresh, governed session under
`child-contract.json` (K-E6-child-t07). Your tools are **Read** and **Write**
only. You may not create, delegate, or launch anything, and you must work only
inside this workspace. Your harness is `child-harness.json`; execute its four
nodes in order.

## Your workspace

- `inputs/render.md` — the complete specification of a placeholder
  substitution language. This is your **only** source material.
- `child-contract.json`, `child-harness.json`, this prompt.

## The task

Read `inputs/render.md` carefully, then author **`render_impl.py`** at the
workspace root: a single, self-contained Python file using only the standard
library, exposing exactly this function:

```python
def render(p):
    ...
```

where `p` is a dict `{"template": <str>, "context": <dict of str -> str>}`
and the return value is the rendered string. Implement **exactly** what
`inputs/render.md` specifies — every clause of the spec, and no behavior
beyond it. Do not add features, normalization, error handling, or
transformations the spec does not call for. Do not print, read files, or run
anything at import time; the file must be importable with no side effects.

## Deliverables

1. `render_impl.py` — the implementation described above.
2. `result.json` — exactly:
   `{"summary": "<one sentence on what you implemented>", "files_produced": ["render_impl.py"], "model_calls_spent": 0}`
3. `execution-ledger.jsonl` — one JSON object per line, each
   `{"event_id", "label", "actor", "timestamp", "artifact_refs", "metadata"}`
   with ISO-8601 UTC timestamps, in this order:
   - `label: "observe"`, `actor: "node:observe-inputs"`,
     `metadata: {"completes_node": "observe-inputs"}` — after reading `inputs/`;
   - `label: "propose"`, `actor: "node:produce-evidence"`,
     `artifact_refs: ["render_impl.py"]`,
     `metadata: {"completes_node": "produce-evidence"}` — at the time you
     author `render_impl.py`;
   - `label: "verify"`, `actor: "node:self-check"`,
     `metadata: {"completes_node": "self-check"}` — after re-reading your
     implementation against the spec (non-authoritative self-check);
   - `label: "return"`, `actor: "node:return-result"`,
     `artifact_refs: ["result.json"]`,
     `metadata: {"completes_node": "return-result"}`;
   - a terminal line `label: "complete"`, `actor: "child"`.

## Conduct

- Derive everything from `inputs/render.md` alone. Where the spec is explicit,
  follow it literally; treat its definitions (e.g. what exactly counts as a
  placeholder) as exhaustive.
- Your self-check is non-authoritative; deterministic verification outside
  your session governs the outcome.
- End your session after the ledger's terminal `complete` event.
