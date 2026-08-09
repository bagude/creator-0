"""Prediction-specific falsification and principle evidence emission.

    falsify(predictions, evaluation) -> FalsificationResult

A topology hypothesis is falsified prediction-by-prediction: task success
does not imply every topology prediction held. Statuses:

    SUPPORTED            every mechanical prediction HELD
    PARTIALLY_SUPPORTED  some HELD, some FAILED
    FALSIFIED            no mechanical prediction HELD, at least one FAILED
    INDETERMINATE        no FAILED but at least one INDETERMINATE

For every invoked principle an append-only evidence event is emitted:
    HELD   -> SUPPORT
    FAILED -> FALSIFY when the prediction carries full weight (>= 1.0),
              CHALLENGE otherwise
    INDETERMINATE -> no event (absence of evidence is not evidence)
"""
from __future__ import annotations
from typing import Any

from .model import (FalsificationResult, Prediction, PrincipleEvidence,
                    TopologyEvaluation)


def falsify(predictions: list[Prediction] | list[dict[str, Any]],
            evaluation: TopologyEvaluation | dict[str, Any],
            ) -> FalsificationResult:
    preds = {p.prediction_id if isinstance(p, Prediction) else
             p["prediction_id"]:
             (p if isinstance(p, Prediction) else Prediction.from_dict(p))
             for p in predictions}
    ev = evaluation.to_dict() if isinstance(evaluation, TopologyEvaluation) \
        else dict(evaluation)
    tid = ev["topology_id"]

    held, failed, indet = [], [], []
    statuses = []
    for o in ev.get("prediction_outcomes", []):
        pid = o["prediction_id"]
        outcome = o["outcome"]
        if outcome == "HELD":
            held.append(pid)
            status = "SUPPORTED"
        elif outcome == "FAILED":
            failed.append(pid)
            status = "FALSIFIED"
        else:
            indet.append(pid)
            status = "INDETERMINATE"
        statuses.append({"prediction_id": pid, "outcome": outcome,
                         "status": status, "why": o.get("why", "")})

    if failed and held:
        topo_status = "PARTIALLY_SUPPORTED"
    elif failed:
        topo_status = "FALSIFIED"
    elif indet:
        topo_status = "INDETERMINATE"
    else:
        topo_status = "SUPPORTED"

    events = principle_evidence_events(list(preds.values()), ev)
    return FalsificationResult(
        topology_id=tid,
        status=topo_status,
        prediction_statuses=statuses,
        falsified_predictions=sorted(failed),
        evidence_events=[e.to_dict() for e in events],
    )


def principle_evidence_events(predictions: list[Prediction],
                              evaluation: dict[str, Any],
                              ) -> list[PrincipleEvidence]:
    tid = evaluation["topology_id"]
    outcome_by_id = {o["prediction_id"]: o["outcome"]
                     for o in evaluation.get("prediction_outcomes", [])}
    events: list[PrincipleEvidence] = []
    n = 0
    for p in sorted(predictions, key=lambda x: x.prediction_id):
        outcome = outcome_by_id.get(p.prediction_id)
        if outcome == "HELD":
            effect = "SUPPORT"
        elif outcome == "FAILED":
            effect = "FALSIFY" if p.weight >= 1.0 else "CHALLENGE"
        else:
            continue
        for principle_id in p.principles:
            n += 1
            events.append(PrincipleEvidence(
                principle_id=principle_id,
                topology_id=tid,
                prediction_id=p.prediction_id,
                effect=effect,
                evidence_refs=[{"evaluation_topology": tid,
                                "prediction_outcome": outcome}],
                event_id=f"{tid}-ev{n:03d}",
            ))
    return events
