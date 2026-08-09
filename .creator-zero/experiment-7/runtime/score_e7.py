"""Deterministic per-trial scoring against frozen private labels (E7).

Reuses the frozen E6 scoring rules verbatim (distinction recall, principle
ranks, topology-correctness feature matching) and adds the preregistered E7
typed metrics: exact admissibility-kind accuracy with per-coordinate stats
(condition B), and role-typing accuracy against the label's required
canonical role."""
from __future__ import annotations
from pathlib import Path
from typing import Any

from .common import bank_dir, e6_runtime, family_of, jdump, jload, trial_dir

# canonical role -> frozen E6 feature vocabulary (for label feature match)
CANON_TO_E6 = {
    "clean_room_author": "clean_room_implementer",
    "non_author_examiner": "adversarial_searcher",
    "independent_decomposer": "independent_decomposer",
    "method_disjoint_verifier": "independent_verifier",
}

FEATURE_KIND = {
    "requires_clean_room_authorship": "CLEAN_ROOM_AUTHORSHIP",
    "requires_nonauthor_search": "NON_AUTHOR_SEARCH",
    "requires_independent_decomposition": "INDEPENDENT_DECOMPOSITION",
    "requires_method_disjoint_verification": "METHOD_DISJOINT_VERIFICATION",
}
KIND_COORD = {"CLEAN_ROOM_AUTHORSHIP": "I_A", "NON_AUTHOR_SEARCH": "I_S",
              "INDEPENDENT_DECOMPOSITION": "I_D",
              "METHOD_DISJOINT_VERIFICATION": "I_M"}


def computed_features(td: Path, topo: dict[str, Any], label: dict[str, Any],
                      cond: str) -> dict[str, Any]:
    has_create = any(n.get("primitive") == "create"
                     for n in topo["harness_spec"].get("nodes", []))
    child_launched = (td / "child" / "launch-provenance.json").exists()
    examiner = (td / "examiner" / "launch-provenance.json").exists()
    role = ""
    clean_room = False
    if child_launched and (td / "child" / "integration-plan.json").exists():
        plan = jload(td / "child" / "integration-plan.json")
        raw = str(plan.get("role", ""))
        role = CANON_TO_E6.get(raw, raw)
        man = jload(td / "child" / "child-input-manifest.json")
        exclusions = label.get("clean_room_exclusions", [])
        clean_room = all(x not in man.get("files", []) for x in exclusions)
    return {
        "child": child_launched,
        "child_role": role,
        "clean_room": clean_room,
        "independent_examiner": examiner,
        "distinct_verification_path": examiner or (
            child_launched and role in ("independent_verifier",
                                        "adversarial_searcher")),
        "independent_decomposition_path":
            child_launched and role == "independent_decomposer",
        "adversarial_path": (child_launched and
                             role == "adversarial_searcher") or examiner,
        "no_extra_path": not child_launched and not examiner,
        "family": family_of(topo["topology_id"], cond),
    }


def typed_admissibility_score(label: dict[str, Any],
                              distinctions: list[dict[str, Any]]
                              ) -> dict[str, Any]:
    """Exact-kind accuracy: the union of inferred required kinds must equal
    {label kind} (LOCAL tasks: the empty set)."""
    inferred: set[str] = set()
    for d in distinctions:
        f = d.get("features", {})
        for feat, kind in FEATURE_KIND.items():
            if bool(f.get(feat, False)):
                inferred.add(kind)
    true_kind = label["admissibility_kind"]
    expected = set() if true_kind == "LOCAL" else {true_kind}
    exact = inferred == expected
    coords = {}
    for kind, coord in KIND_COORD.items():
        coords[coord] = {"inferred": kind in inferred,
                         "true": kind in expected}
    return {"true_kind": true_kind, "inferred_kinds": sorted(inferred),
            "exact": exact, "coordinates": coords}


def role_typing_score(td: Path, label: dict[str, Any]) -> dict[str, Any]:
    role = jload(td / "role-typing.json")
    required = label["required_role"]
    realized = role.get("realized_role", "")
    has_path = bool(role.get("independent_path"))
    if not has_path:
        return {"required_role": required, "realized_role": "",
                "independent_path": False, "counted": False,
                "correct": None}
    return {"required_role": required, "realized_role": realized,
            "independent_path": True, "counted": True,
            "correct": realized == required
            and required != "local_author"}


def score_trial(tid: str, cond: str) -> dict[str, Any]:
    e6score = e6_runtime("score")
    td = trial_dir(tid, cond)
    label = jload(bank_dir(tid) / "private" / "label.json")
    distinctions = jload(td / "distinctions.json")["unresolved_distinctions"]
    applicability = jload(td / "applicability.json")
    ranking = jload(td / "candidate-ranking.json")
    selected = ranking["selected"]
    topo = jload(td / "candidates" / f"{selected}.json")
    calib = jload(td / "calibration.json")
    observed = jload(td / "observed-value.json")
    verification = jload(td / "verification.json")

    ds = e6score.score_distinctions(label, distinctions)
    lab = dict(label)
    if cond == "B":
        lab["expected_principles"] = label["expected_principles_v2"]
    ps = e6score.score_principles(lab, applicability)
    feats = computed_features(td, topo, label, cond)
    ts = e6score.score_topology(label, feats)

    typed = typed_admissibility_score(label, distinctions) \
        if cond == "B" else None
    role = role_typing_score(td, label)

    failures = []
    if ds["critical_recall"] < 0.75:
        failures.append("S1_DISTINCTION_FAIL")
    if not ps["top2_hit"]:
        failures.append("S2_PRINCIPLE_FAIL")
    if calib["calibration_error"]["utility_error"] > 0.25:
        failures.append("S4_PREDICTION_FAIL")
    if ts["verdict"] == "TOPOLOGY_INCORRECT":
        failures.append("S5_RANKING_FAIL")
    gov = jload(td / "governance-events.json")["summary"]
    if gov["fatal_events"] > 0:
        failures.append("FATAL_GOVERNANCE_FAIL")
    if gov["nonfatal_events"] > 0:
        failures.append("NONFATAL_GOVERNANCE_EVENTS")
    if typed is not None and not typed["exact"]:
        failures.append("ADMISSIBILITY_KIND_FAIL")
    if role["counted"] and role["correct"] is False:
        failures.append("ROLE_TYPE_FAIL")
    if ranking.get("selected") is None:
        failures.append("ADMISSIBILITY_FAIL")

    doc = {
        "trial_id": tid,
        "condition": cond,
        "latent_class": label["latent_class"],
        "admissibility_kind": label["admissibility_kind"],
        "surface_domain": label.get("surface_domain", ""),
        "selected_topology": selected,
        "distinction_score": ds,
        "principle_score": ps,
        "topology_score": ts,
        "typed_admissibility": typed,
        "role_typing": role,
        "predicted_utility": calib["predicted_utility"],
        "observed_utility": calib["observed_utility"],
        "calibration_error": calib["calibration_error"],
        "governance_summary": gov,
        "task_verified": verification.get("task_verified"),
        "failure_tags": failures,
    }
    jdump(td / "trial-score.json", doc)
    return doc


if __name__ == "__main__":
    import sys
    print(score_trial(sys.argv[1], sys.argv[2]))
