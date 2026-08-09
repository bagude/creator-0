"""Deterministic stream-json session audit (Experiment 5).

Parses a claude CLI stream-json log and extracts: tool-use counts, file
paths touched outside the session workspace, uses of tools outside the
granted set, uses of process-spawning tools, reported session id, and the
final result record. Used as evidence input to the topology guard and the
freshness check. Read-only; never modifies the log.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any

SPAWN_CAPABLE_TOOLS = {"Bash", "Task", "Agent", "Workflow"}


def audit_stream_log(log_path: str | Path, *, workspace: str | Path,
                     allowed_tools: list[str]) -> dict[str, Any]:
    log_path = Path(log_path)
    workspace = str(Path(workspace).resolve())
    counts: dict[str, int] = {}
    disallowed: list[dict[str, Any]] = []
    spawn: list[dict[str, Any]] = []
    outside: list[str] = []
    session_ids: list[str] = []
    result: dict[str, Any] | None = None
    parse_errors = 0

    for line in log_path.read_text(encoding="utf-8",
                                   errors="replace").splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            parse_errors += 1
            continue
        sid = obj.get("session_id")
        if sid and sid not in session_ids:
            session_ids.append(sid)
        if obj.get("type") == "result":
            result = {k: obj.get(k) for k in
                      ("subtype", "is_error", "duration_ms", "num_turns",
                       "total_cost_usd")}
        msg = obj.get("message")
        if not isinstance(msg, dict):
            continue
        for block in msg.get("content") or []:
            if not isinstance(block, dict) or block.get("type") != "tool_use":
                continue
            name = str(block.get("name"))
            counts[name] = counts.get(name, 0) + 1
            entry = {"tool": name, "id": block.get("id")}
            if name not in allowed_tools:
                disallowed.append(entry)
            if name in SPAWN_CAPABLE_TOOLS:
                spawn.append(entry)
            inp = block.get("input") or {}
            for key in ("file_path", "path", "notebook_path"):
                p = inp.get(key)
                if isinstance(p, str) and p.startswith("/") and \
                        not p.startswith(workspace):
                    outside.append(p)

    return {
        "log_path": str(log_path),
        "workspace": workspace,
        "allowed_tools": list(allowed_tools),
        "tool_use_counts": dict(sorted(counts.items())),
        "disallowed_tool_uses": disallowed,
        "spawn_capable_tool_uses": spawn,
        "file_paths_outside_workspace": sorted(set(outside)),
        "session_ids_reported": session_ids,
        "session_result": result,
        "parse_errors": parse_errors,
    }
