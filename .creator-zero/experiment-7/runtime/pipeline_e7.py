"""Deterministic S2-S5 pipelines for both E7 conditions.

Condition A is the frozen E6 pipeline semantics (theta-v1, grammar v1,
per-family model estimates, utility v1); condition B is the candidate
theta-v2 system (typed features, grammar v2, admissibility filtering before
economics, deterministic saturating utility components, typed prediction
attribution). Selection is complete before any realization in both
conditions; model output cannot override any rejection or the ranking
arithmetic."""
from __future__ import annotations
from pathlib import Path
from typing import Any

from .common import (E7, family_of, jdump, load_theta, predicted_cost,
                     trial_contract, tt_mod)


def ordered_applicability(theory, distinctions) -> list[dict[str, Any]]:
    """E6 rule verbatim: feature-match count desc, principle id asc."""
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


def _persist(out_dir: Path, candidates, validation, ranking_rows,
             selected, runner_up, extra: dict[str, Any]) -> dict[str, Any]:
    (out_dir / "candidates").mkdir(parents=True, exist_ok=True)
    for c in candidates:
        jdump(out_dir / "candidates" / f"{c.topology_id}.json", c.to_dict())
    doc = {
        "validation": validation,
        "ranking": ranking_rows,
        "selected": selected,
        "runner_up": runner_up,
        **extra,
    }
    jdump(out_dir / "candidate-ranking.json", doc)
    return doc


def run_pipeline_a(trial_id: str, task: dict[str, Any],
                   distinctions_doc: dict[str, Any],
                   estimates_doc: dict[str, Any],
                   out_dir: Path) -> dict[str, Any]:
    """Frozen E6 semantics under promoted theta-v1."""
    abduct = tt_mod("abduct")
    generate = tt_mod("generate")
    predict = tt_mod("predict")
    validate = tt_mod("validate")
    utility = tt_mod("utility")

    theory = load_theta("A")
    contract = trial_contract()
    distinctions = distinctions_doc["unresolved_distinctions"]
    estimates = estimates_doc["estimates"]

    app = abduct.abduce(task, distinctions, contract=contract, theory=theory)
    app_doc = app.to_dict()
    app_doc["ordered_applicability"] = ordered_applicability(theory,
                                                             distinctions)
    jdump(out_dir / "applicability.json", app_doc)

    candidates = generate.generate_candidates(
        task, distinctions, app, contract, max_candidates=4)
    for c in candidates:
        fam = family_of(c.topology_id, "A")
        est = estimates[fam if fam in estimates else fam]
        c.predicted_value = {
            "delta_e": round(float(est["delta_e"]), 4),
            "cost": predicted_cost(fam, "A"),
            "redundancy": round(float(est["redundancy"]), 4),
            "governance_risk": round(float(est["governance_risk"]), 4),
        }

    frozen = {}
    for c in candidates:
        preds = predict.freeze_predictions(c, distinctions)
        frozen[c.topology_id] = {
            "predictions": [p.to_dict() for p in preds],
            "predictions_hash": c.predictions_hash,
        }
    jdump(out_dir / "frozen-predictions.json", frozen)

    (out_dir / "formal-results").mkdir(parents=True, exist_ok=True)
    valid, validation = [], {}
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
    rows = utility.rank_candidates(valid)
    selected = rows[0]["topology_id"] if rows else None
    runner_up = rows[1]["topology_id"] if len(rows) > 1 else None
    return _persist(out_dir, candidates, validation, rows, selected,
                    runner_up, {"condition": "A", "theory_version": 1})


def run_pipeline_b(trial_id: str, task: dict[str, Any],
                   distinctions_doc: dict[str, Any],
                   estimates_doc: dict[str, Any],
                   out_dir: Path) -> dict[str, Any]:
    """Candidate theta-v2 system: typed admissibility before economics."""
    abduct = tt_mod("abduct")
    generate2 = tt_mod("generate2")
    predict2 = tt_mod("predict2")
    validate = tt_mod("validate")
    utility = tt_mod("utility")
    adm = tt_mod("admissibility")

    theory = load_theta("B")
    contract = trial_contract()
    distinctions = distinctions_doc["unresolved_distinctions"]
    values = {q: float(v["value"])
              for q, v in estimates_doc["estimates"].items()}

    app = abduct.abduce(task, distinctions, contract=contract, theory=theory)
    app_doc = app.to_dict()
    app_doc["ordered_applicability"] = ordered_applicability(theory,
                                                             distinctions)
    jdump(out_dir / "applicability.json", app_doc)

    candidates = generate2.generate_candidates_v2(
        task, distinctions, app, contract, values)

    reqs = [adm.requirement_for_distinction(d) for d in distinctions]
    jdump(out_dir / "requirements.json",
          {"requirements": [r.to_dict() for r in reqs]})

    frozen = {}
    for c in candidates:
        preds = predict2.freeze_predictions_v2(c, distinctions)
        frozen[c.topology_id] = {
            "predictions": [p.to_dict() for p in preds],
            "predictions_hash": c.predictions_hash,
        }
    jdump(out_dir / "frozen-predictions.json", frozen)

    (out_dir / "formal-results").mkdir(parents=True, exist_ok=True)
    valid, validation, admissibility = [], {}, {}
    for c in candidates:
        res = validate.validate_topology(c, contract)
        jdump(out_dir / "formal-results" / f"{c.topology_id}.json",
              res.to_dict())
        validation[c.topology_id] = res.status
        a = adm.topology_admissible(
            adm.provisions_from_spec(c.harness_spec), reqs)
        admissibility[c.topology_id] = a
        if res.status == "PASS" and a["admissible"]:
            c.status = "VALIDATED"
            valid.append(c)
        else:
            c.status = "REJECTED"
    rows = utility.rank_candidates(valid)
    selected = rows[0]["topology_id"] if rows else None
    runner_up = rows[1]["topology_id"] if len(rows) > 1 else None
    return _persist(out_dir, candidates, validation, rows, selected,
                    runner_up, {"condition": "B",
                                "theory_version": "candidate-theta-v2",
                                "admissibility": {
                                    t: a["admissible"]
                                    for t, a in admissibility.items()}})


def run_pipeline(condition: str, *args, **kw) -> dict[str, Any]:
    return (run_pipeline_a if condition == "A" else run_pipeline_b)(
        *args, **kw)
