"""Batch orchestration helper for Experiment 6 (root-side glue only).

Sequences the deterministic drivers and the fresh launcher over many
trials, with bounded parallel session launches. Adds no judgment: every
governed decision stays inside the frozen drivers/kernel.

    python3 tools/orchestrate.py infer  t1 t2 ... [--parallel 4]
    python3 tools/orchestrate.py exec   t1 t2 ... [--shadow] [--parallel 4]
    python3 tools/orchestrate.py post   t1 t2 ... [--shadow] [--parallel 4]

`infer`: prepare -> launch S1 session -> after (validation + pipeline).
`exec` : prepare-exec -> launch S6 session -> after-exec.
`post` : family-specific tail: examiner or child launch + collection,
         then finalize.
"""
from __future__ import annotations
import argparse
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

E6 = Path(__file__).resolve().parents[1]
SC = Path("/tmp/claude-0/-home-user-creator-0/"
          "113f7cc5-237e-5d6a-8867-a97fd89c58dd/scratchpad/e6")
PY = sys.executable


def run(args: list[str]) -> int:
    print("+", " ".join(str(a) for a in args), flush=True)
    return subprocess.run(args, cwd=E6).returncode


def trial_dir(tid: str, shadow: bool) -> Path:
    d = (E6 / "pilot" / "trials" / tid
         if (E6 / "pilot" / "task-bank" / tid).is_dir()
         else E6 / "trials" / tid)
    return d / "shadow" if shadow else d


def ws(tid: str, shadow: bool, name: str) -> Path:
    return (SC / tid / ("shadow" if shadow else "primary") / name
            if name != "infer-ws" else SC / tid / name)


def launch(tid: str, shadow: bool, kind: str) -> int:
    td = trial_dir(tid, shadow)
    wsp = ws(tid, shadow, f"{kind}-ws")
    sub = {"infer": ("", "infer"), "exec": ("", "exec"),
           "examiner": ("examiner/", "examiner"),
           "child": ("child/", "child")}[kind]
    log = td / f"{sub[0]}{sub[1]}-session.log"
    prov = td / (f"{sub[0]}launch-provenance.json" if kind in
                 ("examiner", "child") else
                 f"{kind}-launch-provenance.json")
    creator = {"infer": "D-E6", "exec": "X-E6", "examiner": "V-E6",
               "child": "C-E6-child"}[kind] + f"-{tid}" + \
        ("-shadow" if shadow else "")
    purpose = (f"Experiment 6 {'shadow ' if shadow else ''}{kind} session "
               f"for trial {tid}")
    if kind == "child":
        # child prompt is the parent's authored child-prompt.md
        wsp_prompt = wsp / "prompt.md"
        if not wsp_prompt.exists():
            (wsp / "prompt.md").write_text(
                (wsp / "child-prompt.md").read_text(encoding="utf-8"),
                encoding="utf-8")
    return run([PY, "-m", "runtime.launch", "--ws", str(wsp),
                "--log", str(log), "--provenance", str(prov),
                "--creator", creator, "--purpose", purpose])


def family_of(tid: str, shadow: bool) -> str:
    td = trial_dir(tid, shadow)
    topo = json.loads((td / "topology.json").read_text(encoding="utf-8"))
    return topo["family"]


def do_infer(tid: str) -> tuple[str, bool]:
    if not ws(tid, False, "infer-ws").exists():
        if run([PY, "-m", "runtime.infer_driver", "prepare", tid]):
            return tid, False
    if launch(tid, False, "infer"):
        return tid, False
    return tid, run([PY, "-m", "runtime.infer_driver", "after", tid]) == 0


def do_exec(tid: str, shadow: bool) -> tuple[str, bool]:
    sh = ["--shadow"] if shadow else []
    if not ws(tid, shadow, "exec-ws").exists():
        if run([PY, "-m", "runtime.exec_driver", "prepare-exec", tid, *sh]):
            return tid, False
    if launch(tid, shadow, "exec"):
        return tid, False
    return tid, run([PY, "-m", "runtime.exec_driver", "after-exec", tid,
                     *sh]) == 0


def do_post(tid: str, shadow: bool) -> tuple[str, bool]:
    sh = ["--shadow"] if shadow else []
    fam = family_of(tid, shadow)
    branch = None
    if fam == "branching":
        td = trial_dir(tid, shadow)
        branch = json.loads((td / "decision.json").read_text(
            encoding="utf-8"))["decision"]
    needs_child = fam == "isolated-child" or (fam == "branching" and
                                              branch == "CREATE")
    needs_examiner = fam == "local-independent-verify"
    if needs_child:
        if run([PY, "-m", "runtime.exec_driver", "prepare-child", tid,
                *sh]):
            return tid, False
        if launch(tid, shadow, "child"):
            return tid, False
        if run([PY, "-m", "runtime.exec_driver", "after-child", tid, *sh]):
            return tid, False
    if needs_examiner:
        if run([PY, "-m", "runtime.exec_driver", "prepare-examiner", tid,
                *sh]):
            return tid, False
        if launch(tid, shadow, "examiner"):
            return tid, False
        if run([PY, "-m", "runtime.exec_driver", "after-examiner", tid,
                *sh]):
            return tid, False
    return tid, run([PY, "-m", "runtime.exec_driver", "finalize", tid,
                     *sh]) == 0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("phase", choices=["infer", "exec", "post"])
    ap.add_argument("trials", nargs="+")
    ap.add_argument("--shadow", action="store_true")
    ap.add_argument("--parallel", type=int, default=4)
    a = ap.parse_args()
    fn = {"infer": lambda t: do_infer(t),
          "exec": lambda t: do_exec(t, a.shadow),
          "post": lambda t: do_post(t, a.shadow)}[a.phase]
    results = {}
    with ThreadPoolExecutor(max_workers=a.parallel) as pool:
        for tid, ok in pool.map(fn, a.trials):
            results[tid] = ok
            print(f"== {tid}: {'OK' if ok else 'FAILED'}", flush=True)
    bad = [t for t, ok in results.items() if not ok]
    print(json.dumps({"phase": a.phase, "shadow": a.shadow,
                      "ok": [t for t in results if results[t]],
                      "failed": bad}))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
