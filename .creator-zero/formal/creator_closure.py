"""Bounded Creator-Closure witness checking.

Abstract (coinductive) definition:
    F(X) = { C | exists C': C --create--> C' and Attenuated(C', C) and C' in X }
    Creator = nu X . F(X)   (greatest fixed point)

The executable check never unfolds an infinite lineage. It verifies the
bounded witness predicate over a parent contract and a child attestation:

    hat_kappa(K_parent, K_child, creation_mechanism) =
        Valid(K_child)
        AND Attenuated(K_child, K_parent)
        AND CreatorCapable(K_child)
        AND CreationMechanismValid
        AND ExternalStopOnly(K_child)

This preserves the Experiment 4B correction: a terminal child
(creator_capability=false, may_create_creator=false) FAILS — it witnesses the
ability to specify a bounded terminal leaf, not preservation of Creator
capability. A Creator-capable child whose realization is externally disabled
(may_realize_creation=false, max_children=0) may PASS: the stop is
architectural, not a capability removal.
"""
from __future__ import annotations
from typing import Any, Optional

from .attenuation import check_attenuation
from .model import FAIL, INDETERMINATE, PASS, FormalResult

RELATION = ("hat_kappa(K_parent, K_child) = Valid AND Attenuated AND "
            "CreatorCapable AND CreationMechanismValid AND ExternalStopOnly")

REQUIRED_CHILD_KEYS = (
    "contract_id", "allowed_primitives", "allowed_tools",
    "max_children", "max_depth", "max_model_calls",
    "may_create_creator", "creator_capability", "may_realize_creation",
)

# Deterministic resolution order for the draft child contract inside an
# attestation document.
CHILD_CONTRACT_KEYS = ("draft_child_contract_K3", "draft_child_contract",
                       "child_contract")
CREATION_COMMAND_KEYS = ("exact_creation_command_NOT_EXECUTED",
                         "exact_creation_command", "creation_command")


def extract_child_contract(attestation: dict[str, Any]) -> Optional[dict[str, Any]]:
    for k in CHILD_CONTRACT_KEYS:
        if isinstance(attestation.get(k), dict):
            return attestation[k]
    return None


def check_creator_closure(parent: dict[str, Any],
                          attestation: dict[str, Any]) -> FormalResult:
    assumptions = [
        "Creator = nu X.F(X) is the abstract coinductive definition; this "
        "check is a bounded finite witness, not a proof of arbitrary "
        "infinite Creator lineage.",
        "CreationMechanismValid = a concrete non-empty creation command is "
        "attested and marked not executed (capability evidenced by "
        "attestation, realization externally stopped).",
    ]
    clauses: dict[str, Any] = {}
    evidence: list[str] = []

    child = extract_child_contract(attestation)
    if child is None:
        return FormalResult(
            check="creator_closure", status=INDETERMINATE,
            formal_relation=RELATION,
            evidence=["no draft child contract found in attestation "
                      f"(searched keys: {list(CHILD_CONTRACT_KEYS)})"],
            assumptions=assumptions,
            detail={"reason": "insufficient evidence: missing child contract"})

    # Valid(K_child)
    missing = [k for k in REQUIRED_CHILD_KEYS if k not in child]
    clauses["Valid"] = not missing
    if missing:
        evidence.append(f"Valid: FAIL, child contract missing keys {missing}")
    else:
        evidence.append("Valid: child contract carries all required governed keys")

    # Attenuated(K_child, K_parent)
    att = check_attenuation(parent, child)
    clauses["Attenuated"] = att.status == PASS
    evidence.append(f"Attenuated: {att.status}")

    # CreatorCapable(K_child)
    creator_capable = (bool(child.get("creator_capability", False))
                      and bool(child.get("may_create_creator", False)))
    clauses["CreatorCapable"] = creator_capable
    evidence.append(
        "CreatorCapable: creator_capability=%s, may_create_creator=%s" % (
            child.get("creator_capability"), child.get("may_create_creator")))

    # CreationMechanismValid
    command = None
    for k in CREATION_COMMAND_KEYS:
        v = attestation.get(k)
        if isinstance(v, str) and v.strip():
            command = (k, v)
            break
    mechanism_ok = command is not None
    executed_marker = "NOT_EXECUTED" in (command[0] if command else "") or \
        bool(attestation.get("architectural_stop_statement"))
    clauses["CreationMechanismValid"] = mechanism_ok and executed_marker
    evidence.append(
        "CreationMechanismValid: command %s, non-execution marker %s" % (
            "present" if mechanism_ok else "ABSENT",
            "present" if executed_marker else "ABSENT"))

    # ExternalStopOnly(K_child)
    external_stop = (not bool(child.get("may_realize_creation", True))
                     and int(child.get("max_children", 1)) == 0)
    clauses["ExternalStopOnly"] = external_stop
    evidence.append(
        "ExternalStopOnly: may_realize_creation=%s, max_children=%s" % (
            child.get("may_realize_creation"), child.get("max_children")))

    failed = sorted(k for k, ok in clauses.items() if not ok)
    if failed:
        counterexample: dict[str, Any] = {"failed_clauses": failed}
        if not clauses["Attenuated"] and att.counterexample:
            counterexample["attenuation"] = att.counterexample
        if not clauses["CreatorCapable"]:
            counterexample["creator_capable"] = {
                "creator_capability": child.get("creator_capability"),
                "may_create_creator": child.get("may_create_creator"),
                "note": "terminal child cannot witness recursive closure "
                        "(Experiment 4B correction)"}
        return FormalResult(
            check="creator_closure", status=FAIL,
            formal_relation=RELATION,
            counterexample=counterexample,
            evidence=evidence, assumptions=assumptions,
            detail={"clauses": clauses})
    return FormalResult(
        check="creator_closure", status=PASS,
        formal_relation=RELATION,
        evidence=evidence, assumptions=assumptions,
        detail={"clauses": clauses,
                "child_contract_id": child.get("contract_id")})
