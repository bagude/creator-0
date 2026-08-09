"""Finite fixed-point classification for Decomposer/Composer synthesis.

Given the unresolved distinction sets Q_before and Q_after, return exactly one:

    Q_after == empty                 -> SYNTHESIS_CLOSED
    Q_after proper-subset Q_before   -> PROGRESS
    Q_after == Q_before != empty     -> SYNTHESIS_FIXED_POINT_UNRESOLVED
    Q_after not-subset  Q_before     -> SYNTHESIS_REGRESSION

This is the v0.1 finite-set implementation: a deterministic progress
classifier, not general Tarski convergence machinery.
"""
from __future__ import annotations
from typing import Any, Iterable

from .model import FAIL, INDETERMINATE, PASS, FormalResult

CLOSED = "SYNTHESIS_CLOSED"
PROGRESS = "PROGRESS"
FIXED_POINT = "SYNTHESIS_FIXED_POINT_UNRESOLVED"
REGRESSION = "SYNTHESIS_REGRESSION"

RELATION = "Q_after vs Q_before over finite unresolved-distinction sets"

# Formal status of each classification: CLOSED and PROGRESS are healthy (PASS);
# an unresolved fixed point is INDETERMINATE (no progress, no regression);
# regression is FAIL.
_STATUS = {CLOSED: PASS, PROGRESS: PASS, FIXED_POINT: INDETERMINATE,
           REGRESSION: FAIL}


def classify_synthesis(before: Iterable[Any], after: Iterable[Any]) -> FormalResult:
    qb = frozenset(before)
    qa = frozenset(after)
    if not qa:
        cls = CLOSED
    elif qa < qb:
        cls = PROGRESS
    elif qa == qb:
        cls = FIXED_POINT
    elif not qa <= qb:
        cls = REGRESSION
    else:  # unreachable: qa <= qb, qa != qb, qa nonempty => qa < qb (PROGRESS)
        cls = PROGRESS
    new_items = sorted(str(x) for x in (qa - qb))
    resolved = sorted(str(x) for x in (qb - qa))
    counterexample = None
    if cls == REGRESSION:
        counterexample = {"new_unresolved_distinctions": new_items}
    elif cls == FIXED_POINT:
        counterexample = {"unchanged_nonempty_set": sorted(str(x) for x in qa)}
    return FormalResult(
        check="synthesis_fixed_point", status=_STATUS[cls],
        formal_relation=RELATION,
        counterexample=counterexample,
        evidence=[f"|Q_before|={len(qb)}, |Q_after|={len(qa)}",
                  f"resolved: {resolved}", f"introduced: {new_items}"],
        assumptions=["Finite-set progress classification only; no Tarski "
                     "convergence claim for arbitrary D/C synthesis."],
        detail={"classification": cls,
                "resolved": resolved, "introduced": new_items})
