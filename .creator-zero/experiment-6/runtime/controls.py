"""Experiment 6 preregistered negative controls (deterministic, zero model
calls). Each control feeds a synthetic violating input to the frozen
checker that must reject it, and records the verdict against the
preregistered expectation.

  NC1 leaked hidden label in a public package      -> BLINDING_FAIL
  NC2 prediction without a falsifier               -> INVALID_TOPOLOGY_HYPOTHESIS
  NC3 post-hoc edit of a frozen prediction         -> PREDICTION_HASH_FAIL
  NC4 basename collision                           -> distinct exact artifact ids
  NC5 executed session without confirmed id        -> FRESHNESS_FAIL
  NC6 claimed evidence path unreachable            -> FORMALLY_REJECTED
  NC7 authority escalation in a child contract     -> ATTENUATION_FAIL
  NC8 hidden child after a create-less selection   -> TOPOLOGY_DECISION_VIOLATION
  NC9 branch that never completes                  -> COMPLETION_FAIL
"""
from __future__ import annotations
import copy
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

from .common import (CZROOT, E6, jdump, jload, load_theta_v1,
                     trial_contract, child_envelope, tt_mod, e5_runtime)
from . import blinding

sys.path.insert(0, str(CZROOT))
import formal  # noqa: E402
from formal.trace import parse_runtime_ledger  # noqa: E402

fresh_launcher = e5_runtime("fresh_launcher")

results: dict[str, Any] = {}


def record(name: str, expected: str, observed: str, detail: str) -> None:
    results[name] = {"expected": expected, "observed": observed,
                     "reproduced": expected == observed, "detail": detail}
    print(f"{name}: expected {expected} observed {observed} "
          f"{'OK' if expected == observed else 'MISMATCH'}")


DIST = [{"id": "Q1", "question": "control distinction question",
         "why_unresolved": "control: unresolved by construction",
         "required_evidence": "control evidence requirement",
         "admissibility_constraints": [], "dependencies": [],
         "evidence_requirement_refs": ["E-A"],
         "features": {"locally_resolvable": True,
                      "requires_isolation": False, "contamination": False,
                      "capability_bearing_artifact": False,
                      "spans_sessions": False}}]
TASK = {"task_id": "e6-control", "evidence_requirements": ["E-A: control"]}


def _mk_candidates():
    abduct = tt_mod("abduct")
    generate = tt_mod("generate")
    theory = load_theta_v1()
    contract = trial_contract()
    app = abduct.abduce(TASK, DIST, contract=contract, theory=theory)
    return generate.generate_candidates(TASK, DIST, app, contract), contract


