"""Root-side deterministic execution driver (Experiment 6, stages S6-S7).

Pure orchestration over the frozen modules: every governed judgment is
produced by the frozen topology-theory kernel, the Formal Semantics Kernel,
the fresh launcher v0.2, the session auditor, and the per-task preregistered
verifiers. This driver sequences them, copies artifacts, and appends the
preregistered root realization events. It never chooses or rewrites
decisions and never solves substantive tasks.

Per-trial flow (primary or shadow):
    prepare-exec     build blinded exec workspace for the (selected or
                     preregistered shadow) topology
    <launch exec session via launch.py>
    after-exec       collect + audit; validate outputs; branch per family
    prepare-child    validate child bundle, build child workspace
    <launch child>   after-child: collect, child formal checks
    prepare-examiner build examiner workspace
    <launch examiner> after-examiner: collect
    finalize         merged-ledger refinement (require_completion=True),
                     freshness, guard, deterministic verification, runtime
                     record, operationalized observed value, mechanical
                     prediction evaluation, calibration, evidence events
"""
from __future__ import annotations
import argparse
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from .common import (CZROOT, COST_DENOMINATOR, E6, FAMILY_CALLS, bank_dir,
                     e5_runtime, family_of, jdump, jload, now, sha256_file,
                     trial_contract, child_envelope, tt_mod, ws_root,
                     SESSION_TOOLS)
from . import package_ws
from . import collect as collectmod

sys.path.insert(0, str(CZROOT))
import formal  # noqa: E402
from formal.serialization import lts_to_json  # noqa: E402
from formal.trace import parse_runtime_ledger  # noqa: E402

fresh_launcher = e5_runtime("fresh_launcher")
session_audit = e5_runtime("session_audit")

ROLES = ("clean_room_implementer", "adversarial_searcher",
         "independent_decomposer", "independent_verifier")


def _tdir(tid: str, shadow: bool) -> Path:
    from .common import trial_dir, pilot_trial_dir
    if (E6 / "pilot" / "task-bank" / tid).is_dir():
        d = pilot_trial_dir(tid)
    else:
        d = E6 / "trials" / tid
    if shadow:
        d = d / "shadow"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _pipeline_dir(tid: str) -> Path:
    """Shadow runs reuse the primary trial's frozen pipeline artifacts."""
    if (E6 / "pilot" / "task-bank" / tid).is_dir():
        return E6 / "pilot" / "trials" / tid
    return E6 / "trials" / tid


def _ws(tid: str, shadow: bool, name: str) -> Path:
    return ws_root(tid) / ("shadow" if shadow else "primary") / name


def lifecycle(td: Path, state: str, **extra):
    rec = {"state": state, "at": now(), **extra}
    import json
    with (td / "lifecycle.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")
    return rec


def append_events(td: Path, events: list[dict[str, Any]]) -> None:
    """Idempotent append to the merged trial ledger."""
    import json
    p = td / "runtime-ledger.jsonl"
    existing = set()
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip():
                existing.add(json.loads(line).get("event_id"))
    with p.open("a", encoding="utf-8") as f:
        for ev in events:
            if ev["event_id"] not in existing:
                f.write(json.dumps(ev) + "\n")


def _node_event(eid: str, label: str, node: str, refs: list[str],
                note: str = "", **meta) -> dict[str, Any]:
    return {"event_id": eid, "label": label, "actor": f"node:{node}",
            "timestamp": now(), "artifact_refs": refs,
            "metadata": {"completes_node": node,
                         **({"note": note} if note else {}), **meta}}


def formal_out(td: Path, name: str, res) -> Any:
    jdump(td / "formal-results" / f"{name}.json", res.to_dict())
    print(f"[{td.name if td.name != 'shadow' else td.parent.name + '/shadow'}]"
          f" {name}: {res.status}")
    return res


def topology_doc(tid: str, shadow: bool) -> dict[str, Any]:
    pd = _pipeline_dir(tid)
    ranking = jload(pd / "candidate-ranking.json")
    topo_id = ranking["runner_up"] if shadow else ranking["selected"]
    if topo_id is None:
        raise SystemExit(f"[{tid}] no {'runner-up' if shadow else 'selected'}"
                         " topology")
    return jload(pd / "candidates" / f"{topo_id}.json")


