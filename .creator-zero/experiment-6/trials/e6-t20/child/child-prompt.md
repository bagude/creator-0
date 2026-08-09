# Child worker prompt — task e6-t20-child

You are an isolated worker session governed by `child-contract.json`
(K-E6-child-t20). You hold exactly two tools, **Read** and **Write**, and one
model call. You are terminal: you may not create, delegate, launch, or consult
anything outside this workspace. Work only inside your workspace using Read
and Write. Execute the four nodes of `child-harness.json` in order:
observe-inputs, produce-evidence, self-check, return-result.

## Your inputs

The directory `inputs/` contains everything you may use:

- `inputs/spec.md` — the semantics of a small stack-machine language.
- `inputs/candidate_a.py`, `inputs/candidate_b.py`, `inputs/candidate_c.py` —
  three implementations, each exposing `run(prog)`.
- `inputs/programs.json` — an ordered JSON list of six programs (0-indexed);
  each program is a list of instructions like `["PUSH", 3]` or `["ADD"]`.

Read all of them at observe-inputs before producing anything.

## Your task

For each candidate (keys `A`, `B`, `C`), decide whether its `run(program)`
returns the same result as `spec.md` prescribes for **every** program in
`inputs/programs.json`. Answer exactly `conforms`, or `diverges:<i>` where
`<i>` is the 0-indexed position in `programs.json` of the **first** program on
which the candidate's result differs from the spec's result. Every answer must
be exactly right: a correct verdict with a wrong index is a wrong answer, and
`conforms` may be declared only after every one of the six programs is
accounted for.

Apply the spec's halting semantics exactly as written (e.g. an underflow that
the spec says halts with "ERROR" halts the program immediately at that
instruction), not intuitive interpreter behavior.

## Mandated method — static code-diff analysis

You MUST derive the verdicts by the following method, and state the method in
your deliverable:

1. **Per-opcode semantic comparison.** For each opcode (PUSH, ADD, DUP, SWAP,
   POP), compare each candidate's source code against `spec.md`, including all
   underflow/empty-stack and halting behavior. Tabulate every semantic delta
   per candidate (candidate behavior vs. spec behavior, and the exact stack
   condition that triggers the delta). A candidate with zero deltas conforms
   on all inputs by construction — but you must still confirm no delta exists
   for any opcode.
2. **First-trigger scan.** For each candidate that has at least one delta,
   scan the programs in `programs.json` **in order**, tracking only what is
   needed (e.g. stack depth at each instruction under the spec's semantics) to
   find the first program in which some delta's trigger condition is actually
   reached during execution. When a trigger is reached, confirm that the two
   final results genuinely differ on that program (compute the spec's final
   result and the candidate's final result for that single program), then stop:
   that index is the divergence index. If no program ever triggers any delta,
   the candidate conforms.

Do NOT use full side-by-side trace simulation of every program against every
candidate as your method; per-program computation is permitted only to locate
trigger points via the depth scan and to confirm the result difference at the
identified first-trigger program.

## Deliverable

At produce-evidence, write `verdicts.json` in your workspace root, exactly:

```json
{
  "answers": {"A": "conforms|diverges:<i>", "B": "...", "C": "..."},
  "method": "<a precise statement of the code-diff method as you applied it, including the per-candidate deltas found and the trigger scan outcome>"
}
```

At self-check, re-read `verdicts.json` and confirm: keys are exactly A, B, C;
each value is `conforms` or `diverges:<i>` with `<i>` a decimal integer in
0..5; the method is stated. Non-authoritative.

At return-result, write `result.json`:

```json
{
  "deliverable": "verdicts.json",
  "files_produced": ["verdicts.json", "result.json", "execution-ledger.jsonl"],
  "model_calls_spent": 0
}
```

## Ledger contract

Maintain `execution-ledger.jsonl` in your workspace root: one JSON object per
line with fields `event_id`, `label`, `actor`, `timestamp`, `artifact_refs`,
`metadata`. Emit exactly one event per node, in order, with
`metadata.completes_node` set:

1. `{"label": "observe", "actor": "node:observe-inputs", ... "metadata": {"completes_node": "observe-inputs"}}`
2. `{"label": "propose", "actor": "node:produce-evidence", "artifact_refs": ["verdicts.json"], "metadata": {"completes_node": "produce-evidence"}}`
3. `{"label": "verify", "actor": "node:self-check", ... "metadata": {"completes_node": "self-check"}}`
4. `{"label": "return", "actor": "node:return-result", "artifact_refs": ["result.json"], "metadata": {"completes_node": "return-result"}}`

Finish with a terminal event `{"label": "complete", "actor": "child", ...}`.
`verdicts.json` must appear in `artifact_refs` of the produce-evidence propose
event at authoring time.
