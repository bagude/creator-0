"""Prediction freezing v2: typed principle attribution + role predictions.

Wraps the promoted freeze_predictions: same falsifier-complete mechanical
prediction kinds, but (a) per-distinction resolution predictions are
attributed to the typed principle matching the distinction's required
admissibility kind, and (b) every non-local evidence provision gets a
mechanical role prediction (FAILED when the runtime records ROLE_TYPE_FAIL —
right graph shape with the wrong epistemic role falsifies the typed
principle instead of silently passing). Hash-freezing semantics unchanged.
"""
from __future__ import annotations
from typing import Any

from .admissibility import requirement_for_distinction
from .model import Prediction, TopologyHypothesis
from .predict import freeze_predictions, predictions_hash

KIND_TO_PRINCIPLE = {
    "LOCAL": "P-LOCALITY",
    "CLEAN_ROOM_AUTHORSHIP": "P-AUTHORSHIP-INDEPENDENCE",
    "NON_AUTHOR_SEARCH": "P-NONAUTHOR-SEARCH",
    "INDEPENDENT_DECOMPOSITION": "P-INDEPENDENT-DECOMPOSITION",
    "METHOD_DISJOINT_VERIFICATION": "P-METHOD-DISJOINT-VERIFICATION",
}


def freeze_predictions_v2(topology: TopologyHypothesis,
                          distinctions: list[dict[str, Any]],
                          ) -> list[Prediction]:
    preds = freeze_predictions(topology, distinctions)
    kind_by_q = {d["id"]: requirement_for_distinction(d).kind
                 for d in distinctions}

    for p in preds:
        if p.kind == "resolves":
            q = p.subject.get("distinction_id")
            p.principles = [KIND_TO_PRINCIPLE[kind_by_q.get(q, "LOCAL")]]

    tid = topology.topology_id
    n = len(preds)
    for prov in topology.harness_spec.get("evidence_provisions", []):
        role = prov["role"]
        if role == "local_author":
            continue
        n += 1
        # principle of the provision's role: the kind it uniquely serves
        role_kind = {
            "clean_room_author": "CLEAN_ROOM_AUTHORSHIP",
            "non_author_examiner": "NON_AUTHOR_SEARCH",
            "independent_decomposer": "INDEPENDENT_DECOMPOSITION",
            "method_disjoint_verifier": "METHOD_DISJOINT_VERIFICATION",
        }[role]
        preds.append(Prediction(
            prediction_id=f"{tid}-pr{n:02d}",
            topology_id=tid,
            claim=f"the independent path at node {prov['node_id']} realizes "
                  f"canonical role {role}",
            observable="realized role typing in the runtime record "
                       "(ROLE_TYPE_FAIL formal failure on mismatch)",
            success_condition=f"realized role of {prov['node_id']} equals "
                              f"{role} and no ROLE_TYPE failure is recorded",
            falsification_condition="the realized path's canonical role "
                                    f"differs from {role} "
                                    "(ROLE_TYPE_FAIL recorded)",
            weight=1.0, kind="verification_effect",
            subject={"checks": ["ROLE_TYPE"], "node": prov["node_id"],
                     "role": role},
            principles=[KIND_TO_PRINCIPLE[role_kind]],
        ))

    topology.predictions = [p.to_dict() for p in preds]
    topology.predictions_hash = predictions_hash(tid, topology.predictions)
    return preds