# ---------------------------------------------------------------- prepare
def cmd_prepare_exec(tid: str, shadow: bool) -> None:
    td = _tdir(tid, shadow)
    pd = _pipeline_dir(tid)
    topo = topology_doc(tid, shadow)
    distinctions = jload(pd / "distinctions.json")
    ws = _ws(tid, shadow, "exec-ws")
    manifest = package_ws.build_exec_workspace(
        trial_id=tid, bank=bank_dir(tid), ws=ws,
        harness_spec=topo["harness_spec"], distinctions=distinctions)
    jdump(td / "exec-package-manifest.json", manifest)
    jdump(td / "topology.json", {
        "topology_id": topo["topology_id"], "family":
        family_of(topo["topology_id"]),
        "predictions_hash": topo["predictions_hash"],
        "role": "shadow (CONTROL_ONLY, preregistered runner-up)" if shadow
        else "primary (selected)"})
    # compiled LTS frozen for the record
    lts = formal.compile_harness_spec(topo["harness_spec"], trial_contract())
    (td / "lts.json").write_text(lts_to_json(lts), encoding="utf-8")
    lifecycle(td, "PREPARED", workspace=str(ws),
              topology=topo["topology_id"],
              blinding_scan="PASS")
    print(f"[{tid}{'/shadow' if shadow else ''}] prepared "
          f"{topo['topology_id']}; ws {ws}")


# ------------------------------------------------------------- after exec
def cmd_after_exec(tid: str, shadow: bool) -> None:
    td = _tdir(tid, shadow)
    pd = _pipeline_dir(tid)
    ws = _ws(tid, shadow, "exec-ws")
    topo = topology_doc(tid, shadow)
    fam = family_of(topo["topology_id"])

    for name in ("resolution.json", "result.json", "evidence.json",
                 "result-pending.json", "decision.json",
                 "examiner-charge.md", "spec-summary.json"):
        src = ws / name
        if src.exists():
            shutil.copy(src, td / name)
    if (ws / "child").is_dir():
        shutil.copytree(ws / "child", td / "child", dirs_exist_ok=True)
    if not (ws / "execution-ledger.jsonl").exists():
        raise SystemExit(f"[{tid}] exec session wrote no ledger")
    shutil.copy(ws / "execution-ledger.jsonl",
                td / "exec-session-ledger.jsonl")
    shutil.copy(ws / "execution-ledger.jsonl", td / "runtime-ledger.jsonl")
    shutil.copy(bank_dir(tid) / "public" / "task.json", td / "task.json")

    audit = session_audit.audit_stream_log(
        td / "exec-session.log", workspace=ws, allowed_tools=SESSION_TOOLS)
    jdump(td / "exec-session-audit.json", audit)

    task = jload(td / "task.json")
    distinctions = jload(pd / "distinctions.json")
    qids = [d["id"] for d in distinctions["unresolved_distinctions"]]
    resolution = jload(td / "resolution.json")
    collectmod.validate_resolution(resolution, task["task_id"], qids)
    evidence = jload(td / "evidence.json")
    collectmod.validate_evidence(evidence)
    lifecycle(td, "EXEC_COLLECTED", family=fam)

    if fam == "branching":
        decision = jload(td / "decision.json")
        dec = decision.get("decision")
        if dec not in ("CREATE", "DO_NOT_CREATE"):
            raise SystemExit(f"[{tid}] invalid branching decision {dec!r}")
        lifecycle(td, "BRANCH_DECIDED", decision=dec)
        print(f"[{tid}] branching decision: {dec}")
    elif fam == "isolated-child":
        if not (td / "child").is_dir():
            raise SystemExit(f"[{tid}] isolated-child run without child "
                             "bundle")
        print(f"[{tid}] child bundle returned; validate with prepare-child")
    elif fam == "local-independent-verify":
        print(f"[{tid}] awaiting examiner (prepare-examiner)")
    else:
        print(f"[{tid}] local family; proceed to finalize")


