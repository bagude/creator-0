# Child worker instructions (e6-e7-p02-child)

You are a terminal worker in a fresh, governed session under
`child-contract.json`. Your tools are **Read** and **Write** only. You may
not create, delegate, or launch anything. Everything you need is inside
your workspace; nothing outside it is readable or writable.

## Your inputs

The directory `inputs/` contains exactly two files:

- `inputs/joinspec.md` — a short specification of a list-joining format.
- `inputs/probes.json` — a JSON array of probe inputs; each entry is a
  list of strings.

Read both completely before producing anything.

## Your task

1. **Implement the specification.** Author `join_items.py` in your
   workspace root: a python file exposing a function `join_items(items)`
   that takes a list of strings and returns the single-line string the
   format in `inputs/joinspec.md` prescribes. Implement exactly what the
   spec says — nothing more, nothing less. Keep the file minimal and
   self-contained (no imports beyond the python standard behavior of the
   language itself, no I/O, no side effects).

2. **Record its outputs on the probes.** For each list in
   `inputs/probes.json`, in order, mechanically evaluate your
   `join_items` on that list (careful hand-evaluation; you cannot execute
   code) and record the resulting string. Write `outputs.json` in your
   workspace root with exactly this shape:

   ```json
   {"outputs": ["<output for probe 0>", "<output for probe 1>", "..."]}
   ```

   One string per probe, same order as `inputs/probes.json`. If a probe's
   output is the empty string, record `""`.

3. **Self-check.** Re-read `join_items.py` and `outputs.json` against
   `inputs/joinspec.md` and `inputs/probes.json`: the function signature
   is `join_items(items)`, every probe has exactly one recorded output,
   and each recorded output is what your implementation returns for that
   probe. This check is non-authoritative; deterministic verification
   happens after your session.

4. **Return.** Write `result.json` in your workspace root:

   ```json
   {
     "summary": "<one sentence: what you implemented and how many probe outputs you recorded>",
     "files_produced": ["join_items.py", "outputs.json"],
     "model_calls_spent": 0
   }
   ```

## Ledger contract

Maintain `execution-ledger.jsonl` in your workspace root: one JSON object
per line, each with `event_id`, `label`, `actor`, `timestamp`,
`artifact_refs`, `metadata`. Emit exactly these node events, in order,
each with `metadata.completes_node` set to the node id:

1. `{"label": "observe", "actor": "node:observe-inputs", ...}` — after
   reading the inputs; `artifact_refs: []`.
2. `{"label": "propose", "actor": "node:produce-evidence", ...}` — at
   authoring time of the deliverable;
   `artifact_refs: ["join_items.py", "outputs.json"]`.
3. `{"label": "verify", "actor": "node:self-check", ...}` — with
   `metadata.outcome` set to `"pass"` or `"fail"`; `artifact_refs: []`.
4. `{"label": "return", "actor": "node:return-result", ...}` —
   `artifact_refs: ["result.json"]`.

Finish with a terminal event: `{"label": "complete", "actor": "child",
"artifact_refs": [], "metadata": {}}`.

## Conduct

- Derive everything solely from the two files in `inputs/`. Do not invent
  requirements the spec does not state; where the spec is silent, follow
  its plain reading.
- Your deliverable is the implementation and its recorded outputs, not an
  essay. Keep prose to the `summary` field.
