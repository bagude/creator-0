"""Root-side deterministic per-trial driver for Experiment 7 (both
conditions). Pure orchestration over promoted/frozen modules; it never
solves substantive tasks and never overrides a deterministic judgment.

    python3 -m runtime.driver <cmd> <trial_id> <A|B> [--shadow]

cmds: infer-prepare, infer-after, exec-prepare, exec-after, child-prepare,
      child-after, examiner-prepare, examiner-after, finalize
"""
from __future__ import annotations
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from .common import (CHILD_FAMILIES, COST_DENOMINATOR, CZROOT, E6, E7,
                     EXAMINER_FAMILIES, ROLES_ACCEPTED, SESSION_TOOLS,
                     bank_dir, canonical_role_of, child_envelope, e5_runtime,
                     e6_runtime, family_of, jdump, jload, now,
                     trial_contract, trial_dir, tt_mod, ws)
from . import collect_e7, package_e7
from .pipeline_e7 import run_pipeline

sys.path.insert(0, str(CZROOT))
import formal                                              # noqa: E402
from formal.serialization import lts_to_json               # noqa: E402
from formal.trace import parse_runtime_ledger              # noqa: E402

fresh_launcher = e5_runtime("fresh_launcher")
session_audit = e5_runtime("session_audit")

EXAMINER_NODE = {"local-independent-verify": "verify-independent",
                 "local-independent-examiner": "verify-independent",
                 "local-method-disjoint-verifier": "verify-method-disjoint"}


def lifecycle(td: Path, state: str, **extra):
    rec = {"state": state, "at": now(), **extra}
    with (td / "lifecycle.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")


def append_events(td: Path, events: list[dict[str, Any]]) -> None:
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


def _node_event(eid, label, node, refs, note="", **meta):
    return {"event_id": eid, "label": label, "actor": f"node:{node}",
            "timestamp": now(), "artifact_refs": refs,
            "metadata": {"completes_node": node,
                         **({"note": note} if note else {}), **meta}}


def formal_out(td: Path, name: str, res) -> Any:
    doc = res.to_dict() if hasattr(res, "to_dict") else res
    jdump(td / "formal-results" / f"{name}.json", doc)
    return res


def topology_doc(tid: str, cond: str, shadow: bool) -> dict[str, Any]:
    pd = trial_dir(tid, cond)
    ranking = jload(pd / "candidate-ranking.json")
    topo_id = ranking["runner_up"] if shadow else ranking["selected"]
    if topo_id is None:
        raise SystemExit(f"[{tid}/{cond}] no "
                         f"{'runner-up' if shadow else 'selected'} topology")
    return jload(pd / "candidates" / f"{topo_id}.json")


# ------------------------------------------------------------------ infer
def cmd_infer_prepare(tid: str, cond: str, shadow: bool) -> None:
    td = trial_dir(tid, cond)
    manifest = package_e7.build_infer_workspace(
        trial_id=tid, condition=cond, bank=bank_dir(tid),
        ws=ws(tid, cond, False, "infer-ws"))
    jdump(td / "infer-package-manifest.json", manifest)
    shutil.copy(bank_dir(tid) / "public" / "task.json", td / "task.json")
    print(f"[{tid}/{cond}] infer ws prepared")


