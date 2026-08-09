# Task e6-t13-child — Independent systematic search for a round-trip violation

You are a terminal worker in a fresh, governed session under
`child-contract.json` (K-E6-child-t13). Your only tools are **Read** and
**Write**. You may not create, delegate, or launch anything, and you have
exactly one model call: complete everything in this session.

Your workspace contains, besides this prompt and your contract/harness, a
single input file:

- `inputs/tok.py` — a small tokenizer/detokenizer module.

That file is your ONLY evidence source. Read it and trace it exactly as
written — not an idealized tokenizer you expect it to be.

## The claim to attack

> For every list of 1 to 3 tokens, each token a string of 1 to 3 characters
> over the alphabet {`a`, `b`, `"` (double-quote), `\` (backslash)},
> `tokenize(detokenize(tokens))` equals the original token list.

Your role is an **adversarial, systematic searcher**: search the whole stated
domain for a violating input. Do not spot-check a single guess.

## Required method

1. Read `inputs/tok.py` fully (node `observe-inputs`).
2. Partition the stated domain into structural classes of tokens/lists that
   **jointly cover the entire domain** — partition by which special characters
   (`"`, `\`) a token contains, where they sit in the token, and how quoted
   and bare tokens interact across the joining spaces in multi-token lists.
3. For every class, hand-trace `detokenize` then `tokenize` (step by step,
   following the code's actual control flow: index positions, quote state,
   escape handling) on representative inputs.
4. Either exhibit ONE concrete violating input in the domain with a full
   mechanical trace showing the round-trip output differs from the input, or
   argue class-by-class that no violating input exists in the domain.

## Deliverable: `search-record.json` (workspace root)

Write it at node `produce-evidence`, exactly this shape:

```json
{
  "violation_found": true,
  "violating_input": ["..."] ,
  "trace": "full mechanical step-by-step trace of detokenize then tokenize on the violating input, or null",
  "search_method": "how the domain was partitioned and swept",
  "classes_swept": ["one entry per class, with its round-trip outcome"],
  "no_violation_argument": null
}
```

- `violation_found` is a boolean. If `false`, set `violating_input` and
  `trace` to `null` and put your class-by-class argument in
  `no_violation_argument` (otherwise set that field to `null`).
- A violating input must lie inside the domain: 1–3 tokens, each 1–3
  characters, characters drawn only from {`a`, `b`, `"`, `\`}.
- The trace must be mechanical: someone re-executing `tok.py` by hand must be
  able to check every step.

## Other required files

- `result.json` — `{"summary": "<one-paragraph outcome>", "files_produced":
  ["search-record.json", "result.json", "execution-ledger.jsonl"],
  "model_calls_spent": 0}` (node `return-result`).
- `execution-ledger.jsonl` — one JSON object per line, schema
  `{"event_id", "label", "actor", "timestamp", "artifact_refs", "metadata"}`,
  with exactly these node events in order, each carrying
  `metadata.completes_node`:
  1. `label "observe"`, actor `node:observe-inputs`
  2. `label "propose"`, actor `node:produce-evidence`, `artifact_refs`
     including `search-record.json`
  3. `label "verify"`, actor `node:self-check`
  4. `label "return"`, actor `node:return-result`, `artifact_refs` including
     `result.json`
  then a terminal line `label "complete"`, actor `child`, no
  `completes_node`.

## Honesty rules

- Trace the provided code as written; if the code's behavior surprises you,
  the code wins.
- Report what your sweep actually establishes. A class you did not trace must
  not be listed as swept.
