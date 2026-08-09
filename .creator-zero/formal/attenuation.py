"""Contract attenuation: K_child <= K_parent as an inductive safety invariant.

No governed authority axis may increase from parent to child. This is checked
locally per creation; repeated locally-checked attenuation inductively implies
no finite descendant escalates (under the encoded transition rule). Coinduction
is deliberately NOT used for this local safety property.

Deterministic handling of historical contract fields:
  - set axes (tools/primitives/relations): child must be a subset;
  - numeric budgets: child <= parent;
  - filesystem scope: every child path must be (a) contained in some parent
    scope path (pure delegation), or (b) sibling-delegated: rooted in the
    workspace envelope of the parent's scope (its paths' parent directories)
    while overlapping none of the parent's protected paths. Rule (b) encodes
    the governed lineage law under which each generation receives a fresh
    disjoint sandbox (c1/ -> c2/ -> c3/) inside the experiment workspace;
  - authority strings (candidate/canonical/git/network) are mapped to a
    deterministic ordinal scale and compared;
  - a key absent on the PARENT is treated as unrestricted at that axis
    (most permissive: the child cannot escalate above it);
  - a key absent on the CHILD is treated as inheriting the parent value
    (equal, no escalation). Both defaults are recorded as assumptions.
"""
from __future__ import annotations
import re
from typing import Any, Optional

from .model import FAIL, PASS, FormalResult

RELATION = "K_child <= K_parent"

SET_AXES = ("allowed_tools", "allowed_primitives", "allowed_relations")
NUMERIC_AXES = ("max_model_calls", "max_children", "max_depth",
                "max_realized_creator_children", "max_realized_creator_depth")

_PAREN = re.compile(r"\s*\([^)]*\)\s*$")


def _norm_path(p: str) -> str:
    return _PAREN.sub("", p.strip()).rstrip("/")


def _under(child: str, parent: str) -> bool:
    return child == parent or child.startswith(parent + "/")


def _overlaps(a: str, b: str) -> bool:
    return _under(a, b) or _under(b, a)


def _parent_dir(p: str) -> str:
    return p.rsplit("/", 1)[0] if "/" in p else ""


def _scope_path_ok(c: str, ppaths: list[str], protected: list[str]) -> bool:
    if any(_under(c, p) for p in ppaths):
        return True  # pure delegation of the parent's own scope
    envelope = {_parent_dir(p) for p in ppaths}
    sibling = any(_under(_parent_dir(c), e) for e in envelope if e)
    return sibling and not any(_overlaps(c, pr) for pr in protected)


def _authority_ordinal(axis: str, value: Any) -> int:
    """Deterministic ordinal scale per authority axis; higher = more authority."""
    if value is None:
        return -1  # absent; resolved by caller defaults
    s = str(value).strip().lower()
    if s.startswith("none"):
        return 0
    if axis == "git_authority":
        return 1 if "read-only" in s or "read only" in s else 2
    if axis == "network_authority":
        return 1 if "model-invocation" in s else 2
    # candidate/canonical write authority: any non-none scoped grant
    return 1


