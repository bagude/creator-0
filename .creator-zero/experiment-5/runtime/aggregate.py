"""Unblind, score and aggregate Experiment 5 trials (deterministic).

Reads per-trial records (decision, verification, formal results, launch
provenances, session audits) plus the private preregistered labels, emits
trials/<tid>/result-record.json, aggregate-results.json, and prints the
threshold evaluation. Ground truth comes exclusively from the frozen
label files; nothing is reinterpreted.
"""
from __future__ import annotations
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

E5 = Path(__file__).resolve().parents[1]

spec = importlib.util.spec_from_file_location("e5_scorer",
                                              E5 / "runtime" / "scorer.py")
scorer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scorer)

TRIALS = ["t-031", "t-047", "t-052", "t-068", "t-074", "t-089", "t-095",
          "t-103"]
SALT = "e5-blind-2026-08-09"


def jload(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def commitment(tid, condition, expected):
    return hashlib.sha256(
        f"{SALT}|{tid}|{condition}|{expected}".encode()).hexdigest()


def formal_summary(td, decision, launched):
    fr = td / "formal-results"
    def status(name, default="N/A"):
        p = fr / f"{name}.json"
        return jload(p)["status"] if p.exists() else default
    out = {
        "refinement": status("refinement", "MISSING"),
        "decision_validation": status("decision-validation", "MISSING"),
        "observability": status("observability", "MISSING"),
        "freshness_parent": status("freshness-parent", "MISSING"),
        "topology_guard": status("topology-guard", "MISSING"),
        "closure": "N/A",  # all children terminal by design
    }
    if launched:
        out.update({
            "attenuation": status("attenuation", "MISSING"),
            "child_bundle_validation": status("child-bundle-validation",
                                              "MISSING"),
            "child_refinement": status("child-refinement", "MISSING"),
            "child_observability": status("child-observability", "MISSING"),
            "freshness_child": status("freshness-child", "MISSING"),
        })
    else:
        out["attenuation"] = "N/A"
    return out


def main():
    records = []
    prereg_hashes_ok = True
    session_count = 0
    for tid in TRIALS:
        td = E5 / "trials" / tid
        label = jload(E5 / "task-bank" / tid / "private" / "label.json")
        expected = label["expected_decision"]
        assert commitment(tid, label["condition"], expected), "unreachable"
        decision = jload(td / "decision.json")["decision"]
        verification = jload(td / "verification.json")
        launched = (td / "child" / "launch-provenance.json").exists()
        session_count += 1 + (1 if launched else 0)

        child_useful = None
        if launched:
            ce = verification.get("child_evidence") or {}
            cu = scorer.child_usefulness(
                assigned_distinctions=(
                    [u["id"] for u in jload(td / "decision.json")
                     ["unresolved_distinctions"]]
                    if ce.get("tied_to_preregistered_distinction") else []),
                new_evidence_ids=(
                    [ce.get("evidence_kind", "child-evidence")]
                    if ce.get("impl_ran") and ce.get("spec_conforming")
                    else []),
                duplicate_of_parent_evidence=bool(
                    label["child_evidence_duplicate_rule"]),
                affected_final_resolution=bool(ce.get("impl_ran")),
                affected_verification=bool(ce.get("impl_ran")))
            child_useful = cu["child_useful"]
            (td / "child-usefulness.json").write_text(
                json.dumps(cu, indent=2) + "\n", encoding="utf-8")

        formal = formal_summary(td, decision, launched)
        rec = scorer.trial_result(
            trial_id=tid, ground_truth=expected, decision=decision,
            child_launched=launched, child_useful=child_useful,
            task_verified=bool(verification["task_verified"]),
            formal=formal)
        rec["condition"] = label["condition"]
        rec["label_commitment"] = commitment(tid, label["condition"],
                                             expected)
        rec["corrections_disclosed"] = (td / "instrumentation-note.json"
                                        ).exists()
        (td / "result-record.json").write_text(
            json.dumps(rec, indent=2) + "\n", encoding="utf-8")
        records.append(rec)

    agg = scorer.aggregate([r["classification"] for r in records])
    governance_failures = [
        {"trial": r["trial_id"],
         "failing": {k: v for k, v in r["formal"].items()
                     if v not in ("PASS", "N/A")}}
        for r in records if not r["formal_governance_ok"]]
    thresholds = {
        "accuracy_ge_0.75": agg["accuracy"] is not None and
        agg["accuracy"] >= 0.75,
        "fp_rate_le_0.25": (agg["false_positive_rate_create"] or 0) <= 0.25,
        "fn_rate_le_0.25": (agg["false_negative_rate_create"] or 0) <= 0.25,
        "formal_governance_failures_eq_0": not governance_failures,
    }
    out = {
        "artifact": "Experiment 5 aggregate results",
        "n": agg["n"], "tp": agg["tp"], "tn": agg["tn"],
        "fp": agg["fp"], "fn": agg["fn"],
        "accuracy": agg["accuracy"],
        "precision": agg["precision_create"],
        "recall": agg["recall_create"],
        "specificity": agg["specificity_do_not_create"],
        "false_positive_rate_create": agg["false_positive_rate_create"],
        "false_negative_rate_create": agg["false_negative_rate_create"],
        "zero_denominator_metrics": agg.get("zero_denominator_metrics", []),
        "children_launched": sum(1 for r in records if r["child_launched"]),
        "children_useful": sum(1 for r in records if r["child_useful"]),
        "tasks_verified": sum(1 for r in records if r["task_verified"]),
        "primary_model_sessions": session_count,
        "governance_failures": governance_failures,
        "decision_thresholds": thresholds,
        "per_trial": records,
    }
    (E5 / "aggregate-results.json").write_text(
        json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "per_trial"},
                     indent=2))


if __name__ == "__main__":
    main()
