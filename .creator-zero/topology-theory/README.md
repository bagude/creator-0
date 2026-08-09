# Topology Theory + Reverse-ITP Self-Modification v0.1

Creator-0's topology choice, upgraded from a binary `CREATE / DO_NOT_CREATE`
decision to an explicit, versioned, falsifiable theory of causal design:

```text
Task
-> unresolved distinctions Q
-> topology theory Theta_H
-> applicable principles
-> candidate topologies
-> predictions/falsifiers
-> formal validation
-> predicted utility
-> selected topology
-> execution
-> observed utility
-> falsification
-> principle evidence
-> candidate theory revision
-> historical replay
-> independent verification
-> Gate
```

Every topology is a **provisional causal hypothesis** about how epistemic
work should be organized — with frozen predictions, observable falsifiers,
and prediction-specific falsification after execution.

## Theory object

`Theta_H = (P, E+, E-, R, V, L)` — principles, supporting evidence,
falsifying/challenging evidence, revision graph, version/promotion status,
lineage. Persisted by `theory_store.py`:

- versions are write-once files (`theta-v<N>.json`); promoted versions are
  immutable and each version links its predecessor by artifact id;
- evidence is an append-only log with a running hash chain
  (`evidence.jsonl` + `evidence-heads.jsonl`); any prefix rewrite is
  detected by `verify_append_only()`;
- promotion demands the deterministic Gate's own PASS (`PromotionError`
  otherwise) — models, verifiers, and revision proposals cannot promote.

Seed principles (`principles.py`) cite only frozen, sha256-pinned artifacts
from Experiments 3, 4, 4C, and 5.

## Module map

| Module | Role |
|---|---|
| `model.py` | typed objects + closed-schema validation |
| `serialization.py` | canonical JSON, `artifact_id = sha256(content \|\| provenance)` |
| `principles.py` | evidence-cited seed principles, seed theory builder |
| `theory_store.py` | immutable versions, append-only evidence, gate-guarded promote |
| `abduct.py` | `abduce(...)` Q -> applicable principles (deterministic core; serialized model input) |
| `generate.py` | `generate_candidates(...)` closed template grammar, ≤ 4 candidates |
| `predict.py` | `freeze_predictions(...)` falsifier-complete, hash-frozen |
| `validate.py` | `validate_topology(...)` deterministic pre-execution rejection |
| `utility.py` | `U_hat = ΔE − λC − μR − νG`, explicit config, deterministic tie-break |
| `evaluate.py` | mechanical prediction comparison, observed value, calibration |
| `falsify.py` | prediction-specific falsification + principle evidence events |
| `revise.py` | `propose_revision(...)` proposal-only reverse-ITP revision |
| `replay.py` | frozen-corpus regression of candidate theories |
| `self_modify.py` | candidate-only guard, protected laws, patch manifest, Gate |

## CLI

All commands emit canonical JSON (`--json-out` writes to a file):

```text
cz.py theory-show          [--version N | --theory f.json]
cz.py theory-abduce        task.json distinctions.json [--model-applicability m.json]
cz.py topology-generate    task.json distinctions.json [--max-candidates 4]
cz.py topology-predict     topology.json distinctions.json
cz.py topology-score       candidates.json [--config utility-config.json]
cz.py topology-evaluate    predictions.json runtime.json [--evidence e.json]
cz.py theory-revise        evidence-events.json
cz.py theory-replay        [--candidate-theory theta.json] [--corpus c.json]
cz.py self-modify          {protected-laws|patch-manifest|gate|authorize-promotion} ...
```

## Determinism boundary

Deterministic (model output can never override):

```text
schema validation, LTS compilation, reachability, attenuation,
protected-law checking, utility arithmetic, tie-breaking,
mechanical prediction comparison, historical replay on mechanical cases,
the Gate
```

Model-mediated (must be serialized into typed artifacts before use):

```text
principle applicability suggestions, candidate topology synthesis,
expected epistemic value estimates, candidate principle wording,
revision proposal wording
```

## Utility

`U_hat(H) = ΔE_hat(H) − λ·C(H) − μ·R(H) − ν·G(H)` with weights in
`utility-config.json` (λ=1.0, μ=1.0, ν=2.0), all components normalized to
[0,1]. Ranking: utility desc, node_count asc, model_calls asc, topology_id
asc — fully deterministic.

## Bounded claim

A PASS of this architecture's acceptance suite justifies only:

> Creator-0 can maintain an evidence-bearing theory of causal-design
> principles, generate falsifiable topology hypotheses from it, compare
> predicted and observed topology value, propose revisions, and use the
> same governed mechanism for bounded candidate-first modification of its
> own topology-generation implementation.

It does **not** claim unrestricted recursive self-improvement or universal
topology optimality.