def cmd_infer_after(tid: str, cond: str, shadow: bool) -> None:
    td = trial_dir(tid, cond)
    wsp = ws(tid, cond, False, "infer-ws")
    task = jload(td / "task.json")
    for name in ("distinctions.json", "value-estimates.json",
                 "spec-summary.json"):
        src = wsp / name
        if not src.exists():
            raise SystemExit(f"[{tid}/{cond}] missing {name}")
        shutil.copy(src, td / name)
    shutil.copy(wsp / "execution-ledger.jsonl",
                td / "infer-session-ledger.jsonl")
    audit = session_audit.audit_stream_log(
        td / "infer-session.log", workspace=wsp,
        allowed_tools=SESSION_TOOLS)
    jdump(td / "infer-session-audit.json", audit)
    prov_path = td / "infer-launch-provenance.json"
    if prov_path.exists():
        formal_out(td, "freshness-infer",
                   fresh_launcher.freshness_result(jload(prov_path)))

    req_ids = [r.split(":", 1)[0].strip()
               for r in task.get("evidence_requirements", [])]
    distinctions = jload(td / "distinctions.json")
    estimates = jload(td / "value-estimates.json")
    # deterministic ref adapter (E6 kernel-adapter practice): a ref given as
    # the full requirement string normalizes to its id; anything else is
    # left for the closed validator to reject
    adapted = []
    for d in distinctions.get("unresolved_distinctions", []):
        refs = d.get("evidence_requirement_refs", [])
        for i, r in enumerate(refs):
            if r not in req_ids:
                head = str(r).split(":", 1)[0].strip()
                if head in req_ids:
                    adapted.append({"distinction": d.get("id"),
                                    "from": r, "to": head})
                    refs[i] = head
    if adapted:
        jdump(td / "distinctions-ref-adapter.json",
              {"rule": "ref := ref.split(':',1)[0] when the head is a "
                       "known requirement id", "rewrites": adapted})
        jdump(td / "distinctions.json", distinctions)
    if cond == "A":
        collect_e7.validate_distinctions_a(distinctions, task["task_id"],
                                           req_ids)
        collect_e7.validate_value_estimates_a(estimates, task["task_id"])
    else:
        collect_e7.validate_distinctions_b(distinctions, task["task_id"],
                                           req_ids)
        qids = [d["id"] for d in distinctions["unresolved_distinctions"]]
        collect_e7.validate_value_estimates_b(estimates, task["task_id"],
                                              qids)

    harness = jload(wsp / "infer-harness.json")
    lts = formal.compile_harness_spec(harness, trial_contract())
    trace = parse_runtime_ledger(td / "infer-session-ledger.jsonl",
                                 strict=True)
    formal_out(td, "infer-refinement",
               formal.check_refinement(trace, lts, require_completion=False))

    ranking = run_pipeline(cond, tid, task, distinctions, estimates, td)
    print(f"[{tid}/{cond}] pipeline: selected={ranking.get('selected')} "
          f"runner_up={ranking.get('runner_up')}")


# ------------------------------------------------------------------- exec
def cmd_exec_prepare(tid: str, cond: str, shadow: bool) -> None:
    td = trial_dir(tid, cond, shadow)
    pd = trial_dir(tid, cond)
    topo = topology_doc(tid, cond, shadow)
    distinctions = jload(pd / "distinctions.json")
    wsp = ws(tid, cond, shadow, "exec-ws")
    manifest = package_e7.build_exec_workspace(
        trial_id=tid, condition=cond, bank=bank_dir(tid), ws=wsp,
        harness_spec=topo["harness_spec"], distinctions=distinctions)
    jdump(td / "exec-package-manifest.json", manifest)
    jdump(td / "topology.json", {
        "topology_id": topo["topology_id"],
        "family": family_of(topo["topology_id"], cond),
        "predictions_hash": topo["predictions_hash"],
        "condition": cond,
        "role": "shadow (CONTROL_ONLY, preregistered runner-up)" if shadow
        else "primary (selected)"})
    lts = formal.compile_harness_spec(topo["harness_spec"],
                                      trial_contract())
    (td / "lts.json").write_text(lts_to_json(lts), encoding="utf-8")
    lifecycle(td, "PREPARED", workspace=str(wsp),
              topology=topo["topology_id"], blinding_scan="PASS")
    print(f"[{tid}/{cond}{'/sh' if shadow else ''}] prepared "
          f"{topo['topology_id']}")


