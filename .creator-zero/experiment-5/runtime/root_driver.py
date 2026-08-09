"""Root-side deterministic trial driver (Experiment 5).

Operational glue over the frozen runtime modules and the Formal Semantics
Kernel. Added after the preregistration freeze as pure orchestration: every
governed judgment it records is produced by the frozen modules
(decision_validator, topology_guard, proposal_observer, fresh_launcher,
session_audit, task-bank verifiers, kernel checks); this driver only
sequences them, copies artifacts, and appends the preregistered root
realization events. It never chooses or rewrites decisions and never solves
substantive tasks.

Subcommands:
    prepare TID          build blinded workspace + lifecycle PREPARED
    after-parent TID     collect parent session; validate decision; branch:
                         local -> verify; create -> validate bundle + build
                         child workspace (stops before launch)
    after-child TID      collect child session; child formal checks;
                         mechanical integration + verification
    finalize TID         merged-ledger refinement, freshness, guard,
                         lifecycle close-out, trial record
"""
from __future__ import annotations
import argparse
import importlib.util
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

E5 = Path(__file__).resolve().parents[1]
CZROOT = E5.parent
if str(CZROOT) not in sys.path:
    sys.path.insert(0, str(CZROOT))

import formal
from formal.serialization import lts_to_json
from formal.trace import parse_runtime_ledger

SCRATCH = Path("/tmp/claude-0/-home-user-creator-0/"
               "f185e5e6-15ee-5d4d-b18e-9b212cd19c12/scratchpad/e5")
ALLOWED_TOOLS = ["Read", "Write"]


