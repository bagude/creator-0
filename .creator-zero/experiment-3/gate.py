"""Deterministic promotion Gate for Creator-0 Experiment 3.

Sole authority for promoting candidate state into canonical state.
Consumes the verify node's verdict and independently re-executes every
deterministic acceptance check. No model judgment is involved.

ACCEPT => tests/test_solver.py := candidate/test_solver.py
REJECT => canonical state preserved unchanged.
"""
from __future__ import annotations
import difflib, json, re, shutil, subprocess, sys, tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
EXP = REPO / ".creator-zero/experiment-3"
CANONICAL_TEST = REPO / "tests/test_solver.py"
CANDIDATE_TEST = EXP / "candidate/test_solver.py"
VERDICT = EXP / "sandbox-verify/verify-verdict.json"
START_COMMIT = "db51bb3ed1eea5f5a836ee5c40d7c291a106cb6f"

checks = []

def check(name, ok, detail):
    checks.append({"check": name, "ok": bool(ok), "detail": detail})
    return ok

def run(cmd, cwd=REPO):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=600)
    return p.returncode, p.stdout + p.stderr

def main() -> int:
    accept = True

    # 1. Verifier verdict exists and is ACCEPT.
    if VERDICT.exists():
        verdict = json.loads(VERDICT.read_text())
        overall = str(verdict.get("overall", verdict.get("verdict", ""))).upper()
        accept &= check("verifier_verdict_accept", overall == "ACCEPT", f"overall={overall!r}")
    else:
        accept &= check("verifier_verdict_accept", False, "verify-verdict.json missing")

    # 2. Candidate exists.
    accept &= check("candidate_exists", CANDIDATE_TEST.exists(), str(CANDIDATE_TEST))

    if CANDIDATE_TEST.exists():
        # 3. Pure-addition scope: canonical lines preserved verbatim and in order.
        old = CANONICAL_TEST.read_text().splitlines(keepends=True)
        new = CANDIDATE_TEST.read_text().splitlines(keepends=True)
        ops = difflib.SequenceMatcher(None, old, new, autojunk=False).get_opcodes()
        pure_add = all(tag in ("equal", "insert") for tag, *_ in ops)
        added = sum(j2 - j1 for tag, i1, i2, j1, j2 in ops if tag == "insert")
        accept &= check("pure_addition_diff_scope", pure_add and added > 0,
                        f"opcodes={[t for t, *_ in ops]}, added_lines={added}")

        # 4. Canonical tree untouched relative to start commit.
        rc, out = run(["git", "diff", "--stat", START_COMMIT, "--",
                       "src/solver.py", "docs/solver_spec.md", "tests/"])
        accept &= check("canonical_tree_untouched", rc == 0 and out.strip() == "", out.strip() or "clean")

        # 5. Candidate suite green against canonical solver (staged, canonical untouched).
        with tempfile.TemporaryDirectory() as td:
            stage = Path(td) / "stage"
            shutil.copytree(REPO / "tests", stage / "tests")
            shutil.copytree(REPO / "src", stage / "src")
            shutil.copy(CANDIDATE_TEST, stage / "tests/test_solver.py")
            rc, out = run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"], cwd=stage)
            m = re.search(r"Ran (\d+) tests", out)
            n = int(m.group(1)) if m else 0
            green = rc == 0 and "OK" in out
            accept &= check("candidate_suite_green_vs_canonical_solver",
                            green and n == 13, f"ran={n}, rc={rc}")

        # 6/7. Differential and probes unchanged.
        rc, out = run([sys.executable, ".creator-zero/harness/differential.py"])
        accept &= check("differential_green",
                        rc == 0 and "ALL    total=20689 pass=20689 fail=0 mutated=0" in out,
                        out.strip().splitlines()[-2] if out.strip() else "no output")
        rc, out = run([sys.executable, ".creator-zero/harness/probes.py"])
        accept &= check("probes_green", rc == 0 and "PROBES total=24 pass=24 fail=0" in out,
                        out.strip().splitlines()[-1] if out.strip() else "no output")

    decision = "ACCEPT" if accept else "REJECT"
    promoted = False
    if accept:
        shutil.copy(CANDIDATE_TEST, CANONICAL_TEST)
        rc, out = run([sys.executable, "-m", "unittest", "discover", "-s", "tests"])
        promoted = rc == 0
        check("post_promotion_suite_green", promoted, "suite re-run after promotion")
        if not promoted:  # rollback: preservation is the default
            run(["git", "checkout", START_COMMIT, "--", "tests/test_solver.py"])
            decision = "REJECT_ROLLED_BACK"

    out_doc = {
        "gate": "deterministic",
        "decision": decision,
        "promoted": promoted,
        "promotion_mechanism": "gate.py shutil.copy(candidate -> tests/test_solver.py)",
        "checks": checks,
    }
    (EXP / "gate-decision.json").write_text(json.dumps(out_doc, indent=2) + "\n")
    print(json.dumps(out_doc, indent=2))
    return 0 if decision == "ACCEPT" else 1

if __name__ == "__main__":
    raise SystemExit(main())