def cmd_exec_after(tid: str, cond: str, shadow: bool) -> None:
    td = trial_dir(tid, cond, shadow)
    pd = trial_dir(tid, cond)
    wsp = ws(tid, cond, shadow, "exec-ws")
    topo = topology_doc(tid, cond, shadow)
    fam = family_of(topo["topology_id"], cond)
    for name in ("resolution.json", "result.json", "evidence.json",
                 "result-pending.json", "decision.json",
                 "examiner-charge.md", "spec-summary.json"):
        src = wsp / name
        if src.exists():
            shutil.copy(src, td / name)
    if (wsp / "child").is_dir():
        shutil.copytree(wsp / "child", td / "child", dirs_exist_ok=True)
    if not (wsp / "execution-ledger.jsonl").exists():
        raise SystemExit(f"[{tid}/{cond}] exec session wrote no ledger")
    shutil.copy(wsp / "execution-ledger.jsonl",
                td / "exec-session-ledger.jsonl")
    shutil.copy(wsp / "execution-ledger.jsonl",
                td / "runtime-ledger.jsonl")
    shutil.copy(bank_dir(tid) / "public" / "task.json", td / "task.json")
    audit = session_audit.audit_stream_log(
        td / "exec-session.log", workspace=wsp,
        allowed_tools=SESSION_TOOLS)
    jdump(td / "exec-session-audit.json", audit)

    task = jload(td / "task.json")
    distinctions = jload(pd / "distinctions.json")
    qids = [d["id"] for d in distinctions["unresolved_distinctions"]]
    collect_e7.validate_resolution(jload(td / "resolution.json"),
                                   task["task_id"], qids)
    collect_e7.validate_evidence(jload(td / "evidence.json"))
    lifecycle(td, "EXEC_COLLECTED", family=fam)
    if fam == "branching":
        dec = jload(td / "decision.json").get("decision")
        if dec not in ("CREATE", "DO_NOT_CREATE"):
            raise SystemExit(f"[{tid}/{cond}] invalid decision {dec!r}")
        lifecycle(td, "BRANCH_DECIDED", decision=dec)
    print(f"[{tid}/{cond}{'/sh' if shadow else ''}] exec collected ({fam})")


# ------------------------------------------------------------------ child
BUNDLE_FILES = ("child-contract.json", "child-harness.json",
                "child-prompt.md", "child-input-manifest.json",
                "integration-plan.json")


def validate_child_bundle(td: Path, tid: str, cond: str, shadow: bool,
                          qids: list[str], declared_role: str
                          ) -> tuple[bool, dict[str, Any]]:
    checks: dict[str, Any] = {}
    child = td / "child"
    ok_all = True

    def rec(name, ok, why=""):
        nonlocal ok_all
        checks[name] = {"status": "PASS" if ok else "FAIL", "detail": why}
        ok_all &= ok
        return ok

    missing = [f for f in BUNDLE_FILES if not (child / f).exists()]
    rec("bundle_complete", not missing,
        f"missing: {missing}" if missing else "all five files present")
    if missing:
        return False, {"checks": checks}
    contract = trial_contract()
    envelope = child_envelope()
    cc = jload(child / "child-contract.json")
    att1 = formal.check_attenuation(contract, cc)
    rec("attenuation_vs_trial", att1.status == "PASS",
        str(att1.counterexample) if att1.status != "PASS" else "attenuates")
    att2 = formal.check_attenuation(envelope, cc)
    rec("within_child_envelope", att2.status == "PASS",
        str(att2.counterexample) if att2.status != "PASS" else "within "
        "envelope")
    clts = None
    try:
        ch = jload(child / "child-harness.json")
        clts = formal.compile_harness_spec(ch, cc)
        rec("child_harness_compiles", True,
            f"{len(clts.states)} states")
    except Exception as e:
        rec("child_harness_compiles", False, str(e))
    wsp = ws(tid, cond, shadow, "exec-ws")
    pkg_files = {str(p.relative_to(wsp))
                 for p in (wsp / "package").rglob("*") if p.is_file()}
    man = jload(child / "child-input-manifest.json")
    files = man.get("files", [])
    bad = [f for f in files if str(f).startswith("/") or ".." in str(f)
           or str(f) not in pkg_files]
    rec("manifest_containment", bool(files) and not bad,
        f"illegal entries: {bad}" if bad else f"{len(files)} contained")
    plan = jload(child / "integration-plan.json")
    role = str(plan.get("role", ""))
    role_ok = role in ROLES_ACCEPTED
    if cond == "B" and declared_role:
        role_ok = role_ok and canonical_role_of(role) == declared_role
    rec("integration_plan", role_ok
        and bool(str(plan.get("child_deliverable", "")).strip())
        and bool(str(plan.get("rule", "")).strip())
        and set(plan.get("expected_contribution", {})) <= set(qids),
        f"role={role!r} declared={declared_role!r}")
    prompt = (child / "child-prompt.md").read_text(encoding="utf-8")
    rec("child_prompt", len(prompt.strip()) > 100, "prompt present")
    parts: dict[str, Any] = {"checks": checks}
    if ok_all:
        parts["child_lts"] = clts
    return ok_all, parts


