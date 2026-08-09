# Creator-0 Experiment 3 Report

External Decomposer/Composer separation, artifact-only communication, candidate-state mutation with deterministic gating.

## 1. Freshness and isolation

    operator_session_fresh: true
    decomposer_sessions_fresh: true
    composer_sessions_fresh: true
    session_resume_used: false

The operator ran in a fresh remote session whose container held an empty clone (no local commits); all state was fetched from the canonical branch. Each Decomposer invocation (D0, D1) and the Composer invocation (C0) was a separate, freshly spawned subagent model instance with an empty context — no `--continue`, no `--resume`, no shared conversation IDs, no transcript copying. The only information crossing role boundaries was the set of serialized JSON artifacts under `.creator-zero/experiment-3/` (task.json, inherited-state.json, repo-facts.json, unresolved-round-0.json, composer-contract.json, composer-round-0.json) plus read-only access to the canonical repository files those artifacts name. D0/D1 and C0 had no Bash access (no execution); C0 was additionally barred from reading the target files themselves. The operator injected no solution reasoning into any prompt: Decomposer/Composer prompts contained only role definitions, artifact paths, schemas, and the experiment's hard constraints, all copied from the experiment protocol.

## 2. Inherited state

Reconstruction started exclusively from `.creator-zero/state/experiment-2.json` (M2) at canonical commit `db51bb3` on `claude/verify-test-spec-alignment-56lixf`. Successfully reconstructed and deterministically reverified in this session:

- suite state: 12/12 green (unittest; pytest is not installed — recorded as an environment fact, not a gap);
- differential harness: `ALL total=20689 pass=20689 fail=0 mutated=0` — exact reproduction of E1-D3/E2 reverification;
- probes: 24/24 — exact reproduction of E1-D4;
- E2 decisions E2-D1..E2-D4 (test-defect correction, solver held) as recorded claims;
- the M2 `unresolved_questions` entry noting R6 is asserted by only one 2-job test.

    INHERITANCE_GAP: none

No older historical artifacts were required: Experiment 1 reports, alternate branches, and prior transcripts were not read. The M2 manifest plus the canonical repository were sufficient to bootstrap the entire run.

## 3. Task interpretation

Exact R6 verification question: **does the 12-test suite at db51bb3 fail at least one test under every implementation that preserves R5 optimality (and R1–R4, R7, R8) but returns a non-lexicographically-minimal optimal index sequence (R6 violation) — or does some such implementation pass the whole suite?** If the latter (H1), derive the smallest regression test discriminating a correct R6 implementation from one returning a different optimal index sequence with the same total weight; `src/solver.py` untouchable absent new defect evidence.

## 4. Decomposer round 0

D0 produced 7 unresolved distinctions (none inherited-resolved) and 6 inheritance-resolved claims:

- **Q1** — does any R5-preserving, R6-violating implementation pass all 12 tests? (executable suite runs against verified surrogates)
- **Q2** — what violation class must be discriminated, and is each surrogate provably R5-satisfying/R6-violating? (per-surrogate oracle differential)
- **Q3** — does the test instance genuinely admit ≥ 2 optimal sequences with R6 selecting one? (exhaustive optimal-set enumeration; classic-instance tie multiplicity unknown from inheritance)
- **Q4** — is the candidate the smallest discriminating case under an explicit minimality measure? (bounded exhaustive search over smaller instances)
- **Q5** — does the test assert only spec-entailed behavior (oracle-first provenance, not solver-copied)?
- **Q6** — does the written test actually fail every surrogate and pass the canonical solver? (executed discrimination)
- **Q7** — post-mutation integrity: pre-existing tests byte-unchanged and green, differential/probes green, diff scope limited to the added test.

D0 proposed no topology and named no agents.

## 5. Composer round 0

C0 proposed a 4-node HarnessSpec (`final-harness.json`), max_depth 0, max_model_calls 6, no create primitive, can_create=false everywhere:

| Node | Primitive | Resolves |
|---|---|---|
| evidence-gap-and-derivation | test | Q1 Q2 Q3 Q4 Q5 |
| act-candidate-test | act (conditional on H1) | — (executes authorized mutation) |
| verify-candidate | verify | Q5 (recheck) Q6 Q7 |
| report | return | — (delivers verdict) |

