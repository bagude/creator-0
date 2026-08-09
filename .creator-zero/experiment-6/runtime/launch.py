"""Fresh-session launches for Experiment 6.

Every model session (inference, execution, examiner, child, shadow) passes
through the frozen Experiment 5 fresh launcher v0.2: sanitized environment,
explicit fresh session id, stream-confirmed identity, persisted provenance.
This module only assembles arguments; freshness enforcement lives in the
frozen launcher.
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

from .common import SESSION_TOOLS, e5_runtime

fresh_launcher = e5_runtime("fresh_launcher")

MODEL = "claude-fable-5"


def launch(*, ws: Path, log_path: Path, provenance_path: Path,
           creator: str, purpose: str, timeout: float = 900.0,
           dry_run: bool = False):
    return fresh_launcher.launch_fresh_child(
        prompt_path=ws / "prompt.md",
        workspace=ws,
        allowed_tools=list(SESSION_TOOLS),
        log_path=log_path,
        provenance_path=provenance_path,
        creator=creator,
        purpose=purpose,
        model=MODEL,
        timeout=timeout,
        dry_run=dry_run,
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ws", required=True)
    ap.add_argument("--log", required=True)
    ap.add_argument("--provenance", required=True)
    ap.add_argument("--creator", required=True)
    ap.add_argument("--purpose", required=True)
    ap.add_argument("--timeout", type=float, default=900.0)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    rec = launch(ws=Path(a.ws), log_path=Path(a.log),
                 provenance_path=Path(a.provenance), creator=a.creator,
                 purpose=a.purpose, timeout=a.timeout, dry_run=a.dry_run)
    ok = rec.get("exit_status") in (0, None)
    print(f"launched {a.creator}: exit={rec.get('exit_status')} "
          f"confirmed={rec.get('session_id_confirmed')}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
