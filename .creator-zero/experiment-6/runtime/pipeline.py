"""Stages S2-S5 of the Experiment 6 pipeline (deterministic, root-side).

    run_pipeline(trial_id, task, distinctions_doc, estimates_doc, out_dir)

Given the blinded session's serialized DistinctionSpec and value estimates:
S2 abduce applicable principles from the promoted theta-v1 (deterministic
   feature matching; ordered applicability persisted for scoring),
S3 generate 2-4 candidate topologies from the closed template grammar,
   attach the serialized model value estimates (cost is deterministic),
S4 freeze falsifier-complete predictions with immutable hashes,
S5 validate every candidate formally, rank the valid ones with the frozen
   utility config, and select the top-ranked candidate.

Selection is complete before any realization; invalid candidates remain
recorded evidence but cannot execute. Model output cannot override any
rejection or the ranking arithmetic.
"""
from __future__ import annotations
from pathlib import Path
from typing import Any

from .common import (family_of, jdump, predicted_cost, load_theta_v1,
                     trial_contract, tt_mod)


def ordered_applicability(theory, distinctions: list[dict[str, Any]]
                          ) -> list[dict[str, Any]]:
    """Deterministic ordering for principle-abduction scoring: number of
    feature-matched distinctions descending, then principle id ascending.
    Only feature:<name> preconditions count — 'always' and structural
    preconditions are governance background, listed after feature-matched
    principles."""
    rows = []
    for p in theory.active_principles():
        matched = set()
        structural = []
        always = False
        for pre in p.preconditions:
            if pre.startswith("feature:"):
                feat = pre.split(":", 1)[1]
                for d in distinctions:
                    if bool(d.get("features", {}).get(feat, False)):
                        matched.add(d["id"])
            elif pre.startswith("topology:"):
                structural.append(pre)
            elif pre == "always":
                always = True
        rows.append({
            "principle_id": p.id,
            "feature_matched_distinctions": sorted(matched),
            "feature_match_count": len(matched),
            "structural_preconditions": structural,
            "always": always,
        })
    rows.sort(key=lambda r: (-r["feature_match_count"], r["principle_id"]))
    for i, r in enumerate(rows):
        r["rank"] = i + 1
    return rows


def run_pipeline(trial_id: str, task: dict[str, Any],
                 distinctions_doc: dict[str, Any],
                 estimates_doc: dict[str, Any],
                 out_dir: Path) -> dict[str, Any]:
    abduct = tt_mod("abduct")
    generate = tt_mod("generate")
    predict = tt_mod("predict")
    validate = tt_mod("validate")
    utility = tt_mod("utility")

    theory = load_theta_v1()
    contract = trial_contract()
    distinctions = distinctions_doc["unresolved_distinctions"]
    estimates = estimates_doc["estimates"]

    # S2 — principle abduction (deterministic feature matching)
    app = abduct.abduce(task, distinctions, contract=contract, theory=theory)
    app_doc = app.to_dict()
    app_doc["ordered_applicability"] = ordered_applicability(theory,
                                                             distinctions)
    jdump(out_dir / "applicability.json", app_doc)

    # S3 — candidate generation from the closed grammar + serialized
    # model value estimates (cost deterministic from call structure)
    candidates = generate.generate_candidates(
        task, distinctions, app, contract, max_candidates=4)
    for c in candidates:
        fam = family_of(c.topology_id)
        est = estimates[fam]
        c.predicted_value = {
            "delta_e": round(float(est["delta_e"]), 4),
            "cost": predicted_cost(fam),
            "redundancy": round(float(est["redundancy"]), 4),
            "governance_risk": round(float(est["governance_risk"]), 4),
        }

    # S4 — freeze falsifier-complete predictions (immutable hashes)
    frozen = {}
    for c in candidates:
        preds = predict.freeze_predictions(c, distinctions)
        frozen[c.topology_id] = {
            "predictions": [p.to_dict() for p in preds],
            "predictions_hash": c.predictions_hash,
        }
    jdump(out_dir / "frozen-predictions.json", frozen)

    # S5 — formal validation, then deterministic ranking of valid candidates
    (out_dir / "formal-results").mkdir(parents=True, exist_ok=True)
    valid = []
    validation = {}
    for c in candidates:
        res = validate.validate_topology(c, contract)
        jdump(out_dir / "formal-results" / f"{c.topology_id}.json",
              res.to_dict())
        validation[c.topology_id] = res.status
        if res.status == "PASS":
            c.status = "VALIDATED"
            valid.append(c)
        else:
            c.status = "REJECTED"
    (out_dir / "candidates").mkdir(parents=True, exist_ok=True)
    for c in candidates:
        jdump(out_dir / "candidates" / f"{c.topology_id}.json", c.to_dict())

    if not valid:
        ranking_doc = {"trial_id": trial_id, "ranking": [],
                       "validation": validation,
                       "selected": None,
                       "runner_up": None,
                       "note": "no valid candidate; FORMAL_REJECTION"}
        jdump(out_dir / "candidate-ranking.json", ranking_doc)
        return ranking_doc

    config = utility.load_utility_config()
    ranking = utility.rank_candidates(valid, config)
    selected_id = ranking[0]["topology_id"]
    runner_up_id = ranking[1]["topology_id"] if len(ranking) > 1 else None
    ranking_doc = {
        "trial_id": trial_id,
        "utility_config": config,
        "ranking": ranking,
        "validation": validation,
        "selected": selected_id,
        "runner_up": runner_up_id,
        "tie_break": "utility desc, node_count asc, model_calls asc, "
                     "topology_id asc",
    }
    jdump(out_dir / "candidate-ranking.json", ranking_doc)

    selected = next(c for c in candidates if c.topology_id == selected_id)
    jdump(out_dir / "selected-topology.json", {
        "trial_id": trial_id,
        "topology_id": selected_id,
        "family": family_of(selected_id),
        "predicted_value": selected.predicted_value,
        "predicted_utility": ranking[0]["utility"],
        "predictions_hash": selected.predictions_hash,
        "selected_before_realization": True,
    })
    return ranking_doc
