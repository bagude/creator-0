#!/usr/bin/env python3
"""Creator-0 deterministic boundary compiler.

Validates and materializes HarnessSpec proposals against the root contract.
This file is protected: model-produced structure is a proposal until this
compiler accepts it. Rejections are causal facts, not inconveniences.

Usage:
    python .creator-zero/cz.py validate    <proposal.json>
    python .creator-zero/cz.py materialize <proposal.json>
"""

import hashlib
import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(ROOT)
CONTRACT_PATH = os.path.join(ROOT, "contracts", "root_contract.json")


def _load(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _fail(errors):
    print("REJECTED")
    for e in errors:
        print("  - " + e)
    return 1


def validate(proposal_path):
    contract = _load(CONTRACT_PATH)
    try:
        prop = _load(proposal_path)
    except (OSError, json.JSONDecodeError) as exc:
        return _fail(["proposal unreadable: %s" % exc])

    errors = []

    # ---- envelope ----
    if prop.get("contract_ref") != contract["contract"]:
        errors.append("contract_ref must be %r" % contract["contract"])
    if prop.get("experiment") != contract["experiment"]:
        errors.append("experiment must be %r" % contract["experiment"])
    if prop.get("creator_depth") != 0:
        errors.append("creator_depth must be 0 for this experiment")

    nodes = prop.get("nodes")
    edges = prop.get("edges")
    if not isinstance(nodes, list) or not nodes:
        errors.append("nodes must be a non-empty list")
        return _fail(errors)
    if not isinstance(edges, list) or not edges:
        errors.append("edges must be a non-empty list")
        return _fail(errors)

    allowed_prims = set(contract["allowed_primitives"])
    allowed_rels = set(contract["allowed_relationships"])
    protected = set(contract["protected_read_only"])
    harness_root = contract["harness_root"]
    candidate_dir = contract["candidate_dir"]

    # ---- nodes ----
    ids = {}
    for n in nodes:
        nid = n.get("id")
        if not isinstance(nid, str) or not nid:
            errors.append("node missing id: %r" % n)
            continue
        if nid in ids:
            errors.append("duplicate node id: %s" % nid)
        ids[nid] = n
        prim = n.get("primitive")
        if prim not in allowed_prims:
            errors.append("node %s: primitive %r not allowed" % (nid, prim))
        if prim in ("creator",) or n.get("spawns_creator"):
            errors.append("node %s: child creators are prohibited" % nid)
        if not isinstance(n.get("purpose"), str) or len(n.get("purpose", "")) < 10:
            errors.append("node %s: purpose must state its distinct function" % nid)
        for tool in n.get("tools", []):
            norm = os.path.normpath(tool)
            if norm.startswith("..") or os.path.isabs(norm):
                errors.append("node %s: tool path escapes workspace: %s" % (nid, tool))
            elif not norm.startswith(harness_root):
                errors.append(
                    "node %s: tool %s must live under %s" % (nid, tool, harness_root)
                )
        for w in n.get("writes", []):
            norm = os.path.normpath(w)
            if norm in protected:
                errors.append("node %s: writes protected path %s" % (nid, w))
            ok_prefixes = (harness_root, candidate_dir, contract["runs_dir"])
            in_sandbox = any(norm.startswith(p) for p in ok_prefixes)
            is_mutable = norm in set(contract["mutation_policy"]["mutable_paths"])
            if not in_sandbox and not is_mutable:
                errors.append("node %s: write target not permitted: %s" % (nid, w))
            if is_mutable and ids.get(nid, {}).get("primitive") != "act":
                errors.append(
                    "node %s: only an act node may target canonical artifact %s"
                    % (nid, w)
                )

    # ---- edges ----
    incoming = {nid: [] for nid in ids}
    outgoing = {nid: [] for nid in ids}
    for e in edges:
        src, dst, rel = e.get("from"), e.get("to"), e.get("type")
        if src not in ids or dst not in ids:
            errors.append("edge references unknown node: %r" % e)
            continue
        if rel not in allowed_rels:
            errors.append("edge %s->%s: type %r not allowed" % (src, dst, rel))
        sem = e.get("semantics")
        if not isinstance(sem, str) or len(sem) < 10:
            errors.append(
                "edge %s->%s: explicit causal semantics required" % (src, dst)
            )
        incoming[dst].append(e)
        outgoing[src].append(e)

    # ---- structural rules ----
    prims = {nid: n.get("primitive") for nid, n in ids.items()}
    if "return" not in prims.values():
        errors.append("topology must contain a return node")
    if "verify" not in prims.values():
        errors.append("topology must contain a verify node")

    for nid, prim in prims.items():
        if prim == "act":
            auth = [
                e
                for e in incoming[nid]
                if e.get("type") == "authorize"
                and prims.get(e.get("from")) == "verify"
            ]
            if not auth:
                errors.append(
                    "act node %s lacks an authorize edge from a verify node" % nid
                )

    # every node participates in the causal graph
    for nid in ids:
        if not incoming[nid] and not outgoing[nid]:
            errors.append("node %s is causally disconnected" % nid)

    if errors:
        return _fail(errors)

    print("VALID")
    return 0


def materialize(proposal_path):
    contract = _load(CONTRACT_PATH)
    rc = validate(proposal_path)
    if rc != 0:
        print("materialization refused: proposal is not valid")
        return rc
    with open(proposal_path, "rb") as f:
        digest = hashlib.sha256(f.read()).hexdigest()
    prop = _load(proposal_path)
    for rel in (contract["harness_root"], contract["candidate_dir"]):
        os.makedirs(os.path.join(REPO, rel), exist_ok=True)
    record = {
        "status": "authorized",
        "experiment": prop["experiment"],
        "proposal_sha256": digest,
        "authorized_nodes": [n["id"] for n in prop["nodes"]],
        "authorized_edges": [
            [e["from"], e["type"], e["to"]] for e in prop["edges"]
        ],
        "constraints": {
            "mutable_paths": contract["mutation_policy"]["mutable_paths"],
            "promotion_requires": contract["mutation_policy"]["promotion_requires"],
            "default": contract["mutation_policy"]["default"],
        },
    }
    out = os.path.join(
        REPO, contract["runs_dir"], "experiment-1-authorized.json"
    )
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2)
        f.write("\n")
    print("MATERIALIZED %s" % out)
    return 0


def main(argv):
    if len(argv) != 3 or argv[1] not in ("validate", "materialize"):
        print(__doc__)
        return 2
    if argv[1] == "validate":
        return validate(argv[2])
    return materialize(argv[2])


if __name__ == "__main__":
    sys.exit(main(sys.argv))
