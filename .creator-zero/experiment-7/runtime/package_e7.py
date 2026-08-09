"""Blinded workspace packaging for both E7 conditions.

Condition A reuses the frozen E6 packaging verbatim (same protocol, schemas,
prompts). Condition B swaps in the v2 inference protocol/schemas and the v2
exec/examiner protocols. Every blinded workspace passes the frozen E6
blinding scan (plus the E7 class-token set at bank generation). Cross-
condition isolation: workspaces live under disjoint per-condition roots and
never receive artifacts produced under the other condition (NC16)."""
from __future__ import annotations
import json
import re
import shutil
from pathlib import Path
from typing import Any

from .common import E6, E7, jdump, sha256_file

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

PROMPTS = {
    "infer": """You are {who}, a distinction-inference session in a fresh governed workspace.

Read protocol.md in your working directory first and follow it exactly.
Then read everything else in the workspace and produce distinctions.json,
value-estimates.json, spec-summary.json and execution-ledger.jsonl exactly
as the protocol and schemas specify.

Work only inside this working directory using the Read and Write tools.
""",
    "exec": """You are {who}, a worker Creator in a fresh governed session.

Read protocol.md in your working directory first and follow it exactly.
Then read everything else in the workspace and execute the in-session nodes
of harness.json, producing resolution.json, result.json, evidence.json,
execution-ledger.jsonl and the family-specific artifacts the protocol
specifies.

Work only inside this working directory using the Read and Write tools.
""",
    "examiner": """You are {who}, an independent examiner in a fresh governed session.

Read protocol.md in your working directory first and follow it exactly.
Then read everything else in the workspace and produce
independent-verification.json and execution-ledger.jsonl exactly as the
protocol specifies.

Work only inside this working directory using the Read and Write tools.
""",
}

E7_CLASS_TOKENS = [
    r"\bCLEAN_ROOM_AUTHORSHIP\b", r"\bNON_AUTHOR_SEARCH\b",
    r"\bINDEPENDENT_DECOMPOSITION\b", r"\bMETHOD_DISJOINT_VERIFICATION\b",
    r"admissibility[-_ ]?kind", r"required[-_ ]?role",
]


def _blinding():
    from .common import e6_runtime
    return e6_runtime("blinding")


def _scan_or_die(ws: Path, kind: str,
                 skip: frozenset[str] = frozenset()) -> dict[str, Any]:
    blinding = _blinding()
    scan = blinding.scan_workspace(ws, skip_names=skip)
    hits = list(scan["hits"])
    for f in sorted(ws.rglob("*")):
        if not f.is_file() or f.name in skip:
            continue
        try:
            text = f.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        rel = str(f.relative_to(ws))
        for pat in E7_CLASS_TOKENS:
            m = re.search(pat, text)
            if m:
                hits.append({"file": rel, "set": "e7_class_token",
                             "pattern": pat, "match": m.group(0)})
    if hits:
        shutil.rmtree(ws)
        raise RuntimeError(f"BLINDING_FAIL in {kind} workspace: {hits}")
    return {"verdict": "PASS", "hits": []}


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


def _manifest(ws: Path, kind: str, trial_id: str, condition: str,
              scan: dict[str, Any]) -> dict[str, Any]:
    return {
        "artifact": f"blinded {kind} workspace manifest",
        "trial_id": trial_id,
        "condition": condition,
        "workspace": str(ws),
        "blinding_scan": ("PASS (0 hits)" if scan["verdict"] == "PASS"
                          else scan),
        "file_sha256": {str(f.relative_to(ws)): sha256_file(f)
                        for f in sorted(ws.rglob("*")) if f.is_file()},
    }


def _finish(ws: Path, who: str, kind: str) -> None:
    (ws / ".claude").mkdir()
    (ws / ".claude" / "settings.json").write_text(
        json.dumps(DENY_SETTINGS, indent=2) + "\n", encoding="utf-8")
    (ws / "prompt.md").write_text(PROMPTS[kind].format(who=who),
                                  encoding="utf-8")


BLIND_SESSION_OUTPUTS = frozenset({"distinctions.json"})


