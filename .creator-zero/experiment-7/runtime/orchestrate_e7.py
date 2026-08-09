"""Batch orchestration for Experiment 7 (root-side glue only).

    python3 -m runtime.orchestrate_e7 infer A t1 t2 ... [--parallel 4]
    python3 -m runtime.orchestrate_e7 exec  A t1 ...    [--shadow]
    python3 -m runtime.orchestrate_e7 post  A t1 ...    [--shadow]

Sequences the deterministic driver and the frozen fresh launcher over many
trials with bounded parallel session launches. Adds no judgment. Cross-
condition isolation is structural: workspaces live under per-condition
roots and the driver never reads the other condition's outputs."""
from __future__ import annotations
import argparse
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .common import (E7, EXAMINER_FAMILIES, CHILD_FAMILIES, e5_runtime,
                     trial_dir, ws)

PY = sys.executable
fresh_launcher = e5_runtime("fresh_launcher")


def run(args: list[str]) -> int:
    print("+", " ".join(str(a) for a in args), flush=True)
    return subprocess.run(args, cwd=E7).returncode


def launch(tid: str, cond: str, shadow: bool, kind: str) -> int:
    td = trial_dir(tid, cond, shadow)
    wsp = ws(tid, cond, shadow, f"{kind}-ws")
    sub = {"infer": ("", "infer"), "exec": ("", "exec"),
           "examiner": ("examiner/", "examiner"),
           "child": ("child/", "child")}[kind]
    log = td / f"{sub[0]}{sub[1]}-session.log"
    prov = td / (f"{sub[0]}launch-provenance.json" if kind in
                 ("examiner", "child") else
                 f"{kind}-launch-provenance.json")
    creator = {"infer": "D-E7", "exec": "X-E7", "examiner": "V-E7",
               "child": "C-E7-child"}[kind] + f"-{cond}-{tid}" + \
        ("-shadow" if shadow else "")
    if kind == "child" and not (wsp / "prompt.md").exists():
        (wsp / "prompt.md").write_text(
            (wsp / "child-prompt.md").read_text(encoding="utf-8"),
            encoding="utf-8")
    try:
        rec = fresh_launcher.launch_fresh_child(
            prompt_path=wsp / "prompt.md", workspace=wsp,
            allowed_tools=["Read", "Write"], log_path=log,
            provenance_path=prov,
            creator=creator,
            purpose=f"E7 {'shadow ' if shadow else ''}{kind} session, "
                    f"condition {cond}, trial {tid}",
            model="claude-fable-5", timeout=900.0)
    except Exception as e:
        print(f"[{tid}/{cond}] launch error: {e}", flush=True)
        return 1
    return 0 if rec.get("exit_status") in (0, None) else 1


def family(tid: str, cond: str, shadow: bool) -> str:
    td = trial_dir(tid, cond, shadow)
    return json.loads((td / "topology.json").read_text(
        encoding="utf-8"))["family"]


def do_infer(tid: str, cond: str) -> tuple[str, bool]:
    td = trial_dir(tid, cond)
    if (td / "candidate-ranking.json").exists():
        return tid, True
    if not ws(tid, cond, False, "infer-ws").exists():
        if run([PY, "-m", "runtime.driver", "infer-prepare", tid, cond]):
            return tid, False
    if not (td / "infer-launch-provenance.json").exists():
        if launch(tid, cond, False, "infer"):
            return tid, False
    return tid, run([PY, "-m", "runtime.driver", "infer-after", tid,
                     cond]) == 0


def do_exec(tid: str, cond: str, shadow: bool) -> tuple[str, bool]:
    sh = ["--shadow"] if shadow else []
    td = trial_dir(tid, cond, shadow)
    if (td / "resolution.json").exists():
        return tid, True
    if not ws(tid, cond, shadow, "exec-ws").exists():
        if run([PY, "-m", "runtime.driver", "exec-prepare", tid, cond,
                *sh]):
            return tid, False
    if not (td / "exec-launch-provenance.json").exists():
        if launch(tid, cond, shadow, "exec"):
            return tid, False
    return tid, run([PY, "-m", "runtime.driver", "exec-after", tid, cond,
                     *sh]) == 0


def do_post(tid: str, cond: str, shadow: bool) -> tuple[str, bool]:
    sh = ["--shadow"] if shadow else []
    td = trial_dir(tid, cond, shadow)
    if (td / "observed-value.json").exists():
        return tid, True
    fam = family(tid, cond, shadow)
    branch = None
    if fam == "branching":
        branch = json.loads((td / "decision.json").read_text(
            encoding="utf-8"))["decision"]
    needs_child = fam in CHILD_FAMILIES or (fam == "branching"
                                            and branch == "CREATE")
    needs_examiner = fam in EXAMINER_FAMILIES
    if needs_child:
        if not ws(tid, cond, shadow, "child-ws").exists():
            if run([PY, "-m", "runtime.driver", "child-prepare", tid,
                    cond, *sh]):
                return tid, False
        if not (td / "child" / "launch-provenance.json").exists():
            if launch(tid, cond, shadow, "child"):
                return tid, False
        if run([PY, "-m", "runtime.driver", "child-after", tid, cond,
                *sh]):
            return tid, False
    if needs_examiner:
        if not ws(tid, cond, shadow, "examiner-ws").exists():
            if run([PY, "-m", "runtime.driver", "examiner-prepare", tid,
                    cond, *sh]):
                return tid, False
        if not (td / "examiner" / "launch-provenance.json").exists():
            if launch(tid, cond, shadow, "examiner"):
                return tid, False
        if run([PY, "-m", "runtime.driver", "examiner-after", tid, cond,
                *sh]):
            return tid, False
    return tid, run([PY, "-m", "runtime.driver", "finalize", tid, cond,
                     *sh]) == 0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("phase", choices=["infer", "exec", "post"])
    ap.add_argument("condition", choices=["A", "B"])
    ap.add_argument("trials", nargs="+")
    ap.add_argument("--shadow", action="store_true")
    ap.add_argument("--parallel", type=int, default=4)
    a = ap.parse_args()
    fn = {"infer": lambda t: do_infer(t, a.condition),
          "exec": lambda t: do_exec(t, a.condition, a.shadow),
          "post": lambda t: do_post(t, a.condition, a.shadow)}[a.phase]
    results = {}
    with ThreadPoolExecutor(max_workers=a.parallel) as pool:
        for tid, ok in pool.map(fn, a.trials):
            results[tid] = ok
            print(f"== {tid}/{a.condition}: {'OK' if ok else 'FAILED'}",
                  flush=True)
    bad = [t for t, ok in results.items() if not ok]
    print(json.dumps({"phase": a.phase, "condition": a.condition,
                      "shadow": a.shadow, "failed": bad}))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
