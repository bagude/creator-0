"""Topology grammar v2: typed-relation candidate generation.

Extends the closed v1 template grammar just enough to express typed
epistemic relations. Families (closed, frozen):

    local                            1 session   role local_author
    local-independent-examiner       2 sessions  + non_author_examiner
    local-method-disjoint-verifier   2 sessions  + method_disjoint_verifier
    isolated-clean-room-author       2 + child   + clean_room_author
    isolated-decomposer              2 + child   + independent_decomposer
    isolated-searcher                2 + child   + non_author_examiner
                                     (admissible for search; dominated on
                                      cost — exists so economics can prove
                                      the examiner wins)
    branching                        2 + child   deferred decision; child
                                     role bound to the required kind

Every spec embeds `evidence_provisions` [(node, canonical role, vector)].
Admissibility filtering happens downstream (admissibility.topology_admissible)
before economics; predicted values here are fully deterministic
(admissibility-saturating ΔE, marginal-coverage redundancy, structural
governance risk, call-structure cost). There is no model path around the
grammar.
"""
from __future__ import annotations
from typing import Any

from .admissibility import (FEATURE_TO_KIND, KIND_REQUIREMENT, TYPED_FEATURES,
                            provision_for_role, provisions_from_spec,
                            requirement_for_distinction, topology_admissible,
                            predicted_components)
from .generate import (_branching_spec, _child_spec, _local_iv_spec,
                       _local_spec, _contract_allows_create)
from .model import ApplicabilityResult, TopologyHypothesis
from .serialization import object_artifact_id

FAMILIES_V2 = ("local", "local-independent-examiner",
               "local-method-disjoint-verifier", "isolated-clean-room-author",
               "isolated-decomposer", "isolated-searcher", "branching")

FAMILY_CALLS_V2 = {
    "local": (1, 0),
    "local-independent-examiner": (2, 0),
    "local-method-disjoint-verifier": (2, 0),
    "isolated-clean-room-author": (2, 1),
    "isolated-decomposer": (2, 1),
    "isolated-searcher": (2, 1),
    "branching": (2, 1),
}

# required kind -> (minimal family, alternative family, child role)
KIND_FAMILIES = {
    "NON_AUTHOR_SEARCH": ("local-independent-examiner", "isolated-searcher",
                          "non_author_examiner"),
    "CLEAN_ROOM_AUTHORSHIP": ("isolated-clean-room-author", "branching",
                              "clean_room_author"),
    "INDEPENDENT_DECOMPOSITION": ("isolated-decomposer", "branching",
                                  "independent_decomposer"),
    "METHOD_DISJOINT_VERIFICATION": ("local-method-disjoint-verifier",
                                     "branching",
                                     "method_disjoint_verifier"),
}


def family_of_v2(topology_id: str) -> str:
    for fam in ("local-independent-examiner", "local-method-disjoint-verifier",
                "isolated-clean-room-author", "isolated-decomposer",
                "isolated-searcher", "branching", "local"):
        if topology_id.endswith(fam):
            return fam
    raise ValueError(f"cannot derive v2 family from {topology_id!r}")


def _spec_for(family: str, task_id: str, contract: dict[str, Any],
              child_role: str) -> dict[str, Any]:
    if family == "local":
        spec = _local_spec(task_id, contract)
        provisions = [("resolve-local", "local_author", "")]
    elif family == "local-independent-examiner":
        spec = _local_iv_spec(task_id, contract)
        spec["goal"] = (f"Local resolution of {task_id} plus an "
                        "information-only independent examiner pass")
        provisions = [("resolve-local", "local_author", ""),
                      ("verify-independent", "non_author_examiner", "")]
    elif family == "local-method-disjoint-verifier":
        spec = _local_iv_spec(task_id, contract)
        spec["goal"] = (f"Local resolution of {task_id} plus re-derivation "
                        "by a verifier bound to a disjoint method family")
        for n in spec["nodes"]:
            if n["id"] == "verify-independent":
                n["id"] = "verify-method-disjoint"
                n["instructions"] = (
                    "Information-only verifier re-derives the result through "
                    "a method family disjoint from the primary method; no "
                    "write, no promotion authority.")
        for e in spec["edges"]:
            for k in ("source", "target"):
                if e[k] == "verify-independent":
                    e[k] = "verify-method-disjoint"
        provisions = [("resolve-local", "local_author", ""),
                      ("verify-method-disjoint", "method_disjoint_verifier",
                       "disjoint")]
    elif family in ("isolated-clean-room-author", "isolated-decomposer",
                    "isolated-searcher"):
        spec = _child_spec(task_id, contract)
        spec["child_role"] = child_role
        spec["goal"] = (f"Isolated fresh child (canonical role {child_role}) "
                        f"resolves the typed distinctions of {task_id}")
        provisions = [("observe-evidence", "local_author", ""),
                      ("child-return", child_role, "")]
    elif family == "branching":
        spec = _branching_spec(task_id, contract)
        spec["child_role"] = child_role
        provisions = [("local-resolve", "local_author", ""),
                      ("child-return", child_role, "")]
    else:
        raise ValueError(f"unknown v2 family {family!r}")
    spec["evidence_provisions"] = [
        provision_for_role(node, role, method_family=mf).to_dict()
        for node, role, mf in provisions]
    return spec