# ---------------------------------------------------------------- child
BUNDLE_FILES = ("child-contract.json", "child-harness.json",
                "child-prompt.md", "child-input-manifest.json",
                "integration-plan.json")


def validate_child_bundle(td: Path, tid: str, qids: list[str]
                          ) -> tuple[bool, dict[str, Any]]:
    checks: dict[str, Any] = {}
    child = td / "child"
    ok_all = True

    def rec(name: str, ok: bool, why: str = "") -> bool:
        nonlocal ok_all
        checks[name] = {"status": "PASS" if ok else "FAIL", "detail": why}
        ok_all &= ok
        return ok

    missing = [f for f in BUNDLE_FILES if not (child / f).exists()]
    rec("bundle_complete", not missing, f"missing: {missing}" if missing
        else "all five bundle files present")
    if missing:
        return False, {"checks": checks}

    contract = trial_contract()
    envelope = child_envelope()
    cc = jload(child / "child-contract.json")
    att1 = formal.check_attenuation(contract, cc)
    rec("attenuation_vs_trial", att1.status == "PASS",
        str(att1.counterexample) if att1.status != "PASS" else
        "child contract attenuates from K-E6-trial")
    att2 = formal.check_attenuation(envelope, cc)
    rec("within_child_envelope", att2.status == "PASS",
        str(att2.counterexample) if att2.status != "PASS" else
        "child contract within K-E6-child-max")
    try:
        ch = jload(child / "child-harness.json")
        clts = formal.compile_harness_spec(ch, cc)
        rec("child_harness_compiles", True,
            f"{len(clts.states)} states, {len(clts.transitions)} transitions")
    except Exception as e:  # SemanticsError, ValueError, KeyError
        rec("child_harness_compiles", False, str(e))

    ws = None
    for candidate_ws in (_ws(td.parent.name if td.name == "shadow"
                             else td.name, td.name == "shadow", "exec-ws"),):
        ws = candidate_ws
    pkg_files = {str(p.relative_to(ws)) for p in (ws / "package").rglob("*")
                 if p.is_file()}
    man = jload(child / "child-input-manifest.json")
    files = man.get("files", [])
    bad = [f for f in files
           if str(f).startswith("/") or ".." in str(f)
           or str(f) not in pkg_files]
    rec("manifest_containment", bool(files) and not bad,
        f"illegal manifest entries: {bad}" if bad else
        f"{len(files)} package files, all contained")

    plan = jload(child / "integration-plan.json")
    rec("integration_plan", plan.get("role") in ROLES
        and bool(str(plan.get("child_deliverable", "")).strip())
        and bool(str(plan.get("rule", "")).strip())
        and set(plan.get("expected_contribution", {})) <= set(qids),
        f"role={plan.get('role')!r}")
    prompt = (child / "child-prompt.md").read_text(encoding="utf-8")
    rec("child_prompt", len(prompt.strip()) > 100,
        "standalone prompt present")
    parts = {"checks": checks}
    if ok_all:
        parts["child_lts"] = clts
    return ok_all, parts


def cmd_prepare_child(tid: str, shadow: bool) -> None:
    td = _tdir(tid, shadow)
    pd = _pipeline_dir(tid)
    distinctions = jload(pd / "distinctions.json")
    qids = [d["id"] for d in distinctions["unresolved_distinctions"]]
    ok, parts = validate_child_bundle(td, tid, qids)
    jdump(td / "formal-results" / "child-bundle-validation.json", {
        "check": "child_bundle_validation",
        "status": "PASS" if ok else "FAIL",
        "checks": parts["checks"],
    })
    if not ok:
        lifecycle(td, "CHILD_INVALID")
        raise SystemExit(f"[{tid}] child bundle INVALID; realization refused")
    (td / "child" / "child-lts.json").write_text(
        lts_to_json(parts["child_lts"]), encoding="utf-8")
    lifecycle(td, "CHILD_VALIDATED")
    ws = _ws(tid, shadow, "exec-ws")
    cws = _ws(tid, shadow, "child-ws")
    manifest = package_ws.build_child_workspace(
        trial_id=tid, exec_ws=ws, child_dir=td / "child", ws=cws)
    jdump(td / "child" / "child-workspace-manifest.json", manifest)
    append_events(td, [
        _node_event("root-validate-child", "verify", "validate-child",
                    ["formal-results/child-bundle-validation.json"],
                    "deterministic bundle validation: attenuation, envelope, "
                    "compilation, manifest containment, plan check")])
    print(f"[{tid}{'/shadow' if shadow else ''}] child validated; ws {cws}")


