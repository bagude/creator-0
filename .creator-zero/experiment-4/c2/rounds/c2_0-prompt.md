# Role: Composer C2_0 (fresh, causally isolated, read-only)

You are a single-purpose Composer invocation for Creator C2 (generation 2)
under Creator-0 Experiment 4, working dir /home/user/creator-0. Your ONLY
job: compose the MINIMUM HarnessSpec (pure JSON) that resolves the
decomposition below. You write no files; you output the spec as text.

## Schema ground truth (READ THESE FIRST)

1. Read `.creator-zero/cz.py` — the function `validate_spec` is the exact
   deterministic validator your spec must pass. Satisfy it literally.
2. Read `.creator-zero/experiment-4/c1/final-harness.json` as a SCHEMA
   example only (its content/verdict is under challenge; do not copy its
   claims — only its structural shape: task_id, goal, nodes, edges,
   max_depth, max_model_calls, coverage_map, minimality_argument).

## Hard limits from contract K2 (violating any -> spec REJECTED)

- allowed_primitives: observe, hypothesize, test, verify, create, return.
  NOTE: "act" is NOT allowed under K2 — C2 has zero mutation authority and
  proposes no mutations. Do not emit any act node.
- allowed_relations: observe, consult, request_response, verify, authorize,
  create, return. "delegate" is NOT allowed, so every edge must have
  "transfers_authority": false.
