# Topology Theory v0.1 — Semantics

## 1. Objects

- **Principle** `P-*`: a causal-design claim with preconditions (a closed
  DSL: `feature:<name>`, `topology:<name>`, `always`), predicted topology
  effects, and evidence citations. Statuses: `CANDIDATE SUPPORTED CHALLENGED
  FALSIFIED REVISED PROMOTED RETIRED`; abduction and replay consider only
  *active* statuses (`CANDIDATE SUPPORTED CHALLENGED REVISED PROMOTED`).
- **TheoryVersion** `Theta_H = (P, E+, E-, R, V, L)`: immutable once
  promoted; `predecessor_hash` links versions; evidence lives in the
  append-only store log, versions record only the log length at promotion.
- **TopologyHypothesis**: candidate topology = HarnessSpec + resolution map
  + frozen predictions + predicted value. Status lattice:
  `CANDIDATE -> VALIDATED | REJECTED`, `VALIDATED -> EXECUTED -> EVALUATED`.
- **Prediction**: observable claim with success AND falsification
  conditions; a prediction without a falsifier is schema-invalid. Machine
  kinds (`resolves`, `runtime_path`, `model_call_budget`,
  `authority_envelope`, `novel_evidence`, `local_sufficiency`, ...) are
  mechanically decidable; prose-only predictions evaluate INDETERMINATE,
  never silently HELD.

## 2. Abduction

`abduce` matches active principles' `feature:*` preconditions against the
typed features of each unresolved distinction; `always` principles apply
task-wide; `topology:*` preconditions bind at generation time. Model input
enters only as a serialized applicability document; unknown/inactive
principles or unknown distinctions are rejected deterministically.

## 3. Prediction freezing

`freeze_predictions` emits per-distinction resolution predictions plus
structural predictions (path, budget, authority; novel evidence for child
topologies; local sufficiency for local ones), then stores
`predictions_hash = artifact_id(canonical(predictions), provenance)` on the
hypothesis. `evaluate_topology` recomputes the hash; a mismatch raises —
retrospective edits are detectable and inadmissible.

## 4. Formal validation

`validate_topology` is a deterministic conjunction: schema, HarnessSpec
boundary validation, LTS compilation, gate-only promote authority,
attenuation (when a child contract is present), budget, finite-LTS
reachability (complete reachable; child return path exists; verify
downstream of act; no non-gate promote), candidate/canonical separation,
freshness declaration for creating topologies, proposal observability
(a hypothesize node upstream of every create/act), protected laws. Only
PASS candidates proceed to ranking.

## 5. Falsification semantics

Per prediction: `HELD -> SUPPORTED`, `FAILED -> FALSIFIED`,
`INDETERMINATE -> INDETERMINATE`. Per topology: all held `SUPPORTED`; mixed
`PARTIALLY_SUPPORTED`; none held with failures `FALSIFIED`; otherwise
`INDETERMINATE`. Task success does not imply topology support: a correct
answer obtained down a path that falsifies the frozen path prediction still
falsifies that prediction.

Principle evidence: `HELD -> SUPPORT`; `FAILED ->` `FALSIFY` at weight ≥ 1,
else `CHALLENGE`; INDETERMINATE emits nothing (absence of evidence is not
evidence).

## 6. Branching completion (Experiment 5 repair)

`formal/semantics.py` accepts optional node `branch` annotations:

```text
LOCAL:  decision -> local -> verify -> complete
CREATE: decision -> propose-child -> validate-child -> create
        -> child-return -> integrate -> verify -> complete
```

Branch exclusivity is encoded in the state space (configurations touching
two branches are unreachable; cross-branch node execution transitions do
not exist), and `complete` is enabled exactly when all shared nodes plus
one entire branch are done. Non-branching specs compile byte-identically to
the previous semantics (complete iff all nodes done). Historical E5
verdicts are unchanged: E5 refinement ran with `require_completion=false`
on parents, and no committed E5 artifact is recomputed.

## 7. Freshness rule v0.2 (`formal/freshness.py`)

```text
if executed:      session_id_confirmed must be True
elif not executed (dry run): None (or True) is permitted
False always fails; a missing executed field fails.
```

Frozen Experiment 5 evidence is untouched; all E5 executed launches carry
`session_id_confirmed=true` and PASS under the tightened rule.

## 8. Artifact identity

`ArtifactID = "sha256:" + hex(sha256(content || 0x00 || provenance_utf8))`.
Identity is exact and stable: same basename with different content yields
distinct ids; moving a file changes nothing. Path/basename is
non-authoritative metadata. New architecture artifacts (theory versions,
frozen predictions, patch manifests, harness refs) use these ids in formal
events; historical adapters keep their original behavior.

## 9. Utility and ranking

`U = ΔE − λC − μR − νG` over normalized [0,1] components with explicit
config. Deterministic total order: `(-utility, node_count, model_calls,
topology_id)`. Observed utility uses the same formula over observed
components; calibration error is component-wise absolute error plus utility
error.

## 10. Replay

A frozen case = pinned artifacts (sha256) + required active principles +
the preregistered historical outcome. COMPATIBLE / CONTRADICTED /
INDETERMINATE per case; a candidate revision that retires a principle
required by history is CONTRADICTED. Replay acceptability = zero
CONTRADICTED. Replay is evidence, not universal proof.

## 11. Self-modification

```text
root -> decompose -> topology-theory -> candidate implementer
     -> formal verifier -> replay -> independent verifier -> deterministic Gate
```

The candidate implementer may write only candidate state
(`candidate_only_guard`); the verifier may not promote
(`authorize_promotion` refuses non-gate actors and non-gate documents);
the Gate alone promotes, as a pure conjunction over serialized verification
inputs. Protected laws (gate monopoly, historical immutability, model
output ≠ authority, attenuation, freshness, proposal observability,
candidate-before-canonical mutation, formal-result integrity) are outside
ordinary self-modification; `check_protected_laws` rejects candidate
patches that touch them.
