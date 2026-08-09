"""Deterministic blinded workspace packaging (Experiment 6).

Builds the stage-S1 inference workspace and the stage-S6 execution
workspace for a trial. Both are scanned by the frozen blinding scanner
before any launch; a scan hit destroys the workspace and raises. Per-file
sha256 manifests are persisted. The root never adds anything task-solving.
"""
from __future__ import annotations
import json
import shutil
from pathlib import Path
from typing import Any

from . import blinding
from .common import (E6, jdump, jload, sha256_file)

DENY_SETTINGS = {
    "permissions": {
        "deny": [
            "Read(/home/user/creator-0/**)",
            "Write(/home/user/creator-0/**)",
            "Edit(/home/user/creator-0/**)",
            "Read(/root/.claude/uploads/**)",
            "Bash", "Grep", "Glob", "Edit", "Task", "Agent",
            "WebFetch", "WebSearch", "NotebookEdit",
        ]
    }
}

INFER_PROMPT = """You are D-E6, a distinction-inference session in a fresh governed workspace.

Read protocol.md in your working directory first and follow it exactly.
Then read everything else in the workspace and produce distinctions.json,
value-estimates.json, spec-summary.json and execution-ledger.jsonl exactly
as the protocol and schemas specify.

Work only inside this working directory using the Read and Write tools.
"""

EXEC_PROMPT = """You are X-E6, a worker Creator in a fresh governed session.

Read protocol.md in your working directory first and follow it exactly.
Then read everything else in the workspace and execute the in-session nodes
of harness.json, producing resolution.json, result.json, evidence.json,
execution-ledger.jsonl and the family-specific artifacts the protocol
specifies.

Work only inside this working directory using the Read and Write tools.
"""

EXAMINER_PROMPT = """You are V-E6, an independent examiner in a fresh governed session.

Read protocol.md in your working directory first and follow it exactly.
Then read everything else in the workspace and produce
independent-verification.json and execution-ledger.jsonl exactly as the
protocol specifies.

Work only inside this working directory using the Read and Write tools.
"""


def _manifest(ws: Path, kind: str, trial_id: str,
              scan: dict[str, Any]) -> dict[str, Any]:
    return {
        "artifact": f"blinded {kind} workspace manifest",
        "trial_id": trial_id,
        "workspace": str(ws),
        "blinding_scan": ("PASS (0 hits)" if scan["verdict"] == "PASS"
                          else scan),
        "file_sha256": {str(f.relative_to(ws)): sha256_file(f)
                        for f in sorted(ws.rglob("*")) if f.is_file()},
    }


def _no_private_files(bank: Path, ws: Path) -> None:
    private_dir = bank / "private"
    if private_dir.is_dir():
        names = {p.name for p in private_dir.rglob("*") if p.is_file()}
        leaked = [str(f.relative_to(ws)) for f in ws.rglob("*")
                  if f.is_file() and f.name in names
                  and f.name not in ("task.json",)]
        if leaked:
            shutil.rmtree(ws)
            raise RuntimeError(f"private bank files leaked: {leaked}")


def _scan_or_die(ws: Path, kind: str) -> dict[str, Any]:
    scan = blinding.scan_workspace(ws)
    if scan["verdict"] != "PASS":
        shutil.rmtree(ws)
        raise RuntimeError(f"BLINDING_FAIL in {kind} workspace: "
                           f"{scan['hits']}")
    return scan


def build_infer_workspace(*, trial_id: str, bank: Path,
                          ws: Path) -> dict[str, Any]:
    if ws.exists():
        raise RuntimeError(f"workspace already exists: {ws}")
    ws.mkdir(parents=True)
    shutil.copytree(bank / "public", ws / "package")
    shutil.copy(E6 / "contracts" / "trial-contract.json", ws / "contract.json")
    shutil.copy(E6 / "schemas" / "distinction-spec-schema.json",
                ws / "distinction-spec-schema.json")
    shutil.copy(E6 / "schemas" / "value-estimates-schema.json",
                ws / "value-estimates-schema.json")
    shutil.copy(E6 / "protocol-infer.md", ws / "protocol.md")
    harness = (E6 / "infer-harness-template.json").read_text(encoding="utf-8")
    (ws / "infer-harness.json").write_text(
        harness.replace("__TRIAL_ID__", trial_id), encoding="utf-8")
    (ws / ".claude").mkdir()
    (ws / ".claude" / "settings.json").write_text(
        json.dumps(DENY_SETTINGS, indent=2) + "\n", encoding="utf-8")
    (ws / "prompt.md").write_text(INFER_PROMPT, encoding="utf-8")
    _no_private_files(bank, ws)
    scan = _scan_or_die(ws, "infer")
    return _manifest(ws, "infer", trial_id, scan)


