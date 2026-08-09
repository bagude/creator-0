"""Candidate topology generation from applicable principles.

    generate_candidates(task, distinctions, applicable_principles, contract,
                        max_candidates=4) -> list[TopologyHypothesis]

The generator answers: what minimum causal organization can resolve the
unresolved distinctions? It composes from a closed template grammar — it
must not maximize node count or recursion. Templates are emitted in
minimality order and every emitted spec respects the governing contract
(primitives, tools, creation capability, model-call budget) by construction;
admissibility is then decided by validate.validate_topology, never here.

Model-mediated synthesis may propose additional candidates, but only by
serializing them into TopologyHypothesis documents that pass the same
deterministic validation; there is no model path around the grammar.
"""
from __future__ import annotations
from typing import Any

from .model import ApplicabilityResult, TopologyHypothesis
from .serialization import object_artifact_id


def _edge(src: str, tgt: str, rel: str, response: bool = False,
          changes: bool = False) -> dict[str, Any]:
    return {"source": src, "target": tgt, "relation": rel,
            "requires_response": response,
            "response_changes_parent_state": changes,
            "transfers_authority": False}


def _node(nid: str, primitive: str, tools: list[str], can_create: bool = False,
          branch: str = "", instructions: str = "") -> dict[str, Any]:
    n = {"id": nid, "primitive": primitive, "tools": tools,
         "can_create": can_create, "instructions": instructions}
    if branch:
        n["branch"] = branch
    return n


def _tools(contract: dict[str, Any], *wanted: str) -> list[str]:
    allowed = set(contract.get("allowed_tools", []))
    return [t for t in wanted if t in allowed]


def _local_spec(task_id: str, contract: dict[str, Any]) -> dict[str, Any]:
    r, w = _tools(contract, "Read"), _tools(contract, "Read", "Write")
    return {
        "task_id": task_id,
        "goal": f"Local resolution of {task_id} under the current topology",
        "max_depth": 0, "max_model_calls": 1,
        "nodes": [
            _node("observe-evidence", "observe", r,
                  instructions="Acquire all governed evidence for the task."),
            _node("resolve-local", "hypothesize", w,
                  instructions="Resolve every unresolved distinction from "
                               "local evidence; persist the resolution."),
            _node("verify-resolution", "verify", r,
                  instructions="Deterministically verify the resolution "
                               "against the task deliverable."),
            _node("return-result", "return", w,
                  instructions="Return the verified result into the governed "
                               "boundary."),
        ],
        "edges": [
            _edge("observe-evidence", "resolve-local", "observe"),
            _edge("resolve-local", "verify-resolution", "verify", True),
            _edge("verify-resolution", "return-result", "authorize"),
        ],
    }


def _local_iv_spec(task_id: str, contract: dict[str, Any]) -> dict[str, Any]:
    spec = _local_spec(task_id, contract)
    spec["goal"] = (f"Local resolution of {task_id} with an additional "
                    "independent verification pass")
    spec["max_model_calls"] = 2
    agent = _tools(contract, "Agent", "Read") or _tools(contract, "Read")
    spec["nodes"].insert(3, _node(
        "verify-independent", "verify", agent,
        instructions="Independent information-only examiner re-verifies the "
                     "resolution; no write, no promotion authority."))
    spec["edges"] = [
        _edge("observe-evidence", "resolve-local", "observe"),
        _edge("resolve-local", "verify-resolution", "verify", True),
        _edge("verify-resolution", "verify-independent", "verify", True),
        _edge("verify-independent", "return-result", "authorize"),
    ]
    return spec


