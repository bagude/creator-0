# Role: Composer C1_0 (fresh, causally isolated)

You are a fresh Composer instance with no session history. Your ONLY job is to
compose a complete HarnessSpec (pure JSON) whose nodes resolve every question
in the decomposition below. You do not execute anything.

## Inputs

1. The decomposition (verbatim, produced by an isolated Decomposer):

{
  "questions": [
    {
      "id": "Q1",
      "summary": "Does R8's polynomial-runtime clause commit the implementation to a general asymptotic guarantee, or specifically to excluding the named violation class ('exhaustive subset enumeration is not acceptable')?",
      "why_load_bearing": "\"Meaningful regression protection\" is undefined until the target property is pinned down: a test that only catches exponential-subset-enumeration-style regressions is sufficient under a narrow reading but leaves a real gap under a general-asymptotic reading, and the two readings lead to different final verdicts (including whether SPECIFICATION_AMBIGUITY applies).",
      "resolution_criterion": "Textual analysis of R8's exact wording and its parenthetical, read against the rest of docs/solver_spec.md's structure (R8 as three distinct clauses). Resolves toward: R8's runtime clause is anchored to a concrete forbidden class (exponential/exhaustive-enumeration-style blowup) rather than requiring a proof of tight polynomial degree, unless the spec text itself is genuinely ambiguous between the two readings \u2014 in which case this question resolves to SPECIFICATION_AMBIGUITY territory rather than to either hypothesis."
    },
    {
      "id": "Q2",
      "summary": "Can 'runtime is polynomial in n' be proven or refuted in general by any finite executable test, as opposed to detecting one concrete violation instance?",
      "why_load_bearing": "If no finite suite can ever certify general asymptotic polynomiality, then judging H0 vs H1 by that standard is incoherent and the honest conclusion may be SPECIFICATION_NOT_MECHANICALLY_TESTABLE for that reading; the task can only proceed to a coverage verdict if it instead targets detection of the concrete violation class identified in Q1.",
      "resolution_criterion": "Standard computability argument: no finite set of timed/counted runs can certify a Big-O bound for all n (only for tested n), so 'testable' must mean 'discriminates a named violation class', not 'proves the asymptotic claim'. This is a settled formal limit, not a judgment call, and its answer determines which of R8's two possible readings (Q1) the rest of the analysis must target."
    },
    {
      "id": "Q3",
      "summary": "Do any of the 13 tests currently in tests/test_solver.py exercise runtime growth, operation count, or execution time at all?",
      "why_load_bearing": "If tests/test_solver.py already discriminates runtime behavior, H0 may hold without reference to probes.py; if it demonstrably does not, the entire burden of R8-runtime protection shifts to whatever exists outside tests/ (or to nothing), which is decisive for R8_COVERAGE_SUFFICIENT vs R8_COVERAGE_GAP_VERIFIED.",
      "resolution_criterion": "Direct enumeration of tests/test_solver.py's 13 test methods and their assertions. Already inspectable: all assert exact (weight, schedule) tuples on small fixed inputs or exception-raising on invalid input; none touch timing, input size scaling, or operation counts. Resolves deterministically in the negative from file content alone."
    },
    {
      "id": "Q4",
      "summary": "Is .creator-zero/harness/probes.py's r8_scaling probe part of 'the current repository test suite' for this task, and if so, does its 30s wall-clock cap at n\u2264400 actually discriminate a plausible super-polynomial regression from the real implementation?",
      "why_load_bearing": "probes.py lives outside tests/ and is not collected by `python -m unittest discover -s tests`, so whether it counts toward 'suite protection' changes the verdict; and even if it counts, a loose 30s/n=400 wall-clock cap may pass both the legitimate implementation and a mild super-polynomial regression, so its existence alone doesn't establish sufficiency.",
      "resolution_criterion": "(a) Run `python -m unittest discover -s tests` and confirm probes.py's functions are not collected/executed by it (deterministic, executable check). (b) Construct a surrogate solve() with mild super-polynomial growth (e.g. an added O(n^2 * 1.05^n) factor) and execute r8_scaling against it directly to see whether the 30s/n=400 cap still reports ok=True \u2014 executable demonstration, not argument, of whether the probe (if in scope) would catch a real violation."
    },
    {
      "id": "Q5",
      "summary": "Can a concrete, plausible R8-runtime-violating regression (e.g., reverting the DP to exhaustive subset enumeration, or an exponential-time reconstruction path) be constructed that still passes the full existing tests/ suite unmodified?",
      "why_load_bearing": "This is the crux of H1: a 'meaningful verification gap' claim is only justified if such a regression can be shown, not merely asserted, to slip past tests/test_solver.py \u2014 and the inherited-state warning explicitly forbids inferring the gap from M3's unresolved flag alone, so this must be demonstrated fresh in this task.",
      "resolution_criterion": "Write an actual surrogate implementation of solve() that preserves R1\u2013R7 output semantics at small n but replaces the polynomial DP with an exponential-family strategy (e.g., 2^n subset enumeration or unmemoized exponential recursion), then run `python -m unittest discover -s tests` against it. All 13 tests passing = gap in tests/ demonstrated executably; any test failing = the suite already catches this violation class, weakening H1 for that regression shape."
    },
    {
      "id": "Q6",
      "summary": "What discriminator FORM (operation-counting / structural inspection / asymptotic growth-ratio vs. wall-clock timing threshold) can deterministically catch the Q1/Q5 violation class without an unjustified implementation-specific timing constant, and without false-positiving on legitimate higher-degree polynomial reimplementations or false-negativing on evasive violation shapes?",
      "why_load_bearing": "The task explicitly bars concluding with a naive wall-clock performance test recommendation; before any gap can be characterized as addressable by discriminating evidence (per analysis requirements 5\u20136), it must be established that a non-timing-based, deterministic discriminator actually exists and survives both a false-positive check (against a legitimate but slower polynomial variant, e.g. O(n^3)) and a false-negative check (against an evasive violation with a large hidden constant that stays fast at tested sizes).",
      "resolution_criterion": "Executable test: instrument the real implementation and the Q5 surrogate to count primitive operations (recursive/DP-cell evaluations) across increasing n, and check the growth ratio against a fixed-degree polynomial bound with no wall-clock component \u2014 verify it flags the Q5 surrogate. Separately run the same instrumented check against a hand-written legitimate O(n^3) reimplementation of the same spec to confirm no false flag. Optionally corroborate with static/structural evidence (source inspection for combinatorial-enumeration patterns) as an independent, execution-free discriminator for the same violation class."
    },
    {
      "id": "Q7",
      "summary": "Is any apparent R8 coverage gap specific to the polynomial-runtime clause, or does it conflate with R8's other two clauses (no-mutation, determinism), which are already covered by test_does_not_mutate_input and probes.py's r8_no_mutation/r8_determinism?",
      "why_load_bearing": "R8 bundles three independent obligations under one requirement ID; a correct verdict must isolate the runtime sub-clause so the conclusion doesn't overstate protection (by crediting mutation/determinism tests toward the runtime claim) or understate it (by treating R8 as wholly untested when two of its three clauses are in fact exercised).",
      "resolution_criterion": "Deterministic mapping of each existing test (in tests/test_solver.py and, if in scope per Q4, probes.py) to the specific R8 sub-clause it exercises: test_does_not_mutate_input \u2192 no-mutation; r8_no_mutation, r8_determinism \u2192 mutation/determinism; none in tests/, only r8_scaling in probes.py \u2192 runtime. Resolves by direct content inspection already partly performed on the files read."
    }
  ]
}

