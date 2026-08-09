# Creator-0 Formal Semantics Kernel v0.1

A deterministic formal layer that converts Creator-0 from a primarily
schema-and-ledger-governed system into one with an explicit operational
semantics: labelled transition systems, simulation/refinement, strong and weak
bisimulation, inductive authority invariants, a coinductively defined (and
finitely witnessed) Creator capability, and finite fixed-point synthesis
monitoring.

The formal layer is **read-only** with respect to canonical task state. It may
parse, compile semantics, compare, verify, reject, and emit evidence. It may
not promote, edit canonical artifacts, weaken contracts, or modify historical
evidence. Formal verification is an epistemic/governance mechanism, not an
Actor. **No LLM may override a failed formal check.**

## Modules

| Module | Purpose |
|---|---|
| `labels.py` | Closed typed transition alphabet (16 labels incl. `tau`) |
| `model.py` | `LTS`, `Transition`, `RuntimeEvent`, `Trace`, `FormalResult` |
| `semantics.py` | Deterministic `HarnessSpec -> FormalLTS` compiler |
| `trace.py` | `RuntimeLedger -> Trace` parser (normalized formal event schema) |
| `adapters.py` | Fixture adapters for immutable historical ledgers (E3, E4 C1) |
| `refinement.py` | `Runtime <= Spec` simulation/refinement check |
| `bisimulation.py` | Strong and weak bisimulation with counterexamples |
| `attenuation.py` | `K_child <= K_parent` inductive authority invariant |
| `creator_closure.py` | Bounded `hat_kappa` Creator-Closure witness check |
| `synthesis_fixedpoint.py` | Finite `Q_before/Q_after` progress classification |
| `serialization.py` | Canonical deterministic JSON in/out |
| `schemas/` | JSON Schemas for LTS, transition, formal-result documents |

## API

```python
compile_harness_spec(spec, contract) -> LTS
parse_runtime_ledger(path, strict=True) -> Trace
check_refinement(trace, lts, require_completion=False) -> FormalResult
strong_bisimilar(a, b) -> FormalResult
weak_bisimilar(a, b, silent_label="tau") -> FormalResult
check_attenuation(parent, child) -> FormalResult
check_creator_closure(parent, attestation) -> FormalResult
classify_synthesis(before, after) -> FormalResult
```

## CLI

All formal commands are additions to `cz.py`; existing validation behavior is
unchanged. Exit codes: `0` PASS, `2` formal relation FAIL, `3` INDETERMINATE /
insufficient evidence, `4` malformed input / parse failure. Every command
prints a concise human-readable status line plus deterministic
machine-readable JSON (inline, or to `--json-out`).

```bash
python .creator-zero/cz.py semantics <harness-spec.json> [--contract C] [--out lts.json]
python .creator-zero/cz.py check-runtime <harness-spec.json> <execution-ledger.jsonl> \
    [--contract C] [--adapter experiment3|experiment4-c1] [--require-completion]
python .creator-zero/cz.py bisim <state-a.json> <state-b.json> --mode weak|strong
python .creator-zero/cz.py attenuation <parent-contract.json> <child-contract.json>
python .creator-zero/cz.py closure <parent-contract.json> <child-attestation.json>
python .creator-zero/cz.py synthesis-status <q-before.json> <q-after.json>
```

## Tests

```bash
python3 -m unittest discover -s .creator-zero/tests          # pre-existing suite
python3 -m unittest discover -s .creator-zero/tests/formal   # formal kernel suite
```

Historical regression fixtures live in `.creator-zero/tests/formal/fixtures/`;
original experiment artifacts are immutable and are pinned by sha256 in
`test_historical_fixtures.py`. Where historical ledgers predate the normalized
event schema, `adapters.py` maps them deterministically and the committed
`*-adapter-mapping.json` files record every event mapping (nothing is silently
reinterpreted or dropped).

## Documents

- `SEMANTICS.md` — formal definitions: state, labels, transition relation,
  tau, refinement, strong/weak bisimulation, attenuation, bounded Creator
  Closure, synthesis fixed-point statuses.
- `PROOF_OBLIGATIONS.md` — what is deterministically checked, what is
  inductively justified, what is coinductively defined but finitely witnessed,
  and what is not established.
- `examples/` — deterministic formal-result examples produced by the CLI.
