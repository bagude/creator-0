# Child Worker Task — e6-t09-child

You are an isolated, terminal worker session governed by `child-contract.json`
and executing the four in-session nodes of `child-harness.json`. Your only
tools are **Read** and **Write**. Work only inside your workspace. You may not
create, delegate, or launch anything.

Your only task input is the file in your `inputs/` directory:

- `inputs/graph.json` — an undirected graph given as a JSON object with a
  `"vertices"` list and an `"edges"` list of two-element vertex pairs.

Derive everything from this file alone.

## Task

A **vertex cover** of the graph is a set of vertices such that every edge in
the `edges` list has at least one endpoint in the set.

1. Determine the minimum vertex cover size `k`: exhibit a cover of size `k`
   and justify that no cover of size `k-1` exists (for example by exhaustive
   search over all smaller subsets, or by a rigorous lower-bound argument).
2. Enumerate **ALL** vertex covers of size exactly `k`, using an exhaustive
   procedure over the search space (for example, checking every vertex subset
   of size `k` against every edge). Completeness is the deliverable: a missed
   cover is a wrong answer.

## Deliverable

Write `result.json` in your workspace root, with exactly this shape:

```json
{
  "items": [["v...", "..."], ...],
  "k": <integer>,
  "method": "<how the minimum size was established and how the enumeration was produced>",
  "complete": <boolean>,
  "files_produced": ["result.json", "execution-ledger.jsonl"],
  "model_calls_spent": 0
}
```

- Each cover in `items` must be its lexicographically sorted vertex list.
- `items` itself must be sorted lexicographically.
- `complete` is `true` only if your enumeration provably covered the whole
  search space.

## Node execution order

Execute the harness nodes in order:

1. `observe-inputs` — read every file in `inputs/`; produce nothing yet.
2. `produce-evidence` — perform the derivation and enumeration; author
   `result.json` under a propose ledger event at authoring time.
3. `self-check` — re-read `result.json` against the requirements above
   (shape, sortedness, every listed item covers every edge, minimality
   argument present); record the outcome. Non-authoritative.
4. `return-result` — finalize `result.json` and the ledger.

## Ledger contract

Write `execution-ledger.jsonl` in your workspace root: one JSON object per
line, each with `event_id`, `label`, `actor`, `timestamp`, `artifact_refs`,
`metadata`. Emit exactly one event per node, in dependency order:

| node             | label     | actor                  | metadata                                |
|------------------|-----------|------------------------|-----------------------------------------|
| observe-inputs   | `observe` | `node:observe-inputs`  | `{"completes_node": "observe-inputs"}`  |
| produce-evidence | `propose` | `node:produce-evidence`| `{"completes_node": "produce-evidence"}`|
| self-check       | `verify`  | `node:self-check`      | `{"completes_node": "self-check"}`      |
| return-result    | `return`  | `node:return-result`   | `{"completes_node": "return-result"}`   |

List the files a node authored in that event's `artifact_refs`. After the
four node events, emit one terminal event `{"label": "complete", "actor":
"child"}`. Optional extra non-authority events with actor `child` are
permitted.

Your session ends after the terminal `complete` event.
