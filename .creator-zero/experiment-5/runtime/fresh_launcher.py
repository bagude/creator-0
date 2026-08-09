"""Fresh-child sanitized launcher (Experiment 5 hardening 2).

All fresh child/model invocations must pass through this one deterministic
launcher. It constructs a sanitized environment (stripping every known
session-continuity variable), assigns an explicit fresh session identity,
launches the process, captures output, and persists exit status and full
provenance. Freshness is an enforced runtime property, not a prompt
convention: the launcher refuses to execute if any session-continuity
variable would reach the child (FRESHNESS_FAIL), and refuses session-id
reuse of the inherited session.

Motivated by the Experiment 4C freshness incident: a child CLI inherited
CLAUDE_CODE_SESSION_ID from the root environment and reported the root
session id, tainting freshness evidence until relaunch.
"""
from __future__ import annotations
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

_CZROOT = Path(__file__).resolve().parents[2]
if str(_CZROOT) not in sys.path:
    sys.path.insert(0, str(_CZROOT))

from formal.model import FAIL, PASS, FormalResult

# Exact environment variables known to carry session identity/continuity.
SESSION_CONTINUITY_EXACT = (
    "CLAUDE_CODE_SESSION_ID",
    "CLAUDE_CODE_CHILD_SESSION",
    "CLAUDE_CODE_REMOTE_SESSION_ID",
    "CLAUDE_SESSION_ID",
    "CLAUDE_CODE_SESSION_RESUME",
    "CLAUDE_CODE_CONTINUE",
    "CLAUDE_AFTER_LAST_COMPACT",
    "CLAUDE_PID",
)

# Pattern rule catching equivalent session-resume/continuation variables that
# are not on the exact list (defense against renamed/new variables).
SESSION_CONTINUITY_PATTERN = re.compile(
    r"^CLAUDE.*(SESSION|RESUME|CONTINUE|TRANSCRIPT|COMPACT)", re.IGNORECASE)


class FreshnessError(RuntimeError):
    """FRESHNESS_FAIL: launching would violate fresh-child guarantees."""


def is_session_continuity_var(name: str) -> bool:
    return name in SESSION_CONTINUITY_EXACT or bool(
        SESSION_CONTINUITY_PATTERN.match(name))


def sanitize_environment(env: Optional[dict[str, str]] = None
                         ) -> tuple[dict[str, str], list[str]]:
    """Return (sanitized copy, sorted names removed). Deterministic."""
    src = dict(os.environ if env is None else env)
    removed = sorted(n for n in src if is_session_continuity_var(n))
    for n in removed:
        del src[n]
    return src, removed


def assert_sanitized(env: dict[str, str]) -> None:
    """Reject execution if known session-continuity variables remain."""
    residual = sorted(n for n in env if is_session_continuity_var(n))
    if residual:
        raise FreshnessError(
            "FRESHNESS_FAIL: session-continuity variables would reach the "
            f"child process: {residual}")


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def confirm_stream_session_id(log_path: Path,
                              session_id: str) -> Optional[bool]:
    """Scan a stream-json log for the first reported session_id.

    Returns True/False when a session_id is observed, None when the log
    carries none (e.g. dry runs or non-stream output)."""
    if not log_path.exists():
        return None
    for line in log_path.read_text(encoding="utf-8",
                                   errors="replace").splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        sid = obj.get("session_id")
        if sid:
            return sid == session_id
    return None


