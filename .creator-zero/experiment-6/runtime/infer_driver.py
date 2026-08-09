"""Root-side driver for stage S1 (distinction inference) — Experiment 6.

    prepare TID    build the blinded inference workspace (scan enforced)
    <launch via launch.py>
    after TID      collect + audit the session; validate the typed outputs
                   (closed schemas); check ledger refinement against the
                   compiled inference harness; then run the deterministic
                   S2-S5 pipeline (abduce/generate/freeze/validate/rank)
"""
from __future__ import annotations
import argparse
import shutil
import sys
from pathlib import Path

from .common import (CZROOT, E6, bank_dir, e5_runtime, jdump, jload, now,
                     trial_contract, ws_root, SESSION_TOOLS)
from . import package_ws
from . import collect as collectmod
from .pipeline import run_pipeline

sys.path.insert(0, str(CZROOT))
import formal  # noqa: E402
from formal.trace import parse_runtime_ledger  # noqa: E402

session_audit = e5_runtime("session_audit")


def _tdir(tid: str) -> Path:
    if (E6 / "pilot" / "task-bank" / tid).is_dir():
        d = E6 / "pilot" / "trials" / tid
    else:
        d = E6 / "trials" / tid
    d.mkdir(parents=True, exist_ok=True)
    return d


def infer_ws(tid: str) -> Path:
    return ws_root(tid) / "infer-ws"


def cmd_prepare(tid: str) -> None:
    td = _tdir(tid)
    manifest = package_ws.build_infer_workspace(
        trial_id=tid, bank=bank_dir(tid), ws=infer_ws(tid))
    jdump(td / "infer-package-manifest.json", manifest)
    shutil.copy(bank_dir(tid) / "public" / "task.json", td / "task.json")
    print(f"[{tid}] infer ws prepared: {infer_ws(tid)}")


def cmd_after(tid: str) -> None:
    td = _tdir(tid)
    ws = infer_ws(tid)
    task = jload(td / "task.json")

    for name in ("distinctions.json", "value-estimates.json",
                 "spec-summary.json"):
        src = ws / name
        if not src.exists():
            raise SystemExit(f"[{tid}] inference session did not produce "
                             f"{name}")
        shutil.copy(src, td / name)
    shutil.copy(ws / "execution-ledger.jsonl",
                td / "infer-session-ledger.jsonl")

    audit = session_audit.audit_stream_log(
        td / "infer-session.log", workspace=ws, allowed_tools=SESSION_TOOLS)
    jdump(td / "infer-session-audit.json", audit)

    # closed-schema validation (typed rejection; model output cannot override)
    req_ids = [r.split(":", 1)[0].strip() for r in
               task.get("evidence_requirements", [])]
    distinctions = jload(td / "distinctions.json")
    collectmod.validate_distinctions(distinctions, task["task_id"], req_ids)
    estimates = jload(td / "value-estimates.json")
    collectmod.validate_value_estimates(estimates, task["task_id"])

    # ledger refinement against the compiled inference harness
    harness = jload(ws / "infer-harness.json")
    lts = formal.compile_harness_spec(harness, trial_contract())
    trace = parse_runtime_ledger(td / "infer-session-ledger.jsonl",
                                 strict=True)
    res = formal.check_refinement(trace, lts, require_completion=False)
    jdump(td / "formal-results" / "infer-refinement.json", res.to_dict())
    print(f"[{tid}] infer-refinement: {res.status}")

    # S2-S5 deterministic pipeline
    ranking = run_pipeline(tid, task, distinctions, estimates, td)
    print(f"[{tid}] pipeline: selected={ranking.get('selected')} "
          f"runner_up={ranking.get('runner_up')}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["prepare", "after"])
    ap.add_argument("trial_id")
    a = ap.parse_args()
    {"prepare": cmd_prepare, "after": cmd_after}[a.cmd](a.trial_id)


if __name__ == "__main__":
    main()
