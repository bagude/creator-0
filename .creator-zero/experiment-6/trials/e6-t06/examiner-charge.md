# Examiner charge — e6-t06 (node verify-independent)

You are the independent, information-only examiner for task e6-t06. You
re-verify; you do not write into the governed boundary and you have no
promotion authority. Your product is a re-derivation report satisfying
evidence requirement E-B: a complete second answer set for all 12 items,
produced by a method disjoint from the first derivation, without consulting
the first derivation's intermediate work, with per-item agreement recorded.

## Non-consultation condition (read this first)

- You MUST NOT read `derivations.md` — it is the first derivation's
  intermediate work; reading it voids E-B.
- Derive your own answers for all 12 items FIRST, from
  `package/artifacts/spec.md` and `package/artifacts/items.json` only.
  Only after your 12 answers are fixed, open `result.json` and read its
  `answers` object (nothing else) to record the per-item comparison.

## What to re-derive

All 12 items in `package/artifacts/items.json`:
- 8 identifiers under `validate` -> VALID or INVALID each.
- 4 payloads under `compute` -> one check digit each.

## Required method (disjoint from the first derivation)

The first derivation tabulated digit-by-digit products walking the payload
with weights assigned right-to-left and then applied the check-digit
formula. Use a different route:

1. For each `validate` identifier of length 8: treat the FINAL digit as
   position 0 and the payload digits as positions 1..7 counted from the
   right. Assign weight 1 to position 0 and weight 3,7,1,3,7,1,3 to
   positions 1..7 respectively (this is exactly spec.md's rule plus the
   check digit at weight 1). Compute the total T over ALL 8 digits.
   The identifier is VALID iff T mod 10 == 0. Do not compute the check
   digit explicitly.
2. For each `compute` payload of length 6: work LEFT to RIGHT with an
   explicit phase correction: the digit at left-to-right index i
   (i = 1..6) sits at right-to-left position p = 7 - i; its weight is 3 if
   p mod 3 == 1, 7 if p mod 3 == 2, 1 if p mod 3 == 0. Sum S, then the
   check digit is (10 - (S mod 10)) mod 10.

Critical spec point to honor and to attack in the first derivation: spec.md
assigns weights RIGHT to LEFT with the RIGHTMOST payload digit at weight 3.
The items are adversarially chosen so that a left-to-right assignment
without phase correction, or any phase shift (rightmost = 7 or = 1), flips
verdicts and digits. If your total for any item differs, recompute that
item once from scratch before recording disagreement.

## Answer components whose failure changes the deliverable

Every one of the 12 answers is load-bearing (E-C demands exact
correctness), but scrutinize hardest:
- The three INVALID verdicts claimed by the first derivation:
  `92489881`, `52874804`, `29067655`. A phase error typically turns
  exactly these.
- Every `compute` digit: `479812`, `153886`, `278381`, `027899`.

## Report to produce

For each item: your independently derived answer, the `result.json`
answer, and AGREE/DISAGREE. Then an overall verdict: whether the second
derivation agrees item by item (settles Q3) and whether any answer in
`result.json` is contradicted. Include your weighted totals so your work
is itself checkable.