def cmd_after_child(tid: str, shadow: bool) -> None:
    td = _tdir(tid, shadow)
    cws = _ws(tid, shadow, "child-ws")
    plan = jload(td / "child" / "integration-plan.json")
    ch = jload(td / "child" / "child-harness.json")
    cc = jload(td / "child" / "child-contract.json")

    audit = session_audit.audit_stream_log(
        td / "child" / "child-session.log", workspace=cws,
        allowed_tools=SESSION_TOOLS)
    jdump(td / "child" / "child-session-audit.json", audit)

    # The parent's authored bundle governs deliverable naming (E5
    # practice): honor the declared ledger path from the child harness,
    # fall back to the template default, then to the unique *.jsonl the
    # child wrote. Deliverable paths are normalized to their basename
    # inside the child workspace (any directory prefix is trial-side
    # transport metadata).
    ledger_decl = str(ch.get("ledger_contract", {})
                      .get("path", "execution-ledger.jsonl")).split()[0]
    ledger_name = None
    for cand in (ledger_decl, "execution-ledger.jsonl"):
        if (cws / Path(cand).name).exists():
            ledger_name = Path(cand).name
            break
    if ledger_name is None:
        jsonls = sorted(p.name for p in cws.glob("*.jsonl"))
        if len(jsonls) == 1:
            ledger_name = jsonls[0]
            print(f"[{tid}] ledger fallback: unique {ledger_name}")
    names = [n for n in (ledger_name, plan["child_deliverable"],
                         "result.json") if n]
    impl = plan.get("child_implementation_file")
    if impl and impl not in names:
        names.append(impl)
    collected_ledger = None
    for name in names:
        base = Path(str(name)).name
        src = cws / base
        if src.exists():
            dst_name = ("execution-ledger.jsonl" if base == ledger_name
                        else base)
            shutil.copy(src, td / "child" / dst_name)
            if base == ledger_name:
                collected_ledger = td / "child" / "execution-ledger.jsonl"
        else:
            print(f"[{tid}] WARNING: child did not produce {base}")

    clts = formal.compile_harness_spec(ch, cc)
    ledger = td / "child" / "execution-ledger.jsonl"
    import json
    if not ledger.exists():
        jdump(td / "formal-results" / "child-refinement.json", {
            "check": "runtime_refinement", "status": "INDETERMINATE",
            "detail": "child produced no execution ledger; refinement "
                      "undecidable (recorded formal failure)"})
        print(f"[{tid}] child-refinement: INDETERMINATE (no ledger)")
        prov = jload(td / "child" / "launch-provenance.json")
        formal_out(td, "freshness-child",
                   fresh_launcher.freshness_result(prov))
        append_events(td, [
            _node_event("root-create-child", "create", "create-child",
                        ["child/launch-provenance.json"],
                        "realized via the deterministic fresh launcher only",
                        event_kind="child_launch"),
            _node_event("root-child-return", "return", "child-return",
                        [f"child/{plan['child_deliverable']}"],
                        event_kind="child_return")])
        lifecycle(td, "CHILD_RETURNED", ledger="MISSING")
        print(f"[{tid}{'/shadow' if shadow else ''}] child returned "
              "(no ledger)")
        return
    # deterministic actor adapter (kernel historical-adapter practice)
    events = [json.loads(l) for l in
              ledger.read_text(encoding="utf-8").splitlines() if l.strip()]
    mapping = []
    for i, ev in enumerate(events):
        node = (ev.get("metadata") or {}).get("completes_node")
        if node and ev.get("actor") != f"node:{node}":
            mapping.append({"index": i, "event_id": ev.get("event_id"),
                            "from_actor": ev.get("actor"),
                            "to_actor": f"node:{node}"})
            ev["actor"] = f"node:{node}"
    parse_path = ledger
    if mapping:
        adapted = td / "child" / "execution-ledger.adapted.jsonl"
        adapted.write_text("\n".join(json.dumps(e) for e in events) + "\n",
                           encoding="utf-8")
        jdump(td / "child" / "child-ledger-adapter-mapping.json",
              {"rule": "actor := node:<metadata.completes_node>",
               "rewrites": mapping})
        parse_path = adapted
    ctrace = parse_runtime_ledger(parse_path, strict=False)
    formal_out(td, "child-refinement",
               formal.check_refinement(ctrace, clts, require_completion=True))
    prov = jload(td / "child" / "launch-provenance.json")
    formal_out(td, "freshness-child", fresh_launcher.freshness_result(prov))

    append_events(td, [
        _node_event("root-create-child", "create", "create-child",
                    ["child/launch-provenance.json"],
                    "realized via the deterministic fresh launcher only",
                    event_kind="child_launch"),
        _node_event("root-child-return", "return", "child-return",
                    [f"child/{plan['child_deliverable']}",
                     "child/execution-ledger.jsonl"],
                    event_kind="child_return")])
    lifecycle(td, "CHILD_RETURNED")
    print(f"[{tid}{'/shadow' if shadow else ''}] child returned")


