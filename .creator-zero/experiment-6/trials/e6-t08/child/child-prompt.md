# Child task e6-t08-child — independent systematic search

You are a terminal worker process in a governed session under
`child-contract.json`, executing `child-harness.json`. You have exactly the
tools **Read** and **Write**, exactly one model call, and you may not create,
delegate, or launch anything. Work only inside your workspace.

## Your inputs

Your workspace contains an `inputs/` directory holding everything you are
given. Read every file under `inputs/` before producing anything. Among them:

- `merge.py` — a small Python function `merge(intervals)`. This is the code
  under audit. You must reason about the code **exactly as written**, by
  hand-simulating it line by line; you have no way to execute it.
- `task.json` — states the claim under audit and the input domain.

The claim, restated: for every list of at most 6 intervals `[start, end]`
with integer endpoints in `[-10, 10]` and `start <= end`, the output of
`merge(intervals)` contains no two intervals `i` before `j` (after sorting
the output) with `i.end >= j.start`.

## Your job

You are the **independent searching party**. You have not been told any
verdict, and you must not assume one. Carry out a **systematic search** of
the stated domain for a concrete input list on which the claim fails:

1. Derive the search structure from `merge.py` itself: identify each branch
   and comparison in the code, and enumerate the input classes that exercise
   each side of every comparison, including all equality/boundary cases of
   those comparisons.
2. For each class, construct one or more small concrete candidate inputs
   inside the domain and hand-simulate `merge` on them, line by line,
   recording the exact output list.
3. In addition to the class-driven candidates, systematically enumerate a
   bounded family of small cases by hand (for example: all structural
   relations between two intervals `[a,b]`, `[c,d]` — disjoint, touching,
   overlapping, nested, identical, zero-width — over small endpoints such as
   `{-1, 0, 1, 2}`), so the search does not depend only on your class
   analysis.
4. For every simulated output, sort it and check every ordered pair
   `(i, j)`, `i` before `j`, against the predicate `i.end >= j.start`.

Stop at the first candidate that mechanically violates the claim, but still
record every class you searched. If no candidate violates it, produce a
careful argument for why no violating input exists anywhere in the domain.

## Deliverable

Write **`search-record.json`** in your workspace root, exactly this shape:

```json
{
  "outcome": "FOUND | NONE",
  "violating_input": "[[s, e], ...] (a concrete in-domain list) or null",
  "trace": "on FOUND: the line-by-line hand simulation of merge on that input, ending with the exact returned list; else null",
  "violating_pair": "on FOUND: {\"i\": [s, e], \"j\": [s, e]} — the pair in the sorted output with i.end >= j.start; else null",
  "argument": "on NONE: your argument that no violating input exists in the domain; else null",
  "classes_searched": ["short description of each input class you examined"],
  "search_method": "how the search was structured and why it is systematic"
}
```

Every value must be derived from your own simulation of `merge.py` as
written — not from an idealized notion of interval merging. On FOUND, the
violating input must have at most 6 intervals, integer endpoints in
`[-10, 10]`, and `start <= end` in every interval.

Also write **`result.json`** in your workspace root (this is the harness
return artifact, distinct from the deliverable):

```json
{
  "deliverable": "search-record.json",
  "summary": "one-paragraph summary of the outcome",
  "files_produced": ["search-record.json", "result.json", "execution-ledger.jsonl"],
  "model_calls_spent": 0
}
```

## Ledger

Write **`execution-ledger.jsonl`** in your workspace root: one JSON object
per line, each `{"event_id", "label", "actor", "timestamp", "artifact_refs",
"metadata"}`. Emit, in order, one event per harness node:

1. `label` `observe`, `actor` `node:observe-inputs`, `metadata.completes_node`
   `observe-inputs`, `artifact_refs` listing the input files you read.
2. `label` `propose`, `actor` `node:produce-evidence`,
   `metadata.completes_node` `produce-evidence`, `artifact_refs`
   `["search-record.json"]` — emitted at authoring time.
3. `label` `verify`, `actor` `node:self-check`, `metadata.completes_node`
   `self-check`, recording your structural self-check of the deliverable
   (non-authoritative).
4. `label` `return`, `actor` `node:return-result`, `metadata.completes_node`
   `return-result`, `artifact_refs` `["result.json"]`.
5. A terminal line `label` `complete`, `actor` `child`.

Your session ends after the terminal event. Deterministic root verification
governs every outcome; report honestly, including a NONE outcome if your
search genuinely finds no violation.
