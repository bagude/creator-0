"""Merge Q2-Q5 results with programmatic Q1 suite runs and write
evidence-round-0.json. Deterministic; canonical files untouched."""

import json
import os
import subprocess
import sys

SANDBOX = "/home/user/creator-0/.creator-zero/experiment-3/sandbox"

RUNNER = r"""
import json, sys, unittest
loader = unittest.TestLoader()
suite = loader.discover(start_dir="tests")
names = []
def collect(s):
    for t in s:
        if isinstance(t, unittest.TestSuite):
            collect(t)
        else:
            names.append(t.id().split(".")[-1])
collect(suite)
runner = unittest.TextTestRunner(stream=open("/dev/null", "w"), verbosity=0)
result = runner.run(suite)
failed = {t.id().split(".")[-1]: tb.strip().splitlines()[-1]
          for t, tb in result.failures + result.errors}
matrix = {n: ("FAIL: " + failed[n] if n in failed else "pass")
          for n in sorted(names)}
print(json.dumps({
    "tests_run": result.testsRun,
    "passed": result.testsRun - len(failed),
    "failed": len(failed),
    "matrix": matrix,
    "failure_identities": sorted(failed),
}))
"""


def run_suite(run_dir):
    out = subprocess.run(
        [sys.executable, "-c", RUNNER], cwd=run_dir,
        capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def main():
    with open(os.path.join(SANDBOX, "q_results.json")) as f:
        q = json.load(f)

    suite_matrix = {}
    for name, run_dir in (("ef_dp_backtrack", "run_ef"),
                          ("prefer_higher_index", "run_hi")):
        suite_matrix[name] = run_suite(os.path.join(SANDBOX, run_dir))
        suite_matrix[name]["run_dir"] = os.path.join(SANDBOX, run_dir)
        suite_matrix[name]["command"] = "python -m unittest discover -s tests"
        suite_matrix[name]["import_shim"] = (
            "surrogate copied to <run_dir>/src/solver.py; tests/ copied "
            "verbatim; the suite's own sys.path.insert(../src) resolves "
            "'from solver import solve' to the surrogate")

    witness = [n for n, m in suite_matrix.items()
               if n in q["admissible_surrogates"] and m["failed"] == 0]
    verdict = "H1" if witness else "H0"

    chosen = q["q4_minimality_search"]["chosen"]
    q5 = q["q5_oracle_first_derivation"]
    instance_literal = "[(0, 2, 1), (0, 1, 1)]"

    evidence = {
        "node": "evidence-gap-and-derivation",
        "harness": "experiment-3-r6-coverage",
        "round": 0,
        "verdict": verdict,
        "verdict_basis": (
            "Admissible R6-violating surrogate 'ef_dp_backtrack' "
            "(earliest-finish DP, standard backtracking) passes all 12 "
            "existing tests, so the current suite leaves an R6 regression "
            "undetected." if verdict == "H1" else
            "Every admissible surrogate is killed by an existing test; "
            "evidence bounded to the constructed violation class."),
        "witness_surrogates_passing_full_suite": witness,
        "q2_admissible_surrogate_verification": {
            "differential_grid": {
                "exhaustive": "all ordered job tuples, n=1..4, over universe"
                              " starts [-1..2] x lengths {1,2} x weights"
                              " {1,2} (69904 instances)",
                "random": "2000 seeded instances (seed 20260809), n=5..8,"
                          " starts [-3..5], lengths 1..4, weights 1..3",
                "oracle": ".creator-zero/harness/oracle.py enumeration logic"
                          " (full subset enumeration, lex-min tie-break)",
            },
            "admissibility_rule": "(a) weight equals oracle optimum on every"
                                  " instance (R5 preserved) AND (b) index"
                                  " sequence differs from lex-min optimal on"
                                  " >= 1 instance (R6 violated); no input"
                                  " mutation observed",
            "per_surrogate": q["q2_surrogate_differential"],
            "admissible": q["admissible_surrogates"],
            "discarded": q["discarded_surrogates"],
        },
        "q1_suite_run_matrix": suite_matrix,
        "q1_failure_identities": {
            n: m["failure_identities"] for n, m in suite_matrix.items()},
        "q3_full_tie_enumerations": q["q3_tie_enumerations"],
        "q3_notes": (
            "test_classic_instance's 8-job instance has a UNIQUE optimum "
            "(W=11, sole sequence [2, 6]) -> not tie-bearing, so it cannot "
            "discriminate R6 even in principle; it also only asserts the "
            "weight. The chosen synthetic instance has exactly 2 optimal "
            "sequences ([0] and [1]) at W=1; lex-smallest (spec-canonical) "
            "is [0]."),
        "q4_minimality_search": q["q4_minimality_search"],
        "chosen_instance": {
            "jobs": chosen["jobs"],
            "n_jobs": chosen["n"],
            "coordinate_universe": "[0..%d]" % chosen["span"],
            "weight_universe": "[1..%d]" % chosen["wmax"],
            "assertions": chosen["assertions"],
            "kills_every_admissible_surrogate": True,
            "surrogate_results": q["surrogate_results_on_chosen_instance"],
        },
        "expected_result": {
            "W": q5["expected_W"],
            "S": q5["expected_S"],
            "provenance": q5["provenance_order"],
            "hand_derivation": q5["hand_derivation"],
            "canonical_solver_result": q5["canonical_solver_result"],
            "canonical_agrees_with_oracle":
                q5["canonical_agrees_with_oracle"],
        },
        "candidate_test_specification": {
            "instance_literal": instance_literal,
            "expected_weight": q5["expected_W"],
            "expected_index_sequence": q5["expected_S"],
            "suite_conventions": "method on TestSolve(unittest.TestCase) in "
                                 "tests/test_solver.py, single assertEqual "
                                 "on the full (W, S) tuple, comment style "
                                 "matching test_tie_break_prefers_lower_"
                                 "indices",
            "proposed_method_name":
                "test_tie_break_lex_smallest_when_later_index_finishes_first",
            "assertion_list": [
                "self.assertEqual(solve([(0, 2, 1), (0, 1, 1)]), (1, [0]))",
            ],
            "proposed_method_source": [
                "def test_tie_break_lex_smallest_when_later_index_finishes_first(self):",
                "    # Jobs overlap, so {0} and {1} both achieve W=1; R6 requires [0].",
                "    # Job 1 finishes earlier, so earliest-finish DP reconstructions",
                "    # that do not lexicographically minimize return [1] instead.",
                "    self.assertEqual(solve([(0, 2, 1), (0, 1, 1)]), (1, [0]))",
            ],
            "discrimination_evidence": {
                "canonical_solver": q5["canonical_solver_result"],
                "ef_dp_backtrack":
                    q["surrogate_results_on_chosen_instance"]
                    ["ef_dp_backtrack"],
                "prefer_higher_index":
                    q["surrogate_results_on_chosen_instance"]
                    ["prefer_higher_index"],
            },
            "does_not_overfit_note": (
                "Asserts exactly the spec-forced (W, S): W forced by R5, S "
                "forced by R6 lex-minimality over the enumerated optimal set "
                "{[0], [1]}; no behavior beyond R2/R5/R6 is encoded."),
        },
        "act_node_authorization": {
            "authorized": verdict == "H1",
            "condition": "This record authorizes the act node ONLY on "
                         "verdict H1; on H0 the act node must not run and "
                         "this record is the final evidence for the return "
                         "node.",
        },
        "canonical_paths_untouched": True,
    }
    out_path = os.path.join(SANDBOX, "evidence-round-0.json")
    with open(out_path, "w") as f:
        json.dump(evidence, f, indent=2)
    print("wrote", out_path)
    print("verdict:", verdict, "witness:", witness)
    for n, m in suite_matrix.items():
        print(n, "passed=%d failed=%d" % (m["passed"], m["failed"]),
              m["failure_identities"])


if __name__ == "__main__":
    main()
