# Task: audit a discount claim by systematic search

You are a fresh, isolated worker session. You have never seen any prior
analysis of this problem, and none exists for you to read. Your tools are
**Read** and **Write** only. You may read only the files listed in your input
manifest.

## The claim to audit

> No cart's total discount exceeds 40 percent (0.40).

Decide whether this claim **HOLDS** or is **VIOLATED** over the domain of all
carts expressible in the cart shape, by carrying out your own systematic
search. If violated, produce one concrete violating cart.

## Materials

Read `rules.md`. It defines the discount rules, how factors combine, how the
total discount is computed, and the cart shape. Everything you need about the
rules is in that file — take the factors and triggers verbatim from it.

## Method (required: systematic, not a spot check)

1. Identify every rule and its trigger condition from `rules.md`.
2. Each rule is governed by one binary trigger, so the whole cart domain
   partitions into a finite set of input classes indexed by which triggers are
   active. Enumerate all of these classes.
3. For each class, compute the final price factor as the product of the
   factors of the active rules, and the total discount as 1.0 minus that
   product.
4. Determine whether any class has total discount strictly greater than 0.40.
   Because every rule's factor is below 1.0, the discount is maximized when the
   greatest number of triggers is active — check the maximizing class
   explicitly and confirm your conclusion covers the entire domain.
5. If some class exceeds 0.40, construct one concrete cart in that class as a
   witness. If none does, state the argument that none can.

## Deliverable

Write exactly one deliverable file named **`search-result.json`** with this
exact shape:

```json
{
  "found": true or false,
  "violating_input": {
    "quantity": <int>,
    "loyalty_member": <bool>,
    "category": "<str>",
    "coupon_code_applied": <bool>
  },
  "total_discount": <number>,
  "input_classes_examined": ["<description>", "..."],
  "argument": "<how the search covered the whole domain and what it concluded>"
}
```

- Set `found` to `true` if you found a cart with total discount > 0.40, else
  `false`.
- On `found: true`, `violating_input` must be a concrete cart in the cart shape
  whose factor product, computed from `rules.md`, gives total discount > 0.40,
  and `total_discount` must be that value.
- On `found: false`, set `violating_input` to `null` and `total_discount` to
  the maximum total discount achievable over the domain.
- `input_classes_examined` must list the classes you enumerated (enough to show
  the search was systematic over the whole domain).

## Ledger contract

Also write `execution-ledger.jsonl`, one JSON object per line, one line per
harness node you execute, in dependency order. Each object:
`{"event_id", "label", "actor", "timestamp", "artifact_refs", "metadata"}`
with `actor` = `node:<id>` and `metadata.completes_node` = `<id>`. Use these
labels by node primitive: observe -> `observe`, hypothesize -> `propose`,
verify -> `verify`, return -> `return`. List files a node authored in its
`artifact_refs`.
