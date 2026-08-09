"""Launch a trial parent or child session via the deterministic fresh
launcher (Experiment 5). The sole invocation path for every model session.

For child launches, appends the preregistered realization events (create +
persist/child_launch) to the merged trial ledger and records the
CHILD_LAUNCHED lifecycle state — creation is observable before the child
runs.
"""
from __future__ import annotations
import argparse
import importlib.util
import sys
from pathlib import Path

E5 = Path(__file__).resolve().parents[1]


def _load_mod(name):
    spec = importlib.util.spec_from_file_location(
        f"e5l_{name}", E5 / "runtime" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


fresh_launcher = _load_mod("fresh_launcher")
rd = _load_mod("root_driver")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("role", choices=["parent", "child", "shadow"])
    ap.add_argument("trial_id")
    ap.add_argument("--timeout", type=float, default=1500.0)
    ap.add_argument("--shadow-dir")
    a = ap.parse_args()
    tid = a.trial_id
    td = rd.trial_dir(tid) if a.role != "shadow" else Path(a.shadow_dir)

    if a.role == "parent":
        ws = rd.ws_dir(tid)
        rec = fresh_launcher.launch_fresh_child(
            prompt_path=ws / "parent-prompt.md", workspace=ws,
            allowed_tools=rd.ALLOWED_TOOLS,
            log_path=td / "parent-session.log",
            provenance_path=td / "parent-launch-provenance.json",
            creator="root-e5", purpose=f"trial {tid} blinded decision-maker "
                                       "(parent Creator C-E5)",
            timeout=a.timeout)
    elif a.role == "child":
        ws = rd.child_ws_dir(tid)
        rd.append_trial_events(tid, [
            {"event_id": "root-create-child", "label": "create",
             "actor": "node:create-child", "timestamp": rd.now(),
             "artifact_refs": ["child/child-contract.json",
                               "child/child-harness.json"],
             "metadata": {"completes_node": "create-child",
                          "note": "validated child realization via fresh "
                                  "launcher"}},
        ])
        rec = fresh_launcher.launch_fresh_child(
            prompt_path=ws / "child-prompt.md", workspace=ws,
            allowed_tools=rd.ALLOWED_TOOLS,
            log_path=td / "child" / "child-session.log",
            provenance_path=td / "child" / "launch-provenance.json",
            creator=f"trial-{tid}-parent",
            purpose=f"trial {tid} validated child (parent-authored spec)",
            timeout=a.timeout)
        rd.append_trial_events(tid, [
            {"event_id": "root-child-launch", "label": "persist",
             "actor": "root", "timestamp": rd.now(),
             "artifact_refs": ["child/launch-provenance.json"],
             "metadata": {"event_kind": "child_launch",
                          "note": "fresh sanitized launch provenance "
                                  "persisted"}},
        ])
        rd.lifecycle(tid, "CHILD_LAUNCHED",
                     session_id=rec["session_id"],
                     exit_status=rec["exit_status"])
    else:  # shadow (CONTROL_ONLY)
        ws = Path(a.shadow_dir) / "ws"
        rec = fresh_launcher.launch_fresh_child(
            prompt_path=ws / "prompt.md", workspace=ws,
            allowed_tools=rd.ALLOWED_TOOLS,
            log_path=td / "session.log",
            provenance_path=td / "launch-provenance.json",
            creator="root-e5-control", purpose=f"CONTROL_ONLY shadow for "
                                               f"{tid}",
            timeout=a.timeout)

    print(f"{tid} {a.role}: exit={rec['exit_status']} "
          f"session={rec['session_id']} "
          f"confirmed={rec['session_id_confirmed']}")


if __name__ == "__main__":
    main()