def _child_spec(task_id: str, contract: dict[str, Any]) -> dict[str, Any]:
    r = _tools(contract, "Read")
    w = _tools(contract, "Read", "Write")
    b = _tools(contract, "Bash") or r
    return {
        "task_id": task_id,
        "goal": f"Isolated fresh child resolves the isolation-requiring "
                f"distinctions of {task_id}",
        "max_depth": 1, "max_model_calls": 2,
        "nodes": [
            _node("observe-evidence", "observe", r,
                  instructions="Acquire governed evidence; identify the "
                               "distinctions requiring isolation."),
            _node("propose-child", "hypothesize", w,
                  instructions="Author the full child bundle (contract, "
                               "harness, prompt, input manifest, integration "
                               "plan) as observable proposal."),
            _node("validate-child", "verify", r,
                  instructions="Deterministic validation: attenuation, kernel "
                               "compilation, manifest containment, freshness "
                               "preflight. Any failure rejects realization."),
            _node("create-child", "create", b, can_create=True,
                  instructions="Realize the validated child via the "
                               "deterministic fresh launcher only."),
            _node("child-return", "return", r,
                  instructions="Receive child deliverables into the governed "
                               "boundary."),
            _node("verify-integration", "verify", r,
                  instructions="Deterministically integrate child evidence "
                               "per the pre-committed plan and verify the "
                               "task result."),
            _node("return-result", "return", w,
                  instructions="Return the verified result."),
        ],
        "edges": [
            _edge("observe-evidence", "propose-child", "observe"),
            _edge("propose-child", "validate-child", "verify", True),
            _edge("validate-child", "create-child", "authorize"),
            _edge("create-child", "child-return", "request_response",
                  True, True),
            _edge("child-return", "verify-integration", "verify", True),
            _edge("verify-integration", "return-result", "authorize"),
        ],
        "freshness": {"fresh_launcher_required": True},
    }


def _branching_spec(task_id: str, contract: dict[str, Any]) -> dict[str, Any]:
    r = _tools(contract, "Read")
    w = _tools(contract, "Read", "Write")
    b = _tools(contract, "Bash") or r
    return {
        "task_id": task_id,
        "goal": f"Deferred topology decision for {task_id}: evaluate "
                "chi(T,E,K) at runtime, then realize exactly one branch",
        "max_depth": 1, "max_model_calls": 2,
        "nodes": [
            _node("observe-evidence", "observe", r,
                  instructions="Acquire evidence; decide nothing yet."),
            _node("decide-topology", "hypothesize", w,
                  instructions="Evaluate chi(T,E,K) and persist the typed "
                               "topology decision under an observable "
                               "propose transition."),
            _node("local-resolve", "hypothesize", w, branch="local",
                  instructions="DO_NOT_CREATE branch: resolve locally."),
            _node("verify-local", "verify", r, branch="local",
                  instructions="Deterministic verification of the local "
                               "resolution."),
            _node("propose-child", "hypothesize", w, branch="create",
                  instructions="CREATE branch: author the child bundle as "
                               "observable proposal."),
            _node("validate-child", "verify", r, branch="create",
                  instructions="Deterministic child validation gates "
                               "realization."),
            _node("create-child", "create", b, can_create=True,
                  branch="create",
                  instructions="Realize via the fresh launcher only."),
            _node("child-return", "return", r, branch="create",
                  instructions="Receive child deliverables."),
            _node("integrate-evidence", "observe", r, branch="create",
                  instructions="Deterministically integrate child evidence "
                               "per the pre-committed plan."),
            _node("verify-child-result", "verify", r, branch="create",
                  instructions="Deterministic verification of the integrated "
                               "result."),
        ],
        "edges": [
            _edge("observe-evidence", "decide-topology", "observe"),
            _edge("decide-topology", "local-resolve", "authorize"),
            _edge("local-resolve", "verify-local", "verify", True),
            _edge("decide-topology", "propose-child", "authorize"),
            _edge("propose-child", "validate-child", "verify", True),
            _edge("validate-child", "create-child", "authorize"),
            _edge("create-child", "child-return", "request_response",
                  True, True),
            _edge("child-return", "integrate-evidence", "return"),
            _edge("child-return", "integrate-evidence", "observe"),
            _edge("integrate-evidence", "verify-child-result", "verify", True),
        ],
        "freshness": {"fresh_launcher_required": True},
    }


def _contract_allows_create(contract: dict[str, Any]) -> bool:
    return (bool(contract.get("may_create_creator", False))
            and int(contract.get("max_children", 0)) > 0
            and "create" in contract.get("allowed_primitives", []))