# -------------------------------------------------------------- examiner
def cmd_prepare_examiner(tid: str, shadow: bool) -> None:
    td = _tdir(tid, shadow)
    ws = _ws(tid, shadow, "exec-ws")
    ews = _ws(tid, shadow, "examiner-ws")
    manifest = package_ws.build_examiner_workspace(
        trial_id=tid, exec_ws=ws, ws=ews)
    jdump(td / "examiner-package-manifest.json", manifest)
    lifecycle(td, "EXAMINER_PREPARED", workspace=str(ews))
    print(f"[{tid}{'/shadow' if shadow else ''}] examiner ws {ews}")


def cmd_after_examiner(tid: str, shadow: bool) -> None:
    td = _tdir(tid, shadow)
    ews = _ws(tid, shadow, "examiner-ws")
    (td / "examiner").mkdir(exist_ok=True)
    for name in ("independent-verification.json", "execution-ledger.jsonl"):
        src = ews / name
        if src.exists():
            shutil.copy(src, td / "examiner" / name)
        else:
            print(f"[{tid}] WARNING: examiner did not produce {name}")
    audit = session_audit.audit_stream_log(
        td / "examiner" / "examiner-session.log", workspace=ews,
        allowed_tools=SESSION_TOOLS)
    jdump(td / "examiner" / "examiner-session-audit.json", audit)
    prov = jload(td / "examiner" / "launch-provenance.json")
    formal_out(td, "freshness-examiner",
               fresh_launcher.freshness_result(prov))
    append_events(td, [
        _node_event("root-verify-independent", "verify", "verify-independent",
                    ["examiner/independent-verification.json"],
                    "independent information-only examiner evidence "
                    "received; no write or promotion authority")])
    lifecycle(td, "EXAMINER_RETURNED")
    print(f"[{tid}{'/shadow' if shadow else ''}] examiner returned")


# -------------------------------------------------------------- finalize
def _satisfier_node(fam: str, satisfied_by: str, branch: str) -> str:
    if satisfied_by == "parent":
        if fam in ("local", "local-independent-verify"):
            return "resolve-local"
        if fam == "isolated-child":
            return "observe-evidence"
        return "local-resolve" if branch == "local" else "observe-evidence"
    if satisfied_by in ("child", "integration"):
        return "child-return"
    if satisfied_by == "examiner":
        return "verify-independent"
    return ""


