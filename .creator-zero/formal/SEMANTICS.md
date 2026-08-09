# Creator-0 Formal Semantics v0.1

## 1. State

A labelled transition system:

```text
L = (S, Lambda, ->, s0)
```

- `S` — externally reconstructible governed states. A state is the governed
  configuration needed to determine allowed future transitions, encoded
  deterministically as

  ```text
  done={<sorted completed node ids>}|promoted=<0|1>|complete=<0|1>
  ```

  The state is **not** a snapshot of an LLM context window. Hidden
  chain-of-thought, inaccessible context dynamics, and unlogged internal
  computation are outside the formal state.
- `Lambda` — the closed label alphabet below.
- `->  ⊆ S × Lambda × S`, transitions additionally carry an **actor pattern**
  (a concrete actor id such as `node:report`, `gate`, `creator`, or `*`).
- `s0 = done={}|promoted=0|complete=0`.

## 2. Labels

Closed enum (`labels.py`); every runtime event must map into it or be
rejected as unmapped:

```text
observe propose validate reject consult delegate create return
act_candidate verify authorize promote persist reconstruct complete tau
```

`tau` is the silent/internal transition: it may participate in weak
equivalence but never in external observation traces.

Deterministic sub-mappings:

- node primitive -> execution label:
  `observe->observe, hypothesize->propose, test->observe, act->act_candidate,
  verify->verify, create->create, return->return`
- edge relation -> interaction label:
  `observe->observe, consult->consult, request_response->consult,
  delegate->delegate, verify->verify, authorize->authorize, create->create,
  return->return`

## 3. Transition relation (HarnessSpec operational semantics)

Compiled deterministically by `semantics.py`; illegal transitions are absent
by construction. The authority partition of the alphabet:

1. **Non-authority labels** (`observe, propose, validate, reject, consult,
   return, persist, reconstruct`) are wildcard-actor self-loops in every
   non-terminal state: they carry information, never authority.
2. **Node execution**: node `n` with primitive `p` yields
   `done -> done ∪ {n}` labelled by `label(p)` with actor `node:<n>`, enabled
   only when every non-return in-edge source of `n` is completed (authorize
   edges therefore gate the target on source completion).
3. **Edge interactions**: an edge `(src, rel, tgt)` yields a self-loop
   labelled `label(rel)` with actor `node:<src>`, present only after `src`
   completed.
4. **create** exists (as a `creator`-actor self-loop) only if the governing
   contract grants it: `may_create_creator` true, `max_children > 0`, and
   `may_realize_creation` not false. A spec that realizes a `can_create` node
   under a denying contract fails compilation.
5. **promote** exists only with actor `gate`, only from states where at least
   one `verify` node has completed, only when the spec contains an `act` node,
   and only when the contract does not deny gate promotion
   (`canonical_write_authority` absent, or naming the gate). Under a contract
   with `canonical_write_authority: "none"` (e.g. K1/K2) no `promote`
   transition exists at all — an Actor canonical write is unmatchable.
6. **complete** exists only when every node has completed, and moves to the
   terminal `complete=1` state.
7. **tau** is a permitted self-loop everywhere.

Example of a transition absent by construction:
`Actor --canonical_write/promote--> Canonical` does not exist when the Actor
holds candidate-write authority only; the only promote transitions carry the
`gate` actor.

## 4. Runtime traces

`trace.py` parses JSONL ledgers of normalized events:

```json
{"event_id": "...", "source": "...", "label": "authorize", "target": "...",
 "actor": "...", "timestamp": "...", "artifact_refs": [], "contract_id": "...",
 "metadata": {}}
```

Timestamps are evidentiary metadata; **causal order is trace position**.
Unknown or malformed governed events raise a parse error (strict) or are
returned as explicit unmapped-event records (non-strict) — never silently
ignored. `metadata.completes_node` marks an event as the execution/completion
of a spec node. Historical ledgers are adapted by `adapters.py` with committed
mapping records.

## 5. Refinement (`Runtime <= Spec`)