def generate_candidates_v2(task: dict[str, Any],
                           distinctions: list[dict[str, Any]],
                           applicable_principles: ApplicabilityResult | dict,
                           contract: dict[str, Any],
                           value_estimates: dict[str, float],
                           max_candidates: int = 6,
                           ) -> list[TopologyHypothesis]:
    """Deterministic v2 generation: one minimal family per required kind
    plus one admissible alternative, plus `local` always (minimality
    baseline; inadmissible candidates are rejected downstream)."""
    if isinstance(applicable_principles, ApplicabilityResult):
        app = applicable_principles.to_dict()
    else:
        app = dict(applicable_principles)
    task_id = str(task.get("task_id", task.get("id", "task")))
    reqs = [requirement_for_distinction(d) for d in distinctions]
    needed = sorted({r.kind for r in reqs} - {"LOCAL"})
    allow_create = _contract_allows_create(contract)

    plan: list[tuple[str, str]] = [("local", "")]
    if not needed:
        plan.append(("local-independent-examiner", ""))
    for kind in needed:
        minimal, alt, role = KIND_FAMILIES[kind]
        plan.append((minimal, role))
        if alt != minimal:
            plan.append((alt, role))
    # deduplicate preserving order; drop create-bearing families when the
    # contract forbids creation
    seen = set()
    final_plan = []
    for fam, role in plan:
        key = (fam, role)
        if key in seen:
            continue
        seen.add(key)
        if fam.startswith("isolated") or fam == "branching":
            if not allow_create:
                continue
        final_plan.append((fam, role))

    out: list[TopologyHypothesis] = []
    invoked = sorted(a["principle_id"] for a in app.get("applicable", []))
    for fam, role in final_plan[:max(1, int(max_candidates))]:
        spec = _spec_for(fam, task_id, contract, role)
        spec["max_model_calls"] = min(int(spec["max_model_calls"]),
                                      int(contract.get("max_model_calls", 1)))
        provisions = provisions_from_spec(spec)
        prov_by_kind: dict[str, str] = {}
        for r in reqs:
            for p in provisions:
                from .admissibility import admissible
                if admissible(p, r)[0]:
                    prov_by_kind[r.distinction_id] = p.node_id
                    break
        local_node = provisions[0].node_id
        resolution_map = {r.distinction_id:
                          prov_by_kind.get(r.distinction_id, local_node)
                          for r in reqs}
        m, c = FAMILY_CALLS_V2[fam]
        predicted = predicted_components(
            provisions, reqs, dict(value_estimates),
            model_sessions=m, child_sessions=c)
        adm = topology_admissible(provisions, reqs)
        spec["admissibility_precheck"] = adm["admissible"]
        tid = f"H-{task_id}-{fam}"
        falsifiers = [
            f"a distinction in {sorted(resolution_map)} remains unresolved "
            "after execution",
            "the runtime path violates the compiled LTS",
            "actual model calls exceed the declared budget",
            "a realized independent path's canonical role differs from the "
            "declared evidence provision role",
        ]
        if fam.startswith("isolated") or fam == "branching":
            falsifiers.append("child evidence duplicates parent evidence "
                              "(no novel contribution)")
        if fam == "local":
            falsifiers.append("local evidence proves insufficient "
                              "(verification impossible locally)")
        out.append(TopologyHypothesis(
            topology_id=tid,
            task_id=task_id,
            unresolved_distinctions=[d["id"] for d in distinctions],
            principles_invoked=invoked,
            harness_spec_ref=object_artifact_id(
                spec, f"creator-0/topology-theory/harness/{tid}"),
            harness_spec=spec,
            resolution_map=resolution_map,
            falsifiers=falsifiers,
            predicted_value=predicted,
            status="CANDIDATE",
        ))
    return out
