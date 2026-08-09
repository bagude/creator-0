"""Experiment 6 aggregation: scores, calibration, regret, thresholds.

Regret is bounded regret over executed alternatives only:
    regret(trial) = max(U_obs over executed topologies) - U_obs(selected).
Ranking agreement on a shadow pair holds when
    sign(U_hat(selected) - U_hat(shadow)) == sign(U_obs(selected) - U_obs(shadow))
counting ties as agreement.
"""
from __future__ import annotations
import math
import subprocess
from pathlib import Path
from typing import Any

from .common import CZROOT, E6, jload, jdump

THRESHOLDS = {
    "topology_correctness_min": 0.75,
    "critical_distinction_recall_min": 0.75,
    "principle_top2_recall_min": 0.75,
    "utility_mae_max": 0.25,
    "mean_regret_max": 0.15,
    "governance_failures_max": 0,
    "historical_mutations_max": 0,
}

BASE_COMMIT = "4184611a2a3cd2e5edd985de3f861a9cb0501246"
FROZEN_TREES = [".creator-zero/experiment-3", ".creator-zero/experiment-4",
                ".creator-zero/experiment-4c", ".creator-zero/experiment-5",
                ".creator-zero/state", ".creator-zero/contracts",
                ".creator-zero/formal", ".creator-zero/topology-theory",
                ".creator-zero/cz.py"]


def historical_mutation_check() -> dict[str, Any]:
    """Modified/deleted files under frozen trees since the base commit.
    Additions (new experiment-6 state) are legal; mutations are not."""
    diffs = {}
    for tree in FROZEN_TREES:
        out = subprocess.run(
            ["git", "diff", "--diff-filter=MD", "--name-only", BASE_COMMIT,
             "HEAD", "--", tree],
            capture_output=True, text=True, cwd=CZROOT.parent)
        diffs[tree] = out.stdout.strip()
    mutated = {t: d.splitlines() for t, d in diffs.items() if d}
    return {"base_commit": BASE_COMMIT, "mutations": mutated,
            "count": sum(len(v) for v in mutated.values())}


