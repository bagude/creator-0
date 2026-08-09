# Task for a fresh, isolated session

You are a terminal worker session. You know nothing beyond this prompt and the
two input files named below. You have exactly the tools **Read** and **Write**.
You may not create, delegate to, or launch any other session or process.

## Your inputs

Your workspace contains exactly two files:

- `format.md` — a written specification of a wire-format encoder.
- `probes.json` — an object `{"probes": [ ... ]}` whose `probes` array holds
  flat maps (string keys to string values) that such an encoder would be asked
  to encode.

There is **no reference implementation** anywhere in your workspace. Do not
assume one exists, and do not try to guess or reconstruct one. Your value comes
entirely from implementing the specification independently, from its text alone.

## What you must produce

1. **`clean_impl.py`** — a Python file exposing a top-level function

   ```python
   def encode(d: dict) -> str:
       ...
   ```

   It must implement **exactly and only** what `format.md` states, so that the
   function can be imported and run mechanically over the probe inputs. Import
   nothing beyond the Python standard library. Do not read `probes.json` at
   runtime or special-case any particular probe — write a general encoder.

2. **`child-result.json`** — a JSON object of this shape:

   ```json
   {
     "encoder_file": "clean_impl.py",
     "undetermined_behaviors": [
       "<a behavior that the probe inputs exercise but that format.md does not fully pin down>"
     ],
     "notes": "<short free-text notes on how you read the spec>"
   }
   ```

   Populate `undetermined_behaviors` with a plain-language description of every
   behavior that (a) at least one probe input actually exercises and (b) the
   text of `format.md` does **not** uniquely determine — i.e. a point where a
   different reader implementing the same spec could justifiably produce a
   different output. If you find none, use an empty list `[]`.

## How to work

- Read `format.md` and `probes.json` first (node `observe-inputs`).
- Implement `encode` strictly from `format.md`. Where the spec is silent or
  ambiguous about something a probe exercises, pick **one** good-faith reading,
  implement it, and record that gap in `undetermined_behaviors`. Do **not**
  invent extra rules to make the output "look right" — implement the spec as
  written and report its gaps honestly. Your independence is the whole point:
  do not try to second-guess what some other implementation might do.
- Re-check `clean_impl.py` against `format.md`: every rule you implemented must
  trace to a sentence in the spec; flag anything that does not (node
  `self-check`).
- Write `child-result.json` and return (node `return-result`).

## What you must NOT assume

- Do not assume any ordering, escaping, defaulting, or normalization rule that
  `format.md` does not state. If the spec does not say it, it is undetermined —
  make a good-faith choice and list it.
- Do not assume the existence of hidden test oracles, reference outputs, or a
  "correct" answer beyond faithful implementation of the written spec.

## Ledger you must maintain

Maintain `child-ledger.jsonl` in your workspace root: one JSON object per line,
each with fields `event_id`, `label`, `actor`, `timestamp`, `artifact_refs`,
`metadata`. Emit, in order:

1. `{"label": "observe", "actor": "node:observe-inputs", "metadata": {"completes_node": "observe-inputs"}}`
2. `{"label": "propose", "actor": "node:produce-evidence", "artifact_refs": ["clean_impl.py"], "metadata": {"completes_node": "produce-evidence"}}`
3. `{"label": "verify", "actor": "node:self-check", "metadata": {"completes_node": "self-check"}}`
4. `{"label": "return", "actor": "node:return-result", "artifact_refs": ["child-result.json", "clean_impl.py"], "metadata": {"completes_node": "return-result"}}`
5. `{"label": "complete", "actor": "child", "metadata": {"event_kind": "child_complete"}}`

Add a `timestamp` and a unique `event_id` to each line. The final `complete`
event terminates your session. Do not emit events for nodes you did not run.