Deterministic trace walk: every observable runtime event must be matched by an
enabled spec transition with the same label whose actor pattern admits the
event actor; events carrying `completes_node` must match that node's execution
move. `tau` events are skipped. First unmatched event returns
`REFINEMENT_VIOLATION` with the offending transition, reconstructed source
state, allowed labels at that state, and the observable trace prefix.
With `require_completion`, a trace that never reaches `complete=1` returns
INDETERMINATE (premature termination / continuation required) — this is how
the Experiment 4 C1 premature-exit deviation is exposed.

## 6. Strong bisimulation

`R ⊆ S_A × S_B` is a strong bisimulation iff for all `(p,q) ∈ R`:
`p --a--> p'` implies `q --a--> q'` with `(p',q') ∈ R`, and symmetrically,
where an action `a` is the pair `(label, actor)`. Implemented as the greatest
fixpoint by naive refinement; PASS iff the initial pair is related.

## 7. Weak bisimulation

`p ==l==> p'` abbreviates `tau* l tau*`. Weak bisimulation matches
`p --l--> p'` (observable) by `q ==l==> q'`, and `p --tau--> p'` by
`q ==tau*==> q'` (possibly zero steps). This is the default relation for
artifact-mediated session equivalence:

```text
E_n ~= E_hat_{n->n+1}
```

means: the reconstructed successor and predecessor are behaviorally
equivalent over the governed observation alphabet, even if their internal
computation differs. No equality of hidden epistemic states is claimed.
For the Experiment 4 session-reconstruction fixture, the exact tau-hiding
decisions are recorded in
`tests/formal/fixtures/e4-c1-session-equivalence-mapping.json`.

## 8. Attenuation (`K_child <= K_parent`)

Inductive safety invariant: no governed authority axis increases. Axes:
`allowed_tools`, `allowed_primitives`, `allowed_relations` (subset);
`max_model_calls`, `max_children`, `max_depth`,
`max_realized_creator_children`, `max_realized_creator_depth` (child <=
parent); `may_create_creator`, `may_realize_creation` (no false->true);
filesystem write scope (parent-scope containment, or sibling delegation
inside the parent scope's workspace envelope with no overlap of parent
protected paths — the governed lineage law under which c1/ -> c2/ -> c3/
sandboxes were granted); candidate/canonical/git/network authority
(deterministic ordinals: none=0 < scoped/read-only/model-invocation=1 <
unrestricted=2). Verdicts: `ATTENUATION_PASS` / `ATTENUATION_FAIL` with the
exact escalating dimensions. Coinduction is deliberately not used here.

## 9. Bounded Creator Closure

Abstract definition (coinductive):

```text
F(X) = { C | exists C': C --create--> C' and Attenuated(C',C) and C' in X }
Creator = nu X . F(X)
```

Executable bounded witness (`hat_kappa(K_parent, K_child, mechanism)`):

```text
Valid(K_child) AND Attenuated(K_child, K_parent) AND CreatorCapable(K_child)
AND CreationMechanismValid AND ExternalStopOnly(K_child)
```

- `CreatorCapable`: `creator_capability == true` and
  `may_create_creator == true`.
- `ExternalStopOnly`: `may_realize_creation == false` and `max_children == 0`.
- `CreationMechanismValid`: a concrete creation command is attested and marked
  not executed.

This preserves the Experiment 4B correction: a terminal child
(`creator_capability=false, may_create_creator=false`) fails; a
Creator-capable child with realization externally disabled may pass.

## 10. Synthesis fixed-point statuses

Over finite unresolved-distinction sets:

```text
Q_after == empty                -> SYNTHESIS_CLOSED            (PASS)
Q_after proper-subset Q_before  -> PROGRESS                    (PASS)
Q_after == Q_before != empty    -> SYNTHESIS_FIXED_POINT_UNRESOLVED (INDETERMINATE)
Q_after not-subset Q_before     -> SYNTHESIS_REGRESSION        (FAIL)
```

This is a finite deterministic progress classifier, not Tarski convergence
machinery.
