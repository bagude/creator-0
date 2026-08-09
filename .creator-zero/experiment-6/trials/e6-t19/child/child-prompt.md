# Task: implement the line-pricing rules

You are a terminal worker with tools **Read** and **Write** only. Your
working directory contains exactly two input files:

- `pricing.md` — a natural-language specification of a pricing function.
- `probes.json` — a JSON array of input objects.

These two files are the *only* source of truth available to you. No
reference implementation exists in your environment, and you must not
assume, reconstruct, or guess at any implementation other than what
`pricing.md` literally states. Implement the rules exactly as written in
`pricing.md` — no more, no less. Where `pricing.md` states a rule (for
example a rounding discipline), implement precisely that rule; do not
substitute a different convention because it is more common.

## What to produce

1. **`impl.py`** — a Python file that defines a top-level function
   `price(p)` taking one probe object `p` (a dict with keys `qty` (int),
   `unit_price` (str), `discount_pct` (int), `tax_pct` (int)) and returning
   the final price as a string, following `pricing.md` exactly. The function
   must be importable (`from impl import price`) and must not read any files
   or require any input beyond its argument. Use only the Python standard
   library.

2. **`result.json`** — a JSON object with exactly this shape:

   ```json
   {
     "implementation_file": "impl.py",
     "outputs": ["<price for probes[0]>", "<price for probes[1]>", "..."]
   }
   ```

   `outputs` must be a list of strings, one per element of `probes.json`, in
   the same order, each being `price(probe)` for that probe as produced by
   your `impl.py`.

3. **`execution-ledger.jsonl`** — one JSON object per line, one per node of
   your harness, in order. Each line:
   `{"event_id": "...", "label": "...", "actor": "node:<id>",
   "timestamp": "...", "artifact_refs": [...], "metadata":
   {"completes_node": "<id>"}}`. Use label `observe` for `observe-inputs`,
   `propose` for `produce-evidence`, `verify` for `self-check`, and `return`
   for `return-result`.

## Rules

- Derive `impl.py` solely from `pricing.md`. Do not encode any behavior that
  `pricing.md` does not state.
- Compute `outputs` by actually applying your `price` function to each probe.
- Do not attempt to launch processes, network, or any tool other than Read
  and Write. Produce the three files above and stop.
