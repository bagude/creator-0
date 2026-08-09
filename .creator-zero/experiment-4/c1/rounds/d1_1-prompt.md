# Role: Decomposer critique D1_1 (fresh, causally isolated)

You are a fresh critique instance with no session history. You previously did
NOT produce either artifact below; treat both as foreign. Your ONLY job is to
judge whether the composed HarnessSpec genuinely covers every question in the
decomposition — i.e., that executing the spec's nodes as instructed would
produce evidence meeting each question's resolution_criterion.

## The decomposition (Q1..Q7):

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

## The composed HarnessSpec:

{
  "task_id": "experiment-4-c1-r8-coverage",
  "goal": "Resolve Q1-Q7 to decide whether tests/ meaningfully protects R8's polynomial-runtime clause in docs/solver_spec.md (H0 sufficient vs H1 gap), producing one of R8_COVERAGE_SUFFICIENT | R8_COVERAGE_GAP_VERIFIED | SPECIFICATION_NOT_MECHANICALLY_TESTABLE | SPECIFICATION_AMBIGUITY | INDETERMINATE, and, only if H1 is established by executable evidence AND a justified non-wall-clock deterministic discriminator exists, produce a minimal operation-count-based candidate regression test in the isolated candidate workspace, verified by a causally distinct locus, whose verdict feeds the deterministic Gate for promotion.",
  "max_depth": 0,
  "max_model_calls": 4,
  "nodes": [
    {
      "id": "evidence-and-discriminator",
      "primitive": "test",
      "tools": [
        "Read",
        "Grep",
        "Bash",
        "Write"
      ],
      "can_create": false,
      "execution_mode": "deterministic_script",
      "resolves": [
        "Q1",
        "Q2",
        "Q3",
        "Q4",
        "Q5",
        "Q6",
        "Q7"
      ],
      "instructions": "You have ZERO mutation authority over canonical paths: never write to src/, tests/, docs/, .creator-zero/experiment-4/c1/candidate/, or .creator-zero/experiment-4/c1/sandbox-verify/. All files you create go under .creator-zero/experiment-4/c1/sandbox/ only (mkdir -p it first). Inputs (read-only): docs/solver_spec.md (R8 clause), tests/test_solver.py, src/solver.py, .creator-zero/harness/oracle.py, .creator-zero/harness/differential.py, .creator-zero/harness/probes.py.\n\n(Q1) Extract R8's exact text from docs/solver_spec.md via Grep/Read. R8 contains three clauses: no-mutation, determinism, and 'Runtime MUST be polynomial in len(jobs)' with parenthetical '(exhaustive subset enumeration is not acceptable)'. Apply this fixed rule: if the parenthetical names a concrete forbidden implementation class, treat R8's runtime clause as targeting exclusion of that named violation class (exponential/exhaustive-subset-enumeration-style blowup), NOT a general proof of tight polynomial degree \u2014 UNLESS a careful line-by-line parse shows the sentence is genuinely read two ways, in which case set reading=AMBIGUOUS. Record the conclusion (reading=NARROW or reading=AMBIGUOUS) and its textual basis under key 'q1_reading', explicitly tagged 'classification: model_judgment' since it is an interpretive step over natural-language spec text, distinct from the mechanical checks below.\n\n(Q2) Record the standard computability argument as a fixed logical note under 'q2_note': no finite set of timed/counted executions can certify a Big-O bound for all n, only for tested n; therefore 'testable' under R8's runtime clause must mean 'discriminates the named violation class identified in q1_reading', not 'proves the asymptotic claim'. If q1_reading=AMBIGUOUS, this note still holds but the task-level conclusion trends toward SPECIFICATION_AMBIGUITY rather than a coverage verdict.\n\n(Q3) Enumerate every 'def test_' method in tests/test_solver.py (Grep + Read) and record each one's assertions in one line under 'q3_enumeration'. Confirm none reference time, timing, len(jobs) scaling, operation counts, or iteration counts; record this negative finding explicitly.\n\n(Q4a) Run `python -m unittest discover -s tests -v` and capture the full list of discovered/executed test IDs under 'q4a_discovery'. Confirm no probes.py function (r8_scaling, r8_no_mutation, r8_determinism) appears in that list \u2014 probes.py is not under tests/ and unittest discover will not collect it.\n(Q4b) In the sandbox, write a surrogate solve() (import-shim wrapping the real src/solver.py.solve but injecting a deliberate extra cost term whose wall-clock cost grows as a mild super-polynomial function of len(jobs), e.g. an added factor shaped like n^2 * c^n scaled by a documented constant so it stays fast for small n but is measurably slower by n=400, while keeping the whole run tractable, e.g. under one minute total \u2014 document the exact constant and shape chosen and why). Call .creator-zero/harness/probes.py's r8_scaling logic (n=100,200,400, 30s cap) against this surrogate via import shim, without modifying probes.py itself. Record times, ratios, and ok=True/False under 'q4b_probe_check'. If ok=True (the cap does NOT catch this mild regression), record that as executable evidence the 30s/n=400 wall-clock cap alone is not a sufficient discriminator.\n\n(Q5) In the sandbox, write a second surrogate solve() that preserves R1-R7 output semantics (validate identical rejection/acceptance behavior and identical (weight, schedule) on the instances used in tests/test_solver.py) but replaces the polynomial DP with an explicit exponential-family strategy (2^n subset enumeration, or unmemoized exponential recursion over intervals). Stage a copy of tests/ into the sandbox with an import shim substituting this surrogate for src/solver.py's solve (canonical tests/ and src/ untouched). Run `python -m unittest discover` against the staged copy and record the full pass/fail matrix under 'q5_gap_demo'. All 13 tests passing = executable evidence of an R8-runtime coverage gap in tests/ (H1-supporting); any failing test = record which, H0-supporting for that violation shape.\n\n(Q6) Build an operation-count instrumentation harness in the sandbox using Python profiling primitives (cProfile.Profile or sys.setprofile) to count function/recursive-call invocations during solve() \u2014 a wall-clock-independent proxy for primitive operations. Run it against: (i) the real src/solver.py at increasing n (e.g. 10,20,40,80,160), computing the call-count growth ratio between doublings of n; (ii) the Q5 exponential surrogate at the same n values; (iii) a third, hand-written legitimate O(n^3) reimplementation of the spec authored fresh in the sandbox (not copied from src/) to check for false positives. Define and document a fixed-degree polynomial growth-ratio bound, and check: the O(n^3) surrogate's ratio stays under the bound (no false positive) and the Q5 surrogate's ratio exceeds it (flags correctly, no false negative). Also perform an independent execution-free structural check: Grep src/solver.py and the Q5 surrogate for combinatorial-enumeration patterns (itertools.combinations/permutations/product, 'range(2**', unmemoized recursion without a cache/DP table). Record all results, the chosen bound and rationale, and the structural grep results under 'q6_discriminator', including a boolean 'q6_discriminator.justified'. If no discriminator form passes both checks, set justified=false and no act node may run.\n\n(Q7) For every test in tests/test_solver.py (from q3_enumeration) and, only if in-scope per q4a_discovery, every probe in probes.py, map it by content inspection to exactly one R8 sub-clause: no-mutation, determinism, or runtime. Record the mapping under 'q7_mapping' and state explicitly which R8 sub-clauses have zero mapped tests in tests/.\n\nOutput: write .creator-zero/experiment-4/c1/sandbox/evidence-round-0.json containing q1_reading, q2_note, q3_enumeration, q4a_discovery, q4b_probe_check, q5_gap_demo, q6_discriminator, q7_mapping, and a top-level 'verdict' field, one of R8_COVERAGE_SUFFICIENT | R8_COVERAGE_GAP_VERIFIED | SPECIFICATION_NOT_MECHANICALLY_TESTABLE | SPECIFICATION_AMBIGUITY | INDETERMINATE, derived strictly from the recorded evidence: verdict=R8_COVERAGE_GAP_VERIFIED only if q5_gap_demo shows all 13 canonical tests passing against the exponential surrogate AND q6_discriminator.justified=true; verdict=SPECIFICATION_AMBIGUITY if q1_reading=AMBIGUOUS; otherwise derive R8_COVERAGE_SUFFICIENT or INDETERMINATE from the remaining evidence. This record is the sole authorization basis for the act node: act runs only if verdict=R8_COVERAGE_GAP_VERIFIED and q6_discriminator.justified=true; on any other verdict act must not run and this record is the final evidence for the report node.",
      "why_necessary": "Sole pre-mutation epistemic locus. It cannot merge into the act node: the mutation locus would then author its own authorization evidence, collapsing the evidence-authorizes-mutation boundary. It cannot merge into the verify node: the verifier would become co-author of the hypothesis, surrogates, and discriminator bound it must independently re-check. Q1-Q7 are deliberately co-located here: all seven are answered by deterministic file inspection, sandboxed executable construction, or a fixed, already-settled logical note (Q2), performed with zero write authority over canonical or candidate state \u2014 including Q1's textual reading, which is explicitly labeled 'model_judgment' rather than hidden as mechanical output, satisfying the 0-fresh_model_invocation allowance without an extra node. Splitting these seven across more nodes would add nodes without adding any authority or causal boundary."
    },
    {
      "id": "act-candidate-test",
      "primitive": "act",
      "tools": [
        "Read",
        "Grep",
        "Bash",
        "Write",
        "Edit"
      ],
      "can_create": false,
      "execution_mode": "deterministic_script",
      "resolves": [],
      "instructions": "CONDITIONAL: run only if .creator-zero/experiment-4/c1/sandbox/evidence-round-0.json exists with verdict=R8_COVERAGE_GAP_VERIFIED and q6_discriminator.justified=true; otherwise do nothing and exit. WRITE RESTRICTION (hard): your write authority covers ONLY .creator-zero/experiment-4/c1/candidate/ \u2014 you MUST NOT write to src/, tests/, docs/, the evidence sandbox (.creator-zero/experiment-4/c1/sandbox/), or sandbox-verify/. Steps: read q6_discriminator's chosen growth-ratio bound, degree, and rationale from the evidence record. Create .creator-zero/experiment-4/c1/candidate/test_solver.py as an exact byte-copy of canonical tests/test_solver.py plus EXACTLY ONE added test method that implements the Q6 discriminator against the real src/solver.py: instrument call-count growth (via cProfile/sys.setprofile, not wall-clock) across the same n values used in q6_discriminator, and assert the growth ratio stays within the recorded polynomial bound. The assertion MUST NOT depend on wall-clock time, on the sandbox surrogates, or on any file outside src/solver.py and the standard library. Match the existing suite's unittest style; alter no other line, do not reorder or reformat anything else. Record the exact unified diff versus canonical tests/test_solver.py at .creator-zero/experiment-4/c1/candidate/candidate.diff. Do NOT run promotion and do NOT copy anything into tests/: promotion is performed exclusively by the deterministic Gate script after the verify node's verdict.",
      "why_necessary": "The only locus holding candidate-write authority. It cannot merge into evidence-and-discriminator or verify-candidate without violating authority-separation: evidence and verification loci must hold zero mutation authority, and verification must be causally distinct from mutation. It exists conditionally because only an upstream H1 verdict with a justified discriminator authorizes mutation, which the contract states is the sole justification for an act node."
    },
    {
      "id": "verify-candidate",
      "primitive": "verify",
      "tools": [
        "Read",
        "Grep",
        "Bash",
        "Write"
      ],
      "can_create": false,
      "execution_mode": "deterministic_script",
      "resolves": [
        "Q6"
      ],
      "instructions": "CONDITIONAL: run only if .creator-zero/experiment-4/c1/candidate/test_solver.py exists. You are causally independent of the act node: re-derive every check from docs/solver_spec.md, .creator-zero/harness/probes.py, and the evidence record; do not trust act's or evidence's conclusions without re-execution. WRITE RESTRICTION: you may write only under .creator-zero/experiment-4/c1/sandbox-verify/; never write to canonical paths, the sandbox, or the candidate workspace. Checks, all deterministic: (i) stage the candidate test file with canonical src/solver.py and run 'python -m unittest' \u2014 must report 14/14 PASS (13 canonical + 1 new). (ii) independently re-author, from scratch in sandbox-verify/, your own exponential-family surrogate (do not reuse act's or evidence's surrogate file directly \u2014 re-derive it from docs/solver_spec.md R1-R8) and run the candidate test file against it via import shim: the new test MUST FAIL \u2014 this is the false-negative re-check on a fresh witness, distinct from Q5's original surrogate. (iii) independently re-author your own legitimate O(n^3)-style polynomial reimplementation and run the candidate test against it: the new test MUST PASS \u2014 false-positive re-check. (iv) diff-scope audit: the candidate file must differ from canonical tests/test_solver.py by exactly the one added test method; run 'git diff -- src/solver.py docs/solver_spec.md tests/' and confirm it is empty (canonical tree untouched); run the canonical suite unmodified (expect 13/13) and .creator-zero/harness/probes.py (record pass/fail counts, expect no regression versus a pre-recorded baseline run). Output: write .creator-zero/experiment-4/c1/sandbox-verify/verify-verdict.json with a per-check pass/fail table and an overall ACCEPT/REJECT verdict. This file is the sole input the deterministic Gate script consumes to decide promotion. You do NOT promote anything.",
      "why_necessary": "The contract requires a verify primitive in any topology containing an act node, and requires verification to be causally distinct from mutation; merging into act-candidate-test would be self-verification, and merging into evidence-and-discriminator would let the author of the discriminator specification certify its own product. Re-deriving the false-positive/false-negative surrogates fresh (rather than reusing act's or evidence's) is what makes this locus genuinely independent rather than a re-run of the same script under a different name. Its verdict is the deterministic Gate's only input."
    },
    {
      "id": "report",
      "primitive": "return",
      "tools": [
        "Read"
      ],
      "can_create": false,
      "execution_mode": "deterministic_script",
      "resolves": [],
      "instructions": "Read .creator-zero/experiment-4/c1/sandbox/evidence-round-0.json and, if present, .creator-zero/experiment-4/c1/sandbox-verify/verify-verdict.json and .creator-zero/experiment-4/c1/candidate/candidate.diff. Compile the final report: state the verdict (one of R8_COVERAGE_SUFFICIENT | R8_COVERAGE_GAP_VERIFIED | SPECIFICATION_NOT_MECHANICALLY_TESTABLE | SPECIFICATION_AMBIGUITY | INDETERMINATE) with its full executable evidence chain, explicitly flagging q1_reading as a model_judgment classification rather than a mechanical result. State explicitly which of Q1-Q7 were resolved and by which node's recorded artifact, and, if the act/verify path ran, whether the Gate's promotion precondition (ACCEPT) is satisfied. Perform no computation that generates new evidence and write nothing.",
      "why_necessary": "The mandated return primitive delivering the final verdict and its evidence chain. It cannot merge into verify-candidate because it must exist on both realized paths \u2014 under H0 (or SPECIFICATION_AMBIGUITY / SPECIFICATION_NOT_MECHANICALLY_TESTABLE / INDETERMINATE) neither act nor verify runs \u2014 and because the return locus must not itself generate evidence or hold any write authority."
    }
  ],
  "edges": [
    {
      "source": "evidence-and-discriminator",
      "target": "act-candidate-test",
      "relation": "authorize",
      "requires_response": false,
      "response_changes_parent_state": false,
      "transfers_authority": false
    },
    {
      "source": "act-candidate-test",
      "target": "verify-candidate",
      "relation": "verify",
      "requires_response": true,
      "response_changes_parent_state": false,
      "transfers_authority": false
    },
    {
      "source": "verify-candidate",
      "target": "report",
      "relation": "return",
      "requires_response": false,
      "response_changes_parent_state": false,
      "transfers_authority": false
    },
    {
      "source": "evidence-and-discriminator",
      "target": "report",
      "relation": "return",
      "requires_response": false,
      "response_changes_parent_state": false,
      "transfers_authority": false
    }
  ],
  "coverage_map": {
    "Q1": [
      "evidence-and-discriminator"
    ],
    "Q2": [
      "evidence-and-discriminator"
    ],
    "Q3": [
      "evidence-and-discriminator"
    ],
    "Q4": [
      "evidence-and-discriminator"
    ],
    "Q5": [
      "evidence-and-discriminator"
    ],
    "Q6": [
      "evidence-and-discriminator",
      "verify-candidate"
    ],
    "Q7": [
      "evidence-and-discriminator"
    ]
  },
  "minimality_argument": "Four nodes is the floor for this task's required separations. Removing evidence-and-discriminator leaves Q1-Q7 unresolved and eliminates the only authorization basis for mutation. Removing act-candidate-test makes the H1 branch's mandated candidate creation impossible, while its existence is conditionally justified because only upstream evidence of H1 plus a justified discriminator can authorize mutation. Removing verify-candidate violates the hard constraint that a topology containing an act node (and here, Write/Edit tools) must contain a causally distinct verify node, leaves the discriminator's false-positive/false-negative claim unre-checked, and starves the deterministic Gate of its sole input. Removing report leaves no return locus on the H0/ambiguous/indeterminate paths, where report must run without act or verify ever executing. No two remaining nodes can merge: evidence+act would let the mutator author its own authorization; act+verify is self-verification, explicitly forbidden; evidence+verify would let the discriminator's author certify its own product with the same surrogates instead of independently re-deriving them; verify+report fails whenever act/verify do not run. Conversely, all seven questions are deliberately co-located in the single zero-canonical-write evidence locus rather than split into more nodes: Q1-Q2 are a fixed textual/logical determination (Q1 explicitly labeled model_judgment rather than hidden inside a separate fresh_model_invocation node, honoring the 0-node allowance in the budget), Q3-Q5 and Q7 are direct file/suite inspection, and Q6 is sandboxed executable construction \u2014 none of these require a distinct authority or causal boundary from one another, so splitting them would add nodes without adding separation. Q6 is additionally re-resolved by verify-candidate because the discriminator's false-positive/false-negative claim is exactly what gates promotion and must survive independent re-derivation, mirroring why Q5's expected-values recheck was duplicated in the R6 analogue (.creator-zero/experiment-3/final-harness.json)."
}

## Judgment standard

For each Qi: does some node's instructions concretely produce the evidence the
resolution_criterion demands (executable demonstrations where demanded, not
arguments)? Coverage is NOT satisfied by a question merely being named in
coverage_map — the instructions must actually do the work. Also flag: any node
instruction that would exceed the stated write scopes; any check whose
false-positive/false-negative burden the decomposition demands but the spec
drops; any conditional path on which some Qi would remain unresolved yet the
spec would still emit a final verdict.

## Output

PURE JSON only — no prose, no markdown fences:
{"coverage_complete": true|false, "missing": ["<Qi>: <what is missing>", ...], "notes": "<short remarks, including minor non-blocking observations>"}
