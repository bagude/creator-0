# Proof Obligations — Formal Semantics Kernel v0.1

Bounded executable checks are not proofs of arbitrary infinite behavior. This
document states exactly which epistemic class each claim belongs to.

## 1. Properties proven by deterministic checking

Each of these is decided mechanically, with a counterexample on failure, for
the **specific finite inputs** given:

- A specific HarnessSpec compiles to a unique LTS (byte-identical canonical
  serialization on repeated compilation).
- A specific runtime trace refines (`<=`) a specific compiled HarnessSpec LTS
  (Experiment 3 ledger: PASS; synthetic Actor canonical write: FAIL).
- A specific finite LTS pair is or is not strongly / weakly bisimilar
  (Experiment 4 session-reconstruction fixtures: weak PASS, strong FAIL).
- A specific contract pair satisfies or violates attenuation on every encoded
  authority axis (K1<=K0 PASS, K2<=K1 PASS, synthetic escalating child FAIL).
- A specific bounded Creator witness satisfies `hat_kappa` (original E4 K3
  attestation FAIL on `CreatorCapable`; corrected 4B attestation PASS).
- A specific `(Q_before, Q_after)` pair classifies into exactly one synthesis
  status.

## 2. Properties inductively justified under the encoded transition rule

- If **every** creation transition in a lineage passes the local attenuation
  check, then no finite descendant escalates authority relative to any
  ancestor (transitivity of the per-axis orders). This holds only under the
  assumption that all creations are actually checked and that the encoded
  axes cover the real authority surface.

## 3. Properties coinductively defined but only finitely witnessed

- Creator capability: `Creator = nu X . F(X)`. The kernel checks the bounded
  witness `hat_kappa` (one generation of draft-child evidence with an
  external stop). Operationally this witnesses membership one unfolding at a
  time; it does **not** construct or verify an infinite lineage.

## 4. Properties assumed

- Runtime event instrumentation is faithful: the ledgers record every
  governed action, and adapter mappings preserve their meaning (mappings are
  recorded, but their semantic fidelity to what actually happened is an
  assumption).
- Ledger position reflects causal order; timestamps are evidentiary only.
- Contract fields carry their documented meanings; absent axes default to
  parent-permissive/child-inheriting as documented in `attenuation.py`.
- Authority-string ordinals (none < scoped/read-only/model-invocation <
  unrestricted) correctly order the real-world authority they describe.
- CPython determinism of the checking code itself.

## 5. Properties not yet proven (and not claimed)

- Existence of an arbitrary infinite Creator lineage (arbitrary infinite
  Creator Closure).
- Semantic equivalence of hidden model/epistemic states across sessions.
- Formal correctness of Claude Code itself, or that its implementation
  globally refines this model.
- Completeness of runtime event instrumentation (unlogged governed actions
  are invisible to refinement).
- Universal decidability of bisimulation for unrestricted future models
  (v0.1 handles finite explicitly-modeled systems only).
- Full Tarski convergence of arbitrary Decomposer/Composer synthesis (v0.1
  classifies finite-set progress only).
