# Child task: independent W371 answers (e6-t06-child)

You are a terminal worker session with tools **Read** and **Write** only.
You may not create, delegate, or launch anything. Work only inside your
workspace. Execute the four nodes of your harness (`child-harness.json`)
in order: observe-inputs → produce-evidence → self-check → return-result.

## Inputs

Your `inputs/` directory contains exactly two files (read every file you
find under `inputs/`, wherever the launcher placed them):

- a spec file (`spec.md`) defining the W371 check-digit rule;
- an items file (`items.json`) with two lists: `validate` (8 identifiers)
  and `compute` (4 payloads).

Use ONLY these inputs. Derive everything yourself from the spec; do not
rely on memory of similar checksum schemes.

## Required method (follow it exactly)

Per the spec, weights cycle 3, 7, 1 assigned to payload digits from RIGHT
to LEFT (rightmost payload digit has weight 3), and the check digit is
(10 − (S mod 10)) mod 10 where S is the weighted payload sum. You must
answer using the following two procedures, which are equivalent to the
spec but organized differently:

**Validate items** (each identifier = payload followed by one check
digit). Do NOT compute the check digit. Instead use the whole-identifier
congruence test:

1. Extend the weight cycle one position to the RIGHT of the payload: the
   final (check) digit receives weight 1, the rightmost payload digit
   weight 3, the next-left weight 7, then 1, 3, 7, 1, ... continuing
   leftward. Equivalently, counting positions p = 0 for the check digit,
   1 for the rightmost payload digit, and increasing leftward: weight(p) =
   3 if p mod 3 = 1, 7 if p mod 3 = 2, 1 if p mod 3 = 0.
2. Compute T = sum over ALL digits of the identifier (including the check
   digit) of digit × weight.
3. The identifier is **VALID** iff T mod 10 = 0, otherwise **INVALID**.

For each identifier show every digit with its weight and product, the
total T, and T mod 10.

**Compute items** (each entry is a bare payload; find its check digit):

1. Let L be the payload length. Assign weights LEFT to RIGHT: the leftmost
   digit has the weight of position L counted from the right, i.e. weight
   3 if L mod 3 = 1, weight 7 if L mod 3 = 2, weight 1 if L mod 3 = 0;
   then continue rightward following the cycle so that the rightmost digit
   ends with weight 3. (For a 6-digit payload the left-to-right weights
   are 1, 7, 3, 1, 7, 3.)
2. Compute S = sum of digit × weight.
3. The check digit is the unique c in {0,...,9} with (S + c) mod 10 = 0.
   Find it by testing candidates, not by a subtraction formula.

For each payload show every digit with its weight and product, S, and the
congruence giving c.

Do every sum twice, digit by digit, before recording an answer. The items
are adversarially chosen: any wrong weight phase or direction produces a
wrong answer.

## Deliverable

At the produce-evidence node, write **`child-answers.json`** in your
workspace root:

```json
{
  "answers": {
    "validate:<identifier>": "VALID or INVALID",
    "compute:<payload>": "<single digit as a string>"
  },
  "method": "<one-paragraph description of the two procedures you used>",
  "derivations": {
    "validate:<identifier>": "<digits, weights, products, T, T mod 10>",
    "compute:<payload>": "<digits, weights, products, S, congruence, c>"
  }
}
```

The `answers` object must have exactly 12 keys: one `validate:<id>` per
identifier in the items file's `validate` list and one
`compute:<payload>` per entry in its `compute` list, values exactly
`"VALID"`, `"INVALID"`, or a single digit string.

At return-result, write `result.json`:
`{"summary": "<what you produced>", "files_produced":
["child-answers.json"], "model_calls_spent": 0}`.

## Ledger

Maintain **`execution-ledger.jsonl`** in your workspace root: one JSON
object per line with fields `event_id`, `label`, `actor`, `timestamp`,
`artifact_refs`, `metadata`. Emit exactly one event per node, in order:

1. `{"label": "observe", "actor": "node:observe-inputs", "metadata": {"completes_node": "observe-inputs"}}`
2. `{"label": "propose", "actor": "node:produce-evidence", "artifact_refs": ["child-answers.json"], "metadata": {"completes_node": "produce-evidence"}}`
3. `{"label": "verify", "actor": "node:self-check", "metadata": {"completes_node": "self-check"}}`
4. `{"label": "return", "actor": "node:return-result", "artifact_refs": ["result.json"], "metadata": {"completes_node": "return-result"}}`

followed by a terminal `{"label": "complete", "actor": "child"}` event.
Fill `event_id` (e.g. c1..c5) and `timestamp` on every line.