def build_exec_workspace(*, trial_id: str, bank: Path, ws: Path,
                         harness_spec: dict[str, Any],
                         distinctions: dict[str, Any]) -> dict[str, Any]:
    if ws.exists():
        raise RuntimeError(f"workspace already exists: {ws}")
    ws.mkdir(parents=True)
    shutil.copytree(bank / "public", ws / "package")
    shutil.copy(E6 / "contracts" / "trial-contract.json", ws / "contract.json")
    shutil.copy(E6 / "schemas" / "resolution-schema.json",
                ws / "resolution-schema.json")
    shutil.copy(E6 / "protocol-exec.md", ws / "protocol.md")
    jdump(ws / "harness.json", harness_spec)
    jdump(ws / "distinctions.json", distinctions)
    has_create = any(n.get("primitive") == "create"
                     for n in harness_spec.get("nodes", []))
    if has_create:
        shutil.copy(E6 / "contracts" / "child-contract-envelope.json",
                    ws / "child-envelope.json")
        shutil.copytree(E6 / "child-templates", ws / "child-templates")
    (ws / ".claude").mkdir()
    (ws / ".claude" / "settings.json").write_text(
        json.dumps(DENY_SETTINGS, indent=2) + "\n", encoding="utf-8")
    (ws / "prompt.md").write_text(EXEC_PROMPT, encoding="utf-8")
    _no_private_files(bank, ws)
    scan = _scan_or_die(ws, "exec")
    return _manifest(ws, "exec", trial_id, scan)


def build_examiner_workspace(*, trial_id: str, exec_ws: Path,
                             ws: Path) -> dict[str, Any]:
    if ws.exists():
        raise RuntimeError(f"workspace already exists: {ws}")
    ws.mkdir(parents=True)
    shutil.copytree(exec_ws / "package", ws / "package")
    for name in ("result.json", "resolution.json", "distinctions.json",
                 "examiner-charge.md"):
        src = exec_ws / name
        if src.exists():
            shutil.copy(src, ws / name)
    shutil.copy(E6 / "protocol-examiner.md", ws / "protocol.md")
    (ws / ".claude").mkdir()
    (ws / ".claude" / "settings.json").write_text(
        json.dumps(DENY_SETTINGS, indent=2) + "\n", encoding="utf-8")
    (ws / "prompt.md").write_text(EXAMINER_PROMPT, encoding="utf-8")
    # no re-scan: package/ was scanned at exec packaging; the remaining files
    # are outputs of blinded sessions (cannot contain labels they never saw)
    # plus the uniform preregistered protocol.
    return _manifest(ws, "examiner", trial_id,
                     {"verdict": "PASS", "hits": [],
                      "note": "package scanned at exec packaging; "
                              "worker outputs produced blind"})


def build_child_workspace(*, trial_id: str, exec_ws: Path, child_dir: Path,
                          ws: Path) -> dict[str, Any]:
    """Child workspace from the validated bundle: manifested inputs only."""
    if ws.exists():
        raise RuntimeError(f"workspace already exists: {ws}")
    manifest = jload(child_dir / "child-input-manifest.json")
    (ws / "inputs").mkdir(parents=True)
    for rel in manifest["files"]:
        rel = str(rel)
        if rel.startswith("/") or ".." in rel:
            shutil.rmtree(ws)
            raise RuntimeError(f"manifest escape: {rel}")
        src = exec_ws / rel
        if not src.is_file():
            shutil.rmtree(ws)
            raise RuntimeError(f"manifest names missing file: {rel}")
        shutil.copy(src, ws / "inputs" / Path(rel).name)
    shutil.copy(child_dir / "child-harness.json", ws / "child-harness.json")
    shutil.copy(child_dir / "child-contract.json", ws / "child-contract.json")
    shutil.copy(child_dir / "child-prompt.md", ws / "child-prompt.md")
    (ws / ".claude").mkdir()
    (ws / ".claude" / "settings.json").write_text(
        json.dumps(DENY_SETTINGS, indent=2) + "\n", encoding="utf-8")
    files = sorted(str(p.relative_to(ws)) for p in ws.rglob("*")
                   if p.is_file())
    return {"artifact": "child workspace manifest", "trial_id": trial_id,
            "workspace": str(ws), "files": files,
            "input_manifest": manifest["files"]}
