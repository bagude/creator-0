"""Shared deterministic verification/integration helpers (Experiment 5,
private side). Root-only: never enters a blinded workspace.

Integration is mechanical execution of the parent's pre-committed
integration-plan verdict rule; the root never solves the substantive task.
"""
from __future__ import annotations
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

RUNNER = r"""
import importlib.util, json, sys
spec = importlib.util.spec_from_file_location("child_impl", sys.argv[1])
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
func = getattr(mod, sys.argv[2])
arg = json.loads(sys.argv[3])
print(json.dumps({"ok": True, "value": func(arg)}))
"""


def load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path: str | Path, obj: Any) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")


def run_callable(impl_path: str | Path, func: str, arg: Any,
                 timeout: float = 30.0) -> dict[str, Any]:
    """Execute `func(arg)` from a python file in a subprocess; deterministic
    JSON result: {ok, value} or {ok: False, error}."""
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write(RUNNER)
        runner = f.name
    try:
        proc = subprocess.run(
            [sys.executable, runner, str(impl_path), func, json.dumps(arg)],
            capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "timeout"}
    if proc.returncode != 0:
        return {"ok": False, "error": proc.stderr.strip()[-2000:]}
    try:
        return json.loads(proc.stdout.strip().splitlines()[-1])
    except (json.JSONDecodeError, IndexError):
        return {"ok": False, "error": f"non-json output: {proc.stdout[:500]}"}


def apply_verdict_rule(plan: dict[str, Any], any_divergence: bool) -> str:
    rule = plan["verdict_rule"]
    key = "if_any_divergence" if any_divergence else "if_none"
    if key not in rule:
        raise ValueError(f"integration plan verdict_rule missing {key}")
    return str(rule[key])


def first_diff_lines(a: str, b: str) -> dict[str, Any]:
    la, lb = a.splitlines(), b.splitlines()
    for i in range(max(len(la), len(lb))):
        x = la[i] if i < len(la) else "<absent>"
        y = lb[i] if i < len(lb) else "<absent>"
        if x != y:
            return {"matches": False, "first_differing_line": i,
                    "a_line": x, "b_line": y}
    return {"matches": True}


def verification_record(*, trial_id: str, branch: str, task_verified: bool,
                        expected: Any, observed: Any, reasons: list[str],
                        child_evidence: dict[str, Any] | None = None
                        ) -> dict[str, Any]:
    rec = {
        "artifact": "deterministic trial verification",
        "trial_id": trial_id,
        "branch": branch,
        "task_verified": task_verified,
        "expected": expected,
        "observed": observed,
        "reasons": reasons,
    }
    if child_evidence is not None:
        rec["child_evidence"] = child_evidence
    return rec
