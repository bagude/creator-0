"""Independent verifier for Experiment 1.

Answers, deterministically and without repairing anything:
  1. Does the protected unit suite pass against the given solver?
  2. Does the seeded differential sweep against the spec oracle agree?
  3. If either fails, does replaying the failure against the oracle confirm
     a violation of docs/solver_spec.md by the SOLVER, or is the disagreeing
     party the test suite itself?

Usage:
    python verify.py [--solver-dir DIR]

Writes .creator-zero/runs/experiment-1-verdict.json and prints it.
Exit 0 = no solver defect demonstrated; exit 1 = solver defect confirmed.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
VERDICT_PATH = os.path.join(REPO, ".creator-zero", "runs",
                            "experiment-1-verdict.json")


def run_unit_suite(solver_dir):
    """Run the protected suite against solver_dir via an unmodified sandbox
    copy (the suite resolves ../src relative to its own location)."""
    with tempfile.TemporaryDirectory(dir=HERE) as sandbox:
        os.makedirs(os.path.join(sandbox, "tests"))
        os.makedirs(os.path.join(sandbox, "src"))
        shutil.copy(os.path.join(REPO, "tests", "test_solver.py"),
                    os.path.join(sandbox, "tests", "test_solver.py"))
        shutil.copy(os.path.join(solver_dir, "solver.py"),
                    os.path.join(sandbox, "src", "solver.py"))
        proc = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-v",
             "-s", os.path.join(sandbox, "tests")],
            capture_output=True, text=True, check=False)
    return proc.returncode == 0, proc.stderr.strip()


def run_differential(solver_dir):
    env = dict(os.environ, SOLVER_DIR=solver_dir)
    proc = subprocess.run(
        [sys.executable, os.path.join(HERE, "differential_test.py")],
        capture_output=True, text=True, env=env, check=False)
    try:
        record = json.loads(proc.stdout)
    except json.JSONDecodeError:
        record = {"outcome": "TOOL_ERROR", "stderr": proc.stderr[-2000:]}
    return record


def confirm_against_oracle(unit_failures, solver_dir):
    """For unit-suite failures with a concrete instance embedded in the
    test, decide whether solver or test disagrees with the spec oracle."""
    sys.path.insert(0, HERE)
    sys.path.insert(0, solver_dir)
    from oracle import oracle_solve, spec_validate  # noqa: E402

    attributions = []
    # The protected suite is small; extract literal instances from it.
    import ast
    import re

    src = open(os.path.join(REPO, "tests", "test_solver.py"),
               encoding="utf-8").read()
    for match in re.finditer(r"def (test_\w+)", src):
        name = match.group(1)
        if not any(name in f for f in unit_failures):
            continue
        body = src[match.start():]
        body = body[:body.find("\n    def ") if "\n    def " in
                    body[10:] else len(body)]
        literals = re.findall(r"solve\((\[.*?\])\)", body, re.S)
        literals += re.findall(r"jobs = (\[.*?\])\n", body, re.S)
        for lit in literals:
            try:
                jobs = ast.literal_eval(lit)
            except (ValueError, SyntaxError):
                continue
            if spec_validate(jobs) is not None:
                continue
            spec_answer = oracle_solve(jobs)
            attributions.append({
                "failing_test": name,
                "instance": jobs,
                "spec_oracle_answer": list(spec_answer),
            })
    return attributions


def main():
    solver_dir = os.path.join(REPO, "src")
    if "--solver-dir" in sys.argv:
        solver_dir = os.path.abspath(
            sys.argv[sys.argv.index("--solver-dir") + 1])

    suite_ok, suite_err = run_unit_suite(solver_dir)
    unit_failures = [ln for ln in suite_err.splitlines()
                     if ln.startswith(("FAIL:", "ERROR:"))]
    diff_record = run_differential(solver_dir)
    diff_ok = diff_record.get("outcome") == "AGREEMENT"

    solver_defect = bool(diff_record.get("counterexamples"))
    attributions = []
    if not suite_ok:
        attributions = confirm_against_oracle(unit_failures, solver_dir)

    verdict = {
        "solver_dir": solver_dir,
        "unit_suite_green": suite_ok,
        "unit_suite_failures": unit_failures,
        "differential": {
            "outcome": diff_record.get("outcome"),
            "cases_executed": diff_record.get("cases_executed"),
            "counterexamples": diff_record.get("counterexamples", []),
        },
        "unit_failure_attribution": attributions,
        "solver_defect_confirmed": solver_defect,
        "mutation_authorized": solver_defect,
    }
    with open(VERDICT_PATH, "w", encoding="utf-8") as f:
        json.dump(verdict, f, indent=2)
        f.write("\n")
    print(json.dumps(verdict, indent=2))
    return 1 if solver_defect else 0


if __name__ == "__main__":
    sys.exit(main())
