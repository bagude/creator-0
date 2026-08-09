# Creator-0 Experiment 6 — Latent Topology Discovery + Calibrated Topology Economics Report

**Result: `LATENT_TOPOLOGY_ECONOMICS_FAIL`** under the frozen thresholds —
with the *discovery and selection* hypotheses (H1, H2) clearly supported
and the *economics and execution-conformance* hypotheses (H3, H4, H5)
refuted by the measured record. Sections 15–17 and 21–22 carry the
mechanisms; section 28 states the verdict precisely.

## 1. Base lineage

- Base: `4184611a2a3cd2e5edd985de3f861a9cb0501246`
  (branch `claude/new-session-aljqd2`; Experiment 5
  `ENDOGENOUS_TOPOLOGY_PASS`; Topology Theory upgrade
  `TOPOLOGY_THEORY_SELF_MODIFICATION_PASS`).
- Hash-pinned in `base-state.json`: promoted `theta-v1`
  (sha256:f7e38eb7…), topology-theory state manifest, Formal Semantics
  Kernel tree, Experiment 5 state, utility config (λ=1, μ=1, ν=2),
  fresh launcher v0.2, root contract, protected-law source.
- All prior experiment artifacts immutable; verified by
  `git diff --diff-filter=MD` against the base commit: **0 mutations**.

## 2. Preregistration

Frozen at commit `861dc8e` before any scored execution:
task bank, private labels, verifiers, salted label commitments
(`commitments.json`), randomization + shadow policy
(`randomization.json`), utility operationalization, thresholds, negative
controls, blinding patterns, stage-scoring rules (`preregistration.md`,
`utility-operationalization.md`). A second freeze point (`3d19511`)
committed every S1–S5 artifact — distinctions, abductions, candidates,
frozen prediction hashes, validations, rankings, selections — **before
any S6 realization**.

## 3. Task-bank construction

20 primary trials, 4 per class, 5 classes, ≥2 surface domains per class
(13 distinct domains overall); class-to-trial-id assignment shuffled
under seed `creator-0-experiment-6-bank-v1`. Every ground truth computed
programmatically and frozen (`tools/gen_bank.py`). Two pilot tasks
(p-01, p-02) disjoint from the primary bank.

## 4. Blinding

Public packages contain only raw task artifacts. The frozen scanner
enforces label-leak patterns workspace-wide and topology-cue patterns
(`requires_isolation`, `child`, `isolat*`, `clean-room`, `verifier`,
`independent*`, `counterexample`, `decompos*`, `adversar*`, `topolog*`,
`local*`, `fresh`, `session`, spawn vocabulary, `condition a/b`) over
every package. All 22 packages scanned PASS at generation and again at
every workspace build. Private labels never entered any workspace; the
negative control NC1 shows an injected label is caught. One
false-positive class was found mid-run and exempted: files authored by
*already-blinded* sessions (a session's own phrase "ground truth" in
`distinctions.json` tripped the label-leak set on trial t03). Blinding
itself was never violated: sessions cannot leak labels they never saw.

## 5. Latent classes

L0 LOCAL, L1 ISOLATION, L2 COUNTEREXAMPLE, L3 ALTERNATIVE_DECOMPOSITION,
L4 SPECIALIZED_VERIFICATION — operationalized through evidence
*admissibility conditions* in the task's own requirements (authorship
without access, non-author search, enumeration without access to the
first, method-disjoint re-derivation), never through topology
instructions. One ISOLATION trial's ground truth is REPRODUCES so the
class is not answer-degenerate.

## 6. Raw-task distinction inference (S1)

One fresh blinded session per trial produced a typed DistinctionSpec
(closed schema, feature booleans inferred from raw semantics — no
deterministic preprocessor inserted any feature) plus per-family value
estimates. All 20 sessions produced valid documents; all inference
ledgers refine the compiled inference harness; all launches fresh and
stream-confirmed.

**Scores:** critical-distinction recall mean **0.975** (18/20 trials at
1.0; two at 0.75); **0 spurious** distinctions across all 20 trials.
Threshold ≥ 0.75: **met**.

## 7. Principle abduction (S2)

