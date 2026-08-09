"""Deterministic blinded trial packaging (Experiment 5).

Builds an isolated parent workspace from a task-bank entry: public package
files, governance envelope (contract, child envelope, harness, schema,
protocol, child templates), permission deny rules, and the parent prompt.
Runs a blinding scan (banned label/condition/answer-key patterns; no private
bank files) and persists a per-file sha256 manifest. The root never adds
anything task-solving to the workspace.
"""
from __future__ import annotations
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any

E5 = Path(__file__).resolve().parents[1]

BANNED_PATTERNS = [
    r"condition[-_ ]*[ab]\b",
    r"ground[-_ ]?truth",
    r"answer[-_ ]?key",
    r"private[-_ ]?label",
    r"expected[-_ ]?(decision|topology|class|create)",
    r"do[-_ ]?not[-_ ]?create[-_ ]?expected",
    r"task-bank/private",
]

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

PARENT_PROMPT = """You are C-E5, a Creator in a fresh governed session.

Read protocol.md in your working directory first and follow it exactly.
Then read everything else in the workspace, evaluate the topology decision
chi(T,E,K), and realize exactly one branch as the protocol specifies.

Work only inside this working directory using the Read and Write tools.
"""


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def blinding_scan(root: Path, skip_names: set[str] = frozenset()) -> list[dict[str, Any]]:
    """Scan every text file in the workspace for banned patterns."""
    hits = []
    pats = [(p, re.compile(p, re.IGNORECASE)) for p in BANNED_PATTERNS]
    for f in sorted(root.rglob("*")):
        if not f.is_file() or f.name in skip_names:
            continue
        try:
            text = f.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for raw, rx in pats:
            m = rx.search(text)
            if m:
                hits.append({"file": str(f.relative_to(root)),
                             "pattern": raw, "match": m.group(0)})
    return hits


def build_workspace(*, trial_id: str, bank_dir: str | Path,
                    workspace: str | Path) -> dict[str, Any]:
    """Create the blinded parent workspace. Returns the package manifest.
    Raises RuntimeError on any blinding violation."""
    bank_dir = Path(bank_dir)
    ws = Path(workspace)
    public = bank_dir / "public"
    if not public.is_dir():
        raise RuntimeError(f"no public package at {public}")
    if ws.exists():
        raise RuntimeError(f"workspace already exists: {ws}")
    ws.mkdir(parents=True)

    # Public task package.
    shutil.copytree(public, ws / "package")

    # Governance envelope (fixed, preregistered files).
    shutil.copy(E5 / "contracts" / "trial-contract.json", ws / "contract.json")
    shutil.copy(E5 / "contracts" / "child-contract-envelope.json",
                ws / "child-envelope.json")
    shutil.copy(E5 / "decision-schema.json", ws / "decision-schema.json")
    shutil.copy(E5 / "protocol.md", ws / "protocol.md")
    shutil.copytree(E5 / "child-templates", ws / "child-templates")
    harness = (E5 / "harness-template.json").read_text(encoding="utf-8")
    (ws / "harness.json").write_text(harness.replace("__TRIAL_ID__", trial_id),
                                     encoding="utf-8")
    (ws / ".claude").mkdir()
    (ws / ".claude" / "settings.json").write_text(
        json.dumps(DENY_SETTINGS, indent=2) + "\n", encoding="utf-8")
    (ws / "parent-prompt.md").write_text(PARENT_PROMPT, encoding="utf-8")

    # Blinding checks.
    private_names = set()
    private_dir = bank_dir / "private"
    if private_dir.is_dir():
        private_names = {p.name for p in private_dir.rglob("*") if p.is_file()}
        copied = [str(f.relative_to(ws)) for f in ws.rglob("*")
                  if f.is_file() and f.name in private_names]
        if copied:
            shutil.rmtree(ws)
            raise RuntimeError(f"private bank files leaked into workspace: "
                               f"{copied}")
    hits = blinding_scan(ws)
    if hits:
        shutil.rmtree(ws)
        raise RuntimeError(f"blinding scan failed: {hits}")

    files = {str(f.relative_to(ws)): sha256_file(f)
             for f in sorted(ws.rglob("*")) if f.is_file()}
    manifest = {
        "artifact": "blinded trial workspace manifest",
        "trial_id": trial_id,
        "workspace": str(ws),
        "bank_dir": str(bank_dir),
        "blinding_scan": "PASS (0 hits)",
        "private_files_excluded": sorted(private_names),
        "file_sha256": files,
    }
    (ws / ".." / f"{trial_id}-package-manifest.json").resolve().write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("trial_id")
    ap.add_argument("bank_dir")
    ap.add_argument("workspace")
    a = ap.parse_args()
    m = build_workspace(trial_id=a.trial_id, bank_dir=a.bank_dir,
                        workspace=a.workspace)
    print(json.dumps({"trial_id": m["trial_id"],
                      "files": len(m["file_sha256"]),
                      "blinding_scan": m["blinding_scan"]}, indent=2))
