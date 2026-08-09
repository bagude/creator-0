"""Prediction freezing: falsifiable consequences before execution.

    freeze_predictions(topology, distinctions) -> list[Prediction]

Every claimed resolved distinction gets at least one prediction with an
observable success condition AND a falsification condition; a prediction
without a falsifier is invalid by the Prediction validator, and a topology
whose resolution claims are not covered raises PredictionError.

Freezing is cryptographic, not procedural: the canonical serialization of
the prediction list is hashed into topology.predictions_hash (artifact id).
evaluate.py refuses to evaluate against predictions whose recomputed hash
differs — retrospective edits are detectable, hence inadmissible.
"""
from __future__ import annotations
from typing import Any

from .model import (ModelValidationError, Prediction, TopologyHypothesis)
from .serialization import object_artifact_id


class PredictionError(ValueError):
    """The topology's predictions are not falsifiable/complete."""


def predictions_hash(topology_id: str,
                     predictions: list[dict[str, Any]]) -> str:
    return object_artifact_id(
        predictions,
        f"creator-0/topology-theory/predictions/{topology_id}")


def _is_child_topology(spec: dict[str, Any]) -> bool:
    return any(n.get("primitive") == "create" for n in spec.get("nodes", []))


def _expected_path(spec: dict[str, Any]) -> list[str]:
    """Deterministic topological order (Kahn, lexicographic tie-break)."""
    ids = [n["id"] for n in spec.get("nodes", [])]
    deg = {i: 0 for i in ids}
    adj: dict[str, list[str]] = {i: [] for i in ids}
    for e in spec.get("edges", []):
        if e.get("relation") == "return":
            continue
        adj[e["source"]].append(e["target"])
        deg[e["target"]] += 1
    ready = sorted(i for i in ids if deg[i] == 0)
    out: list[str] = []
    while ready:
        x = ready.pop(0)
        out.append(x)
        for y in sorted(adj[x]):
            deg[y] -= 1
            if deg[y] == 0:
                ready.append(y)
        ready.sort()
    return out