Deterministic `abduce()` over promoted theta-v1; ordered applicability =
feature-matched distinction count desc, id asc (frozen). Primary
expected principle top-1 rate 0.25, **top-2 rate 0.95** (19/20;
threshold ≥ 0.75 **met**), expected-set recall **1.0**. Top-1 misses are
structural: sessions typically emit more locally-resolvable distinctions
than isolation-requiring ones, so P-LOCALITY outranks P-INDEPENDENCE by
count on non-LOCAL tasks — an ordering artifact worth revising in
Experiment 7, not an abduction failure (the expected principle was
abduced as applicable in 20/20).

## 8. Candidate generation (S3)

Closed template grammar (local, local-independent-verify, isolated-child,
branching), 3–4 candidates per trial, minimality order, model value
estimates attached as serialized typed input, cost deterministic from
call structure. Candidate coverage: a family structurally capable of the
labeled causal shape was generated and formally valid in **20/20**
trials.

## 9. Formal candidate rejection (S5a)

All 60 generated candidates passed the 11-check validation (schema,
HarnessSpec, LTS compilation, reachability, authority, attenuation,
budget, freshness feasibility, proposal observability, artifact identity,
protected laws); none needed rejection — the closed grammar emits
admissible-by-construction specs. The rejection path itself is exercised
and proven live by negative control NC6 (unreachable evidence path →
FORMALLY_REJECTED).

## 10. Frozen predictions (S4)

Falsifier-complete predictions frozen for every candidate with immutable
`predictions_hash` (artifact-id of the canonical serialization), all
committed at `3d19511` before any realization. NC3 proves a post-hoc
edit raises `PREDICTION_HASH_FAIL`. Zero hash mismatches occurred in
evaluation.

## 11. Predicted utility

`U_hat = ΔE − 1.0·C − 1.0·R − 2.0·G`, components per the frozen
operationalization (ΔE/R/G model-estimated by the blinded session; C
deterministic: local 0.125, local-iv 0.25, isolated-child/branching
0.375). Ranking deterministic with the promoted tie-break.

## 12. Selected topology

| class | selections |
|---|---|
| LOCAL | local ×4 |
| ISOLATION | isolated-child ×4 |
| COUNTEREXAMPLE | isolated-child ×4 |
| ALTERNATIVE_DECOMPOSITION | isolated-child ×4 |
| SPECIALIZED_VERIFICATION | isolated-child ×3, local-independent-verify ×1 |

Selection occurred before realization in 20/20 (enforced and committed).

## 13. Primary execution (S6)

Every realized topology ran through the frozen fresh launcher v0.2:
20 exec sessions, 16 child sessions, 1 examiner session (primaries) — all
with sanitized environments, explicit fresh identities, and
stream-confirmed session ids. Children: attenuated contracts within
K-E6-child-max (21/21 validations PASS across primaries and shadows), compiled harnesses, contained
input manifests, observable propose of the full bundle. Merged trial
ledgers checked with `require_completion=True`: 18/20 PASS; t09 and
t10 INDETERMINATE from session-authored ledger defects (an invented
label; a defective event stream). Child-ledger refinement: 12/16 PASS;
t09/t10 FAIL, t18/t19 INDETERMINATE (nonconforming or missing child
ledgers) — every defect recorded as a formal failure in the trial's
governance component.

## 14. Observed utility (S7)

Operationalized per the frozen document: ΔE = fraction of task evidence
requirements satisfied with admissible evidence (deterministic
verifiers), C = sessions/8, R = duplicate-evidence fraction, G = 0.25 ×
formal failures. R_sat = 1.0 in 14/20 trials. Class means (observed
utility of the selected topology): LOCAL 0.875, ISOLATION 0.29,
COUNTEREXAMPLE −0.02, SPECIALIZED_VERIFICATION 0.09,
ALTERNATIVE_DECOMPOSITION −0.63.

## 15. Calibration

**Utility MAE 0.484 (threshold ≤ 0.25: MISSED), RMSE 0.708.**
Component MAE: ΔE 0.218, cost **0.000**, redundancy 0.081, governance
0.138. Nine trials calibrate within 0.2 (seven ≤ 0.07); the tail is
driven by (a) over-optimistic ΔE for over-structured selections whose
extra path failed an admissibility condition (mistyped roles), (b)
unpredicted governance failures (ν=2 doubles every 0.25 miss), and
(c) unpredicted redundancy when the child duplicated a parent that
already sufficed. Deterministic cost prediction was exact everywhere.

## 16. Shadow topologies

