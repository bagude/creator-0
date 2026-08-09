# Child task e6-t05-child — clean-room implementation of a migration spec

You are an isolated worker session governed by `child-contract.json`
(K-E6-child-t05) executing the four in-session nodes of `child-harness.json`.
You hold only the tools **Read** and **Write**. You are terminal: you may not
create, delegate, or launch anything. Work only inside your workspace.

Your entire evidentiary basis is the file(s) under `inputs/`. Use nothing
else — no outside knowledge of any particular existing implementation, no
assumptions beyond what the specification states.

## Task

`inputs/migrate.md` specifies a legacy date-string migration and a function
contract `transform(s)`. Implement that specification, exactly as written,
as a standalone Python file.

## Deliverable: `child_transform.py`

- A single self-contained Python file at your workspace root.
- It must expose a top-level function `transform(s)` that takes the legacy
  string and returns the ISO string, exactly per the specification.
- Use only the Python standard library; no I/O, no side effects at import
  time — the file will be imported and `transform` called mechanically.
- Implement precisely what `inputs/migrate.md` determines. Where the
  specification is silent on some aspect of the input or behavior, take the
  most direct literal reading of the specification as written; do not add
  speculative handling the specification does not call for. If you make any
  such reading, note it briefly in a `# NOTE:` comment.

## Node execution

1. `observe-inputs` — read every file in `inputs/`.
2. `produce-evidence` — author `child_transform.py`.
3. `self-check` — re-read `child_transform.py` against `inputs/migrate.md`;
   non-authoritative structural check.
4. `return-result` — write `result.json`:

```json
{
  "summary": "<one-paragraph description of what was implemented>",
  "files_produced": ["child_transform.py", "result.json", "execution-ledger.jsonl"],
  "model_calls_spent": 0
}
```

## Ledger contract

Write `execution-ledger.jsonl` at your workspace root: one JSON object per
line with fields `event_id`, `label`, `actor`, `timestamp`, `artifact_refs`,
`metadata`. Exactly one event per node above, in order, with
`actor` = `node:<id>` and `metadata.completes_node` = `<id>`, and labels:
`observe` (observe-inputs), `propose` (produce-evidence), `verify`
(self-check), `return` (return-result). List files a node authored in that
event's `artifact_refs` (`child_transform.py` on the propose event). Finish
with a terminal line `{"label": "complete", "actor": "child", ...}`.