def launch_fresh_child(*,
                       prompt_path: str | Path,
                       workspace: str | Path,
                       allowed_tools: list[str],
                       log_path: str | Path,
                       provenance_path: str | Path,
                       creator: str,
                       purpose: str,
                       model: str = "claude-fable-5",
                       session_id: Optional[str] = None,
                       executable: str = "claude",
                       extra_args: tuple[str, ...] = (),
                       env: Optional[dict[str, str]] = None,
                       timeout: Optional[float] = None,
                       dry_run: bool = False,
                       _dangerously_skip_sanitization: bool = False,
                       ) -> dict[str, Any]:
    """Sanitize, verify freshness, launch a fresh child session, persist
    provenance. Raises FreshnessError (FRESHNESS_FAIL) before any process
    creation if freshness cannot be guaranteed.

    `_dangerously_skip_sanitization` exists only so deterministic negative
    controls can demonstrate that the always-on rejection gate is independent
    of the scrubbing step; it never bypasses `assert_sanitized`.
    """
    prompt_path = Path(prompt_path)
    workspace = Path(workspace)
    log_path = Path(log_path)
    provenance_path = Path(provenance_path)
    if not prompt_path.exists():
        raise FileNotFoundError(f"prompt not found: {prompt_path}")
    if not workspace.is_dir():
        raise FileNotFoundError(f"workspace not found: {workspace}")

    source_env = dict(os.environ if env is None else env)
    inherited_session = source_env.get("CLAUDE_CODE_SESSION_ID", "")

    if _dangerously_skip_sanitization:
        child_env, removed = dict(source_env), []
    else:
        child_env, removed = sanitize_environment(source_env)

    def _refuse(reason: str) -> None:
        record = {
            "artifact": "fresh-child launch refusal (no process created)",
            "verdict": "FRESHNESS_FAIL",
            "reason": reason,
            "creator": creator,
            "purpose": purpose,
            "sanitizer": {
                "exact": list(SESSION_CONTINUITY_EXACT),
                "pattern": SESSION_CONTINUITY_PATTERN.pattern,
                "skip_sanitization_flag": _dangerously_skip_sanitization,
            },
            "refused_at": _utcnow(),
        }
        provenance_path.parent.mkdir(parents=True, exist_ok=True)
        provenance_path.write_text(json.dumps(record, indent=2) + "\n",
                                   encoding="utf-8")

    # Always-on rejection gate: no known session-continuity variable may
    # reach the child, whatever the caller did.
    try:
        assert_sanitized(child_env)
    except FreshnessError as e:
        _refuse(str(e))
        raise

    # Explicit fresh session identity; never the inherited session id.
    if session_id is None:
        session_id = str(uuid.uuid4())
    if inherited_session and session_id == inherited_session:
        msg = ("FRESHNESS_FAIL: requested session id equals the inherited "
               "root session id (session-identity reuse)")
        _refuse(msg)
        raise FreshnessError(msg)

    argv = [executable, "-p", prompt_path.read_text(encoding="utf-8"),
            "--session-id", session_id,
            "--model", model,
            "--allowedTools", " ".join(allowed_tools),
            "--output-format", "stream-json", "--verbose",
            *extra_args]

    record: dict[str, Any] = {
        "artifact": "fresh-child launch provenance",
        "creator": creator,
        "purpose": purpose,
        "fresh": True,
        "model": model,
        "session_id": session_id,
        "allowed_tools": list(allowed_tools),
        "working_directory": str(workspace),
        "prompt_path": str(prompt_path),
        "prompt_sha256": _sha256_file(prompt_path),
        "command_display": " ".join(
            shlex.quote(a) if a is not argv[2] else "<prompt text>"
            for a in argv),
        "environment_sanitization": {
            "removed_variables": removed,
            "exact_denylist": list(SESSION_CONTINUITY_EXACT),
            "pattern_denylist": SESSION_CONTINUITY_PATTERN.pattern,
            "residual_continuity_variables": [],
            "inherited_session_id_present": bool(inherited_session),
            "session_id_reuse": False,
        },
        "dry_run": dry_run,
        "started_at": _utcnow(),
    }

    if dry_run:
        record.update({"executed": False, "exit_status": None,
                       "finished_at": record["started_at"],
                       "session_id_confirmed": None})
    else:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("wb") as log:
            proc = subprocess.run(argv, cwd=str(workspace), env=child_env,
                                  stdout=log, stderr=subprocess.STDOUT,
                                  timeout=timeout)
        record.update({
            "executed": True,
            "exit_status": proc.returncode,
            "finished_at": _utcnow(),
            "log_path": str(log_path),
            "log_sha256": _sha256_file(log_path),
            "session_id_confirmed": confirm_stream_session_id(log_path,
                                                              session_id),
        })

    provenance_path.parent.mkdir(parents=True, exist_ok=True)
    provenance_path.write_text(json.dumps(record, indent=2) + "\n",
                               encoding="utf-8")
    return record


def freshness_result(provenance: dict[str, Any]) -> FormalResult:
    """Deterministic FreshChild verdict over a persisted launch provenance."""
    checks = {
        "launched_via_fresh_launcher":
            provenance.get("artifact") == "fresh-child launch provenance",
        "declared_fresh": provenance.get("fresh") is True,
        "sanitization_recorded":
            "environment_sanitization" in provenance,
        "no_residual_continuity_vars": not provenance.get(
            "environment_sanitization", {}).get(
                "residual_continuity_variables", ["<missing>"]),
        "no_session_id_reuse": provenance.get(
            "environment_sanitization", {}).get("session_id_reuse") is False,
        "explicit_session_id": bool(provenance.get("session_id")),
        "session_id_confirmed_in_stream": provenance.get(
            "session_id_confirmed") in (True, None),
    }
    failed = sorted(k for k, v in checks.items() if not v)
    status = PASS if not failed else FAIL
    return FormalResult(
        check="fresh_child", status=status,
        formal_relation="FreshChild ∧ SanitizedEnvironment",
        counterexample=({"violation": "FRESHNESS_FAIL",
                         "failed_clauses": failed} if failed else None),
        evidence=[f"session_id: {provenance.get('session_id')}",
                  "removed variables: "
                  f"{provenance.get('environment_sanitization', {}).get('removed_variables')}",
                  f"session_id_confirmed: {provenance.get('session_id_confirmed')}"],
        assumptions=[
            "session_id_confirmed=None (no stream log or dry run) does not "
            "refute freshness; True confirms it; False fails it.",
            "The launcher is the sole legal child-invocation path; the "
            "topology guard cross-checks that no child ran outside it.",
        ],
        detail={"clauses": checks})