Edges: evidence —authorize→ act; act —verify→ verify; verify —return→ report; evidence —return→ report (H0 path). Q1–Q5 deliberately co-located in one zero-write-authority deterministic locus; Q6–Q7 in one verification locus; the Composer's `why_necessary` fields argue each remaining separation is an authority boundary, not style.

## 6. Decomposer critique

D1 (fresh instance) checked each of Q1–Q7 against node authority/tools/instructions/causal position and each hard authority-separation rule. Verdict: **all required distinctions addressable; missing = []**. No authority violations found (no canonical-path writes, no self-verification, promotion reserved to the deterministic Gate). One non-blocking note: Q7 evidence is generated pre-promotion on staged copies with the Gate's byte-copy bridging to post-promotion state — judged logically sufficient, not a capability gap.

## 7. Synthesis convergence

    number of D invocations: 2 (D0, D1)
    number of C invocations: 1 (C0)
    number of synthesis rounds: 1
    closure achieved: true

## 8. Final topology

    primitives used: test, act, verify, return
    instantiated nodes: 4
    typed edges: 4 (authorize, verify, return, return)
    permissions: evidence {Read,Grep,Bash,Write→sandbox only};
                 act {Read,Grep,Bash,Write,Edit→candidate workspace only};
                 verify {Read,Grep,Bash,Write→sandbox-verify only};
                 report {Read only}
    resource bounds: max_depth=0, max_model_calls=6 (4 used), no child creators

## 9. Epistemic compression

    |Q| = 7
    |V_H| = 4
    rho_H = 4/7 ≈ 0.571

Coverage was total: all 7 distinctions were resolved by recorded deterministic artifacts (§11). Compression came from co-locating Q1–Q5 (five distinctions sharing one authority envelope: deterministic execution with zero mutation authority) and Q5–Q7 in the verifier. The compression cost nothing measurable: every resolution_condition demanded by D0 was met by executable evidence. Lower rho here reflects genuine shared authority structure, not corner-cutting.

## 10. Minimality

- **H^(−evidence-gap-and-derivation)**: Q1–Q4 unresolved; no authorization basis for mutation. Coverage lost.
- **H^(−act-candidate-test)**: the H1 branch's mandated candidate creation impossible; mutation rule unsatisfiable. Coverage lost.
- **H^(−verify-candidate)**: Q6–Q7 unresolved; Gate starved of its sole input; topology with an act node but no verify primitive is also rejected by the deterministic boundary (`required_primitives_for_mutation`). Coverage lost.
- **H^(−report)**: no return locus on the H0 path (where act/verify never run). Required delivery lost.

No pair of nodes can merge without violating an authority rule (evidence+act = mutator authors its own authorization; act+verify = self-verification; evidence+verify = specifier certifies own product; verify+report fails under H0). |H| = 4 is minimal subject to Coverage(H,Q) = 1.

## 11. Evidence

- **Inherited**: M2 manifest claims (E1-D1..D9, E2-D1..D4).
- **Reverified inherited**: suite 12/12; differential 20,689/20,689 (0 mutated); probes 24/24 — re-run by operator at session start and again independently by the verify node and Gate.
- **Newly generated deterministic**: surrogate admissibility over 71,904 instances per surrogate (0 weight mismatches vs oracle; 13,754 / 37,296 R6-divergences); suite matrix — `ef_dp_backtrack` 12/12 pass (gap witness), `prefer_higher_index` 11/12; exhaustive optimal-set enumerations (classic instance: unique optimum [2,6], not tie-bearing; chosen instance: ties {[0],[1]}); bounded exhaustive minimality search with n<2 no-tie proof; candidate discrimination runs (fails both surrogates, passes canonical, 13/13).
- **Model hypotheses**: surrogate family selection and candidate-test specification — both converted into deterministic evidence by machine admissibility checks and verifier re-execution before being relied upon.
- **Verifier findings**: 9/9 checks pass, overall ACCEPT.

Truth was resolved by execution; at no point was D/C agreement treated as evidence.

