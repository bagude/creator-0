"""Topology economics: predicted/observed utility and deterministic ranking.

    U_hat(H) = DeltaE_hat(H) - lambda*C(H) - mu*R(H) - nu*G(H)

Weights live in explicit config (utility-config.json beside this module),
never in prompts. All components are normalized [0,1] for v0.1.

Ranking is fully deterministic:
    utility desc, then node_count asc, then model_calls asc,
    then topology_id asc (lexicographic).
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any

from .model import ModelValidationError, TopologyHypothesis

CONFIG_PATH = Path(__file__).resolve().parent / "utility-config.json"

DEFAULT_CONFIG = {
    "lambda_cost": 1.0,
    "mu_redundancy": 1.0,
    "nu_governance": 2.0,
}

COMPONENTS = ("delta_e", "cost", "redundancy", "governance_risk")


def load_utility_config(path: str | Path | None = None) -> dict[str, float]:
    p = Path(path) if path else CONFIG_PATH
    if p.exists():
        cfg = json.loads(p.read_text(encoding="utf-8"))
    else:
        cfg = dict(DEFAULT_CONFIG)
    for k in DEFAULT_CONFIG:
        if k not in cfg:
            raise ModelValidationError(f"utility config missing {k}")
    return {k: float(cfg[k]) for k in DEFAULT_CONFIG}


def _components(value: dict[str, Any], where: str) -> dict[str, float]:
    out = {}
    for c in COMPONENTS:
        if c not in value:
            raise ModelValidationError(f"{where}: missing component {c!r}")
        v = float(value[c])
        if not (0.0 <= v <= 1.0):
            raise ModelValidationError(
                f"{where}: component {c}={v} outside normalized [0,1]")
        out[c] = v
    return out


def utility(value: dict[str, Any], config: dict[str, float],
            where: str = "value") -> float:
    v = _components(value, where)
    u = (v["delta_e"]
         - config["lambda_cost"] * v["cost"]
         - config["mu_redundancy"] * v["redundancy"]
         - config["nu_governance"] * v["governance_risk"])
    return round(u, 10)


def predicted_utility(topology: TopologyHypothesis | dict[str, Any],
                      config: dict[str, float] | None = None) -> float:
    if isinstance(topology, dict):
        topology = TopologyHypothesis.from_dict(topology)
    cfg = config or load_utility_config()
    return utility(topology.predicted_value, cfg,
                   f"{topology.topology_id}.predicted_value")


def observed_utility(observed_value: dict[str, Any],
                     config: dict[str, float] | None = None) -> float:
    cfg = config or load_utility_config()
    return utility(observed_value, cfg, "observed_value")


def rank_candidates(candidates: list[TopologyHypothesis],
                    config: dict[str, float] | None = None,
                    ) -> list[dict[str, Any]]:
    """Deterministic ranking of (already validated) candidates."""
    cfg = config or load_utility_config()
    rows = []
    for c in candidates:
        rows.append({
            "topology_id": c.topology_id,
            "utility": predicted_utility(c, cfg),
            "node_count": c.node_count(),
            "model_calls": c.model_calls(),
            "predicted_value": dict(c.predicted_value),
        })
    rows.sort(key=lambda r: (-r["utility"], r["node_count"],
                             r["model_calls"], r["topology_id"]))
    for i, r in enumerate(rows):
        r["rank"] = i + 1
    return rows


def calibration_error(predicted_value: dict[str, Any],
                      observed_value: dict[str, Any],
                      config: dict[str, float] | None = None,
                      ) -> dict[str, Any]:
    """Component-wise absolute error + utility error. Deterministic."""
    cfg = config or load_utility_config()
    pv = _components(predicted_value, "predicted_value")
    ov = _components(observed_value, "observed_value")
    comp = {c: round(abs(pv[c] - ov[c]), 10) for c in COMPONENTS}
    return {
        "component_absolute_error": comp,
        "mean_component_error": round(sum(comp.values()) / len(comp), 10),
        "utility_error": round(
            abs(utility(pv, cfg) - utility(ov, cfg)), 10),
    }
