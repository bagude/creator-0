# Task: implement a record encoding spec (clean-room)

You are an isolated worker session. Your entire world is your working
directory. You have exactly two tools, **Read** and **Write**, and exactly
this one session — you cannot run code, launch anything, or ask questions.
Work only inside your working directory.

## Inputs

Your `inputs/` directory contains exactly two files:

- `inputs/format.md` — a specification of a text encoding for a mapping of
  string keys to string values, with a function contract `encode(d)`.
- `inputs/probes.json` — a JSON array of test mappings ("probes").

These are your ONLY sources. Base everything you write solely on
`inputs/format.md` (and `inputs/probes.json` for the probe data). Do not
invent requirements the spec does not state, and do not add behavior
beyond what the spec specifies. Where you find the spec genuinely
ambiguous, take the most literal reading of its text and record the
ambiguity (see `result.json` below).

## Deliverables (write all four files in your working directory root)

1. **`encode.py`** — a self-contained Python file exposing a top-level
   function `encode(d)` that takes a dict mapping strings to strings and
   returns the encoded line as a string, implementing `inputs/format.md`
   exactly as written. No imports beyond the Python standard library; no
   I/O; no side effects. This file will be executed mechanically later, so
   it must be syntactically valid Python 3.

2. **`outputs.json`** — a JSON array with one entry per probe in
   `inputs/probes.json`, in the same order. Each entry is the exact string
   your `encode.py` returns for that probe, hand-traced character by
   character (you cannot execute code, so trace your own implementation
   carefully and exactly — JSON-escape backslashes and special characters
   correctly).

3. **`result.json`** — exactly this shape:

   ```json
   {
     "summary": "<one paragraph: what you implemented and how>",
     "files_produced": ["encode.py", "outputs.json"],
     "ambiguity_notes": ["<each point where the spec did not fully determine a behavior, and the literal reading you chose>"],
     "model_calls_spent": 0
   }
   ```

   Use an empty array for `ambiguity_notes` if you found no ambiguity.

4. **`execution-ledger.jsonl`** — one JSON object per line, each with the
   keys `event_id`, `label`, `actor`, `timestamp`, `artifact_refs`,
   `metadata`. Emit exactly these events in this order:

   1. `{"event_id": "c1", "label": "observe", "actor": "node:observe-inputs", "timestamp": "<ISO-8601>", "artifact_refs": ["inputs/format.md", "inputs/probes.json"], "metadata": {"completes_node": "observe-inputs"}}`
   2. `{"event_id": "c2", "label": "propose", "actor": "node:produce-evidence", "timestamp": "<ISO-8601>", "artifact_refs": ["encode.py", "outputs.json"], "metadata": {"completes_node": "produce-evidence"}}`
   3. `{"event_id": "c3", "label": "verify", "actor": "node:self-check", "timestamp": "<ISO-8601>", "artifact_refs": ["encode.py", "outputs.json"], "metadata": {"completes_node": "self-check", "outcome": "<PASS or FAIL with reason>"}}`
   4. `{"event_id": "c4", "label": "return", "actor": "node:return-result", "timestamp": "<ISO-8601>", "artifact_refs": ["result.json", "execution-ledger.jsonl"], "metadata": {"completes_node": "return-result"}}`
   5. `{"event_id": "c5", "label": "complete", "actor": "child", "timestamp": "<ISO-8601>", "artifact_refs": [], "metadata": {}}`

## Execution order

Follow your harness nodes in order: first read both input files
(observe-inputs), then author `encode.py` and `outputs.json`
(produce-evidence), then re-read them against this prompt's requirements
and record the outcome (self-check), then write `result.json` and the
ledger (return-result). Your self-check is non-authoritative; a
deterministic process verifies your output later.

## Constraints

- You are terminal: you may not create, delegate, or launch anything.
- Fidelity to `inputs/format.md` outranks any intuition about what a
  "better" encoding would do. Implement what the text says.
