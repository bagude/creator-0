"""Deterministic HarnessSpec -> FormalLTS compiler.

The compiled LTS is the authoritative abstract behavior of the HarnessSpec.
Illegal transitions are absent by construction: authority is encoded, not mere
graph connectivity.

Formal state = externally reconstructible governed configuration:
    (completed node set, promoted flag, complete flag)
encoded deterministically as a state id string.

Authority partition of the alphabet (see SEMANTICS.md):
  - non-authority labels (observe, propose, validate, reject, consult, return,
    persist, reconstruct) are wildcard self-loops in every non-terminal state;
  - node-execution labels come only from the node's primitive with actor
    node:<id>, enabled only when the node's dependencies are complete;
  - edge-interaction labels (authorize, delegate, verify, consult, ...) exist
    only after the source node completed, with actor node:<source>;
  - create at Creator level exists only if the governing contract grants it;
  - promote exists only for actor `gate`, only after a verify node completed,
    and only when the contract does not deny gate promotion;
  - complete exists only when every node has completed;
  - tau is permitted everywhere as a silent self-loop.
"""
from __future__ import annotations
from itertools import combinations
from typing import Any

from .labels import (Label, NON_AUTHORITY_LABELS, primitive_label,
                     relation_label)
from .model import ANY_ACTOR, LTS, Transition

GATE_ACTOR = "gate"
CREATOR_ACTOR = "creator"


class SemanticsError(ValueError):
    """The HarnessSpec or contract cannot be compiled deterministically."""


def state_id(done: frozenset[str], promoted: bool, complete: bool) -> str:
    return "done={%s}|promoted=%d|complete=%d" % (
        ",".join(sorted(done)), int(promoted), int(complete))


def node_actor(node_id: str) -> str:
    return f"node:{node_id}"


def _contract_allows_create(contract: dict[str, Any]) -> bool:
    if not bool(contract.get("may_create_creator", False)):
        return False
    if int(contract.get("max_children", 0)) <= 0:
        return False
    if "may_realize_creation" in contract and not bool(contract["may_realize_creation"]):
        return False
    return True


def _contract_allows_gate_promotion(contract: dict[str, Any]) -> bool:
    """Deterministic rule: gate promotion is permitted unless the contract
    carries an explicit canonical_write_authority denial that does not name
    the gate as promotion mechanism. Absent key = root default (permitted)."""
    cwa = contract.get("canonical_write_authority")
    if cwa is None:
        return True
    return "gate" in str(cwa).lower()


def compile_harness_spec(spec: dict[str, Any], contract: dict[str, Any]) -> LTS:
    for k in ("task_id", "nodes", "edges"):
        if k not in spec:
            raise SemanticsError(f"spec missing required key: {k}")
    nodes = {n["id"]: n for n in spec["nodes"]}
    if len(nodes) != len(spec["nodes"]):
        raise SemanticsError("duplicate node ids")
    if not nodes:
        raise SemanticsError("spec has no nodes")

    # Per-node execution label from its primitive (closed mapping; unmapped -> error).
    exec_label: dict[str, Label] = {}
    for nid, n in nodes.items():
        if "primitive" not in n:
            raise SemanticsError(f"node {nid} missing primitive")
        exec_label[nid] = primitive_label(n["primitive"])
        if n.get("can_create") and not _contract_allows_create(contract):
            raise SemanticsError(
                f"node {nid} realizes create but contract forbids creation "
                "(may_create_creator/max_children/may_realize_creation)")

    # Dependencies: non-return edges gate target execution on source completion.
    deps: dict[str, set[str]] = {nid: set() for nid in nodes}
    edges = []
    for e in spec["edges"]:
        for k in ("source", "target", "relation"):
            if k not in e:
                raise SemanticsError(f"edge missing {k}")
        if e["source"] not in nodes or e["target"] not in nodes:
            raise SemanticsError(f"edge references unknown node: {e}")
        lab = relation_label(e["relation"])
        edges.append((e["source"], e["target"], lab))
        if e["relation"] != "return":
            deps[e["target"]].add(e["source"])

    verify_nodes = {nid for nid, n in nodes.items() if n["primitive"] == "verify"}
    act_nodes = {nid for nid, n in nodes.items() if n["primitive"] == "act"}
    allow_create = _contract_allows_create(contract)
    allow_promote = (bool(act_nodes) and bool(verify_nodes)
                     and _contract_allows_gate_promotion(contract))

    node_ids = sorted(nodes)
    transitions: set[Transition] = set()
    states: set[str] = set()

    def add_governance_selfloops(sid: str) -> None:
        for lab in sorted(NON_AUTHORITY_LABELS):
            transitions.add(Transition(sid, lab, sid, ANY_ACTOR))
        transitions.add(Transition(sid, Label.TAU.value, sid, ANY_ACTOR))
        if allow_create:
            transitions.add(Transition(sid, Label.CREATE.value, sid, CREATOR_ACTOR))

    # Enumerate reachable governed configurations. Node sets are small
    # (validated specs are bounded), so subset enumeration is finite and cheap.
    for r in range(len(node_ids) + 1):
        for combo in combinations(node_ids, r):
            done = frozenset(combo)
            # only configurations closed under dependencies are reachable
            if any(not deps[nid] <= done for nid in done):
                continue
            for promoted in ((False, True) if allow_promote else (False,)):
                if promoted and not (verify_nodes & done):
                    continue
                sid = state_id(done, promoted, False)
                states.add(sid)
                add_governance_selfloops(sid)

                # node execution moves
                for nid in node_ids:
                    if nid in done or not deps[nid] <= done:
                        continue
                    tgt = state_id(done | {nid}, promoted, False)
                    transitions.add(Transition(
                        sid, exec_label[nid].value, tgt, node_actor(nid)))

                # edge interactions after source completion
                for (src, tgt_node, lab) in edges:
                    if src in done:
                        transitions.add(Transition(sid, lab.value, sid, node_actor(src)))

                # gate promotion
                if allow_promote and not promoted and (verify_nodes & done):
                    transitions.add(Transition(
                        sid, Label.PROMOTE.value,
                        state_id(done, True, False), GATE_ACTOR))

                # completion
                if len(done) == len(node_ids):
                    fin = state_id(done, promoted, True)
                    states.add(fin)
                    transitions.add(Transition(sid, Label.COMPLETE.value, fin, ANY_ACTOR))
                    transitions.add(Transition(fin, Label.TAU.value, fin, ANY_ACTOR))

    initial = state_id(frozenset(), False, False)
    labels = frozenset({t.label for t in transitions})
    return LTS(
        states=frozenset(states), labels=labels,
        transitions=frozenset(transitions), initial=initial,
        metadata={
            "task_id": spec.get("task_id", ""),
            "contract_id": contract.get("contract_id", contract.get("version", "")),
            "nodes": node_ids,
            "verify_nodes": sorted(verify_nodes),
            "act_nodes": sorted(act_nodes),
            "allow_create": allow_create,
            "allow_promote": allow_promote,
        })