def cmd_child_prepare(tid: str, cond: str, shadow: bool) -> None:
    td = trial_dir(tid, cond, shadow)
    pd = trial_dir(tid, cond)
    topo = topology_doc(tid, cond, shadow)
    distinctions = jload(pd / "distinctions.json")
    qids = [d["id"] for d in distinctions["unresolved_distinctions"]]
    declared = str(topo["harness_spec"].get("child_role", ""))
    ok, parts = validate_child_bundle(td, tid, cond, shadow, qids, declared)
    jdump(td / "formal-results" / "child-bundle-validation.json", {
        "check": "child_bundle_validation",
        "status": "PASS" if ok else "FAIL", "checks": parts["checks"]})
    if not ok:
        lifecycle(td, "CHILD_INVALID")
        raise SystemExit(f"[{tid}/{cond}] child bundle INVALID")
    (td / "child" / "child-lts.json").write_text(
        lts_to_json(parts["child_lts"]), encoding="utf-8")
    lifecycle(td, "CHILD_VALIDATED")
    manifest = package_e7.build_child_workspace(
        trial_id=tid, exec_ws=ws(tid, cond, shadow, "exec-ws"),
        child_dir=td / "child", ws=ws(tid, cond, shadow, "child-ws"))
    jdump(td / "child" / "child-workspace-manifest.json", manifest)
    append_events(td, [_node_event(
        "root-validate-child", "verify", "validate-child",
        ["formal-results/child-bundle-validation.json"],
        "deterministic bundle validation")])
    print(f"[{tid}/{cond}{'/sh' if shadow else ''}] child validated")


def cmd_child_after(tid: str, cond: str, shadow: bool) -> None:
    td = trial_dir(tid, cond, shadow)
    cws = ws(tid, cond, shadow, "child-ws")
    plan = jload(td / "child" / "integration-plan.json")
    ch = jload(td / "child" / "child-harness.json")
    cc = jload(td / "child" / "child-contract.json")
    audit = session_audit.audit_stream_log(
        td / "child" / "child-session.log", workspace=cws,
        allowed_tools=SESSION_TOOLS)
    jdump(td / "child" / "child-session-audit.json", audit)
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
    names = [n for n in (ledger_name, plan["child_deliverable"],
                         "result.json") if n]
    impl = plan.get("child_implementation_file")
    if impl and impl not in names:
        names.append(impl)
    for name in names:
        base = Path(str(name)).name
        src = cws / base
        if src.exists():
            dst = ("execution-ledger.jsonl" if base == ledger_name else base)
            shutil.copy(src, td / "child" / dst)
    prov = jload(td / "child" / "launch-provenance.json")
    formal_out(td, "freshness-child", fresh_launcher.freshness_result(prov))
    ledger = td / "child" / "execution-ledger.jsonl"
    if not ledger.exists():
        jdump(td / "formal-results" / "child-refinement.json", {
            "check": "runtime_refinement", "status": "INDETERMINATE",
            "detail": "child produced no execution ledger"})
    else:
        events = [json.loads(l) for l in ledger.read_text(
            encoding="utf-8").splitlines() if l.strip()]
        mapping = []
        for i, ev in enumerate(events):
            node = (ev.get("metadata") or {}).get("completes_node")
            if node and ev.get("actor") != f"node:{node}":
                mapping.append({"index": i,
                                "from_actor": ev.get("actor")})
                ev["actor"] = f"node:{node}"
        parse_path = ledger
        if mapping:
            adapted = td / "child" / "execution-ledger.adapted.jsonl"
            adapted.write_text(
                "\n".join(json.dumps(e) for e in events) + "\n",
                encoding="utf-8")
            jdump(td / "child" / "child-ledger-adapter-mapping.json",
                  {"rule": "actor := node:<metadata.completes_node>",
                   "rewrites": mapping})
            parse_path = adapted
        clts = formal.compile_harness_spec(ch, cc)
        ctrace = parse_runtime_ledger(parse_path, strict=False)
        formal_out(td, "child-refinement",
                   formal.check_refinement(ctrace, clts,
                                           require_completion=True))
    append_events(td, [
        _node_event("root-create-child", "create", "create-child",
                    ["child/launch-provenance.json"],
                    "realized via the deterministic fresh launcher only",
                    event_kind="child_launch"),
        _node_event("root-child-return", "return", "child-return",
                    [f"child/{plan['child_deliverable']}"],
                    event_kind="child_return")])
    lifecycle(td, "CHILD_RETURNED")
    print(f"[{tid}/{cond}{'/sh' if shadow else ''}] child returned")