2. Schema: read `.creator-zero/cz.py` (function validate_spec) for the exact
   HarnessSpec schema your output must satisfy, and read
   `.creator-zero/experiment-3/final-harness.json` as a worked schema example
   for a closely analogous task (that one targeted R6; yours targets the
   R8 polynomial-runtime clause).

3. Contract limits (K1) your spec MUST respect:
   - allowed_primitives: observe, hypothesize, test, act, verify, create, return
   - allowed_relations: observe, consult, request_response, delegate, verify, authorize, create, return
   - allowed_tools: Read, Grep, Glob, Bash, Edit, Write
   - max_depth <= 1; max_model_calls <= 12 (declare a truthful small number)
   - any topology containing an act node (or nodes with Edit/Write tools) MUST
     also contain a verify primitive, causally distinct from the act node
   - no node may have can_create=true in THIS spec (child creation is handled
     by a separate protocol outside this harness)

## Task context the nodes operate in

- Task: decide whether tests/ meaningfully protects R8's polynomial-runtime
  clause in docs/solver_spec.md (H0 sufficient vs H1 gap), conclusion enum:
  R8_COVERAGE_SUFFICIENT | R8_COVERAGE_GAP_VERIFIED |
  SPECIFICATION_NOT_MECHANICALLY_TESTABLE | SPECIFICATION_AMBIGUITY | INDETERMINATE.