- allowed_tools: Read, Grep, Glob, Bash, Write (each node's tools must be a
  subset; Write is only for outputs under .creator-zero/experiment-4/c2/**).
- max_depth: 0 (spec's max_depth must be 0).
- NO node may have "can_create": true (K2 max_children=0; the validator
  rejects any realized create node). Every node: "can_create": false.
- max_model_calls: must be truthful and small. C2 has 2 model calls left
  after synthesis; the spec should declare "max_model_calls": 1 and at most
  ONE node may declare execution_mode "fresh_model_invocation" — and only
  if some question truly requires irreducible judgment. Strongly prefer
  "execution_mode": "deterministic_script" for EVERY node; a decomposition
  question that is an interpretive reading can be handled inside a
  deterministic node's output as an explicitly-tagged model_judgment note
  by the executing Creator, as C1 did for its Q1.
- If ANY node has Write in tools, the spec must contain at least one node
  with primitive "verify" (contract required_primitives_for_mutation).
- Edges: every edge needs source, target, relation, requires_response,
  response_changes_parent_state, transfers_authority; non-"return" edges
  must form a DAG.
- Each node additionally declares "execution_mode":
  "deterministic_script" | "fresh_model_invocation" (custom field, allowed).

## Execution context the spec must respect

C2 itself executes every node (no children). All scripts and outputs live
under `.creator-zero/experiment-4/c2/sandbox/`. Canonical paths (src/,
tests/, docs/, .creator-zero/harness/, .creator-zero/experiment-4/c1/**)
are READ-ONLY; staged copies/shims go under c2/sandbox/. Evidence rule:
C1's records are claims — every check the verdict depends on must be
RE-EXECUTED with C2-authored code (own surrogates, own instrumentation,
own diffs). Node instructions should be concrete enough to execute
deterministically: name the input files, the checks, the output JSON path
under c2/sandbox/, and the pass/fail criterion per question. The final
node (primitive "return") compiles `.creator-zero/experiment-4/c2/evidence.json`
entries classified deterministic | model_judgment | inherited and the
verdict inputs for result.json (verdicts CONFIRM_C1 | PARTIAL_CONFIRMATION
| REFUTE_C1 | INDETERMINATE plus boolean candidate_endorsed).

## Minimality

Fewest nodes that preserve the needed causal boundaries. Grouping several
questions into one node is encouraged when they share tools, inputs, and
authority; keep verification of C2's OWN discriminating artifacts (e.g.
C2's surrogate admissibility) causally separated from the node that
authors them only if that separation is load-bearing — you may instead
have a verify node re-check C2-authored artifacts with independently
derived expectations. Include "coverage_map" mapping every Q id to >=1
node id, and a "minimality_argument".

## The decomposition to cover (every Q id must appear in coverage_map)

{
  "questions": [
    {
      "id": "Q1",
      "summary": "Does R8's runtime clause ('Runtime MUST be polynomial in len(jobs) (exhaustive subset enumeration is not acceptable)') obligate exclusion of the one named violation class, or a general degree-unspecified polynomial guarantee, and is this reading textually forced or genuinely ambiguous?",
      "why_load_bearing": "The discriminator's entire design (a fixed growth-ratio bound admitting up to degree 5) and the choice between R8_COVERAGE_GAP_VERIFIED and SPECIFICATION_AMBIGUITY both depend on this reading; C2 must re-derive it from docs/solver_spec.md itself rather than inherit C1's E7/q1_reading, since an inherited reading cannot independently corroborate C1's conclusion.",
      "resolution_criterion": "Independent line-by-line parse of R8 in docs/solver_spec.md, performed without first reading C1's decomposition.json/evidence.json Q1 conclusion, checking whether any degree bound is stated or implied anywhere else in the spec (none is). If the parenthetical is read as naming a concrete forbidden implementation class, reading=NARROW; if a substantial textual case supports a general bound, reading=AMBIGUOUS. Irreducibly requires judgment (natural-language interpretation) \u2014 must be explicitly labeled model_judgment in C2's output, not treated as mechanical."
    },
    {
      "id": "Q2",
      "summary": "Does an exponential-family surrogate that C2 constructs from scratch (not C1's sandbox files), verified output-equivalent to a spec oracle, pass all 13 canonical tests in tests/test_solver.py unmodified?",
      "why_load_bearing": "C1's H1 claim rests on a single self-authored witness (E4); if C2 cannot independently reproduce a passing exponential surrogate, or produces one a canonical test actually catches, the coverage-gap conclusion is unsupported by any evidence C2 itself controls and cannot be confirmed on C2's own authority. Covers 'missing counterexamples' for the gap-demonstration direction and grounds the 'false equivalence' question (Q6) in an independently reproduced fact.",
      "resolution_criterion": "C2 authors an exponential-family solve() with a construction distinct from C1's (different recursion/enumeration shape), checks R1/R5/R6-equivalence against an oracle on a battery of instances, stages it against tests/test_solver.py via import shim, runs `python -m unittest discover`, and records the pass/fail matrix. 13/13 pass reproduces the gap; any failure requires downgrading or refuting H1."
    },
    {
      "id": "Q3",
      "summary": "Does C1's growth-ratio discriminator (sys.settrace event counts, bound 32x per doubling) false-positive on a legitimate polynomial solve() that C2 authors with a structurally different algorithm/degree from both C1's real implementation and its O(n^3) control?",
      "why_load_bearing": "Directly probes 'overfitting to implementation structure': if the bound or event-counting method implicitly encodes assumptions about src/solver.py's specific DP shape rather than the abstract polynomial property, it doesn't test R8 in general \u2014 it tests conformance to one implementation's call-graph shape, and would wrongly fail future legitimate refactors.",
      "resolution_criterion": "C2 authors at least one legitimate polynomial reimplementation using a structurally distinct approach (e.g. different data structure, no bisect, different degree such as O(n^2) or O(n^4)) preserving R1-R7 semantics, and runs the candidate's discriminator logic against it at the recorded n-schedule. Required: ratio <= 32 at every doubling for all such variants; any exceedance is a confirmed, executable false positive."
    },
    {
      "id": "Q4",
      "summary": "Does the discriminator fail to flag plausible evasive super-polynomial regressions \u2014 a low-base exponential (growth base near 1, e.g. 1.01^n-1.05^n), or work executed inside C-level/builtin calls invisible to sys.settrace?",
      "why_load_bearing": "Covers 'weak surrogate construction' and 'missing counterexamples': C1's own E10 already names these as residual risks but dismisses them by assertion (model_judgment) rather than by constructing and executing them; a claim of 'justified discriminator' cannot stand while known evasion shapes remain untested.",
      "resolution_criterion": "C2 builds (a) a low-base exponential surrogate (e.g. base 1.02) and runs the candidate's exact n-schedule (8,16,32,64) against it to see whether the fixed 32x/doubling bound catches or misses it at those specific sample points; (b) a surrogate whose extra combinatorial cost is dispatched through a C-accelerated builtin (e.g. bulk itertools consumption) to check whether trace-event counts still detect the blowup. Any miss is an executable counterexample to sufficiency, not a hypothetical one."
    },
    {
      "id": "Q5",
      "summary": "Are the growth-ratio measurements (op-count-per-doubling at 4 sample points) and C1's separate wall-clock r8_scaling claim (E3) reproducible across repeated runs, or noisy enough that the 32x bound or the E3 finding could flip on a different run?",
      "why_load_bearing": "Directly probes 'noisy timing inference': even a non-wall-clock metric can vary with interpreter/GC/tracer state, and a claim resting on only 4 discrete n values could be an unsupported extrapolation if those measurements aren't stable; if E3 or the bound is noise-sensitive, both the probe-insufficiency claim and the discriminator-justification claim weaken.",
      "resolution_criterion": "Re-run the real implementation's op-count measurement and the constructed candidate test at least 5 times each and confirm counts/ratios are exact or within negligible tolerance (a deterministic algorithm's settrace count should be bit-identical per run). Separately re-run probes.py's r8_scaling wall-clock timings 5x under normal load and confirm the ok=True/False outcome doesn't flip. Stable results resolve 'not noisy'; any outcome-changing variance resolves 'noisy' and weakens the corresponding C1 claim."
    },
    {
      "id": "Q6",
      "summary": "Even granting 14/14 tests passing and C1's ACCEPT verdict, does this constitute genuine protection against future R8-runtime regressions in general, or only against the specific violation shapes C1 (and C2) happened to construct?",
      "why_load_bearing": "This is the central question the challenge task exists to force: 'protected' is a claim about the space of future regressions, while 'passes constructed surrogates' is a claim about specific tested instances. Conflating them is the named false-equivalence risk, and it directly gates whether the verdict is CONFIRM_C1 vs PARTIAL_CONFIRMATION regardless of how Q1-Q5 resolve.",
      "resolution_criterion": "Enumerate the complete set of known-uncaught or marginal violation shapes surfaced by Q1/Q3/Q4/Q5 plus C1's own E10 residual-risk list. Judge whether this residual set is narrow enough that 'protected' fairly characterizes the candidate test's effect (supports CONFIRM_C1/candidate_endorsed=true) or broad/plausible enough that it does not (forces PARTIAL_CONFIRMATION or candidate_endorsed=false). Irreducibly requires judgment \u2014 no script decides how much residual risk is acceptable; must be explicitly flagged as such."
    },
    {
      "id": "Q7",
      "summary": "Did C1's act node stay strictly within its declared write authority (candidate/ only, pure addition, canonical paths untouched), and was the mutation authorized by the evidence verdict rather than performed speculatively or across a masked anomaly?",
      "why_load_bearing": "Covers 'unjustified mutation' and 'authority violations' directly: the harness's legitimacy rests entirely on the authorize\u2192act\u2192verify chain holding; a canonical-path write, a non-pure diff, mutation despite an unmet authorization precondition, or a self-authored 'fix' to the verifier's own rejection criteria would disqualify the candidate regardless of its technical merit.",
      "resolution_criterion": "Run `git diff -- src/ tests/ docs/` against pre-C1 HEAD and confirm empty; diff .creator-zero/experiment-4/c1/candidate/test_solver.py against tests/test_solver.py and confirm exactly one added method with zero other lines altered; read execution-ledger.jsonl in full and confirm act-candidate-test's node_start is causally after an evidence-and-discriminator node_end recording verdict=R8_COVERAGE_GAP_VERIFIED and justified=true; specifically examine the ledger's recorded 'verify checker initially REJECTed... checker pattern corrected... re-run ACCEPT' anomaly and determine whether the correction was applied by a locus independent of the candidate's author \u2014 flag if not, even if the final numeric checks still hold."
    },
    {
      "id": "Q8",
      "summary": "Is verify-candidate's ACCEPT genuinely independent of evidence-and-discriminator and act-candidate-test, given that C1 is the single authoring locus for all four nodes' scripts?",
      "why_load_bearing": "Probes 'verifier dependence' directly \u2014 C1's own topology_note flags this exact risk. A verifier that reuses the evidence node's bound value, tooling, or unstated assumptions without re-deriving them is not a causal check; its ACCEPT would then be C1 re-confirming itself rather than independent evidence, which C2's own verdict cannot rely on without re-derivation.",
      "resolution_criterion": "Inspect .creator-zero/experiment-4/c1/sandbox-verify/ (exp_mask.py, poly_alt.py, run_verify.py) to confirm no import of evidence-sandbox modules and that the bound (32) and surrogate constructions differ in actual code from evidence-and-discriminator's, not just in name. Independently of trusting either, C2 constructs its own from-scratch surrogates and bound derivation (per Q2-Q4) and checks whether C2's own from-scratch result agrees with C1's stated ACCEPT. Agreement between C2's independent check and C1's claim is the operative confirmation; C1's self-reported 'independence' language is not."
    },
    {
      "id": "Q9",
      "summary": "Is the candidate test (test_r8_operation_growth_is_polynomial) deterministic and non-flaky when run repeatedly against the unmodified canonical src/solver.py?",
      "why_load_bearing": "A candidate whose pass/fail outcome varies across runs on the non-regressed canonical implementation would itself violate the suite's 'protected: do not weaken' contract by introducing spurious failures, independent of whether the underlying discriminator concept is sound \u2014 this is a separate, mechanical disqualifier from Q1-Q8.",
      "resolution_criterion": "Run the candidate test method at least 10 consecutive times (staged with canonical src/solver.py) via `python -m unittest`, ideally interleaved with artificial load, and confirm 10/10 pass with no sys.settrace/sys.gettrace interaction failures (e.g. conflicts with coverage tools or other installed tracers). Any failure or exception across the 10 runs resolves this negatively."
    }
  ]
}

## Output

PURE JSON HarnessSpec only. No markdown fences, no prose before or after.
