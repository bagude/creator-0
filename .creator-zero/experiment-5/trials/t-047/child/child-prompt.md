# Clean-room implementation task

You are a fresh, isolated worker session. You know nothing beyond this prompt
and the two input files you are given. Follow these instructions exactly and
produce the deliverable. You have only the **Read** and **Write** tools. You
cannot and must not launch, delegate to, or create any other process, session,
or agent.

## Your inputs

You receive exactly two files:

- `spec.md` — a natural-language specification of a function `next_order`.
- `probes.json` — an object `{"probes": [ ... ]}` where each probe is a list
  of job records (the `jobs` argument to `next_order`).

`spec.md` is the **complete and only** description of the required behavior.
There is **no reference implementation** available to you, and you must **not**
assume one exists, guess what one might do, or optimize your output to match any
hidden implementation. Your entire value is that you work only from the spec.

## What to produce

1. **`next_order.py`** — a Python file exposing exactly:

   ```python
   def next_order(jobs: list[dict]) -> list[str]:
       ...
   ```

   Implement precisely what `spec.md` states, and nothing more. Use only the
   fields `spec.md` actually names. Do not add behavior the spec does not call
   for. The function must be deterministic and importable (no side effects at
   import time, no reading of external files).

2. **Wherever `spec.md` does not pin down a unique answer** — i.e. any point
   where two implementations that both fully honor the spec could legitimately
   return different orderings — make **one concrete, deterministic choice** in
   your code, and **record that point** as an undetermined behavior. Describe it
   in plain terms (what the spec leaves open), without claiming what the "right"
   answer is — there may be none. If you find no such point, record an explicit
   statement that the spec determines a unique output on every probe.

3. Run your `next_order` (mentally or by tracing your own code — you have no
   execution tool, so compute carefully and deterministically) on **every**
   probe in `probes.json`, in order, and record the returned id-list for each.

## Deliverable file: `child-result.json`

Write a JSON object with exactly this shape:

```json
{
  "implementation_file": "next_order.py",
  "per_probe_outputs": [
    {"probe_index": 0, "output": ["...id..."]}
  ],
  "undetermined_behaviors": [
    "short description of a behavior spec.md does not determine, or the explicit statement that none exists"
  ],
  "notes": "optional short free text"
}
```

`per_probe_outputs` must have one entry per probe, `probe_index` matching the
zero-based position in `probes.json`, and `output` equal to what your
`next_order.py` returns for that probe.

## Ledger

Maintain `child-ledger.jsonl` in your workspace root: one JSON object per line
with `event_id`, `label`, `actor`, `timestamp`, `artifact_refs`, `metadata`.
Emit, in order:

1. `observe` (actor `node:observe-inputs`, `metadata.completes_node="observe-inputs"`) after reading the inputs.
2. `propose` (actor `node:produce-evidence`, `metadata.completes_node="produce-evidence"`, `artifact_refs=["next_order.py","child-result.json"]`) after authoring the implementation and outputs.
3. `verify` (actor `node:self-check`, `metadata.completes_node="self-check"`) after your structural self-check.
4. `return` (actor `node:return-result`, `metadata.completes_node="return-result"`, `artifact_refs=["child-result.json"]`).
5. `complete` (actor `child`, `metadata.event_kind="child_complete"`) as the final line.

## What you must NOT do

- Do not assume, infer, or reverse-engineer any reference implementation.
- Do not shape your tie-handling or ordering choices to match anything other
  than what `spec.md` literally requires; where the spec is silent, choose
  freely and record the silence.
- Do not read or request any file other than the two inputs.
- Do not launch, spawn, or delegate to anything.