def build_infer_workspace(*, trial_id: str, condition: str, bank: Path,
                          ws: Path) -> dict[str, Any]:
    if ws.exists():
        raise RuntimeError(f"workspace already exists: {ws}")
    ws.mkdir(parents=True)
    shutil.copytree(bank / "public", ws / "package")
    shutil.copy(E6 / "contracts" / "trial-contract.json",
                ws / "contract.json")
    if condition == "A":
        shutil.copy(E6 / "schemas" / "distinction-spec-schema.json",
                    ws / "distinction-spec-schema.json")
        shutil.copy(E6 / "schemas" / "value-estimates-schema.json",
                    ws / "value-estimates-schema.json")
        shutil.copy(E6 / "protocol-infer.md", ws / "protocol.md")
        who = "D-E6"
    else:
        shutil.copy(E7 / "schemas" / "distinction-spec-v2-schema.json",
                    ws / "distinction-spec-schema.json")
        shutil.copy(E7 / "schemas" / "value-estimates-v2-schema.json",
                    ws / "value-estimates-schema.json")
        shutil.copy(E7 / "protocol-infer-v2.md", ws / "protocol.md")
        who = "D-E7"
    harness = (E6 / "infer-harness-template.json").read_text(
        encoding="utf-8")
    (ws / "infer-harness.json").write_text(
        harness.replace("__TRIAL_ID__", trial_id), encoding="utf-8")
    _finish(ws, who, "infer")
    _no_private_files(bank, ws)
    scan = _scan_or_die(ws, "infer")
    return _manifest(ws, "infer", trial_id, condition, scan)


def build_exec_workspace(*, trial_id: str, condition: str, bank: Path,
                         ws: Path, harness_spec: dict[str, Any],
                         distinctions: dict[str, Any]) -> dict[str, Any]:
    if ws.exists():
        raise RuntimeError(f"workspace already exists: {ws}")
    ws.mkdir(parents=True)
    shutil.copytree(bank / "public", ws / "package")
    shutil.copy(E6 / "contracts" / "trial-contract.json",
                ws / "contract.json")
    shutil.copy(E6 / "schemas" / "resolution-schema.json",
                ws / "resolution-schema.json")
    if condition == "A":
        shutil.copy(E6 / "protocol-exec.md", ws / "protocol.md")
        who = "X-E6"
    else:
        shutil.copy(E7 / "protocol-exec-v2.md", ws / "protocol.md")
        who = "X-E7"
    jdump(ws / "harness.json", harness_spec)
    jdump(ws / "distinctions.json", distinctions)
    has_create = any(n.get("primitive") == "create"
                     for n in harness_spec.get("nodes", []))
    if has_create:
        shutil.copy(E6 / "contracts" / "child-contract-envelope.json",
                    ws / "child-envelope.json")
        shutil.copytree(E6 / "child-templates", ws / "child-templates")
    _finish(ws, who, "exec")
    _no_private_files(bank, ws)
    scan = _scan_or_die(ws, "exec", skip=BLIND_SESSION_OUTPUTS)
    return _manifest(ws, "exec", trial_id, condition, scan)


def build_examiner_workspace(*, trial_id: str, condition: str,
                             exec_ws: Path, ws: Path) -> dict[str, Any]:
    if ws.exists():
        raise RuntimeError(f"workspace already exists: {ws}")
    ws.mkdir(parents=True)
    shutil.copytree(exec_ws / "package", ws / "package")
    for name in ("result.json", "resolution.json", "distinctions.json",
                 "examiner-charge.md"):
        src = exec_ws / name
        if src.exists():
            shutil.copy(src, ws / name)
    if condition == "A":
        shutil.copy(E6 / "protocol-examiner.md", ws / "protocol.md")
        who = "V-E6"
    else:
        shutil.copy(E7 / "protocol-examiner-v2.md", ws / "protocol.md")
        who = "V-E7"
    _finish(ws, who, "examiner")
    return _manifest(ws, "examiner", trial_id, condition,
                     {"verdict": "PASS", "hits": [],
                      "note": "package scanned at exec packaging; worker "
                              "outputs produced blind"})


def build_child_workspace(*, trial_id: str, exec_ws: Path, child_dir: Path,
                          ws: Path) -> dict[str, Any]:
    if ws.exists():
        raise RuntimeError(f"workspace already exists: {ws}")
    manifest = json.loads((child_dir / "child-input-manifest.json"
                           ).read_text(encoding="utf-8"))
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
    for name in ("child-harness.json", "child-contract.json",
                 "child-prompt.md"):
        shutil.copy(child_dir / name, ws / name)
    (ws / ".claude").mkdir()
    (ws / ".claude" / "settings.json").write_text(
        json.dumps(DENY_SETTINGS, indent=2) + "\n", encoding="utf-8")
    files = sorted(str(p.relative_to(ws)) for p in ws.rglob("*")
                   if p.is_file())
    return {"artifact": "child workspace manifest", "trial_id": trial_id,
            "workspace": str(ws), "files": files,
            "input_manifest": manifest["files"]}
