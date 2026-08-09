"""Experiment 7 negative controls NC1-NC17 (preregistration §12).

Every control perturbs a copy or uses a scratch store — no canonical or
frozen artifact is touched. Expected outcome per control is preregistered;
the run records observed vs expected and an overall verdict.

    python3 -m runtime.controls_e7
"""
from __future__ import annotations
import importlib.util
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

from .common import CZROOT, E7, REPO, jdump, jload, tt_mod


def _lineage():
    if "lineage" in sys.modules:
        return sys.modules["lineage"]
    spec = importlib.util.spec_from_file_location(
        "lineage", CZROOT / "lineage" / "__init__.py",
        submodule_search_locations=[str(CZROOT / "lineage")])
    mod = importlib.util.module_from_spec(spec)
    sys.modules["lineage"] = mod
    spec.loader.exec_module(mod)
    return mod


def _rebuild(doc: dict, **edits) -> dict:
    from lineage.model import checkpoint_id_for
    d = {k: v for k, v in doc.items() if k != "checkpoint_id"}
    d.update(edits)
    d["checkpoint_id"] = checkpoint_id_for(d)
    return d


def run_controls() -> dict[str, Any]:
    lin = _lineage()
    model = tt_mod("model")
    ingest = tt_mod("ingest")
    adm = tt_mod("admissibility")
    gov = tt_mod("governance")
    tg = tt_mod("theory_gate")
    sm = tt_mod("self_modify")
    evaluate = tt_mod("evaluate")
    store_mod = tt_mod("theory_store")
    utility = tt_mod("utility")

    base_cp = jload(E7 / "base-checkpoint.json")
    pins = jload(E7 / "frozen-inputs" / "e6-input-pins.json")
    results: list[dict[str, Any]] = []

    def record(nc: str, perturbation: str, expected: str, observed: str,
               ok: bool) -> None:
        results.append({"id": nc, "perturbation": perturbation,
                        "expected": expected, "observed": observed,
                        "reproduced": ok})

    # NC1 commit mutation
    bad = _rebuild(base_cp, commit_sha="0" * 40)
    r = lin.verify_checkpoint(REPO, bad)
    record("NC1", "checkpoint commit mutated", "COMMIT_MISMATCH / "
           "LINEAGE_RESUME_FAIL",
           f"{r.failure_codes} / {r.result}",
           "COMMIT_MISMATCH" in r.failure_codes
           and r.result == "LINEAGE_RESUME_FAIL")

    # NC2 tree mutation
    bad = _rebuild(base_cp, tree_sha="f" * 40)
    r = lin.verify_checkpoint(REPO, bad)
    record("NC2", "checkpoint tree mutated", "TREE_MISMATCH",
           str(r.failure_codes), "TREE_MISMATCH" in r.failure_codes)

    # NC3 predecessor-hash mismatch
    tmp = Path(tempfile.mkdtemp())
    st = store_mod.TheoryStore(tmp)
    theta1 = model.TheoryVersion.from_dict(
        jload(CZROOT / "state" / "topology-theory" / "theta-v1.json"))
    st.write_version(theta1)
    succ = model.TheoryVersion(
        version=2, principles=theta1.principles,
        predecessor_hash="sha256:" + "0" * 64, status="CANDIDATE")
    try:
        st.write_version(succ)
        record("NC3", "successor with wrong predecessor hash",
               "TheoryStoreError", "accepted", False)
    except store_mod.TheoryStoreError as e:
        record("NC3", "successor with wrong predecessor hash",
               "TheoryStoreError", f"TheoryStoreError: {e}", True)

    # NC4 evidence source hash mutation
    mutated = tmp / "mutated.jsonl"
    text = (REPO / pins["e6_evidence_source"]["path"]).read_text(
        encoding="utf-8")
    mutated.write_text(text.replace("SUPPORT", "FALSIFY", 1),
                       encoding="utf-8")
    r4 = ingest.verify_source_pin(mutated, pins["e6_evidence_source"])
    record("NC4", "E6 evidence source byte-mutated",
           "EVIDENCE_SOURCE_MISMATCH",
           str(r4["failure_code"]),
           r4["failure_code"] == "EVIDENCE_SOURCE_MISMATCH")

    # NC5 duplicate id, conflicting content
    st5 = store_mod.TheoryStore(tmp / "s5")
    ev = {"principle_id": "P-X", "topology_id": "t", "prediction_id": "p",
          "effect": "SUPPORT", "event_id": "e-1"}
    ingest.ingest_evidence(st5, [ev])
    try:
        ingest.ingest_evidence(st5, [{**ev, "effect": "FALSIFY"}])
        record("NC5", "same event id, different content",
               "EVIDENCE_ID_CONFLICT", "accepted", False)
    except ingest.EvidenceImportError as e:
        record("NC5", "same event id, different content",
               "EVIDENCE_ID_CONFLICT", str(e)[:60],
               "EVIDENCE_ID_CONFLICT" in str(e))

    # NC6 context-stripping parser
    try:
        model.PrincipleEvidence.from_dict({**ev, "trial_ctx": {"k": 1}})
        record("NC6", "unknown contextual field on evidence",
               "ModelValidationError", "silently accepted", False)
    except model.ModelValidationError as e:
        record("NC6", "unknown contextual field on evidence",
               "ModelValidationError", str(e)[:60], True)

    # NC7 right graph shape, wrong role
    vec, roles = adm.KIND_REQUIREMENT["NON_AUTHOR_SEARCH"]
    req = adm.EvidenceRequirement(
        requirement_id="r", distinction_id="Q1", kind="NON_AUTHOR_SEARCH",
        independence=adm.IndependenceVector.of(vec), allowed_roles=roles)
    prov = adm.provision_for_role("child-return", "clean_room_author")
    ok7, _ = adm.admissible(prov, req)
    record("NC7", "isolated clean-room child offered for a search "
           "requirement", "inadmissible", "admissible" if ok7 else
           "inadmissible", not ok7)

    # NC8 isolated child where examiner suffices -> strictly lower utility
    d = {"id": "Q1", "features": {"requires_nonauthor_search": True}}
    reqs = [adm.requirement_for_distinction(d)]
    exam = [adm.provision_for_role("resolve-local", "local_author"),
            adm.provision_for_role("verify-independent",
                                   "non_author_examiner")]
    child = [adm.provision_for_role("observe-evidence", "local_author"),
             adm.provision_for_role("child-return", "non_author_examiner")]
    v_by = {"Q1": 0.8}
    pe = adm.predicted_components(exam, reqs, v_by, model_sessions=2,
                                  child_sessions=0)
    pc = adm.predicted_components(child, reqs, v_by, model_sessions=2,
                                  child_sessions=1)
    cfg = utility.load_utility_config()
    ue = utility.utility(pe, cfg)
    uc = utility.utility(pc, cfg)
    record("NC8", "isolated searcher child vs examiner on the same "
           "requirement", "U(examiner) > U(child) at equal admissibility",
           f"U_e={ue} U_c={uc}", ue > uc and pe["delta_e"] == pc["delta_e"])

    # NC9 unauthorized capability-bearing tool
    evs = gov.classify_session_audit(
        {"disallowed_tool_uses": [{"tool": "Bash", "id": "x"}]}, "s")
    record("NC9", "capability-bearing tool outside envelope",
           "capability_violation (fatal)",
           f"{evs[0]['category']} fatal={evs[0]['fatal']}",
           evs[0]["category"] == "capability_violation" and evs[0]["fatal"])

    # NC10 meta-tool observation only
    evs = gov.classify_session_audit(
        {"disallowed_tool_uses": [{"tool": "ToolSearch", "id": "x"}]}, "s")
    s10 = gov.summarize(evs)
    record("NC10", "schema/meta-tool observation alone",
           "meta_tool_observation, 0 capability violations, G_obs 0",
           f"{evs[0]['category']} cap={s10['capability_violations']} "
           f"g={s10['observed_governance_risk']}",
           evs[0]["category"] == "meta_tool_observation"
           and s10["capability_violations"] == 0
           and s10["observed_governance_risk"] == 0.0)

    # NC11 hidden child
    evs = gov.classify_session_audit(
        {"spawn_capable_tool_uses": [{"tool": "Agent", "id": "x"}]}, "s")
    record("NC11", "spawn-capable tool use in an audited session",
           "fatal capability_violation (HIDDEN_CHILD_RISK)",
           f"{evs[0]['code']} fatal={evs[0]['fatal']}",
           evs[0]["code"] == "HIDDEN_CHILD_RISK" and evs[0]["fatal"])

    # NC12 prediction mutation after freeze
    td = None
    for cand in sorted((E7 / "pilot" / "trials" / "A").glob("*")):
        if (cand / "frozen-predictions.json").exists() and \
                (cand / "runtime-record.json").exists():
            td = cand
            break
    if td is None:
        record("NC12", "prediction mutation after freeze",
               "PredictionIntegrityError", "no pilot trial available",
               False)
    else:
        runtime = jload(td / "runtime-record.json")
        frozen = jload(td / "frozen-predictions.json")[
            runtime["topology_id"]]
        preds = [dict(p) for p in frozen["predictions"]]
        preds[0]["claim"] = preds[0]["claim"] + " [POST-HOC EDIT]"
        try:
            evaluate.evaluate_topology(preds, runtime, [])
            record("NC12", "frozen prediction edited post hoc",
                   "PredictionIntegrityError", "accepted", False)
        except evaluate.PredictionIntegrityError as e:
            record("NC12", "frozen prediction edited post hoc",
                   "PredictionIntegrityError", str(e)[:60], True)

    # NC13 direct theta promotion without a Gate PASS
    st13 = store_mod.TheoryStore(tmp / "s13")
    try:
        st13.promote(theta1, {"check": "verifier", "status": "PASS",
                              "detail": {"issued_by": "verifier"}})
        record("NC13", "promotion from a non-gate document",
               "PromotionError", "accepted", False)
    except store_mod.PromotionError as e:
        record("NC13", "promotion from a non-gate document",
               "PromotionError", str(e)[:60], True)

    # NC14 E6 historical file edit in a candidate patch
    r14 = sm.check_protected_laws(
        [".creator-zero/experiment-6/theory-evidence-events.jsonl"])
    record("NC14", "candidate patch touching an E6 artifact",
           "protected-law FAIL", r14["status"], r14["status"] == "FAIL")

    # NC15 held-out label leak in a public package
    from .common import e6_runtime
    blinding = e6_runtime("blinding")
    leak_dir = tmp / "leaky-pkg"
    leak_dir.mkdir()
    shutil.copy(E7 / "task-bank" / "e7-t05" / "public" / "task.json",
                leak_dir / "task.json")
    (leak_dir / "hint.md").write_text(
        "the latent class of this task is LOCAL\n", encoding="utf-8")
    scan = blinding.scan_package(leak_dir)
    record("NC15", "class label leaked into a public package",
           "BLINDING_FAIL", scan["verdict"],
           scan["verdict"] == "BLINDING_FAIL")

    # NC16 cross-condition artifact reuse
    #   (a) structural: every real B workspace denies the whole A root and
    #       vice versa (sampled from persisted workspace settings);
    #   (b) detective: an other-condition artifact injected into a
    #       workspace copy is caught by hash intersection with the other
    #       condition's outputs.
    from .common import SCRATCH
    settings_checked, settings_ok = 0, True
    for cond, other in (("A", "B"), ("B", "A")):
        for st_file in sorted((SCRATCH / cond).rglob(
                ".claude/settings.json"))[:6]:
            deny = jload(st_file)["permissions"]["deny"]
            if not any(str(SCRATCH / other) in d for d in deny):
                settings_ok = False
            settings_checked += 1
    inj_dir = tmp / "b-ws-copy"
    inj_dir.mkdir()
    a_out = next((E7 / "pilot" / "trials" / "A" / "e7-p01").glob(
        "resolution.json"))
    shutil.copy(a_out, inj_dir / "stray.json")
    import hashlib
    a_hashes = {hashlib.sha256(f.read_bytes()).hexdigest()
                for f in (E7 / "pilot" / "trials" / "A").rglob("*.json")
                if f.is_file()}
    contaminated = [str(f) for f in inj_dir.rglob("*") if f.is_file()
                    and hashlib.sha256(f.read_bytes()).hexdigest()
                    in a_hashes]
    record("NC16", "cross-condition artifact injected + real workspace "
           "deny audit",
           "injection detected; all sampled workspaces deny the other "
           "condition root",
           f"detected={bool(contaminated)} "
           f"settings={settings_checked} ok={settings_ok}",
           bool(contaminated) and settings_ok and settings_checked > 0)

    # NC17 final theory promotion before held-out validation
    eval_inputs = {k: {"status": "PASS"}
                   for k in tg.REQUIRED_EVAL_INPUTS}
    auth = tg.evaluation_authorization(eval_inputs)
    gate_no_heldout = tg.theory_gate(
        {**eval_inputs, "evaluation_authorization": auth})
    st17 = store_mod.TheoryStore(tmp / "s17")
    try:
        st17.promote(theta1, auth)
        promo = "accepted"
    except store_mod.PromotionError as e:
        promo = f"PromotionError: {str(e)[:40]}"
    record("NC17", "promotion attempted from stage-1 authorization; "
           "theory gate evaluated without held-out inputs",
           "PromotionError + gate FAIL",
           f"{promo}; gate={gate_no_heldout['status']}",
           promo.startswith("PromotionError")
           and gate_no_heldout["status"] == "FAIL")

    shutil.rmtree(tmp, ignore_errors=True)
    doc = {
        "artifact": "Experiment 7 negative-control results",
        "controls": results,
        "reproduced": sum(1 for r in results if r["reproduced"]),
        "total": len(results),
        "all_reproduced": all(r["reproduced"] for r in results),
    }
    jdump(E7 / "controls" / "results.json", doc)
    return doc


if __name__ == "__main__":
    doc = run_controls()
    print(f"{doc['reproduced']}/{doc['total']} controls reproduced")
    for r in doc["controls"]:
        print(f"  {r['id']}: {'OK' if r['reproduced'] else 'NOT REPRODUCED'}"
              f" ({r['observed'][:70]})")