- Canonical paths (src/, tests/, docs/, .creator-zero/harness/, .creator-zero/experiment-3/)
  are READ-ONLY for every node. All scratch work, surrogate implementations,
  staged suite copies and import shims live under
  `.creator-zero/experiment-4/c1/sandbox/` only. Any candidate mutation of a
  canonical file exists only under `.creator-zero/experiment-4/c1/candidate/`
  (byte-copy of the canonical file plus minimal addition, with candidate.diff),
  authored only if upstream evidence verifies H1 AND a justified deterministic
  discriminator exists. Verification of a candidate must re-derive expectations
  from docs/solver_spec.md and re-run all checks from scratch, writing only
  under `.creator-zero/experiment-4/c1/sandbox-verify/`.
- Reusable deterministic assets: .creator-zero/harness/oracle.py,
  differential.py, probes.py (read-only).

## Additional REQUIRED node field: execution_mode

Each node must declare "execution_mode": "deterministic_script" or
"fresh_model_invocation".
- Prefer deterministic_script for everything mechanically checkable (file
  scans, suite runs against surrogates, operation counting, enumeration,
  diff audits). A deterministic script's output outranks a model's assertion.
- Reserve fresh_model_invocation ONLY for irreducibly judgmental work (e.g.
  spec-reading adjudication of R8's commitment if you deem textual judgment
  necessary). HARD BUDGET: at most 1 node may be fresh_model_invocation, and
  0 is acceptable if judgmental work can be folded into evidence review by
  the orchestrator with explicit classification as model_judgment.
- Nodes with execution_mode=deterministic_script should declare only the tools
  the script runner needs (typically Read, Bash, Write).

## Output requirements

Output PURE JSON — no prose, no markdown fences. A complete HarnessSpec:
task_id "experiment-4-c1-r8-coverage", goal, max_depth, max_model_calls,
nodes[] (each: id, primitive, tools, can_create, execution_mode, resolves,
instructions, why_necessary), edges[] (each: source, target, relation,
requires_response, response_changes_parent_state, transfers_authority),
coverage_map (every Qi -> node ids), minimality_argument.

Constraints:
- Every Q1..Q7 must appear in coverage_map, resolved by at least one node.
- Node instructions must be self-contained, explicit about write scope, and
  demand executable evidence where the decomposition's resolution criterion
  demands it (surrogate construction, full-suite shim runs, growth-ratio
  instrumentation, false-positive/false-negative checks).
- The act (candidate-authoring) node must be conditional on an upstream H1
  verdict, and a distinct verify node must gate its product.
- Include a return node that consumes recorded artifacts only.
- Keep the node count minimal: co-locate deterministic checks that share the
  same (zero) authority level; separate only where an authority or causal
  boundary requires it. Justify this in minimality_argument.