# --------------------------------------------------------------- examiner
def cmd_examiner_prepare(tid: str, cond: str, shadow: bool) -> None:
    td = trial_dir(tid, cond, shadow)
    manifest = package_e7.build_examiner_workspace(
        trial_id=tid, condition=cond,
        exec_ws=ws(tid, cond, shadow, "exec-ws"),
        ws=ws(tid, cond, shadow, "examiner-ws"))
    jdump(td / "examiner-package-manifest.json", manifest)
    lifecycle(td, "EXAMINER_PREPARED")
    print(f"[{tid}/{cond}{'/sh' if shadow else ''}] examiner ws ready")


def cmd_examiner_after(tid: str, cond: str, shadow: bool) -> None:
    td = trial_dir(tid, cond, shadow)
    ews = ws(tid, cond, shadow, "examiner-ws")
    (td / "examiner").mkdir(exist_ok=True)
    for name in ("independent-verification.json", "execution-ledger.jsonl"):
        src = ews / name
        if src.exists():
            shutil.copy(src, td / "examiner" / name)
    audit = session_audit.audit_stream_log(
        td / "examiner" / "examiner-session.log", workspace=ews,
        allowed_tools=SESSION_TOOLS)
    jdump(td / "examiner" / "examiner-session-audit.json", audit)
    prov = jload(td / "examiner" / "launch-provenance.json")
    formal_out(td, "freshness-examiner",
               fresh_launcher.freshness_result(prov))
    topo = topology_doc(tid, cond, shadow)
    fam = family_of(topo["topology_id"], cond)
    node = EXAMINER_NODE.get(fam, "verify-independent")
    append_events(td, [_node_event(
        "root-verify-independent", "verify", node,
        ["examiner/independent-verification.json"],
        "independent information-only examiner evidence received")])
    lifecycle(td, "EXAMINER_RETURNED")
    print(f"[{tid}/{cond}{'/sh' if shadow else ''}] examiner returned")


# --------------------------------------------------------------- finalize
def _satisfier_node(fam: str, satisfied_by: str, branch: str) -> str:
    if satisfied_by == "parent":
        if fam == "local" or fam in EXAMINER_FAMILIES:
            return "resolve-local"
        if fam in CHILD_FAMILIES:
            return "observe-evidence"
        return "local-resolve" if branch == "local" else "observe-evidence"
    if satisfied_by in ("child", "integration"):
        return "child-return"
    if satisfied_by == "examiner":
        return {"local-method-disjoint-verifier": "verify-method-disjoint"
                }.get(fam, "verify-independent")
    return ""


def _role_typing(td: Path, fam: str, cond: str,
                 topo: dict[str, Any]) -> dict[str, Any]:
    """Realized canonical role of the independent path vs the declared
    provision role (spec-side; private labels are never read here)."""
    declared = ""
    for p in topo["harness_spec"].get("evidence_provisions", []):
        if p["role"] != "local_author":
            declared = p["role"]
    realized = ""
    detail = ""
    if (td / "child" / "integration-plan.json").exists():
        raw = str(jload(td / "child" / "integration-plan.json"
                        ).get("role", ""))
        realized = canonical_role_of(raw)
        detail = f"child integration-plan role {raw!r}"
    elif (td / "examiner" / "launch-provenance.json").exists():
        realized = "non_author_examiner"
        detail = "examiner session"
        if fam == "local-method-disjoint-verifier":
            charge = (td / "examiner-charge.md")
            iv = td / "examiner" / "independent-verification.json"
            method = primary = examiner_method = ""
            if charge.exists():
                for line in charge.read_text(encoding="utf-8").splitlines():
                    if line.lower().startswith("method:"):
                        method = line.split(":", 1)[1].strip()
                    if line.lower().startswith("primary-method:"):
                        primary = line.split(":", 1)[1].strip()
            if iv.exists():
                examiner_method = str(jload(iv).get("method_family", ""))
            if method and examiner_method and (
                    not primary or examiner_method != primary):
                realized = "method_disjoint_verifier"
                detail = (f"charge method {method!r}, examiner used "
                          f"{examiner_method!r}, primary {primary!r}")
            else:
                detail = (f"method-disjointness not evidenced: charge "
                          f"method {method!r}, examiner {examiner_method!r},"
                          f" primary {primary!r}")
    mismatch = bool(declared) and realized != declared
    return {"declared_role": declared, "realized_role": realized,
            "detail": detail, "role_type_fail": mismatch,
            "independent_path": bool(realized)}


