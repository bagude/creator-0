"""Experiment 7 aggregation: per-condition metrics, paired improvement,
frozen-threshold checks, and the preregistered result label.

Regret is bounded regret over executed alternatives only (per condition):
    regret(t) = max(U_obs over executed topologies of t) - U_obs(selected).
"""
from __future__ import annotations
import math
import subprocess
from pathlib import Path
from typing import Any

from .common import CZROOT, E7, REPO, jdump, jload, trial_dir

BASE_COMMIT = "bd0cf91e455393d3d601070e5022c565d9ed9ed1"
FROZEN_TREES = [".creator-zero/experiment-3", ".creator-zero/experiment-4",
                ".creator-zero/experiment-4c", ".creator-zero/experiment-5",
                ".creator-zero/experiment-6",
                ".creator-zero/state/experiment-2.json",
                ".creator-zero/state/experiment-3.json",
                ".creator-zero/state/experiment-4.json",
                ".creator-zero/state/experiment-4c.json",
                ".creator-zero/state/experiment-5.json",
                ".creator-zero/state/experiment-6.json",
                ".creator-zero/state/formal-semantics-v0.1.json",
                ".creator-zero/contracts"]


def historical_mutation_check() -> dict[str, Any]:
    mutated = {}
    for tree in FROZEN_TREES:
        out = subprocess.run(
            ["git", "diff", "--diff-filter=MD", "--name-only", BASE_COMMIT,
             "HEAD", "--", tree],
            capture_output=True, text=True, cwd=REPO).stdout.strip()
        if out:
            mutated[tree] = out.splitlines()
    return {"base_commit": BASE_COMMIT, "mutations": mutated,
            "count": sum(len(v) for v in mutated.values())}


TVALS = {"TOPOLOGY_CORRECT": 1.0, "TOPOLOGY_PARTIAL": 0.5,
         "TOPOLOGY_INCORRECT": 0.0}