def _predicted_value(template: str, isolation: bool, locality: bool,
                     spec: dict[str, Any]) -> dict[str, float]:
    """Normalized [0,1] components. Deterministic template economics:
    epistemic gain rises with match between structure and need; cost with
    node count and model calls; redundancy when a child duplicates locally
    sufficient evidence; governance risk with creation/authority surface."""
    nodes = len(spec["nodes"])
    cost = round(min(1.0, 0.05 * nodes + 0.05 * spec["max_model_calls"]), 4)
    if template == "local":
        gain = 0.7 if locality else (0.2 if isolation else 0.5)
        redundancy, governance = 0.0, 0.0
    elif template == "local-independent-verify":
        gain = 0.75 if locality else (0.35 if isolation else 0.55)
        redundancy, governance = 0.1, 0.05
    elif template == "isolated-child":
        gain = 0.9 if isolation else 0.35
        redundancy = 0.6 if (locality and not isolation) else 0.05
        governance = 0.1
    else:  # branching
        gain = 0.8 if isolation else 0.6
        redundancy = 0.15
        governance = 0.1
    return {"delta_e": round(gain, 4), "cost": cost,
            "redundancy": round(redundancy, 4),
            "governance_risk": round(governance, 4)}


def generate_candidates(task: dict[str, Any],
                        distinctions: list[dict[str, Any]],
                        applicable_principles: ApplicabilityResult | dict,
                        contract: dict[str, Any],
                        max_candidates: int = 4,
                        ) -> list[TopologyHypothesis]:
    if isinstance(applicable_principles, ApplicabilityResult):
        app = applicable_principles.to_dict()
    else:
        app = dict(applicable_principles)
    max_candidates = max(1, min(4, int(max_candidates)))
    task_id = str(task.get("task_id", task.get("id", "task")))
    qids = [d["id"] for d in distinctions]

    by_principle = {a["principle_id"]: a for a in app.get("applicable", [])}
    iso_q = set(by_principle.get("P-INDEPENDENCE", {}).get(
        "distinction_ids", []))
    loc_q = set(by_principle.get("P-LOCALITY", {}).get("distinction_ids", []))
    isolation = bool(iso_q)
    locality = bool(loc_q) and set(qids) <= loc_q
    allow_create = _contract_allows_create(contract)

    templates: list[tuple[str, dict[str, Any]]] = []
    # minimality order: fewest nodes first, creation-bearing last
    if not isolation or not allow_create:
        templates.append(("local", _local_spec(task_id, contract)))
        templates.append(("local-independent-verify",
                          _local_iv_spec(task_id, contract)))
    else:
        if locality:
            templates.append(("local", _local_spec(task_id, contract)))
        templates.append(("local-independent-verify",
                          _local_iv_spec(task_id, contract)))
        templates.append(("isolated-child", _child_spec(task_id, contract)))
        templates.append(("branching", _branching_spec(task_id, contract)))
    if allow_create and not isolation and len(templates) < max_candidates:
        templates.append(("branching", _branching_spec(task_id, contract)))

    out: list[TopologyHypothesis] = []
    invoked_base = sorted(p for p in by_principle)
    for name, spec in templates[:max_candidates]:
        spec["max_model_calls"] = min(int(spec["max_model_calls"]),
                                      int(contract.get("max_model_calls", 1)))
        resolver = {
            "local": "resolve-local",
            "local-independent-verify": "resolve-local",
            "isolated-child": "child-return",
            "branching": "local-resolve",
        }[name]
        resolution_map = {}
        for q in qids:
            if name == "isolated-child":
                resolution_map[q] = "child-return" if q in iso_q else \
                    "observe-evidence"
            elif name == "branching":
                resolution_map[q] = "child-return" if q in iso_q else \
                    "local-resolve"
            else:
                resolution_map[q] = resolver
        tid = f"H-{task_id}-{name}"
        falsifiers = [
            f"a distinction in {sorted(resolution_map)} remains unresolved "
            "after execution",
            "the runtime path violates the compiled LTS",
            "actual model calls exceed the declared budget",
        ]
        if name in ("isolated-child", "branching"):
            falsifiers.append("child evidence duplicates parent evidence "
                              "(no novel contribution)")
        if name == "local":
            falsifiers.append("local evidence proves insufficient "
                              "(verification impossible locally)")
        out.append(TopologyHypothesis(
            topology_id=tid,
            task_id=task_id,
            unresolved_distinctions=list(qids),
            principles_invoked=invoked_base,
            harness_spec_ref=object_artifact_id(
                spec, f"creator-0/topology-theory/harness/{tid}"),
            harness_spec=spec,
            resolution_map=resolution_map,
            falsifiers=falsifiers,
            predicted_value=_predicted_value(name, isolation, locality, spec),
            status="CANDIDATE",
        ))
    return out
