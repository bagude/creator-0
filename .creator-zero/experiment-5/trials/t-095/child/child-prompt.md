# Clean-room reproduction task

You are a fresh, isolated worker session. You know nothing about this task
beyond what is written here and in the two input files you have been given.
Your tools are **Read** and **Write** only.

## Your inputs

You have exactly two files:

- `build-notes.md` — notes describing how an output file is produced.
- `records.csv` — the source data referenced by those notes.

You do **not** have, and must **not** assume anything about, the produced
output file (its name may be referenced in the notes). You have never seen it.
Its contents, ordering, formatting, and every other property are unknown to you.
Do not try to read it, reconstruct it from memory, or guess what it "should"
look like beyond what the notes and the CSV strictly entail.

## What to do

1. **observe-inputs** — Read `build-notes.md` and `records.csv`.

2. **produce-evidence** — Write a self-contained Python file
   `produce_summary.py` that exposes a function:

   ```python
   def produce_summary(csv_text: str) -> str:
       ...
   ```

   It must take the raw text of a CSV (same schema as `records.csv`) and return
   the produced output as a single string, implementing **only** the
   transformation the notes describe. Rules:
   - Follow the notes literally. Do **not** invent any behavior the notes do not
     state — this includes any choice of output line ordering, any change of
     letter case, any particular decimal/number formatting, any field separator
     spacing, and whether or not a trailing newline is emitted.
   - Wherever the notes are **silent** on something that affects the exact bytes
     of the output, take the most literal, minimal reading of the notes, and
     **record** that the notes forced you into a free choice there.
   - The function must be deterministic and depend only on its `csv_text`
     argument — no file reads, no randomness, no clock, no network.

   Then compute `produce_summary(<the exact text of records.csv>)` and capture
   the returned string exactly.

   Then, reasoning **only from the notes and the CSV** (never from any assumed
   target output), list every aspect of the output that the notes leave as a
   free choice affecting the exact output bytes. Consider at least: line
   ordering, region/label case, numeric and decimal formatting, trailing
   newline, line terminator (LF vs CRLF), and separator spacing.

   Write your deliverable `reproduction.json` with this exact shape:

   ```json
   {
     "produce_summary_file": "produce_summary.py",
     "reproduced_output": "<the exact string produce_summary returned on records.csv>",
     "underdetermined_aspects": ["<one description per free choice the notes leave open>"],
     "notes_fully_determine_output": <true if and only if underdetermined_aspects is empty>
   }
   ```

3. **self-check** — Re-read `produce_summary.py` and `reproduction.json`.
   Confirm the file defines `produce_summary(csv_text: str) -> str`, is
   deterministic, reads no external file, and that `reproduced_output` is exactly
   what the function returns on `records.csv`. Confirm each listed aspect is
   justified from the notes alone.

4. **return-result** — `reproduction.json` (together with `produce_summary.py`)
   is your final deliverable. Do not attempt any comparison against a target you
   do not have.

## What you must NOT assume

- Do not assume any particular ordering, casing, rounding, or trailing-newline
  convention "because it is standard." If the notes do not state it, it is a
  free choice you must record, and you must pick the most literal reading.
- Do not assume the output file's contents. You have never seen them.
- Do not add columns, filters, aggregations, or formatting the notes do not
  describe.

## Ledger

Maintain `child-ledger.jsonl` in your workspace root: one JSON object per line,
each with `event_id`, `label`, `actor`, `timestamp`, `artifact_refs`, and
`metadata`. Emit one event per node as you complete it, in order:

1. `{"label":"observe","actor":"node:observe-inputs","metadata":{"completes_node":"observe-inputs"}}`
2. `{"label":"propose","actor":"node:produce-evidence","artifact_refs":["produce_summary.py","reproduction.json"],"metadata":{"completes_node":"produce-evidence"}}`
3. `{"label":"verify","actor":"node:self-check","metadata":{"completes_node":"self-check"}}`
4. `{"label":"return","actor":"node:return-result","artifact_refs":["reproduction.json"],"metadata":{"completes_node":"return-result"}}`

Then emit a final terminal event:

5. `{"label":"complete","actor":"child","artifact_refs":["reproduction.json"],"metadata":{"event_kind":"child_complete"}}`

Fill in a unique `event_id` and an ISO-8601 `timestamp` for each line. The
ledger must end with the `complete` event.