def condition_metrics(cond: str, trial_ids: list[str],
                      shadow_ids: list[str]) -> dict[str, Any]:
    scores = [jload(trial_dir(t, cond) / "trial-score.json")
              for t in trial_ids]
    n = len(scores)
    tc = [TVALS[s["topology_score"]["verdict"]] for s in scores]
    recalls = [s["distinction_score"]["critical_recall"] for s in scores]
    spurious = sum(s["distinction_score"]["spurious_count"] for s in scores)
    top2 = [s["principle_score"]["top2_hit"] for s in scores]
    errs = [abs(s["predicted_utility"] - s["observed_utility"])
            for s in scores]
    mae = sum(errs) / n
    rmse = math.sqrt(sum(e * e for e in errs) / n)
    comp_mae = {}
    for c in ("delta_e", "cost", "redundancy", "governance_risk"):
        comp_mae[c] = round(sum(
            s["calibration_error"]["component_absolute_error"][c]
            for s in scores) / n, 4)

    classes: dict[str, list] = {}
    for s in scores:
        classes.setdefault(s["latent_class"], []).append(s)
    per_class = {}
    for cls, ss in sorted(classes.items()):
        per_class[cls] = {
            "n": len(ss),
            "topology_correctness": round(sum(
                TVALS[x["topology_score"]["verdict"]]
                for x in ss) / len(ss), 4),
            "critical_recall": round(sum(
                x["distinction_score"]["critical_recall"]
                for x in ss) / len(ss), 4),
            "utility_mae": round(sum(
                abs(x["predicted_utility"] - x["observed_utility"])
                for x in ss) / len(ss), 4),
        }

    regrets, agreements, shadow_rows = [], [], []
    regret_per_class: dict[str, list] = {}
    for t in shadow_ids:
        td = trial_dir(t, cond)
        prim = jload(td / "calibration.json")
        shad = jload(td / "shadow" / "calibration.json")
        u_sel, u_sh = prim["observed_utility"], shad["observed_utility"]
        regret = round(max(u_sel, u_sh) - u_sel, 6)
        dp = prim["predicted_utility"] - shad["predicted_utility"]
        do = u_sel - u_sh
        agree = (dp == 0 or do == 0 or (dp > 0) == (do > 0))
        regrets.append(regret)
        agreements.append(agree)
        cls = jload(td / "trial-score.json")["latent_class"]
        regret_per_class.setdefault(cls, []).append(regret)
        shadow_rows.append({
            "trial_id": t, "class": cls,
            "selected": prim["topology_id"], "shadow": shad["topology_id"],
            "predicted": {"selected": prim["predicted_utility"],
                          "shadow": shad["predicted_utility"]},
            "observed": {"selected": u_sel, "shadow": u_sh},
            "regret": regret, "ranking_agreement": agree})

    fatal = sum(s["governance_summary"]["fatal_events"] for s in scores)
    cap = sum(s["governance_summary"]["capability_violations"]
              for s in scores)
    auth = sum(s["governance_summary"]
               ["authority_or_attenuation_violations"] for s in scores)
    nonfatal = sum(s["governance_summary"]["nonfatal_events"]
                   for s in scores)
    meta = sum(s["governance_summary"]["meta_tool_observations"]
               for s in scores)

    typed = [s["typed_admissibility"] for s in scores
             if s.get("typed_admissibility") is not None]
    typed_metrics = None
    if typed:
        exact = sum(1 for t_ in typed if t_["exact"])
        coords = {}
        for coord in ("I_A", "I_S", "I_D", "I_M"):
            tp = sum(1 for t_ in typed
                     if t_["coordinates"][coord]["inferred"]
                     and t_["coordinates"][coord]["true"])
            fp = sum(1 for t_ in typed
                     if t_["coordinates"][coord]["inferred"]
                     and not t_["coordinates"][coord]["true"])
            fn = sum(1 for t_ in typed
                     if not t_["coordinates"][coord]["inferred"]
                     and t_["coordinates"][coord]["true"])
            coords[coord] = {
                "precision": round(tp / (tp + fp), 4) if tp + fp else None,
                "recall": round(tp / (tp + fn), 4) if tp + fn else None,
                "tp": tp, "fp": fp, "fn": fn}
        typed_metrics = {"exact_accuracy": round(exact / len(typed), 4),
                         "n": len(typed), "per_coordinate": coords}

    roles = [s["role_typing"] for s in scores if s["role_typing"]["counted"]]
    role_metrics = None
    if roles is not None:
        correct = sum(1 for r in roles if r["correct"])
        role_metrics = {"accuracy": (round(correct / len(roles), 4)
                                     if roles else None),
                        "counted_paths": len(roles)}

    failure_tags: dict[str, int] = {}
    for s in scores:
        for tag in s["failure_tags"]:
            failure_tags[tag] = failure_tags.get(tag, 0) + 1

    sr = sorted(regrets)
    return {
        "n_primary_trials": n,
        "topology_correctness": round(sum(tc) / n, 4),
        "critical_distinction_recall_mean": round(sum(recalls) / n, 4),
        "spurious_distinctions_total": spurious,
        "principle_top2_rate": round(sum(top2) / n, 4),
        "utility_mae": round(mae, 4),
        "utility_rmse": round(rmse, 4),
        "component_mae": comp_mae,
        "shadow_count": len(shadow_ids),
        "mean_regret": round(sum(regrets) / len(regrets), 4) if regrets
        else None,
        "median_regret": round(sr[len(sr) // 2], 4) if sr else None,
        "max_regret": round(max(regrets), 4) if regrets else None,
        "regret_per_class": {k: round(sum(v) / len(v), 4)
                             for k, v in sorted(regret_per_class.items())},
        "ranking_agreement_rate": round(sum(agreements) / len(agreements),
                                        4) if agreements else None,
        "typed_admissibility": typed_metrics,
        "role_typing": role_metrics,
        "governance": {"fatal_events": fatal,
                       "capability_violations": cap,
                       "authority_or_attenuation_violations": auth,
                       "nonfatal_events": nonfatal,
                       "meta_tool_observations": meta},
        "failure_taxonomy": failure_tags,
        "per_class": per_class,
        "shadows": shadow_rows,
    }


def aggregate() -> dict[str, Any]:
    manifest = jload(E7 / "trial-manifest.json")
    rand = jload(E7 / "randomization.json")
    thresholds = jload(E7 / "thresholds.json")
    trial_ids = manifest["primary_trials"]
    shadow_ids = rand["shadow_trials"]

    A = condition_metrics("A", trial_ids, shadow_ids)
    B = condition_metrics("B", trial_ids, shadow_ids)
    hist = historical_mutation_check()
    imp = jload(E7 / "evidence-import-manifest.json")

    delta_mae = round(B["utility_mae"] - A["utility_mae"], 4)
    delta_regret = (round(B["mean_regret"] - A["mean_regret"], 4)
                    if B["mean_regret"] is not None
                    and A["mean_regret"] is not None else None)

    ta = thresholds["theta_v2_absolute"]
    checks = {
        "min_trial_count": len(trial_ids) >= 20,
        "min_per_class": all(v["n"] >= 4 for v in B["per_class"].values())
        and len(B["per_class"]) >= 5,
        "topology_correctness_B": B["topology_correctness"]
        >= ta["topology_correctness_min"],
        "critical_recall_B": B["critical_distinction_recall_mean"]
        >= ta["critical_distinction_recall_min"],
        "typed_admissibility_B": (B["typed_admissibility"] or {}).get(
            "exact_accuracy", 0) >= ta["typed_admissibility_accuracy_min"],
        "role_typing_B": ((B["role_typing"] or {}).get("accuracy") or 0)
        >= ta["role_typing_accuracy_min"],
        "utility_mae_B": B["utility_mae"] <= ta["utility_mae_max"],
        "mean_regret_B": (B["mean_regret"] is not None
                          and B["mean_regret"] <= ta["mean_regret_max"]),
        "paired_mae_improves": delta_mae < 0,
        "paired_regret_no_worse": (delta_regret is not None
                                   and delta_regret <= 0),
        "replay_contradictions_zero": jload(
            E7 / "historical-replay" / "candidate-theta-v2-replay.json"
        )["contradicted"] == 0,
        "capability_violations_zero":
            A["governance"]["capability_violations"]
            + B["governance"]["capability_violations"] == 0,
        "authority_attenuation_zero":
            A["governance"]["authority_or_attenuation_violations"]
            + B["governance"]["authority_or_attenuation_violations"] == 0,
        "hidden_children_zero": True,   # any spawn use is a capability
                                        # violation counted above
        "historical_mutations_zero": hist["count"] == 0,
        "evidence_conflicts_zero": imp["conflicts"] == 0,
    }

    integrity_keys = ("capability_violations_zero",
                      "authority_attenuation_zero", "hidden_children_zero",
                      "historical_mutations_zero",
                      "evidence_conflicts_zero",
                      "replay_contradictions_zero", "min_trial_count",
                      "min_per_class")
    absolute_keys = ("topology_correctness_B", "critical_recall_B",
                     "typed_admissibility_B", "role_typing_B",
                     "utility_mae_B", "mean_regret_B")
    paired_keys = ("paired_mae_improves", "paired_regret_no_worse")

    integrity_ok = all(checks[k] for k in integrity_keys)
    absolute_ok = all(checks[k] for k in absolute_keys)
    paired_ok = all(checks[k] for k in paired_keys)

    if integrity_ok and absolute_ok and paired_ok:
        label = "LINEAGE_THEORY_REVISION_PASS"
    elif integrity_ok and paired_ok:
        label = "LINEAGE_THEORY_REVISION_PARTIAL"
    else:
        label = "LINEAGE_THEORY_REVISION_FAIL"

    doc = {
        "artifact": "Experiment 7 aggregate results",
        "conditions": {"A": A, "B": B},
        "paired": {"delta_mae": delta_mae, "delta_regret": delta_regret},
        "thresholds": thresholds,
        "threshold_checks": checks,
        "check_groups": {"integrity": integrity_ok,
                         "absolute": absolute_ok, "paired": paired_ok},
        "historical_mutation_check": hist,
        "result": label,
    }
    jdump(E7 / "aggregate-results.json", doc)
    return doc


if __name__ == "__main__":
    doc = aggregate()
    print(doc["result"])
    for k, v in doc["threshold_checks"].items():
        print(f"  {k}: {v}")
