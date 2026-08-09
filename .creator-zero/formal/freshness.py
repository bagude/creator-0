"""Hardened freshness verdict v0.2 over persisted launch provenance.

Tightens the Experiment 5 rule (where session_id_confirmed=None was
acceptable for executed sessions) to:

    if executed:      session_id_confirmed must be True
    elif not executed (dry run):  None (or True) is permitted

The Experiment 5 launcher and its frozen evidence are untouched: this check
lives in the kernel and applies to all new architecture launches. Frozen E5
provenance records (executed=true, session_id_confirmed=true) PASS under
the tightened rule; the rule change never rewrites historical artifacts.
"""
from __future__ import annotations
from typing import Any

from .model import FAIL, PASS, FormalResult

RELATION = "FreshChild ∧ SanitizedEnvironment ∧ ConfirmedExecutedIdentity"


def check_freshness(provenance: dict[str, Any]) -> FormalResult:
    executed = provenance.get("executed")
    confirmed = provenance.get("session_id_confirmed")
    checks = {
        "launched_via_fresh_launcher":
            provenance.get("artifact") == "fresh-child launch provenance",
        "declared_fresh": provenance.get("fresh") is True,
        "sanitization_recorded": "environment_sanitization" in provenance,
        "no_residual_continuity_vars": not provenance.get(
            "environment_sanitization", {}).get(
                "residual_continuity_variables", ["<missing>"]),
        "no_session_id_reuse": provenance.get(
            "environment_sanitization", {}).get("session_id_reuse") is False,
        "explicit_session_id": bool(provenance.get("session_id")),
        "executed_recorded": isinstance(executed, bool),
        # the hardened clause: executed sessions demand stream confirmation
        "session_id_confirmed_rule": (
            confirmed is True if executed is True
            else confirmed in (True, None) if executed is False
            else False),
    }
    failed = sorted(k for k, v in checks.items() if not v)
    status = PASS if not failed else FAIL
    return FormalResult(
        check="fresh_child_v2", status=status,
        formal_relation=RELATION,
        counterexample=({"violation": "FRESHNESS_FAIL",
                         "failed_clauses": failed} if failed else None),
        evidence=[f"executed: {executed}",
                  f"session_id: {provenance.get('session_id')}",
                  f"session_id_confirmed: {confirmed}"],
        assumptions=[
            "Rule v0.2: an executed session requires session_id_confirmed="
            "True; None is acceptable only for explicit dry-run/non-executed "
            "launches; False always fails.",
            "The launcher is the sole legal child-invocation path; the "
            "topology guard cross-checks that no child ran outside it.",
        ],
        detail={"clauses": checks, "rule_version": "0.2"})
