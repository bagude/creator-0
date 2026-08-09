# Task: implement build_index from a specification

You are a fresh, isolated worker session. You know nothing beyond this prompt
and the two files handed to you. Your only tools are **Read** and **Write**,
confined to your working directory.

## What you are given

- `rules.md` — a written specification of a function `build_index(text: str) -> str`.
- `document.txt` — a text document.

These are the only inputs. Do not assume the existence of any other file,
reference, prior solution, or "expected" answer. There is no hidden oracle to
match; your job is to realize the specification faithfully on its own terms.

## What you must produce

1. `clean_impl.py` — a Python file defining a function with exactly the
   signature `build_index(text: str) -> str` that implements **exactly and
   only** what `rules.md` states. Implement every rule; add no behavior that
   `rules.md` does not require.

2. Evaluate your `build_index` on the **entire contents of `document.txt`**
   (the whole file passed as the single `text` argument) and record the exact
   string it returns.

3. `child-result.json` — your deliverable, of the shape:

   ```json
   {
     "implementation_file": "clean_impl.py",
     "output_on_document": "<the exact string build_index returns for document.txt>",
     "silent_choices": [
       {"detail": "<a point rules.md did not fully specify>",
        "choice_made": "<what you decided>",
        "reason": "<why>"}
     ]
   }
   ```

   If `rules.md` fully determined every detail you needed, use an empty
   `silent_choices` array. If, while implementing, you found any point where
   `rules.md` was silent or ambiguous about a detail you nonetheless had to fix
   in order to produce output, pick a reasonable option, implement it, and
   record it in `silent_choices`. Report honestly — do not invent gaps, and do
   not paper over real ones.

## Constraints

- Work only from `rules.md`. Where the specification is precise, follow it
  precisely; where it is silent, make and record a reasonable choice as above.
- You cannot run code (Read/Write only). Evaluate `build_index` on
  `document.txt` by careful manual tracing, and make sure `clean_impl.py` would
  reproduce exactly that string if executed. Keep the code simple and literal so
  it is trivially executable by a third party.
- Do not attempt to create, delegate to, or launch any other session; you are a
  terminal worker.

## Ledger

Maintain `child-execution-ledger.jsonl` in your working directory: one JSON
object per line, each with `event_id`, `label`, `actor`, `timestamp`,
`artifact_refs`, and `metadata` (node executions carry
`metadata.completes_node`). Record, in causal order:

1. `observe` — completing `observe-inputs` (after reading the two files).
2. `propose` — completing `produce-evidence`, `artifact_refs: ["clean_impl.py"]`.
3. `verify` — completing `self-check` (you re-read `clean_impl.py` against
   `rules.md` and confirm the signature and that each rule is honored).
4. `return` — completing `return-result`, `artifact_refs: ["child-result.json"]`.
5. `complete` — a final terminating event (`metadata.event_kind = "child_complete"`).

Your session ends after the `complete` event.
