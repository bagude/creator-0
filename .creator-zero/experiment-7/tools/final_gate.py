"""E7 finalization: score all trials, aggregate, run the final theory Gate,
and promote theta-v2 only on a Gate PASS.

    python3 tools/final_gate.py score        score every primary trial
    python3 tools/final_gate.py aggregate    aggregate + threshold checks
    python3 tools/final_gate.py gate         stage-2 theory gate (+promotion
                                             through TheoryStore.promote on
                                             PASS; otherwise theta-v1 stays)
"""
from __future__ import annotations
import importlib.util
import json
import sys
from pathlib import Path

E7 = Path(__file__).resolve().parents[1]
CZROOT = E7.parent
REPO = CZROOT.parent
sys.path.insert(0, str(E7))

from runtime.common import jdump, jload, tt_mod          # noqa: E402
from runtime import score_e7, aggregate_e7               # noqa: E402


def cmd_score() -> None:
    manifest = jload(E7 / "trial-manifest.json")
    for cond in ("A", "B"):
        for tid in manifest["primary_trials"]:
            doc = score_e7.score_trial(tid, cond)
            print(f"{tid}/{cond}: {doc['topology_score']['verdict']} "
                  f"recall={doc['distinction_score']['critical_recall']} "
                  f"|err|={round(abs(doc['predicted_utility']-doc['observed_utility']),3)}")


def cmd_aggregate() -> None:
    doc = aggregate_e7.aggregate()
    print(doc["result"])
    for k, v in doc["threshold_checks"].items():
        print(f"  {k}: {v}")
    print("paired:", doc["paired"])


def cmd_gate() -> None:
    tg = tt_mod("theory_gate")
    model = tt_mod("model")
    store_mod = tt_mod("theory_store")

    agg = jload(E7 / "aggregate-results.json")
    checks = agg["threshold_checks"]
    groups = agg["check_groups"]

    # lineage re-verification at gate time
    spec = importlib.util.spec_from_file_location(
        "lineage", CZROOT / "lineage" / "__init__.py",
        submodule_search_locations=[str(CZROOT / "lineage")])
    lin = importlib.util.module_from_spec(spec)
    sys.modules["lineage"] = lin
    spec.loader.exec_module(lin)
    cp_res = lin.verify_checkpoint(REPO, jload(E7 / "base-checkpoint.json"))
    jdump(E7 / "checkpoint-verification-final.json", cp_res.to_dict())

    tests = jload(E7 / "infrastructure" / "test-results.json")
    candidate = jload(E7 / "candidate-revisions" / "candidate-theta-v2.json")
    try:
        model.TheoryVersion.from_dict(candidate)
        schema = {"status": "PASS"}
    except model.ModelValidationError as e:
        schema = {"status": "FAIL", "detail": str(e)}
    imp = jload(E7 / "evidence-import-manifest.json")

    inputs = {
        "candidate_schema": schema,
        "evidence_provenance": {"status": "PASS" if (
            imp.get("append_only_intact") and imp.get("conflicts") == 0
            and imp.get("source_pin_verification", {}).get("status")
            == "PASS") else "FAIL"},
        "historical_replay": jload(E7 / "historical-replay" /
                                   "candidate-theta-v2-replay.json"),
        "protected_laws": {"status": "PASS" if
                           agg["historical_mutation_check"]["count"] == 0
                           else "FAIL"},
        "tests_existing": {"status": tests["status"]},
        "tests_new": {"status": tests["status"]},
        "independent_verifier": jload(E7 / "independent-verification" /
                                      "revision-verification.json"),
        "evaluation_authorization": jload(
            E7 / "candidate-revisions" / "evaluation-authorization.json"),
        "heldout_thresholds": {"status": "PASS" if groups["absolute"]
                               and checks["min_trial_count"]
                               and checks["min_per_class"] else "FAIL",
                               "detail": {k: checks[k] for k in checks
                                          if k.endswith("_B")}},
        "paired_improvement": {"status": "PASS" if groups["paired"]
                               else "FAIL",
                               "detail": agg["paired"]},
        "governance": {"status": "PASS" if
                       checks["capability_violations_zero"]
                       and checks["authority_attenuation_zero"]
                       and checks["hidden_children_zero"] else "FAIL"},
        "historical_immutability": {"status": "PASS" if
                                    checks["historical_mutations_zero"]
                                    and cp_res.status == "PASS"
                                    else "FAIL"},
    }
    gate_result = tg.theory_gate(inputs)
    jdump(E7 / "gate-result.json", gate_result)
    print("final theory gate:", gate_result["status"])
    for line in gate_result["evidence"]:
        print(" ", line)

    promotion = {"promotion_performed": False, "canonical_after": "theta-v1"}
    if gate_result["status"] == "PASS":
        store = store_mod.TheoryStore(CZROOT / "state" / "topology-theory")
        cand = model.TheoryVersion.from_dict(candidate)
        path = store.promote(cand, gate_result)
        promotion = {
            "promotion_performed": True,
            "canonical_after": "theta-v2",
            "written": str(path),
            "theta_v2_hash": store.version_hash(2),
        }
        print("theta-v2 PROMOTED via TheoryStore.promote:",
              promotion["theta_v2_hash"])
    else:
        print("theta-v1 remains canonical (candidate retained as evidence)")
    jdump(E7 / "promotion-record.json", promotion)


def main() -> None:
    {"score": cmd_score, "aggregate": cmd_aggregate,
     "gate": cmd_gate}[sys.argv[1]]()


if __name__ == "__main__":
    main()