def _load_mod(name):
    spec = importlib.util.spec_from_file_location(
        f"e5_{name}", E5 / "runtime" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


fresh_launcher = _load_mod("fresh_launcher")
proposal_observer = _load_mod("proposal_observer")
decision_validator = _load_mod("decision_validator")
topology_guard = _load_mod("topology_guard")
session_audit = _load_mod("session_audit")
package_trial = _load_mod("package_trial")


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def jload(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def jdump(p, obj):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    Path(p).write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")


def trial_dir(tid):
    d = E5 / "trials" / tid
    d.mkdir(parents=True, exist_ok=True)
    return d


def ws_dir(tid):
    return SCRATCH / tid / "parent-ws"


def child_ws_dir(tid):
    return SCRATCH / tid / "child-ws"


def lifecycle(tid, state, **extra):
    rec = {"state": state, "at": now(), **extra}
    with (trial_dir(tid) / "lifecycle.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")
    return rec


def lifecycle_states(tid):
    p = trial_dir(tid) / "lifecycle.jsonl"
    if not p.exists():
        return []
    return [json.loads(l)["state"]
            for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def append_trial_events(tid, events):
    """Append root realization events to the merged trial ledger."""
    p = trial_dir(tid) / "runtime-ledger.jsonl"
    with p.open("a", encoding="utf-8") as f:
        for ev in events:
            f.write(json.dumps(ev) + "\n")


def formal_result_out(tid, name, res):
    jdump(trial_dir(tid) / "formal-results" / f"{name}.json", res.to_dict())
    print(f"[{tid}] {name}: {res.status}")
    return res


def cmd_prepare(tid):
    bank = E5 / "task-bank" / tid
    ws = ws_dir(tid)
    manifest = package_trial.build_workspace(
        trial_id=tid, bank_dir=bank, workspace=ws)
    jdump(trial_dir(tid) / "package-manifest.json", manifest)
    shutil.copy(bank / "public" / "task.json", trial_dir(tid) / "task.json")
    # Frozen instantiated harness + compiled LTS for the record.
    harness = jload(ws / "harness.json")
    contract = jload(E5 / "contracts" / "trial-contract.json")
    lts = formal.compile_harness_spec(harness, contract)
    (trial_dir(tid) / "harness.json").write_text(
        json.dumps(harness, indent=2) + "\n", encoding="utf-8")
    (trial_dir(tid) / "lts.json").write_text(lts_to_json(lts),
                                             encoding="utf-8")
    lifecycle(tid, "PREPARED", workspace=str(ws),
              blinding_scan=manifest["blinding_scan"])
    print(f"[{tid}] prepared; workspace {ws}")


def _collect(src, dst):
    if src.exists():
        if src.is_dir():
            shutil.copytree(src, dst, dirs_exist_ok=True)
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(src, dst)
        return True
    return False


def cmd_after_parent(tid):
    ws = ws_dir(tid)
    td = trial_dir(tid)
    # 1. Collect parent deliverables.
    for name in ("decision.json", "resolution.json", "result.json",
                 "result-pending.json"):
        _collect(ws / name, td / name)
    _collect(ws / "child", td / "child")
    if not (ws / "execution-ledger.jsonl").exists():
        raise SystemExit(f"[{tid}] parent wrote no execution ledger")
    shutil.copy(ws / "execution-ledger.jsonl",
                td / "parent-execution-ledger.jsonl")
    shutil.copy(ws / "execution-ledger.jsonl", td / "runtime-ledger.jsonl")

    # 2. Session audit.
    audit = session_audit.audit_stream_log(
        td / "parent-session.log", workspace=ws, allowed_tools=ALLOWED_TOOLS)
    jdump(td / "parent-session-audit.json", audit)

    # 3. Decision validation.
    decision = jload(td / "decision.json")
    lifecycle(tid, "DECISION_PROPOSED", decision=decision.get("decision"))
    dv = decision_validator.validate_decision(decision, tid)
    formal_result_out(tid, "decision-validation", dv)
    if dv.status != "PASS":
        lifecycle(tid, "DECISION_INVALID",
                  violation=dv.counterexample.get("violation"))
        print(f"[{tid}] decision INVALID; no realization permitted")
        return
    lifecycle(tid, "DECISION_VALIDATED")

    dec = decision["decision"]
    trace = parse_runtime_ledger(td / "parent-execution-ledger.jsonl",
                                 strict=True)

    # 4. Capability observability over the parent trace.
    artifacts = ["decision.json"]
    if dec == "CREATE":
        artifacts += [f"child/{f}"
                      for f in decision_validator.CHILD_BUNDLE_FILES]
    obs = proposal_observer.check_all_capability_artifacts(trace, artifacts)
    formal_result_out(tid, "observability", obs)

    if dec == "DO_NOT_CREATE":
        lifecycle(tid, "LOCAL_EXECUTION",
                  note="in-session local resolution accepted at validation; "
                       "no realization authority exercised")
        verify = E5 / "task-bank" / tid / "private" / "verify.py"
        subprocess.run([sys.executable, str(verify), "--mode", "verify-local",
                        "--result", str(td / "result.json"),
                        "--out", str(td / "verification.json")], check=True)
        append_trial_events(tid, [{
            "event_id": "root-verify-local", "label": "verify",
            "actor": "node:verify-trial-local", "timestamp": now(),
            "artifact_refs": ["verification.json"],
            "metadata": {"completes_node": "verify-trial-local",
                         "note": "deterministic root verification"}}])
        lifecycle(tid, "RESULT_VERIFIED",
                  task_verified=jload(td / "verification.json")["task_verified"])
        print(f"[{tid}] local branch processed")
        return

    # CREATE branch: validate bundle, build child workspace, stop.
    lifecycle(tid, "CHILD_SPEC_PROPOSED")
    task = jload(td / "task.json")
    trial_contract = jload(E5 / "contracts" / "trial-contract.json")
    child_env = jload(E5 / "contracts" / "child-contract-envelope.json")
    package_files = [str(p.relative_to(ws)) for p in (ws / "package").rglob("*")
                     if p.is_file()]
    res, parts = decision_validator.validate_child_bundle(
        td / "child", trial_contract, child_env, package_files,
        task.get("clean_room_exclusions", []))
    formal_result_out(tid, "child-bundle-validation", res)
    if "attenuation_vs_trial" in parts:
        formal_result_out(tid, "attenuation", parts["attenuation_vs_trial"])
    if res.status != "PASS":
        lifecycle(tid, "CHILD_INVALID",
                  violation=res.counterexample.get("violation"))
        print(f"[{tid}] child bundle INVALID; realization refused")
        return
    (trial_dir(tid) / "child" / "child-lts.json").write_text(
        lts_to_json(parts["child_lts"]), encoding="utf-8")
    lifecycle(tid, "CHILD_VALIDATED")

    cws = child_ws_dir(tid)
    if cws.exists():
        raise SystemExit(f"[{tid}] child workspace already exists")
    (cws / "inputs").mkdir(parents=True)
    manifest = parts["manifest"]
    for rel in manifest["files"]:
        src = ws / rel
        shutil.copy(src, cws / "inputs" / Path(rel).name)
    shutil.copy(td / "child" / "child-harness.json", cws / "child-harness.json")
    shutil.copy(td / "child" / "child-contract.json",
                cws / "child-contract.json")
    shutil.copy(td / "child" / "child-prompt.md", cws / "child-prompt.md")
    (cws / ".claude").mkdir()
    (cws / ".claude" / "settings.json").write_text(
        json.dumps(package_trial.DENY_SETTINGS, indent=2) + "\n",
        encoding="utf-8")
    jdump(td / "child" / "child-workspace-manifest.json", {
        "files": sorted(str(p.relative_to(cws)) for p in cws.rglob("*")
                        if p.is_file()),
        "clean_room_exclusions": task.get("clean_room_exclusions", []),
    })
    print(f"[{tid}] child validated; workspace {cws} ready for launch")


def cmd_after_child(tid):
    td = trial_dir(tid)
    cws = child_ws_dir(tid)
    task = jload(td / "task.json")
    plan = jload(td / "child" / "integration-plan.json")

    audit = session_audit.audit_stream_log(
        td / "child" / "child-session.log", workspace=cws,
        allowed_tools=ALLOWED_TOOLS)
    jdump(td / "child" / "child-session-audit.json", audit)

    for name in ("execution-ledger.jsonl", "result.json",
                 plan["child_deliverable"]):
        if not _collect(cws / name, td / "child" / name):
            print(f"[{tid}] WARNING: child did not produce {name}")

    # Child formal checks.
    child_contract = jload(td / "child" / "child-contract.json")
    child_harness = jload(td / "child" / "child-harness.json")
    clts = formal.compile_harness_spec(child_harness, child_contract)
    ctrace = parse_runtime_ledger(td / "child" / "execution-ledger.jsonl",
                                  strict=True)
    formal_result_out(tid, "child-refinement",
                      formal.check_refinement(ctrace, clts,
                                              require_completion=True))
    cobs = proposal_observer.check_capability_observability(
        ctrace, plan["child_deliverable"])
    formal_result_out(tid, "child-observability", cobs)
    prov = jload(td / "child" / "launch-provenance.json")
    formal_result_out(tid, "freshness-child",
                      fresh_launcher.freshness_result(prov))

    # Root realization events (create/child_launch already appended at
    # launch time by the launch step; append return + verify here).
    append_trial_events(tid, [
        {"event_id": "root-child-return", "label": "return",
         "actor": "node:child-return", "timestamp": now(),
         "artifact_refs": [f"child/{plan['child_deliverable']}",
                           "child/result.json",
                           "child/execution-ledger.jsonl"],
         "metadata": {"completes_node": "child-return",
                      "event_kind": "child_return"}},
    ])
    lifecycle(tid, "CHILD_RETURNED")

    # Mechanical integration + deterministic verification.
    verify = E5 / "task-bank" / tid / "private" / "verify.py"
    subprocess.run(
        [sys.executable, str(verify), "--mode", "integrate-and-verify",
         "--plan", str(td / "child" / "integration-plan.json"),
         "--child-deliverable", str(td / "child" / plan["child_deliverable"]),
         "--integrated-out", str(td / "result.json"),
         "--out", str(td / "verification.json")], check=True)
    append_trial_events(tid, [{
        "event_id": "root-verify-child", "label": "verify",
        "actor": "node:verify-trial-child", "timestamp": now(),
        "artifact_refs": ["verification.json", "result.json"],
        "metadata": {"completes_node": "verify-trial-child",
                     "note": "mechanical integration per parent plan + "
                             "deterministic root verification"}}])
    lifecycle(tid, "RESULT_VERIFIED",
              task_verified=jload(td / "verification.json")["task_verified"])
    print(f"[{tid}] child branch processed")


def cmd_finalize(tid):
    td = trial_dir(tid)
    decision = jload(td / "decision.json")["decision"]
    contract = jload(E5 / "contracts" / "trial-contract.json")
    harness = jload(td / "harness.json")
    lts = formal.compile_harness_spec(harness, contract)
    trace = parse_runtime_ledger(td / "runtime-ledger.jsonl", strict=True)
    formal_result_out(tid, "refinement",
                      formal.check_refinement(trace, lts,
                                              require_completion=False))
    prov = jload(td / "parent-launch-provenance.json")
    formal_result_out(tid, "freshness-parent",
                      fresh_launcher.freshness_result(prov))

    provs = []
    cp = td / "child" / "launch-provenance.json"
    if cp.exists():
        provs.append(jload(cp))
    audit = jload(td / "parent-session-audit.json")
    guard = topology_guard.guard_trial(
        decision=decision, lifecycle_states=lifecycle_states(tid) +
        ["FORMALLY_CHECKED"], trace=trace, launch_provenances=provs,
        session_audit=audit)
    formal_result_out(tid, "topology-guard", guard)
    lifecycle(tid, "FORMALLY_CHECKED")
    print(f"[{tid}] finalized")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["prepare", "after-parent", "after-child",
                                    "finalize"])
    ap.add_argument("trial_id")
    a = ap.parse_args()
    {"prepare": cmd_prepare, "after-parent": cmd_after_parent,
     "after-child": cmd_after_child, "finalize": cmd_finalize}[a.cmd](a.trial_id)


if __name__ == "__main__":
    main()