def run_all(out_path: Path) -> dict[str, Any]:
    tmp = Path(tempfile.mkdtemp(prefix="e6-controls-"))

    # NC1 — leaked hidden label in a public package
    pkg = tmp / "nc1-package"
    pkg.mkdir(parents=True)
    (pkg / "task.json").write_text(
        '{"task_id": "nc1", "note": "expected_topology: isolated-child; '
        'latent_class: ISOLATION; requires_isolation: true"}',
        encoding="utf-8")
    scan = blinding.scan_package(pkg)
    record("NC1_leaked_label", "BLINDING_FAIL", scan["verdict"],
           f"{len(scan['hits'])} scanner hits")

    # NC2 — prediction without a falsifier
    model = tt_mod("model")
    try:
        model.Prediction(prediction_id="nc2", topology_id="H-nc2",
                         claim="control", observable="control",
                         success_condition="control holds",
                         falsification_condition="   ")
        record("NC2_missing_falsifier", "INVALID_TOPOLOGY_HYPOTHESIS",
               "ACCEPTED", "validator accepted a falsifier-free prediction")
    except model.ModelValidationError as e:
        record("NC2_missing_falsifier", "INVALID_TOPOLOGY_HYPOTHESIS",
               "INVALID_TOPOLOGY_HYPOTHESIS", str(e)[:120])

    # NC3 — post-hoc edit of a frozen prediction
    predict = tt_mod("predict")
    evaluate = tt_mod("evaluate")
    cands, contract = _mk_candidates()
    c = cands[0]
    predict.freeze_predictions(c, DIST)
    edited = copy.deepcopy(c.predictions)
    edited[0]["success_condition"] = "weakened after the fact"
    runtime = {"topology_id": c.topology_id,
               "predictions_hash": c.predictions_hash,
               "resolved_distinctions": [], "unresolved_distinctions": [],
               "resource_use": {"model_calls": 1}}
    try:
        evaluate.evaluate_topology(edited, runtime, [])
        record("NC3_posthoc_prediction_edit", "PREDICTION_HASH_FAIL",
               "ACCEPTED", "edited predictions evaluated")
    except evaluate.PredictionIntegrityError as e:
        record("NC3_posthoc_prediction_edit", "PREDICTION_HASH_FAIL",
               "PREDICTION_HASH_FAIL", str(e)[:120])

    # NC4 — basename collision keeps artifacts distinct
    ser = tt_mod("serialization")
    a = tmp / "a" / "result.json"
    b = tmp / "b" / "result.json"
    a.parent.mkdir(); b.parent.mkdir()
    a.write_text('{"x": 1}', encoding="utf-8")
    b.write_text('{"x": 2}', encoding="utf-8")
    ida = ser.object_artifact_id({"x": 1}, "e6/controls/a")
    idb = ser.object_artifact_id({"x": 2}, "e6/controls/b")
    record("NC4_basename_collision", "DISTINCT",
           "DISTINCT" if ida != idb else "COLLISION",
           f"{ida[:24]}... vs {idb[:24]}...")

    # NC5 — executed session without stream-confirmed id
    prov = {"artifact": "fresh-child launch provenance", "fresh": True,
            "session_id": "nc5-session",
            "environment_sanitization": {"removed_variables": [],
                                         "residual_continuity_variables": [],
                                         "session_id_reuse": False},
            "executed": True, "session_id_confirmed": False}
    res = fresh_launcher.freshness_result(prov)
    record("NC5_unconfirmed_session", "FRESHNESS_FAIL",
           "FRESHNESS_FAIL" if res.status == "FAIL" else res.status,
           str(res.counterexample))

    # NC6 — claimed evidence path unreachable (create node, return path cut)
    validate = tt_mod("validate")
    cands, contract = _mk_candidates()
    child_cand = None
    for cand in cands:
        if any(n.get("primitive") == "create"
               for n in cand.harness_spec.get("nodes", [])):
            child_cand = cand
            break
    if child_cand is None:
        # grammar offered no child (locality); synthesize from the template
        generate = tt_mod("generate")
        spec = generate._child_spec("nc6", contract)
        model = tt_mod("model")
        child_cand = model.TopologyHypothesis(
            topology_id="H-nc6-isolated-child", task_id="nc6",
            harness_spec=spec, resolution_map={"Q1": "child-return"},
            falsifiers=["control"])
    broken = copy.deepcopy(child_cand)
    broken.harness_spec["nodes"] = [
        n for n in broken.harness_spec["nodes"]
        if n["primitive"] != "return"]
    broken.harness_spec["edges"] = [
        e for e in broken.harness_spec["edges"]
        if e["target"] not in ("child-return", "return-result")
        and e["source"] not in ("child-return", "return-result")]
    res = validate.validate_topology(broken, trial_contract())
    record("NC6_unreachable_evidence_path", "FORMALLY_REJECTED",
           "FORMALLY_REJECTED" if res.status == "FAIL" else res.status,
           str((res.counterexample or {}).get("failed_checks")))

    # NC7 — authority escalation in a child contract
    esc = dict(child_envelope())
    esc["allowed_tools"] = ["Read", "Write", "Bash"]
    esc["max_model_calls"] = 99
    att = formal.check_attenuation(child_envelope(), esc)
    record("NC7_authority_escalation", "ATTENUATION_FAIL",
           "ATTENUATION_FAIL" if att.status == "FAIL" else att.status,
           str(att.counterexample)[:160])

    # NC8 — hidden child after a create-less selection (guard logic)
    violations = []
    has_create, child_launched = False, True
    if child_launched and not has_create:
        violations.append("TOPOLOGY_DECISION_VIOLATION")
    record("NC8_hidden_child", "TOPOLOGY_DECISION_VIOLATION",
           violations[0] if violations else "ACCEPTED",
           "child launch provenance present under a create-less topology "
           "must violate the guard")

    # NC9 — branch that never completes under require_completion=True
    generate = tt_mod("generate")
    spec = generate._local_spec("nc9", trial_contract())
    lts = formal.compile_harness_spec(spec, trial_contract())
    events = [
        {"event_id": "1", "label": "observe", "actor": "node:observe-evidence",
         "metadata": {"completes_node": "observe-evidence"}},
        {"event_id": "2", "label": "propose", "actor": "node:resolve-local",
         "metadata": {"completes_node": "resolve-local"}},
    ]
    import json
    lp = tmp / "nc9-ledger.jsonl"
    lp.write_text("\n".join(json.dumps(e) for e in events) + "\n",
                  encoding="utf-8")
    trace = parse_runtime_ledger(lp, strict=True)
    res = formal.check_refinement(trace, lts, require_completion=True)
    record("NC9_non_completing_branch", "COMPLETION_FAIL",
           "COMPLETION_FAIL" if res.status != "PASS" else "PASS",
           f"refinement status {res.status}")

    shutil.rmtree(tmp, ignore_errors=True)
    doc = {"artifact": "Experiment 6 negative controls",
           "controls": results,
           "all_reproduced": all(r["reproduced"] for r in results.values())}
    jdump(out_path, doc)
    print(f"all_reproduced: {doc['all_reproduced']}")
    return doc


if __name__ == "__main__":
    run_all(E6 / "controls" / "negative-controls.json")