10 preregistered runner-up shadows (2 per class, 50%), all CONTROL_ONLY
in fresh workspaces with fresh sessions (10 exec + 5 child + 2 examiner
launches), no primary child-output reuse, full formal governance
(refinement PASS 10/10, freshness PASS 17/17 shadow launches). Branching
shadows decided at run time: DO_NOT_CREATE on both LOCAL tasks, CREATE
on all others — the deferred decision again tracked the latent classes.

## 17. Regret

**Mean 0.242 (threshold ≤ 0.15: MISSED); median 0.0; max 1.333.**
Six of ten shadow pairs show zero regret. Per class: LOCAL 0.0,
SPECIALIZED_VERIFICATION 0.0, ISOLATION 0.167, COUNTEREXAMPLE 0.375,
ALTERNATIVE_DECOMPOSITION 0.667. Mechanisms: t08/t11 — the cheaper
independent examiner satisfied the non-author-search admissibility at
lower cost than the selected isolated child (regret 0.125/0.625);
t07/t09 — the primary's own execution failures (governance flags; a
role-typing cascade) let a cleaner shadow win. Predicted-vs-observed
ranking agreement on shadow pairs: 0.6.

## 18. Topology correctness

**0.875 (threshold ≥ 0.75: MET)** — 15/20 TOPOLOGY_CORRECT, 5/20
TOPOLOGY_PARTIAL, 0 INCORRECT, judged on causal features (child
presence, clean-room manifest, declared role, examiner path), not graph
identity. All four ALTERNATIVE_DECOMPOSITION trials are PARTIAL for the
same reason: the exec sessions realized an isolated child but typed its
role `clean_room_implementer`/`independent_verifier` instead of
`independent_decomposer`; one SPECIALIZED_VERIFICATION trial (t14)
likewise. The causal *shape* was right in 20/20; the *role typing* of
the distinct path failed in 5.

## 19. Distinction-quality score

Recall mean 0.975; MATCH 38/40 criticals, PARTIAL 2, MISS 0; spurious 0.
The blinded sessions reliably recovered both the substantive unresolved
question and the admissibility/contamination structure from raw
semantics — the core latent-discovery claim of the experiment.

## 20. Principle-abduction score

Top-1 0.25, top-2 0.95, expected-set recall 1.0. See §7 for the ordering
artifact behind the low top-1.

## 21. Failure taxonomy

| tag | trials |
|---|---|
| S4_PREDICTION_FAIL | 11 |
| S6_RUNTIME_FAIL / FORMAL_GOVERNANCE_FAIL | 8 |
| S2_PRINCIPLE_FAIL | 1 (t07) |
| S1_DISTINCTION_FAIL, S3_GENERATION_FAIL, S5_RANKING_FAIL, S7_OBSERVATION_FAIL | 0 |

The zero S5 count is exact: whenever a capable candidate existed (all 20
trials), the realized topology was never INCORRECT.

## 22. Formal governance

79/79 sessions fresh and stream-confirmed; 0 freshness failures; 0
attenuation failures; 0 hidden children; 0 authority escalations; exact
artifact identity in force everywhere. **8 trials nonetheless carry
formal failures** under the frozen counting: 4 ToolSearch-only
tool-envelope flags (the harness's schema-loading meta-tool, which
grants no read/write/spawn capability, appeared in session logs outside
the granted Read+Write set), and 4 instrumentation nonconformances
(t10's exec session invented ledger label `record`; t09's child ledger
defective; t18/t19 children wrote nonconforming/missing ledgers). The
frozen rule counts all of these; the distinction between
capability-bearing violations (zero observed) and conformance defects
(eight) is analysis, not scoring.

## 23. Negative controls

9/9 reproduced deterministically (`controls/negative-controls.json`):
BLINDING_FAIL, INVALID_TOPOLOGY_HYPOTHESIS, PREDICTION_HASH_FAIL,
distinct exact artifact ids under basename collision, FRESHNESS_FAIL,
FORMALLY_REJECTED, ATTENUATION_FAIL, TOPOLOGY_DECISION_VIOLATION,
COMPLETION_FAIL.

## 24. Historical immutability

`git diff --diff-filter=MD <base> HEAD` over experiments 3/4/4C/5, state,
contracts, the formal kernel, topology-theory, and `cz.py`: **0 modified
or deleted files**. All 193 pre-existing deterministic tests remain
green. The canonical theory store was never written.

## 25. Theory evidence emitted

