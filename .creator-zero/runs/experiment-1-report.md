# Creator-0 Experiment 1 — Run Record

Date: 2026-08-09
Creator depth: 0 (no child creators instantiated)
Canonical artifact: `src/solver.py` at commit f060bdf (unchanged)

## Provenance caveat

The repository was empty at session start: no `.creator-zero` boundary, no
target files. Creator-0 bootstrapped the boundary (contract + `cz.py`), the
authoritative spec, the implementation, and the "existing" test suite, then
froze them as canonical state X_t (commit f060bdf) before composing any
harness. Because the auditor also authored the artifact, this run is a
process/smoke validation of the causal-epistemic machinery, not a blind
audit. An arithmetic slip made during authoring became an organic, unplanned
defect — in the protected test suite, not the implementation — which the
harness located and attributed without being told it existed.

## Harness

Proposal: `.creator-zero/runs/experiment-1-proposal.json`
Boundary verdicts: VALID on first submission; MATERIALIZED
(`experiment-1-authorized.json`, sha256-pinned).

Topology (6 nodes):

    n_observe --observe--> n_hypothesize --request_response--> n_test
    n_test --verify--> n_verify
    n_verify --authorize--> n_act          (never realized)
    n_act --request_response--> n_verify   (never realized)
    n_verify --return--> n_return

## Evidence

- Differential sweep (`differential_test.py`): 3,008 seeded deterministic
  cases across 5 regimes plus 8 invalid-input probes, solver vs an
  independent exhaustive oracle derived only from the spec.
  Outcome: AGREEMENT. Zero counterexamples.
- Protected unit suite: 11/12 pass. `test_classic_instance` FAILS.
- Oracle attribution of the failure: on the test's instance the
  spec-governed optimum is (11, [2, 6]) — jobs (0,6,6) and (6,10,5) touch
  at t=6, compatible under R2 — and the solver returns exactly (11, [2, 6]).
  The test's expected weight 10 contradicts the authoritative spec.

## Conclusion

Implementation: **NO_DEFECT_DEMONSTRATED**.
mutation_performed: **false** — canonical state preserved (git-verified:
no diff on `src/solver.py`).

Separately demonstrated: a defect in the protected test suite
(`test_classic_instance` expects 10; spec-derived optimum is 11).
The root contract lists `tests/test_solver.py` as protected_read_only, so
no correction was applied this run. Recommended follow-up: an explicitly
authorized amendment changing the expectation to weight 11
(schedule [2, 6]).

## Boundary events

- Proposal rejections: 0. Action rejections: 0. Permission failures: 0.
- One harness-tool iteration: the verifier's counterexample extraction
  initially missed `jobs = [...]` bindings and was extended
  (harness tooling, not the artifact under audit; both runs recorded).