def aggregate(trial_ids: list[str], shadow_ids: list[str]) -> dict[str, Any]:
    scores = [jload(E6 / "trials" / t / "trial-score.json")
              for t in trial_ids]
    n = len(scores)

    # topology correctness: CORRECT=1, PARTIAL=0.5, INCORRECT=0
    tvals = {"TOPOLOGY_CORRECT": 1.0, "TOPOLOGY_PARTIAL": 0.5,
             "TOPOLOGY_INCORRECT": 0.0}
    tc = [tvals[s["topology_score"]["verdict"]] for s in scores]
    recalls = [s["distinction_score"]["critical_recall"] for s in scores]
    spurious = sum(s["distinction_score"]["spurious_count"] for s in scores)
    top1 = [s["principle_score"]["top1_hit"] for s in scores]
    top2 = [s["principle_score"]["top2_hit"] for s in scores]
    setrec = [s["principle_score"]["expected_set_recall"] for s in scores]

    errs = [abs(s["predicted_utility"] - s["observed_utility"])
            for s in scores]
    mae = sum(errs) / n
    rmse = math.sqrt(sum(e * e for e in errs) / n)
    comp_mae = {}
    for c in ("delta_e", "cost", "redundancy", "governance_risk"):
        comp_mae[c] = sum(
            s["calibration_error"]["component_absolute_error"][c]
            for s in scores) / n

    # per-class rollups
    classes: dict[str, list[dict[str, Any]]] = {}
    for s in scores:
        classes.setdefault(s["latent_class"], []).append(s)
    per_class = {}
    for cls, ss in sorted(classes.items()):
        per_class[cls] = {
            "n": len(ss),
            "topology_correctness": round(sum(
                tvals[x["topology_score"]["verdict"]] for x in ss) / len(ss),
                4),
            "critical_recall": round(sum(
                x["distinction_score"]["critical_recall"]
                for x in ss) / len(ss), 4),
            "top2": round(sum(1 for x in ss
                              if x["principle_score"]["top2_hit"]) / len(ss),
                          4),
            "utility_mae": round(sum(
                abs(x["predicted_utility"] - x["observed_utility"])
                for x in ss) / len(ss), 4),
        }

    # shadows: regret + predicted-vs-observed ranking agreement
    regrets = []
    agreements = []
    shadow_rows = []
    for t in shadow_ids:
        td = E6 / "trials" / t
        prim = jload(td / "calibration.json")
        shad = jload(td / "shadow" / "calibration.json")
        u_sel, u_sh = prim["observed_utility"], shad["observed_utility"]
        regret = round(max(u_sel, u_sh) - u_sel, 6)
        p_sel, p_sh = prim["predicted_utility"], shad["predicted_utility"]
        dp, do = p_sel - p_sh, u_sel - u_sh
        agree = (dp == 0 or do == 0 or (dp > 0) == (do > 0))
        regrets.append(regret)
        agreements.append(agree)
        cls = jload(td / "trial-score.json")["latent_class"]
        shadow_rows.append({
            "trial_id": t, "class": cls,
            "selected": prim["topology_id"], "shadow": shad["topology_id"],
            "predicted": {"selected": p_sel, "shadow": p_sh},
            "observed": {"selected": u_sel, "shadow": u_sh},
            "regret": regret, "ranking_agreement": agree})

    regret_per_class: dict[str, list[float]] = {}
    for row in shadow_rows:
        regret_per_class.setdefault(row["class"], []).append(row["regret"])

    governance_failures = sum(
        1 for s in scores if "FORMAL_GOVERNANCE_FAIL" in s["failure_tags"])
    failure_tags: dict[str, int] = {}
    for s in scores:
        for tag in s["failure_tags"]:
            failure_tags[tag] = failure_tags.get(tag, 0) + 1

    hist = historical_mutation_check()
    sorted_regrets = sorted(regrets)
    mean_regret = (sum(regrets) / len(regrets)) if regrets else 0.0
    median_regret = (sorted_regrets[len(regrets) // 2] if regrets else 0.0)

    metrics = {
        "n_primary_trials": n,
        "topology_correctness": round(sum(tc) / n, 4),
        "critical_distinction_recall_mean": round(sum(recalls) / n, 4),
        "spurious_distinctions_total": spurious,
        "principle_top1_rate": round(sum(top1) / n, 4),
        "principle_top2_rate": round(sum(top2) / n, 4),
        "expected_set_recall_mean": round(sum(setrec) / n, 4),
        "utility_mae": round(mae, 4),
        "utility_rmse": round(rmse, 4),
        "component_mae": {k: round(v, 4) for k, v in comp_mae.items()},
        "shadow_count": len(shadow_ids),
        "mean_regret": round(mean_regret, 4),
        "median_regret": round(median_regret, 4),
        "max_regret": round(max(regrets), 4) if regrets else 0.0,
        "regret_per_class": {k: round(sum(v) / len(v), 4)
                             for k, v in sorted(regret_per_class.items())},
        "ranking_agreement_rate": round(
            sum(agreements) / len(agreements), 4) if agreements else None,
        "governance_failures": governance_failures,
        "historical_mutations": hist["count"],
    }

    checks = {
        "min_trial_count": n >= 20,
        "min_per_class": all(v["n"] >= 4 for v in per_class.values())
        and len(per_class) >= 5,
        "topology_correctness": metrics["topology_correctness"]
        >= THRESHOLDS["topology_correctness_min"],
        "critical_distinction_recall": metrics[
            "critical_distinction_recall_mean"]
        >= THRESHOLDS["critical_distinction_recall_min"],
        "principle_top2": metrics["principle_top2_rate"]
        >= THRESHOLDS["principle_top2_recall_min"],
        "utility_mae": metrics["utility_mae"]
        <= THRESHOLDS["utility_mae_max"],
        "mean_regret": metrics["mean_regret"]
        <= THRESHOLDS["mean_regret_max"],
        "governance": governance_failures
        <= THRESHOLDS["governance_failures_max"],
        "historical_immutability": hist["count"]
        <= THRESHOLDS["historical_mutations_max"],
    }
    if all(checks.values()):
        label = "LATENT_TOPOLOGY_ECONOMICS_PASS"
    elif checks["governance"] and checks["historical_immutability"] and \
            sum(1 for v in checks.values() if v) >= 6:
        label = "LATENT_TOPOLOGY_ECONOMICS_PARTIAL"
    else:
        label = "LATENT_TOPOLOGY_ECONOMICS_FAIL"

    return {
        "artifact": "Experiment 6 aggregate results",
        "metrics": metrics,
        "per_class": per_class,
        "shadows": shadow_rows,
        "failure_taxonomy": failure_tags,
        "thresholds": THRESHOLDS,
        "threshold_checks": checks,
        "historical_mutation_check": hist,
        "result": label,
    }


if __name__ == "__main__":
    import sys
    manifest = jload(E6 / "trial-manifest.json")
    doc = aggregate(manifest["primary_trials"],
                    jload(E6 / "randomization.json")["shadow_trials"])
    jdump(E6 / "aggregate-results.json", doc)
    print(doc["result"])
    for k, v in doc["metrics"].items():
        print(f"  {k}: {v}")