264 prediction-specific evidence events
(`theory-evidence-events.jsonl`), emitted by the promoted falsification
machinery; no promotion called, no theta-v2, no canonical principle
touched. Headlines for Experiment 7:

- **P-INDEPENDENCE**: 27 SUPPORT / 15 FALSIFY — supported where the
  isolated path was admissibility-required (ISOLATION), falsified where
  the child duplicated a sufficient parent (COUNTEREXAMPLE/SV trials
  whose worker already carried the evidence). The principle is too
  coarse: it does not distinguish *clean-room authorship*, *non-author
  search*, *independent decomposition*, and *method-disjoint
  verification* — the four admissibility kinds this experiment separated.
  Candidate revision: SPLIT.
- **P-LOCALITY**: 55 SUPPORT / 31 FALSIFY — the falsifications are
  resolves-predictions on distinctions the local path could not
  admissibly settle; evidence for feature-conditional scoping.
- **P-AUTHORITY-SEPARATION**: 54 SUPPORT / 6 FALSIFY — the falsifications
  are exactly the 8 conformance-defect trials' authority-envelope
  predictions.
- **P-MINIMALITY**: 30 SUPPORT, 0 FALSIFY — every zero-regret shadow pair
  and every duplicate-child redundancy penalty is minimality evidence;
  the regret table is a direct measurement of its claim.

## 26. Known limitations

1. N=20 primary trials; no population-level calibration claim
   (preregistered).
2. The distinction/principle scores rest on frozen regex matching against
   session prose; t07's E-A miss shows the patterns can under-credit
   valid phrasings.
3. The guard's tool-envelope rule cannot distinguish harness-injected
   meta-tools from capability-bearing tools; 4 of 8 governance-failing
   trials are ToolSearch-only.
4. The role vocabulary (4 roles) is the interface between the worker and
   the verifier's admissibility rules; the ALT-D failures show the
   mapping "second enumeration without access" → `independent_decomposer`
   was not reliably made by blinded workers. Whether that is a protocol
   readability defect or a genuine capability gap is not separable at
   this N.
5. Value estimates came from the S1 session with a general prior, not
   from per-family experience; the observed over-optimism for isolated
   children is partly a cold-start artifact.
6. Orchestration/instrumentation fixes were made after the freeze (pilot
   label table, blind-output scan exemption, non-strict parsing, child
   deliverable-name normalization); none changed tasks, labels,
   thresholds, patterns, weights, or scoring rules (all enumerated in
   `state/experiment-6.json`).
7. Shadow coverage is runner-up-only; regret is bounded regret over
   executed alternatives, not global optimality.

## 27. Commit hashes

- Base: `4184611a2a3cd2e5edd985de3f861a9cb0501246`
- Preregistration freeze: `861dc8e91085b90a1ab35d9dcbe33abd4718cca8`
- Primary selection freeze (S1–S5 before any S6): `3d19511`
- Final: the commit introducing this report and
  `state/experiment-6.json` (branch `claude/new-session-ltyh1o`).

## 28. Result

**`LATENT_TOPOLOGY_ECONOMICS_FAIL`** under the frozen composite rule
(PARTIAL requires zero formal governance failures; 8 trials carry them).
Threshold detail: topology correctness 0.875 ✓, distinction recall
0.975 ✓, principle top-2 0.95 ✓, trial counts ✓, historical mutations
0 ✓, blinding intact ✓, predictions frozen before execution ✓, zero
hidden children ✓, negative controls 9/9 ✓ — utility MAE 0.484 ✗
(≤ 0.25), mean regret 0.242 ✗ (≤ 0.15), governance failures 8 ✗ (= 0).

What the record supports: Creator-0 **can** infer latent topology-
relevant structure from raw task semantics, generate and formally govern
competing causal organizations, and select the causally right *shape*
before execution. What it cannot yet do, on this evidence: predict the
*economics* of its choices within the frozen tolerance (it overvalues
full isolation where a cheaper independent examiner satisfies the same
admissibility condition), type the role of the independent path
reliably, and keep its execution instrumentation defect-free. Those are
precisely the CHALLENGE/FALSIFY evidence streams Experiment 7's
theory-revision loop (`Theta_1 -> evidence -> candidate revision ->
replay -> gate -> Theta_2`) is designed to consume. No global
optimality, universal scientific taste, arbitrary-task discovery, or
theory self-improvement is claimed — and no theory promotion was
performed here.
