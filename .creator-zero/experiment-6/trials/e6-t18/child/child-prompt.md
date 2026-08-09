# Isolated Worker Task — Route Enumeration

You are an isolated, terminal worker session governed by `child-contract.json`
and `child-harness.json`. You have exactly the tools **Read** and **Write**,
exactly one model call, and you may not create, delegate, or launch anything.
Your only inputs are the files listed in your input manifest; do not assume,
seek, or reference any other material.

## Input

- `package/artifacts/network.json` — a directed network:
  - `nodes`: node names.
  - `links`: one-way links, each `{"from", "to", "cost"}`. A link may be
    traversed only from `from` to `to`.

## Task

Enumerate **ALL** routes from node `S` to node `T` whose total cost (sum of
link costs along the route) is the minimum possible. Rules:

- Links are one-way; a route may only follow links in their stated direction.
- A route never repeats a node.
- Write each route as its node names joined by `-`, for example `S-A-C-T`.
- Completeness is the deliverable: a missed qualifying route is a wrong
  answer. Enumerate the full route space systematically and state the method
  you used.

## Deliverable

Write `enumeration-b.json` with exactly this shape:

```json
{
  "items": ["<route string>", "..."],
  "method": "<how you produced the enumeration, precisely>",
  "complete": true
}
```

- `items`: every minimum-total-cost route, sorted lexicographically, no
  duplicates, no non-minimum routes.
- `method`: the systematic procedure you actually used (e.g. exhaustive
  search over simple paths), stated so a checker can re-run it.
- `complete`: `true` only if your method covered the entire route space;
  otherwise `false`.

## Execution ledger

Execute the four nodes of `child-harness.json` in dependency order:
`observe-inputs`, `produce-evidence`, `self-check`, `return-result`.
Write `child-ledger.jsonl` — one JSON object per line:

```json
{"event_id": "c-evt-1", "label": "observe", "actor": "node:observe-inputs", "timestamp": "<ISO-8601>", "artifact_refs": ["package/artifacts/network.json"], "metadata": {"completes_node": "observe-inputs"}}
```

One event per node, in order, with these fixed labels:
`observe-inputs` → `observe`; `produce-evidence` → `propose`;
`self-check` → `verify`; `return-result` → `return`.
List any file a node authored in that event's `artifact_refs`.

At `self-check`, re-verify against `network.json` that every item in
`enumeration-b.json` is a valid one-way, non-repeating route attaining the
minimum cost, and that no qualifying route is missing. Your session ends
after `return-result`.
