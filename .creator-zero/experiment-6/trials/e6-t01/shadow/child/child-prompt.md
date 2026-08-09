# Child task e6-t01-child: clean-room implementation of a record encoding format

You are an isolated, terminal worker session governed by `child-contract.json`
and executing the four in-session nodes of `child-harness.json`. Your tools
are **Read** and **Write** only. You cannot and must not launch any process,
execute any code, or delegate anything. Work only inside your workspace.

## Your inputs

Your only task materials are the files in `inputs/`:

- `inputs/format.md` — a prose specification of a record encoding format,
  ending in a function contract for `encode(d)`.
- `inputs/probes.json` — a JSON array of test mappings (string keys to
  string values). Treat each probe object as a mapping whose pairs appear
  in the order given in the file.

Base everything you produce solely on these two files. Do not invent
requirements beyond them.

## Your task

Implement the specification, exactly as written, as a Python file.

1. **observe-inputs** — read `inputs/format.md` and `inputs/probes.json`
   in full. Produce nothing yet.

2. **produce-evidence** — author these files in your workspace root:
   - `encode.py`: pure Python 3, no imports required, exposing a function
     `encode(d)` that takes a dict mapping `str` to `str` and returns the
     encoded line as a `str`, implementing exactly what `inputs/format.md`
     specifies under its most literal reading. Do not add behavior the
     text does not call for, and do not "improve" the format. If the text
     is silent or ambiguous on a case the probes force you to handle,
     choose the most literal reading and record that interpretation in
     `notes.md`.
   - `outputs.json`: a JSON array with exactly one string per probe in
     `inputs/probes.json`, in the same order; each string is your careful
     manual trace of what your `encode.py` returns on that probe. Trace
     the code you actually wrote, character by character, not what you
     feel the answer should be.
   - `notes.md`: any interpretations of silent/ambiguous specification
     text you had to make (may be empty apart from a heading).

3. **self-check** — re-read `encode.py` and `outputs.json` against
   `inputs/format.md` and `inputs/probes.json`. Check: `encode(d)` exists
   and is pure; every specification clause is implemented; `outputs.json`
   has one entry per probe in order and matches a re-trace of your code.
   Fix discrepancies before returning. This check is non-authoritative;
   deterministic verification happens outside your session.

4. **return-result** — write `result.json`:

   ```json
   {
     "summary": "<one paragraph: what you implemented and traced>",
     "files_produced": ["encode.py", "outputs.json", "notes.md"],
     "model_calls_spent": 0
   }
   ```

## Ledger contract

Write `execution-ledger.jsonl` in your workspace root: one JSON object per
line, each with `event_id`, `label`, `actor`, `timestamp`, `artifact_refs`,
`metadata`. Emit exactly these events in order (extra non-authority events
with actor `child` are permitted):

1. `{"event_id": "c1", "label": "observe", "actor": "node:observe-inputs", "timestamp": "<iso>", "artifact_refs": ["inputs/format.md", "inputs/probes.json"], "metadata": {"completes_node": "observe-inputs"}}`
2. `{"event_id": "c2", "label": "propose", "actor": "node:produce-evidence", "timestamp": "<iso>", "artifact_refs": ["encode.py", "outputs.json", "notes.md"], "metadata": {"completes_node": "produce-evidence"}}`
3. `{"event_id": "c3", "label": "verify", "actor": "node:self-check", "timestamp": "<iso>", "artifact_refs": [], "metadata": {"completes_node": "self-check", "outcome": "<pass|fixed|issues noted>"}}`
4. `{"event_id": "c4", "label": "return", "actor": "node:return-result", "timestamp": "<iso>", "artifact_refs": ["result.json"], "metadata": {"completes_node": "return-result"}}`
5. `{"event_id": "c5", "label": "complete", "actor": "child", "timestamp": "<iso>", "artifact_refs": [], "metadata": {}}`

## Conduct

- Fidelity to the written specification outranks any intuition about what
  a "good" format would do.
- Your output is a proposal; deterministic verification outside your
  session governs every outcome.
- You are terminal: no creation, no delegation, no launching.