## 12. Coverage verdict

    R6_COVERAGE_GAP_VERIFIED

The pre-existing suite (12 tests, all green) is passed in full by `ef_dp_backtrack`, an implementation verified to preserve R5 on 71,904 instances while returning non-lex-minimal optimal sequences on 13,754 of them. All four H1 evidence requirements from the task were demonstrated executably.

## 13. Mutation

    mutation_performed: true

- **Actor identity**: harness node `act-candidate-test`, an independent model instance holding candidate-write authority only.
- **Candidate workspace**: `.creator-zero/experiment-3/candidate/` (isolated; never canonical).
- **Exact candidate diff**: `+6/−0` lines in `tests/test_solver.py` — one added method `test_tie_break_lex_smallest_when_later_index_finishes_first` asserting `solve([(0, 2, 1), (0, 1, 1)]) == (1, [0])` (recorded at `candidate/candidate.diff`).
- **Evidence authorizing Act**: H1 verdict in `sandbox/evidence-round-0.json` (gap witness + tie enumeration + minimality + oracle-first expectation).
- **Verifier result**: ACCEPT, 9/9 checks (`sandbox-verify/verify-verdict.json`).
- **Deterministic gate result**: ACCEPT, 8/8 checks including independent re-execution of suite/differential/probes and pure-addition diff audit (`gate-decision.json`).
- **Promotion mechanism**: `gate.py` deterministic byte-copy candidate → `tests/test_solver.py`, followed by a post-promotion suite re-run (green). Rollback-by-default on any failed check.

## 14. Runtime topology fidelity

    EXACT

H_declared: evidence —authorize→ act —verify→ verify —return→ report, Gate promoting. H_executed: identical. Each of the four nodes ran as its own fresh model instance; the operator performed none of the nodes' work; the Actor wrote only in the candidate workspace; the Verifier was a distinct instance that re-executed every check; promotion was performed exclusively by the deterministic Gate script. Unlike Experiment 2 (where the parent Creator applied the canonical edit), no model session ever wrote to a canonical target file.

## 15. Authority separation

    Ctrl(operator -> canonical task mutation) = 0
    Ctrl(decomposer -> canonical task mutation) = 0
    Ctrl(composer -> canonical task mutation) = 0
    Ctrl(verifier -> canonical task mutation) = 0

Only the Actor created candidate state; only the Gate promoted. The operator authored and invoked `gate.py`, but the Gate's decision is a pure function of its eight deterministic checks — the operator supplied no epistemic input to the accept/reject outcome and never edited a target file directly. D0/D1/C0 had no Bash and no write authority beyond their single output artifacts; the Verifier's writes were confined to its own staging area.

## 16. Boundary events

One validation event: `composer-round-0.json` → `VALID` on first submission (0 rejections, `validation-events.jsonl`). No topology, action, or permission rejections occurred anywhere in the run.

## 17. Successor state

`.creator-zero/state/experiment-3.json` produced and persisted. It names the parent manifest, start/end commits, the inherited claims used and reverified, all new decisions with their evidence pointers, the final topology, the mutation record, and a recommended next task. Judged sufficient for an Experiment 4 bootstrap: every quantitative claim is reproducible from the committed harness (`differential.py`, `probes.py`, `oracle.py`), the committed surrogates and sandbox records, and the canonical suite at the end commit — no access to this session is needed.

## 18. Experiment result

    PASS

All 12 primary success criteria were met: M2-only reconstruction (no older artifacts), fresh causally separated D/C invocations communicating only through explicit artifacts, D never composed, C never redefined the task, closure in 1 round of a 3-round budget, first-pass deterministic validation, truth resolved by execution (surrogate suite runs, exhaustive enumerations), mutation confined to candidate state, executed topology EXACT to declared, promotion only by the deterministic Gate, and successor state externalized. The lineage reconstructed temporary specialized Selves — a Decomposer that only decomposed, a Composer that only composed, four harness nodes with disjoint authority envelopes — and no single model session contained the whole reasoning process: the operator never reasoned about the task, D/C never saw execution, the evidence node never wrote canonical state, and the Actor never verified itself.