def check_attenuation(parent: dict[str, Any], child: dict[str, Any]) -> FormalResult:
    failures: list[dict[str, Any]] = []
    evidence: list[str] = []
    assumptions = [
        "Axis absent on parent = unrestricted (most permissive) at that axis.",
        "Axis absent on child = inherited from parent (no escalation).",
        "Filesystem scope: child paths accepted by parent-scope containment "
        "or by sibling delegation inside the parent scope's workspace "
        "envelope with no overlap of parent protected paths; paths compared "
        "as normalized repo-relative strings, parenthetical annotations "
        "(e.g. '(append only)') stripped.",
        "Authority strings mapped to deterministic ordinals: "
        "none=0 < scoped/read-only/model-invocation=1 < unrestricted=2.",
        "Local check only; 'no finite descendant escalates' follows "
        "inductively only if every creation transition is checked.",
    ]

    for axis in SET_AXES:
        if axis not in parent and axis not in child:
            continue
        pv = set(parent.get(axis, [])) if axis in parent else None
        cv = set(child[axis]) if axis in child else None
        if cv is None:
            evidence.append(f"{axis}: child absent, inherits parent")
            continue
        if pv is None:
            evidence.append(f"{axis}: parent unrestricted")
            continue
        extra = sorted(cv - pv)
        if extra:
            failures.append({"dimension": axis, "escalation": extra,
                             "parent": sorted(pv), "child": sorted(cv)})
        else:
            evidence.append(f"{axis}: {sorted(cv)} subset of {sorted(pv)}")

    for axis in NUMERIC_AXES:
        if axis not in parent and axis not in child:
            continue
        if axis not in child:
            evidence.append(f"{axis}: child absent, inherits parent")
            continue
        cv = int(child[axis])
        if axis not in parent:
            evidence.append(f"{axis}: parent unrestricted")
            continue
        pv = int(parent[axis])
        if cv > pv:
            failures.append({"dimension": axis, "escalation": f"{cv} > {pv}",
                             "parent": pv, "child": cv})
        else:
            evidence.append(f"{axis}: {cv} <= {pv}")

    # boolean capability realization axes: True may not appear where parent has False
    for axis in ("may_create_creator", "may_realize_creation"):
        if axis in child and axis in parent:
            if bool(child[axis]) and not bool(parent[axis]):
                failures.append({"dimension": axis,
                                 "escalation": "child true, parent false",
                                 "parent": parent[axis], "child": child[axis]})
            else:
                evidence.append(f"{axis}: {child[axis]} <= {parent[axis]}")

    # filesystem scope: pure delegation or protected-disjoint sibling delegation
    if "filesystem_write_scope" in child:
        cpaths = [_norm_path(p) for p in child["filesystem_write_scope"]]
        if "filesystem_write_scope" in parent:
            ppaths = [_norm_path(p) for p in parent["filesystem_write_scope"]]
            protected = [_norm_path(p) for p in parent.get("protected_paths", [])]
            outside = [c for c in cpaths
                       if not _scope_path_ok(c, ppaths, protected)]
            if outside:
                failures.append({"dimension": "filesystem_write_scope",
                                 "escalation": outside,
                                 "parent": ppaths, "child": cpaths})
            else:
                evidence.append("filesystem_write_scope: child paths delegated "
                                "within parent scope/workspace envelope, "
                                "disjoint from parent protected paths")
        else:
            evidence.append("filesystem_write_scope: parent unrestricted")

    # candidate/canonical/git/network authority ordinals
    for axis in ("candidate_write_authority", "canonical_write_authority",
                 "git_authority", "network_authority"):
        if axis not in parent and axis not in child:
            continue
        c_ord = _authority_ordinal(axis, child.get(axis))
        p_ord = _authority_ordinal(axis, parent.get(axis))
        if c_ord < 0:
            evidence.append(f"{axis}: child absent, inherits parent")
            continue
        if p_ord < 0:
            p_ord = 2  # parent unrestricted
            evidence.append(f"{axis}: parent unrestricted")
        if c_ord > p_ord:
            failures.append({"dimension": axis,
                             "escalation": f"ordinal {c_ord} > {p_ord}",
                             "parent": parent.get(axis), "child": child.get(axis)})
        else:
            evidence.append(f"{axis}: ordinal {c_ord} <= {p_ord}")

    if failures:
        return FormalResult(
            check="contract_attenuation", status=FAIL,
            formal_relation=RELATION,
            counterexample={"verdict": "ATTENUATION_FAIL",
                            "escalating_dimensions": failures},
            evidence=evidence, assumptions=assumptions)
    return FormalResult(
        check="contract_attenuation", status=PASS,
        formal_relation=RELATION,
        evidence=evidence, assumptions=assumptions,
        detail={"verdict": "ATTENUATION_PASS"})
