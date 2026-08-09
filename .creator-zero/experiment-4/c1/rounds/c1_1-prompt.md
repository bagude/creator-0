# Role: Composer C1_1 (fresh, causally isolated) — revision round

You are a fresh Composer instance with no session history. A prior Composer
produced the HarnessSpec below; a fresh critique found a coverage defect. Your
ONLY job is to output a corrected complete HarnessSpec (pure JSON) that fixes
the defect while changing as little else as possible.

## The prior HarnessSpec (foreign artifact):

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

## The critique to fix:

{
  "coverage_complete": false,
  "missing": [
    "Q6: The evidence node instructs running the true exponential-family Q5 surrogate (2^n subset enumeration / unmemoized exponential recursion) at 'the same n values' used for the real implementation, explicitly including n=80 and n=160. This is not merely slow but computationally infeasible (2^160 operations cannot execute in any realistic time), so the instructed methodology cannot actually produce the 'executable demonstration' the resolution_criterion demands for the growth-ratio false-negative check at those sizes \u2014 the node would hang or never complete as written. No cap, timeout, or reduced-n schedule is specified for the exponential surrogate specifically (unlike Q4b, which explicitly requires the surrogate be tuned to stay tractable/'under one minute total'). This risks either the node silently failing to finish Q6, or an implementer silently truncating n without the truncation being recorded, undermining the executable-evidence requirement."
  ],
  "notes": "Minor non-blocking observation: Q6's why_load_bearing calls for a false-negative check specifically against 'an evasive violation with a large hidden constant that stays fast at tested sizes,' but the harness (mirroring the literal resolution_criterion, which only requires checking against the Q5 exponential surrogate and an O(n^3) legitimate reimplementation) never constructs a distinct large-hidden-constant surrogate. This is arguably subsumed by the growth-ratio method's scale-invariance to multiplicative constants, but it is not explicitly demonstrated, so it is worth noting even though it does not strictly violate the stated resolution_criterion text. All other questions (Q1-Q5, Q7) are concretely and, where the criterion demands it, executably addressed by evidence-and-discriminator's instructions, with Q6 additionally independently re-derived (not just re-run) by verify-candidate using fresh surrogates, satisfying the causal-independence requirement. Write-scope restrictions for all four nodes appear correctly bounded to their designated subdirectories with no instruction directing writes outside those scopes. The report node correctly has access to Q1-Q7 evidence regardless of which branch (H0/H1/AMBIGUOUS/INDETERMINATE) is taken, since evidence-and-discriminator resolves all seven questions unconditionally before any verdict branching, so no path leaves a Qi unresolved while still emitting a final verdict."
}

## Requirements for the revision

1. Fix the Q6 infeasibility defect: give the exponential surrogate its OWN
   explicit n-schedule, capped where 2^n work is tractable (e.g. n in
   {10, 14, 18, 22} or similar), with the cap and its rationale REQUIRED to be
   recorded in the evidence output. The real implementation and the legitimate
   O(n^3) reimplementation keep a larger schedule (e.g. up to n=160). The
   growth-ratio comparison must be defined so it is computable on these
   distinct schedules (per-doubling call-count ratios within each
   implementation's own schedule), and the evidence record must state
   explicitly that the exponential surrogate's schedule was capped for
   tractability and why that does not weaken the discrimination claim
   (exponential growth ratio per doubling diverges already at small n;
   polynomial ratio is bounded by 2^degree at any n).
2. Address the critique's non-blocking note in the cheapest sound way: either
   require an explicit note in the evidence record explaining why a
   multiplicative-constant-evasive violation is or is not caught by
   growth-ratio methodology (scale-invariance argument, recorded as reasoning,
   flagged model_judgment), or add a cheap constant-scaled surrogate check —
   your choice, but be explicit.
3. Keep everything else (topology, node ids, edges, coverage_map keyed Q1..Q7,
   write scopes, conditionality, max_model_calls, execution_mode fields)
   unchanged except where the fix requires wording changes inside
   instructions/minimality_argument.
4. Schema: identical schema to the prior spec (it validated VALID against the
   contract). Do not add or remove nodes or edges.

## Output

PURE JSON only — the complete corrected HarnessSpec. No prose, no markdown
fences, nothing before or after the JSON object.