def cmd_finalize(tid: str, shadow: bool) -> None:
    td = _tdir(tid, shadow)
    pd = _pipeline_dir(tid)
    topo = topology_doc(tid, shadow)
    fam = family_of(topo["topology_id"])
    contract = trial_contract()
    task = jload(td / "task.json")
    distinctions = jload(pd / "distinctions.json")["unresolved_distinctions"]

    branch = ""
    if fam == "branching":
        branch = ("create" if jload(td / "decision.json")["decision"] ==
                  "CREATE" else "local")

    # 1. deterministic per-task verification (preregistered verifier)
    verify = bank_dir(tid) / "private" / "verify.py"
    subprocess.run([sys.executable, str(verify), "--trial-dir", str(td),
                    "--out", str(td / "verification.json")], check=True)
    verification = jload(td / "verification.json")

    # 2. root realization events + completion
    root_events: list[dict[str, Any]] = []
    if fam == "local-independent-verify":
        root_events.append(_node_event(
            "root-return-result", "return", "return-result",
            ["result.json", "verification.json"],
            "verified result received into the governed boundary"))
    elif fam == "isolated-child":
        root_events.append(_node_event(
            "root-verify-integration", "verify", "verify-integration",
            ["verification.json"],
            "mechanical integration per the pre-committed plan + "
            "deterministic verification"))
        root_events.append(_node_event(
            "root-return-result", "return", "return-result",
            ["result.json", "verification.json"]))
    elif fam == "branching" and branch == "create":
        root_events.append(_node_event(
            "root-integrate-evidence", "observe", "integrate-evidence",
            ["child/integration-plan.json"],
            "deterministic integration of child evidence"))
        root_events.append(_node_event(
            "root-verify-child-result", "verify", "verify-child-result",
            ["verification.json"]))
    append_events(td, root_events)
    append_events(td, [{
        "event_id": "root-complete", "label": "complete", "actor": "root",
        "timestamp": now(), "artifact_refs": ["verification.json"],
        "metadata": {"note": "trial completion after deterministic "
                             "verification"}}])

    # 3. refinement with required completion. Non-strict parse: an
    # unmapped governed event is an explicit formal outcome (refinement
    # INDETERMINATE over an incomplete mapping -> recorded failure), never
    # a silent skip and never a driver crash.
    lts = formal.compile_harness_spec(topo["harness_spec"], contract)
    trace = parse_runtime_ledger(td / "runtime-ledger.jsonl", strict=False)
    ref = formal_out(td, "refinement",
                     formal.check_refinement(trace, lts,
                                             require_completion=True))

    # 4. freshness for every launched session
    provs = []
    fresh_all = []
    for name, path in (("exec", td / "exec-launch-provenance.json"),
                       ("examiner", td / "examiner" /
                        "launch-provenance.json"),
                       ("child", td / "child" / "launch-provenance.json")):
        if path.exists():
            prov = jload(path)
            provs.append({"kind": name, "provenance": prov})
            res = fresh_launcher.freshness_result(prov)
            formal_out(td, f"freshness-{name}", res)
            fresh_all.append(res.status == "PASS")

    # 5. topology guard: no hidden children, launches consistent with the
    # selected topology, sessions within tool envelope
    has_create = any(n.get("primitive") == "create"
                     for n in topo["harness_spec"].get("nodes", []))
    child_launched = (td / "child" / "launch-provenance.json").exists()
    examiner_launched = (td / "examiner" /
                         "launch-provenance.json").exists()
    audits = []
    for p in (td / "exec-session-audit.json",
              td / "examiner" / "examiner-session-audit.json",
              td / "child" / "child-session-audit.json"):
        if p.exists():
            audits.append(jload(p))
    spawn_uses = [a.get("spawn_capable_tool_uses", a.get("spawn", []))
                  for a in audits]
    spawn_flat = [s for lst in spawn_uses for s in (lst or [])]
    disallowed = [a.get("disallowed_tool_uses", a.get("disallowed", []))
                  for a in audits]
    disallowed_flat = [s for lst in disallowed for s in (lst or [])]
    guard_violations = []
    if child_launched and not has_create:
        guard_violations.append("TOPOLOGY_DECISION_VIOLATION: child launch "
                                "under a create-less topology")
    if fam == "branching" and branch == "local" and child_launched:
        guard_violations.append("TOPOLOGY_DECISION_VIOLATION: child launch "
                                "after DO_NOT_CREATE")
    if has_create and fam == "isolated-child" and not child_launched:
        guard_violations.append("COMPLETION_FAIL: create topology without "
                                "realized child")
    if examiner_launched and fam != "local-independent-verify":
        guard_violations.append("TOPOLOGY_DECISION_VIOLATION: examiner "
                                "launch outside local-independent-verify")
    if spawn_flat:
        guard_violations.append(
            f"HIDDEN_CHILD_RISK: session used spawn-capable tools "
            f"{spawn_flat}")
    if disallowed_flat:
        guard_violations.append(
            f"TOOL_ENVELOPE: disallowed tool uses {disallowed_flat}")
    jdump(td / "formal-results" / "topology-guard.json", {
        "check": "topology_guard",
        "status": "PASS" if not guard_violations else "FAIL",
        "violations": guard_violations,
        "launches": {"exec": True, "examiner": examiner_launched,
                     "child": child_launched},
        "audit_summaries": [
            {k: a.get(k) for k in ("tool_use_counts", "outside_workspace",
                                   "session_ids") if k in a}
            for a in audits],
    })

    # 6. runtime record (typed) — resolution admissibility via verification
    reqs = verification["requirements"]
    sat = {r for r, v in reqs.items() if v["satisfied"]}
    by_q = {d["id"]: d for d in distinctions}
    resolved: dict[str, str] = {}
    changed = True
    while changed:
        changed = False
        for d in distinctions:
            q = d["id"]
            if q in resolved:
                continue
            if not set(d["evidence_requirement_refs"]) <= sat:
                continue
            if not all(dep in resolved for dep in d["dependencies"]):
                continue
            first = d["evidence_requirement_refs"][0]
            node = _satisfier_node(fam, reqs[first].get("satisfied_by",
                                                        "parent"), branch)
            resolved[q] = node
            changed = True
    unresolved = sorted(set(by_q) - set(resolved))

    # evidence: session records + verifier-added records, duplicates flagged
    evidence = jload(td / "evidence.json")
    for extra in verification.get("extra_evidence_records", []):
        evidence.append(extra)
    dup_ids = set(verification.get("duplicate_evidence_ids", []))
    for e in evidence:
        e["duplicate_of_parent"] = bool(e.get("duplicate_of_parent")) or \
            e["id"] in dup_ids

    formal_failures = []
    if ref.status != "PASS":
        formal_failures.append("REFINEMENT_VIOLATION")
    cref_path = td / "formal-results" / "child-refinement.json"
    if cref_path.exists() and jload(cref_path).get("status") != "PASS":
        formal_failures.append("CHILD_REFINEMENT_FAIL")
    if fresh_all and not all(fresh_all):
        formal_failures.append("FRESHNESS_FAIL")
    if guard_violations:
        formal_failures.append("TOPOLOGY_GUARD_FAIL")

    n_sessions = 1 + int(examiner_launched) + int(child_launched)
    child_calls = int(child_launched)
    wall_ms = 0
    for p in provs:
        pr = p["provenance"]
        try:
            from datetime import datetime
            t0 = datetime.fromisoformat(pr["started_at"].replace("Z",
                                                                 "+00:00"))
            t1 = datetime.fromisoformat(pr["finished_at"].replace("Z",
                                                                  "+00:00"))
            wall_ms += int((t1 - t0).total_seconds() * 1000)
        except (KeyError, ValueError):
            pass

    runtime = {
        "topology_id": topo["topology_id"],
        "predictions_hash": topo["predictions_hash"],
        "resolved_distinctions": [
            {"id": q, "resolved_by": resolved[q]} for q in sorted(resolved)],
        "unresolved_distinctions": unresolved,
        "node_completion_order": [
            dict(e.meta()).get("completes_node") for e in trace.events
            if dict(e.meta()).get("completes_node")],
        "resource_use": {
            "model_calls": n_sessions,
            "child_calls": child_calls,
            "model_call_budget": int(topo["harness_spec"]
                                     ["max_model_calls"]),
            "wall_clock_ms": wall_ms,
        },
        "formal_failures": formal_failures,
        "authority_violations": [],
        "verification_effect": verification.get("verification_effect", ""),
        "task_result": ("correct" if verification.get("result_correct")
                        else ("unverified" if not verification.get(
                            "task_verified") else "incorrect")),
        "child_launches": child_calls,
    }
    jdump(td / "runtime-record.json", runtime)

    # 7. operationalized observed value + promoted utility arithmetic
    utility = tt_mod("utility")
    config = utility.load_utility_config()
    r_sat = round(len(sat) / max(1, len(reqs)), 4)
    dup = sorted(e["id"] for e in evidence if e.get("duplicate_of_parent"))
    novel = sorted(e["id"] for e in evidence
                   if not e.get("duplicate_of_parent"))
    redundancy = round(len(dup) / len(evidence), 4) if evidence else 0.0
    governance = round(min(1.0, 0.25 * len(formal_failures)), 4)
    cost = round((n_sessions + child_calls) / COST_DENOMINATOR, 4)
    observed_value = {"delta_e": r_sat, "cost": cost,
                      "redundancy": redundancy,
                      "governance_risk": governance}
    obs_u = utility.observed_utility(observed_value, config)
    predicted_value = topo["predicted_value"]
    calib = utility.calibration_error(predicted_value, observed_value,
                                      config)
    observed_doc = {
        "topology_id": topo["topology_id"],
        "gain": {
            "resolved_distinctions": sorted(resolved),
            "requirements_satisfied": sorted(sat),
            "requirements_total": sorted(reqs),
            "novel_evidence": novel,
            "verification_effect": verification.get("verification_effect"),
            "coverage_gain": verification.get("details", {}).get(
                "coverage_gain", 0.0),
            "score": r_sat,
        },
        "cost": {
            "model_calls": n_sessions,
            "child_calls": child_calls,
            "wall_clock_ms": wall_ms,
            "score": cost,
        },
        "redundancy": {
            "duplicate_evidence": dup,
            "unused_outputs": verification.get("details", {}).get(
                "unused_outputs", []),
            "score": redundancy,
        },
        "governance": {
            "violations": formal_failures + guard_violations,
            "score": governance,
        },
        "observed_utility": obs_u,
    }
    jdump(td / "observed-value.json", observed_doc)
    jdump(td / "calibration.json", {
        "topology_id": topo["topology_id"],
        "predicted_value": predicted_value,
        "observed_value": observed_value,
        "predicted_utility": utility.utility(
            predicted_value, config,
            f"{topo['topology_id']}.predicted_value"),
        "observed_utility": obs_u,
        "calibration_error": calib,
    })

    # 8. mechanical prediction evaluation + falsification evidence
    evaluate = tt_mod("evaluate")
    falsify = tt_mod("falsify")
    frozen = jload(pd / "frozen-predictions.json")[topo["topology_id"]]
    evaluation = evaluate.evaluate_topology(
        frozen["predictions"], runtime, evidence,
        predicted_value=predicted_value)
    ev_doc = evaluation.to_dict()
    # authoritative observed economics are the operationalized ones above
    ev_doc["observed_value_operationalized"] = observed_value
    ev_doc["observed_utility_operationalized"] = obs_u
    jdump(td / "evaluation.json", ev_doc)
    fres = falsify.falsify(frozen["predictions"], evaluation)
    jdump(td / "falsification.json", fres.to_dict())

    lifecycle(td, "FORMALLY_CHECKED",
              task_verified=verification.get("task_verified"),
              observed_utility=obs_u)
    print(f"[{tid}{'/shadow' if shadow else ''}] finalized: "
          f"U_obs={obs_u} R_sat={r_sat} refinement={ref.status}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=[
        "prepare-exec", "after-exec", "prepare-child", "after-child",
        "prepare-examiner", "after-examiner", "finalize"])
    ap.add_argument("trial_id")
    ap.add_argument("--shadow", action="store_true")
    a = ap.parse_args()
    fn = {"prepare-exec": cmd_prepare_exec, "after-exec": cmd_after_exec,
          "prepare-child": cmd_prepare_child, "after-child": cmd_after_child,
          "prepare-examiner": cmd_prepare_examiner,
          "after-examiner": cmd_after_examiner,
          "finalize": cmd_finalize}[a.cmd]
    fn(a.trial_id, a.shadow)


if __name__ == "__main__":
    main()
