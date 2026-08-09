# Task: enumerate all minimum vertex covers

You are an isolated, terminal worker session. Your tools are **Read** and
**Write** only. You may read exactly the files listed in your input manifest
and nothing else; do not attempt to launch any process, agent, or session.

## Your input

- `graph.json` — an undirected graph as `{"vertices": [...], "edges": [[a,b], ...]}`.

This is the only material you have. Work solely from it.

## What to produce

A **vertex cover** is a set of vertices such that every edge has at least one
endpoint in the set. A **minimum** vertex cover is one of the smallest possible
size. Your job is to enumerate **ALL** minimum-size vertex covers of the graph.
Completeness is the whole point: missing even one minimum cover, or including a
non-cover or a non-minimum set, is a wrong answer.

Method requirements:

1. Determine the minimum cover size `k`. Establish it rigorously: exhibit a
   cover of size `k`, and give a demonstration that no cover of size `k-1`
   exists (for example, an exhaustive check over all vertex subsets of the
   relevant sizes, or a matching / counting lower-bound argument). State the
   method you used.
2. Enumerate **every** vertex cover of size exactly `k`. An exhaustive procedure
   over the search space (e.g. testing every vertex subset of size `k`) is the
   safest way to guarantee completeness.
3. Report each cover as its **sorted** vertex list, and sort the overall list of
   covers.

## Deliverable

Write a single file **`enumeration.json`** with exactly this shape:

```json
{
  "k": <integer minimum cover size>,
  "covers": [["v1", "v2", ...], ...],
  "method": "<how you determined k and enumerated the covers>",
  "complete": true
}
```

- `covers`: every minimum cover, each a sorted vertex list, the list of lists
  sorted lexicographically. Set `complete` to `true` only if your procedure was
  exhaustive over the whole space.

## Ledger

Also write `execution-ledger.jsonl`, one JSON object per line, one per harness
node you execute, in dependency order:
`{"event_id", "label", "actor", "timestamp", "artifact_refs", "metadata"}`.
Use `actor` = `node:<id>` and `metadata.completes_node` = `<id>`. Event labels
by node primitive: observe → `observe`, hypothesize → `propose`,
verify → `verify`, return → `return`. List files a node authored in its
`artifact_refs`.