def freeze_predictions(topology: TopologyHypothesis,
                       distinctions: list[dict[str, Any]],
                       ) -> list[Prediction]:
    spec = topology.harness_spec
    if not spec:
        raise PredictionError(
            f"{topology.topology_id}: cannot freeze predictions without an "
            "embedded harness spec")
    tid = topology.topology_id
    by_q = {d["id"]: d for d in distinctions}
    preds: list[Prediction] = []
    n = 0

    def pid() -> str:
        nonlocal n
        n += 1
        return f"{tid}-pr{n:02d}"

    child = _is_child_topology(spec)

    # 1. per-distinction resolution predictions (claim + resolver node)
    for q in sorted(topology.resolution_map):
        node = topology.resolution_map[q]
        question = by_q.get(q, {}).get("question", "")
        preds.append(Prediction(
            prediction_id=pid(), topology_id=tid,
            claim=f"distinction {q} ({question[:80]}) is resolved by node "
                  f"{node}",
            observable="post-execution resolved/unresolved distinction "
                       "record and evidence provenance",
            success_condition=f"{q} appears in resolved_distinctions with "
                              f"resolving evidence attributed to {node}",
            falsification_condition=f"{q} appears in "
                                    "unresolved_distinctions after "
                                    "execution, or its evidence is not "
                                    f"attributable to {node}",
            weight=1.0, kind="resolves",
            subject={"distinction_id": q, "node": node},
            principles=(["P-INDEPENDENCE"] if child and
                        node in ("child-return", "create-child")
                        else ["P-LOCALITY"]),
        ))

    # 2. expected runtime path
    path = _expected_path(spec)
    preds.append(Prediction(
        prediction_id=pid(), topology_id=tid,
        claim="runtime realizes the declared causal order",
        observable="execution ledger completes_node sequence",
        success_condition=f"node completion order equals a legal "
                          f"linearization of {path}",
        falsification_condition="any completion outside the compiled LTS "
                                "(REFINEMENT_VIOLATION) or a node absent "
                                "from the realized branch",
        weight=1.0, kind="runtime_path",
        subject={"expected_order": path},
        principles=["P-AUTHORITY-SEPARATION"],
    ))

    # 3. model-call budget
    budget = int(spec.get("max_model_calls", 1))
    preds.append(Prediction(
        prediction_id=pid(), topology_id=tid,
        claim=f"execution uses at most {budget} model calls",
        observable="resource_use.model_calls in the runtime record",
        success_condition=f"model_calls <= {budget}",
        falsification_condition=f"model_calls > {budget}",
        weight=0.5, kind="model_call_budget",
        subject={"max": budget},
        principles=["P-MINIMALITY"],
    ))

    # 4. authority envelope
    preds.append(Prediction(
        prediction_id=pid(), topology_id=tid,
        claim="no actor exceeds its authority envelope",
        observable="formal check results over the execution ledger",
        success_condition="zero authority/refinement/attenuation failures",
        falsification_condition="any authority escalation, non-gate "
                                "promotion, or attenuation failure",
        weight=1.0, kind="authority_envelope",
        subject={},
        principles=["P-AUTHORITY-SEPARATION"],
    ))

    if child:
        # 5. novel child evidence (falsified by duplicate-child outcomes)
        child_q = sorted(q for q, node in topology.resolution_map.items()
                         if node in ("child-return", "create-child"))
        preds.append(Prediction(
            prediction_id=pid(), topology_id=tid,
            claim="the child contributes novel evidence not derivable from "
                  "parent-local evidence",
            observable="evidence records with duplicate_of_parent flags",
            success_condition="at least one child evidence record with "
                              "duplicate_of_parent=false, attributed to the "
                              "child",
            falsification_condition="every child evidence record duplicates "
                                    "parent evidence",
            weight=1.0, kind="novel_evidence",
            subject={"distinction_ids": child_q},
            principles=["P-INDEPENDENCE"],
        ))
        preds.append(Prediction(
            prediction_id=pid(), topology_id=tid,
            claim="the realized child is fresh and attenuated",
            observable="launch provenance + attenuation results",
            success_condition="freshness PASS and attenuation PASS for the "
                              "realized child",
            falsification_condition="FRESHNESS_FAIL or ATTENUATION_FAIL on "
                                    "the realized child",
            weight=1.0, kind="verification_effect",
            subject={"checks": ["freshness", "attenuation"]},
            principles=["P-FRESHNESS", "P-ATTENUATION"],
        ))
    else:
        # 5'. local sufficiency (falsified when local evidence cannot verify)
        preds.append(Prediction(
            prediction_id=pid(), topology_id=tid,
            claim="local evidence is sufficient: resolution and verification "
                  "complete without any descendant",
            observable="verification record + child launch count",
            success_condition="verification completes with zero child "
                              "launches",
            falsification_condition="verification is impossible from local "
                                    "evidence, or a distinction requires an "
                                    "isolated source",
            weight=1.0, kind="local_sufficiency",
            subject={},
            principles=["P-LOCALITY"],
        ))

    validate_frozen_coverage(topology, preds)
    topology.predictions = [p.to_dict() for p in preds]
    topology.predictions_hash = predictions_hash(tid, topology.predictions)
    return preds


def validate_frozen_coverage(topology: TopologyHypothesis,
                             predictions: list[Prediction]) -> None:
    """Every claimed resolved distinction needs >=1 falsifiable prediction."""
    covered = set()
    for p in predictions:
        if p.kind == "resolves":
            if not p.falsification_condition.strip():
                raise PredictionError(
                    f"{p.prediction_id}: resolution claim without falsifier")
            covered.add(p.subject.get("distinction_id"))
    missing = sorted(set(topology.resolution_map) - covered)
    if missing:
        raise PredictionError(
            f"{topology.topology_id}: claimed resolved distinctions without "
            f"falsifiable predictions: {missing}")


def load_predictions(docs: list[dict[str, Any]]) -> list[Prediction]:
    out = []
    for d in docs:
        try:
            out.append(Prediction.from_dict(d))
        except ModelValidationError:
            raise
    return out
