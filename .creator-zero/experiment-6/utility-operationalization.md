# Experiment 6 — Utility Operationalization (frozen before any primary trial)

The utility model is the promoted explicit model of `theta-v1`:

```text
U(H) = DeltaE - lambda*C - mu*R - nu*G
lambda = 1.0   mu = 1.0   nu = 2.0        (topology-theory/utility-config.json)
```

All components normalized to [0,1]. Utility arithmetic, calibration
arithmetic, and ranking are executed by the promoted
`topology-theory/utility.py`; this document freezes how the *components*
are measured in Experiment 6. Nothing here may be tuned after the first
primary trial.

## Predicted components (per candidate, frozen at S4)

- `delta_e` — model-mediated estimate, serialized by the blinded S1
  session in `value-estimates.json` per candidate family: the predicted
  fraction of the task's `evidence_requirements` the family will satisfy
  with admissible evidence.
- `cost` — deterministic from the family's expected call structure:
  `cost = (expected model sessions + expected child sessions) / 8`
  (denominator = 2 x K-E6-trial.max_model_calls, fixed):

  | family                    | model sessions | child sessions | cost   |
  |---------------------------|----------------|----------------|--------|
  | local                     | 1              | 0              | 0.125  |
  | local-independent-verify  | 2              | 0              | 0.25   |
  | isolated-child            | 2              | 1              | 0.375  |
  | branching                 | 2 (worst case) | 1 (worst case) | 0.375  |

- `redundancy` — model-mediated estimate: predicted fraction of evidence
  records that duplicate parent-derivable evidence.
- `governance_risk` — model-mediated estimate: 0.25 x expected count of
  formal/governance failures.

The S1 session that produces these estimates is blinded (raw package
only). Cost is never model-estimated. Estimates are attached to the
generated candidates before prediction freezing and are part of the
committed candidate documents; ranking over them is deterministic
(utility desc, node_count asc, model_calls asc, topology_id asc).

## Observed components (per realized topology, computed at S7)

Let `REQ` be the task's evidence requirements and `SAT` the subset judged
satisfied by the trial's preregistered deterministic verifier
(admissibility conditions enforced; `satisfied_by` recorded as
parent/child/examiner/integration).

- `delta_e = |SAT| / |REQ|` (the scored gain). Q-resolution fraction,
  novel-evidence list, verification effect, and coverage gain are
  reported in `observed-value.json` as auxiliary gain observables but do
  not enter the scored `delta_e`: the distinction set's size is chosen by
  the model, so scoring on it would let the decision-maker inflate gain
  by emitting easy distinctions. Requirements are task-anchored.
- `cost = (model sessions launched + child sessions launched) / 8` with
  the same denominator as predicted cost. Sessions are counted from
  launch provenances (exec session, examiner session, child session).
  Wall-clock is recorded but not scored.
- `redundancy = duplicate evidence records / total evidence records`
  (0 when no evidence records). Duplicate flags are set by the
  preregistered verifier under the frozen duplicate rule: a
  child/examiner record that adds no new item, no material divergence,
  and no settled pending field duplicates parent evidence; parent records
  are never duplicates of themselves.
- `governance_risk = min(1, 0.25 x formal/governance failures)`
  (refinement, freshness, guard violations).

## Resolution admissibility (runtime record)

A distinction `Q` is recorded resolved iff every evidence requirement it
references is in `SAT` and all its declared dependencies are resolved
(fixed point). Its `resolved_by` node is mapped from the verifier's
`satisfied_by` of its first referenced requirement:
parent -> `resolve-local` (local families) / `observe-evidence`
(create-bearing families), child/integration -> `child-return`,
examiner -> `verify-independent`.

## Calibration and regret

- Per trial: `CalibrationError = |U_hat(selected) - U_obs(selected)|`,
  plus component-wise absolute errors (promoted
  `utility.calibration_error`).
- Aggregate: utility MAE and RMSE over primary trials; per-component MAE.
- Shadow pairs: ranking agreement = sign(U_hat(sel) - U_hat(shadow))
  equals sign(U_obs(sel) - U_obs(shadow)), ties counting as agreement.
- Regret per shadowed trial: `max(U_obs over executed topologies) -
  U_obs(selected)`; bounded regret over executed alternatives only.

## Authority note

`evaluate.evaluate_topology` (promoted) performs the mechanical
prediction-outcome comparison and enforces the frozen predictions hash;
its internal generic observed-value formula is superseded for scoring by
the operationalization above (persisted side by side; the operationalized
values are authoritative for Experiment 6 and are computed by
`runtime/exec_driver.py` with the promoted `utility.py` arithmetic).