def cmd_finalize(tid: str, cond: str, shadow: bool) -> None:
    td = trial_dir(tid, cond, shadow)
    pd = trial_dir(tid, cond)
    topo = topology_doc(tid, cond, shadow)
    fam = family_of(topo["topology_id"], cond)
    contract = trial_contract()
    distinctions = jload(pd / "distinctions.json")["unresolved_distinctions"]

    branch = ""
    if fam == "branching":
        branch = ("create" if jload(td / "decision.json")["decision"] ==
                  "CREATE" else "local")

    verify = bank_dir(tid) / "private" / "verify.py"
    subprocess.run([sys.executable, str(verify), "--trial-dir", str(td),
                    "--out", str(td / "verification.json")], check=True)
    verification = jload(td / "verification.json")

    root_events: list[dict[str, Any]] = []
    if fam in EXAMINER_FAMILIES:
        root_events.append(_node_event(
            "root-return-result", "return", "return-result",
            ["result.json", "verification.json"]))
    elif fam in CHILD_FAMILIES:
        root_events.append(_node_event(
            "root-verify-integration", "verify", "verify-integration",
            ["verification.json"]))
        root_events.append(_node_event(
            "root-return-result", "return", "return-result",
            ["result.json", "verification.json"]))
    elif fam == "branching" and branch == "create":
        root_events.append(_node_event(
            "root-integrate-evidence", "observe", "integrate-evidence",
            ["child/integration-plan.json"]))
        root_events.append(_node_event(
            "root-verify-child-result", "verify", "verify-child-result",
            ["verification.json"]))
    append_events(td, root_events)
    append_events(td, [{
        "event_id": "root-complete", "label": "complete", "actor": "root",
        "timestamp": now(), "artifact_refs": ["verification.json"],
        "metadata": {"note": "trial completion after deterministic "
                             "verification"}}])

    lts = formal.compile_harness_spec(topo["harness_spec"], contract)
    trace = parse_runtime_ledger(td / "runtime-ledger.jsonl", strict=False)
    ref = formal.check_refinement(trace, lts, require_completion=True)
    formal_out(td, "refinement", ref)

    provs, fresh_all = [], []
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

    has_create = any(n.get("primitive") == "create"
                     for n in topo["harness_spec"].get("nodes", []))
    child_launched = (td / "child" / "launch-provenance.json").exists()
    examiner_launched = (td / "examiner" /
                         "launch-provenance.json").exists()
    audits = []
    audit_actors = []
    for actor, p in (("exec", td / "exec-session-audit.json"),
                     ("examiner", td / "examiner" /
                      "examiner-session-audit.json"),
                     ("child", td / "child" / "child-session-audit.json")):
        if p.exists():
            audits.append(jload(p))
            audit_actors.append(actor)
    guard_violations = []
    if child_launched and not has_create:
        guard_violations.append("TOPOLOGY_DECISION_VIOLATION: child launch "
                                "under a create-less topology")
    if fam == "branching" and branch == "local" and child_launched:
        guard_violations.append("TOPOLOGY_DECISION_VIOLATION: child after "
                                "DO_NOT_CREATE")
    if has_create and fam in CHILD_FAMILIES and not child_launched:
        guard_violations.append("COMPLETION_FAIL: create topology without "
                                "realized child")
    if examiner_launched and fam not in EXAMINER_FAMILIES:
        guard_violations.append("TOPOLOGY_DECISION_VIOLATION: examiner "
                                "outside examiner families")
    jdump(td / "formal-results" / "topology-guard.json", {
        "check": "topology_guard",
        "status": "PASS" if not guard_violations else "FAIL",
        "violations": guard_violations,
        "launches": {"exec": True, "examiner": examiner_launched,
                     "child": child_launched}})

    # governance taxonomy v2 classification (preregistered; both conditions).
    # Audit outside-workspace paths are ATTEMPTS from tool-call inputs: an
    # attempt covered by the session's deny rules was blocked (protocol
    # event); an uncovered path is an exercised capability (fatal).
    gov = tt_mod("governance")

    def _deny_prefixes(wsp: Path) -> list[str]:
        st = wsp / ".claude" / "settings.json"
        out = []
        if st.exists():
            for rule in jload(st).get("permissions", {}).get("deny", []):
                if rule.startswith(("Read(", "Write(", "Edit(")) and \
                        rule.endswith("/**)"):
                    out.append(rule.split("(", 1)[1][:-len("/**)")])
        return out

    def _classify_audit(audit: dict[str, Any], actor: str,
                        wsp: Path) -> list[dict[str, Any]]:
        denies = _deny_prefixes(wsp)
        a = dict(audit)
        outside = a.get("file_paths_outside_workspace", []) or []
        # the session's own harness-provided scratchpad is part of its
        # envelope (temporary space advertised by the harness itself)
        own_scratch = "/tmp/claude-0/" + str(wsp).replace("/", "-")
        outside = [x for x in outside if not x.startswith(own_scratch)]
        # a path that does not exist exercised no capability: record the
        # attempt as a protocol event, never as a capability violation
        ghosts = [x for x in outside if not Path(x).exists()]
        outside = [x for x in outside if x not in ghosts]
        blocked = [x for x in outside
                   if any(x.startswith(d) for d in denies)]
        blocked += ghosts
        a["file_paths_outside_workspace"] = [x for x in outside
                                             if x not in blocked]
        evs = gov.classify_session_audit(a, actor)
        for x in blocked:
            evs.append(gov.event(
                "protocol_violation", "BLOCKED_WORKSPACE_ACCESS_ATTEMPT",
                actor, [{"path": x}],
                "outside-workspace access attempt denied by the session's "
                "permission rules (no capability exercised)"))
        return evs

    def _classify_refinement_structural(doc: dict[str, Any], actor: str
                                        ) -> list[dict[str, Any]]:
        status = str(doc.get("status", ""))
        if status == "PASS":
            return []
        ce = doc.get("counterexample") or {}
        viol = str(ce.get("violation", "")).upper() \
            if isinstance(ce, dict) else ""
        det = doc.get("detail")
        reason = str(det.get("reason", "")) if isinstance(det, dict) \
            else str(det or "")
        if "AUTHORITY" in viol or "PROMOTE" in viol:
            cat, code = "authority_violation", "REFINEMENT_AUTHORITY"
        elif status == "INDETERMINATE":
            cat, code = ("instrumentation_violation",
                         "REFINEMENT_UNDECIDABLE")
        elif "COMPLET" in viol or "complet" in reason.lower():
            cat, code = "protocol_violation", "COMPLETION_MISSING"
        else:
            cat, code = ("instrumentation_violation",
                         "REFINEMENT_NONCONFORMANT")
        return [gov.event(cat, code, actor, [ce or reason])]

    ws_of = {"exec": ws(tid, cond, shadow, "exec-ws"),
             "examiner": ws(tid, cond, shadow, "examiner-ws"),
             "child": ws(tid, cond, shadow, "child-ws")}
    gov_events: list[dict[str, Any]] = []
    for actor, audit in zip(audit_actors, audits):
        gov_events += _classify_audit(audit, actor, ws_of[actor])
    gov_events += _classify_refinement_structural(ref.to_dict(), "trial")
    cref_path = td / "formal-results" / "child-refinement.json"
    if cref_path.exists() and jload(cref_path).get("status") != "PASS":
        gov_events += _classify_refinement_structural(jload(cref_path),
                                                      "child")
    for v in guard_violations:
        cat = ("capability_violation" if "child launch" in v
               else "protocol_violation")
        gov_events.append(gov.event(cat, v.split(":")[0], "trial",
                                    [v]))
    if fresh_all and not all(fresh_all):
        gov_events.append(gov.event("protocol_violation", "FRESHNESS_FAIL",
                                    "trial", ["freshness results"]))

    # role typing (spec-declared vs realized; label-free)
    role = _role_typing(td, fam, cond, topo)
    jdump(td / "role-typing.json", role)

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
    if cref_path.exists() and jload(cref_path).get("status") != "PASS":
        formal_failures.append("CHILD_REFINEMENT_FAIL")
    if fresh_all and not all(fresh_all):
        formal_failures.append("FRESHNESS_FAIL")
    if guard_violations:
        formal_failures.append("TOPOLOGY_GUARD_FAIL")
    if role["role_type_fail"]:
        formal_failures.append("ROLE_TYPE_FAIL")
        gov_events.append(gov.event(
            "protocol_violation", "ROLE_TYPE_FAIL", "trial",
            [role], "realized role differs from declared provision role"))

    gov_summary = gov.summarize(gov_events)
    jdump(td / "governance-events.json", {
        "events": gov_events, "summary": gov_summary})

    n_sessions = 1 + int(examiner_launched) + int(child_launched)
    child_calls = int(child_launched)
    wall_ms = 0
    for p in provs:
        pr = p["provenance"]
        try:
            from datetime import datetime
            t0 = datetime.fromisoformat(
                pr["started_at"].replace("Z", "+00:00"))
            t1 = datetime.fromisoformat(
                pr["finished_at"].replace("Z", "+00:00"))
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

    utility = tt_mod("utility")
    config = utility.load_utility_config()
    r_sat = round(len(sat) / max(1, len(reqs)), 4)
    dup = sorted(e["id"] for e in evidence if e.get("duplicate_of_parent"))
    redundancy = round(len(dup) / len(evidence), 4) if evidence else 0.0
    governance = gov_summary["observed_governance_risk"]
    cost = round((n_sessions + child_calls) / COST_DENOMINATOR, 4)
    observed_value = {"delta_e": r_sat, "cost": cost,
                      "redundancy": redundancy,
                      "governance_risk": governance}
    obs_u = utility.observed_utility(observed_value, config)
    predicted_value = topo["predicted_value"]
    calib = utility.calibration_error(predicted_value, observed_value,
                                      config)
    jdump(td / "observed-value.json", {
        "topology_id": topo["topology_id"],
        "gain": {"requirements_satisfied": sorted(sat),
                 "requirements_total": sorted(reqs), "score": r_sat},
        "cost": {"model_calls": n_sessions, "child_calls": child_calls,
                 "wall_clock_ms": wall_ms, "score": cost},
        "redundancy": {"duplicate_evidence": dup, "score": redundancy},
        "governance": {"violations": formal_failures + guard_violations,
                       "taxonomy_v2": gov_summary, "score": governance},
        "observed_utility": obs_u})
    jdump(td / "calibration.json", {
        "topology_id": topo["topology_id"],
        "predicted_value": predicted_value,
        "observed_value": observed_value,
        "predicted_utility": utility.utility(
            predicted_value, config,
            f"{topo['topology_id']}.predicted_value"),
        "observed_utility": obs_u,
        "calibration_error": calib})

    evaluate = tt_mod("evaluate")
    falsify = tt_mod("falsify")
    frozen = jload(pd / "frozen-predictions.json")[topo["topology_id"]]
    evaluation = evaluate.evaluate_topology(
        frozen["predictions"], runtime, evidence,
        predicted_value=predicted_value)
    ev_doc = evaluation.to_dict()
    ev_doc["observed_value_operationalized"] = observed_value
    ev_doc["observed_utility_operationalized"] = obs_u
    jdump(td / "evaluation.json", ev_doc)
    fres = falsify.falsify(frozen["predictions"], evaluation)
    jdump(td / "falsification.json", fres.to_dict())

    lifecycle(td, "FORMALLY_CHECKED",
              task_verified=verification.get("task_verified"),
              observed_utility=obs_u)
    print(f"[{tid}/{cond}{'/sh' if shadow else ''}] finalized: "
          f"U_obs={obs_u} R_sat={r_sat} refinement={ref.status} "
          f"role_fail={role['role_type_fail']}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=[
        "infer-prepare", "infer-after", "exec-prepare", "exec-after",
        "child-prepare", "child-after", "examiner-prepare",
        "examiner-after", "finalize"])
    ap.add_argument("trial_id")
    ap.add_argument("condition", choices=["A", "B"])
    ap.add_argument("--shadow", action="store_true")
    a = ap.parse_args()
    fn = {"infer-prepare": cmd_infer_prepare, "infer-after": cmd_infer_after,
          "exec-prepare": cmd_exec_prepare, "exec-after": cmd_exec_after,
          "child-prepare": cmd_child_prepare,
          "child-after": cmd_child_after,
          "examiner-prepare": cmd_examiner_prepare,
          "examiner-after": cmd_examiner_after,
          "finalize": cmd_finalize}[a.cmd]
    fn(a.trial_id, a.condition, a.shadow)


if __name__ == "__main__":
    main()
