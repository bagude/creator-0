"""Evidence-conditioned revision engine v2: context-aware candidate family.

Builds on the existing revision algebra (model.Revision, revise.apply_revision;
SPLIT was already recognized) — no second incompatible mechanism. What v2
adds, per the frozen Experiment 7 preregistration §6:

    context_stats()          SUPPORT/FALSIFY per admissibility context
    split_trigger()          evidence-grounded SPLIT eligibility
    build_candidates()       {no-change, SPECIALIZE, SPLIT, DEPRECATE}
    explanation_scores()     frozen deterministic explanation scoring
    propose_revision_v2()    scored, deterministic selection

Nothing here promotes anything: every produced Revision is CANDIDATE and the
successor TheoryVersion built from it stays CANDIDATE until the final theory
Gate. Wording of candidate principles may be model-drafted, but it enters
only as serialized text validated structurally; partitioning, scoring, and
selection are deterministic. 'Split because the operator said so' is
impossible: the trigger demands mixed evidence occupying >=2 reproducible
contexts with a support-rate spread.
"""
from __future__ import annotations
from typing import Any, Optional

from .model import (ModelValidationError, Principle, Revision, TheoryVersion)
from .admissibility import KIND_REQUIREMENT

# Frozen rule constants (preregistration §6; never tuned after Phase A)
FROZEN_RULES = {
    "min_context_events": 4,
    "min_spread": 0.3,
    "min_context_coverage": 0.9,
    "reproducibility_floor": 2,
    "specialize_max_falsify_rate": 0.2,
}

# Preregistered split basis for P-INDEPENDENCE: context kind -> child spec
SPLIT_BASIS = {
    "P-INDEPENDENCE": {
        "CLEAN_ROOM_AUTHORSHIP": {
            "id": "P-AUTHORSHIP-INDEPENDENCE",
            "feature": "requires_clean_room_authorship",
            "role": "clean_room_author",
        },
        "NON_AUTHOR_SEARCH": {
            "id": "P-NONAUTHOR-SEARCH",
            "feature": "requires_nonauthor_search",
            "role": "non_author_examiner",
        },
        "INDEPENDENT_DECOMPOSITION": {
            "id": "P-INDEPENDENT-DECOMPOSITION",
            "feature": "requires_independent_decomposition",
            "role": "independent_decomposer",
        },
        "METHOD_DISJOINT_VERIFICATION": {
            "id": "P-METHOD-DISJOINT-VERIFICATION",
            "feature": "requires_method_disjoint_verification",
            "role": "method_disjoint_verifier",
        },
    },
}

_DEFAULT_STATEMENTS = {
    "P-AUTHORSHIP-INDEPENDENCE":
        "When a distinction's admissibility requires clean-room authorship "
        "(evidence authored without access to a contaminating reference), "
        "only an isolated fresh descendant authoring solely from the "
        "sanctioned description supplies admissible evidence; examiner "
        "review of contaminated work cannot.",
    "P-NONAUTHOR-SEARCH":
        "When a distinction requires a search for violating inputs by a "
        "party that did not author the candidate answer, an information-"
        "only independent examiner supplies admissible evidence; full "
        "clean-room isolation satisfies the same requirement at strictly "
        "higher cost and adds no admissible value.",
    "P-INDEPENDENT-DECOMPOSITION":
        "When completeness of an enumeration or decomposition is admissible "
        "only via a second decomposition produced without access to the "
        "first, an isolated independent decomposer is required; review or "
        "re-verification of the first decomposition is inadmissible for "
        "that distinction.",
    "P-METHOD-DISJOINT-VERIFICATION":
        "When correctness must be established by re-derivation through a "
        "method disjoint from the primary method, a method-disjoint "
        "verifier path supplies the admissible evidence; isolation without "
        "method disjointness is insufficient, and method-sharing review is "
        "inadmissible.",
}

_DEFAULT_FALSIFIERS = {
    "P-AUTHORSHIP-INDEPENDENCE":
        "a reference-exposed path yields evidence scored admissible for a "
        "clean-room distinction, or the isolated clean-room author fails "
        "to add admissible value where the requirement is present",
    "P-NONAUTHOR-SEARCH":
        "the independent examiner's search is scored inadmissible where "
        "predicted admissible, or an isolated child strictly outperforms "
        "the examiner on the same search requirement at equal "
        "admissibility and equal coverage",
    "P-INDEPENDENT-DECOMPOSITION":
        "a decomposition produced with access to the first is scored "
        "admissible, or the isolated decomposer duplicates the first "
        "decomposition without novel enumeration evidence",
    "P-METHOD-DISJOINT-VERIFICATION":
        "a method-sharing verification is scored admissible for a "
        "method-disjoint distinction, or the method-disjoint verifier "
        "fails to add admissible value where the requirement is present",
}


def context_stats(events: list[Any], principle_id: str) -> dict[str, Any]:
    """SUPPORT/FALSIFY/CHALLENGE counts per resolved admissibility context."""
    ctx: dict[str, dict[str, Any]] = {}
    unresolved = 0
    total = 0
    for e in events:
        d = e.to_dict() if hasattr(e, "to_dict") else dict(e)
        if d.get("principle_id") != principle_id:
            continue
        total += 1
        c = (d.get("context") or {})
        kind = c.get("admissibility_kind")
        if c.get("context_status") != "OK" or not kind:
            unresolved += 1
            continue
        slot = ctx.setdefault(kind, {"SUPPORT": 0, "CHALLENGE": 0,
                                     "FALSIFY": 0, "event_ids": []})
        slot[d["effect"]] += 1
        slot["event_ids"].append(d.get("event_id") or d["prediction_id"])
    for slot in ctx.values():
        slot["event_ids"] = sorted(slot["event_ids"])
        sf = slot["SUPPORT"] + slot["FALSIFY"]
        slot["support_rate"] = round(slot["SUPPORT"] / sf, 4) if sf else None
        slot["falsify_rate"] = round(slot["FALSIFY"] / sf, 4) if sf else None
    return {"principle_id": principle_id, "total_events": total,
            "unresolved_context_events": unresolved, "contexts": ctx}


def split_trigger(stats: dict[str, Any],
                  rules: dict[str, Any] = FROZEN_RULES) -> dict[str, Any]:
    ctx = stats["contexts"]
    total = stats["total_events"]
    support = sum(c["SUPPORT"] for c in ctx.values())
    falsify = sum(c["FALSIFY"] for c in ctx.values())
    coverage = ((total - stats["unresolved_context_events"]) / total
                if total else 0.0)
    qualifying = {k: c for k, c in ctx.items()
                  if (c["SUPPORT"] + c["CHALLENGE"] + c["FALSIFY"])
                  >= rules["min_context_events"]}
    rates = [c["support_rate"] for c in qualifying.values()
             if c["support_rate"] is not None]
    spread = (max(rates) - min(rates)) if len(rates) >= 2 else 0.0
    clauses = {
        "mixed_evidence": support >= 1 and falsify >= 1,
        "context_coverage": coverage >= rules["min_context_coverage"],
        "enough_contexts": len(qualifying) >= 2,
        "support_rate_spread": spread >= rules["min_spread"],
    }
    return {"eligible": all(clauses.values()), "clauses": clauses,
            "qualifying_contexts": sorted(qualifying),
            "support_rate_spread": round(spread, 4),
            "context_coverage": round(coverage, 4)}


def _validate_split_children(children: list[dict[str, Any]]) -> None:
    ids = [c["id"] for c in children]
    if len(ids) != len(set(ids)):
        raise ModelValidationError("split children must have unique ids")
    pre = [tuple(c["preconditions"]) for c in children]
    eff = [tuple(c["predicted_topology_effects"]) for c in children]
    if len(set(pre)) != len(pre) or len(set(eff)) != len(eff):
        raise ModelValidationError(
            "split children are semantic duplicates (identical "
            "preconditions or predicted effects)")
    for c in children:
        if not str(c.get("falsifier", "")).strip():
            raise ModelValidationError(
                f"split child {c['id']} lacks an explicit falsifier")
        if not c.get("supporting_evidence"):
            raise ModelValidationError(
                f"split child {c['id']} lacks motivating evidence")
        Principle.from_dict(c)      # closed-schema validation


def build_split_candidate(theory: TheoryVersion, pid: str,
                          stats: dict[str, Any],
                          wording: Optional[dict[str, str]] = None,
                          rules: dict[str, Any] = FROZEN_RULES,
                          ) -> Revision:
    basis = SPLIT_BASIS.get(pid)
    if basis is None:
        raise ModelValidationError(f"no preregistered split basis for {pid}")
    trigger = split_trigger(stats, rules)
    if not trigger["eligible"]:
        raise ModelValidationError(
            f"split trigger not satisfied for {pid}: {trigger['clauses']}")
    wording = wording or {}
    children = []
    partition = {}
    motivating: list[str] = []
    for kind in sorted(stats["contexts"]):
        c = stats["contexts"][kind]
        n = c["SUPPORT"] + c["CHALLENGE"] + c["FALSIFY"]
        if n < rules["min_context_events"] or kind not in basis:
            continue
        spec = basis[kind]
        cid = spec["id"]
        stmt = wording.get(cid, _DEFAULT_STATEMENTS[cid])
        if len(stmt.strip()) < 40:
            raise ModelValidationError(
                f"candidate principle {cid} wording too thin")
        vec, roles = KIND_REQUIREMENT[kind]
        children.append({
            "id": cid,
            "statement": stmt,
            "status": "CANDIDATE",
            "scope": ["topology-decision", "verification"],
            "preconditions": [f"feature:{spec['feature']}"],
            "predicted_topology_effects": [
                f"adds an independent path with canonical role "
                f"{spec['role']}",
                f"that path's evidence is admissible for "
                f"{kind} distinctions (required vector {list(vec)})",
                "cheaper admissible paths dominate costlier ones at equal "
                "coverage (saturating value)",
            ],
            "supporting_evidence": [
                {"evidence_event_id": eid,
                 "context_kind": kind,
                 "source": "experiment-6 imported theory evidence"}
                for eid in c["event_ids"]],
            "contradicting_evidence": [],
            "parent_principles": [pid],
            "version": 1,
            "falsifier": _DEFAULT_FALSIFIERS[cid],
        })
        partition[kind] = {"SUPPORT": c["SUPPORT"], "FALSIFY": c["FALSIFY"],
                           "CHALLENGE": c["CHALLENGE"],
                           "event_ids": c["event_ids"]}
        motivating.extend(c["event_ids"])
    _validate_split_children(children)
    return Revision(
        revision_id=f"rev-split-{pid.lower()}",
        type="SPLIT",
        parents=[pid],
        candidate_principles=children,
        motivating_evidence=sorted(motivating),
        historical_cases_affected=[],
        changed_predictions=[
            "typed admissibility replaces coarse isolation preference in "
            "topology generation and ranking",
            "an examiner (not an isolated child) is predicted optimal for "
            "pure NON_AUTHOR_SEARCH requirements",
            "a method-disjoint verifier (not an isolated child) is "
            "predicted optimal for METHOD_DISJOINT_VERIFICATION",
        ],
        context_partition=partition,
        status="CANDIDATE")


def build_specialize_candidate(theory: TheoryVersion, pid: str,
                               stats: dict[str, Any],
                               rules: dict[str, Any] = FROZEN_RULES,
                               ) -> Revision:
    parent = theory.principle(pid)
    retained = sorted(
        k for k, c in stats["contexts"].items()
        if c["falsify_rate"] is not None
        and c["falsify_rate"] < rules["specialize_max_falsify_rate"])
    narrowed = dict(parent.to_dict()) if parent else {"id": pid}
    narrowed.update({
        "id": f"{pid}-SPECIALIZED",
        "status": "CANDIDATE",
        "parent_principles": [pid],
        "version": 1,
        "statement": (parent.statement if parent else "") +
        f" [SPECIALIZED: preconditions narrowed to admissibility contexts "
        f"{retained} in which the principle's predictions held]",
    })
    motivating = []
    for k, c in stats["contexts"].items():
        if k not in retained:
            motivating.extend(c["event_ids"])
    return Revision(
        revision_id=f"rev-specialize-{pid.lower()}",
        type="SPECIALIZE",
        parents=[pid],
        candidate_principles=[narrowed],
        motivating_evidence=sorted(motivating),
        context_partition={"retained_contexts": retained},
        status="CANDIDATE")


def build_deprecate_candidate(pid: str, stats: dict[str, Any]) -> Revision:
    falsify = sorted(eid for c in stats["contexts"].values()
                     for eid in c["event_ids"] if c["FALSIFY"])
    return Revision(
        revision_id=f"rev-deprecate-{pid.lower()}",
        type="DEPRECATE",
        parents=[pid],
        candidate_principles=[],
        motivating_evidence=falsify,
        status="CANDIDATE")


def explanation_scores(stats: dict[str, Any],
                       rules: dict[str, Any] = FROZEN_RULES,
                       ) -> dict[str, float]:
    """Frozen explanation scoring over the parent's evidence events."""
    total = stats["total_events"]
    if total == 0:
        return {"no-change": 0.0, "SPECIALIZE": 0.0, "SPLIT": 0.0,
                "DEPRECATE": 0.0}
    floor = rules["reproducibility_floor"]
    retained = {k for k, c in stats["contexts"].items()
                if c["falsify_rate"] is not None
                and c["falsify_rate"] < rules["specialize_max_falsify_rate"]}
    nc = sp = sl = dp = 0
    for kind, c in stats["contexts"].items():
        s, f = c["SUPPORT"], c["FALSIFY"]
        nc += s
        dp += f
        sp += s if kind in retained else f
        sl += (s if s >= floor else 0) + (f if f >= floor else 0)
    return {"no-change": round(nc / total, 4),
            "SPECIALIZE": round(sp / total, 4),
            "SPLIT": round(sl / total, 4),
            "DEPRECATE": round(dp / total, 4)}


_TIE_ORDER = ("no-change", "SPECIALIZE", "SPLIT", "DEPRECATE")


def propose_revision_v2(theory: TheoryVersion, events: list[Any],
                        target: str = "P-INDEPENDENCE",
                        wording: Optional[dict[str, str]] = None,
                        rules: dict[str, Any] = FROZEN_RULES,
                        ) -> dict[str, Any]:
    """Generate the frozen candidate family, score, and select. Returns a
    serializable proposal document; the selected Revision (if any) is
    CANDIDATE and promotes nothing."""
    stats = context_stats(events, target)
    trigger = split_trigger(stats, rules)
    candidates: dict[str, Optional[Revision]] = {
        "no-change": None,
        "SPECIALIZE": build_specialize_candidate(theory, target, stats,
                                                 rules),
        "DEPRECATE": build_deprecate_candidate(target, stats),
    }
    if trigger["eligible"]:
        candidates["SPLIT"] = build_split_candidate(theory, target, stats,
                                                    wording, rules)
    scores = explanation_scores(stats, rules)
    if "SPLIT" not in candidates:
        scores = {k: v for k, v in scores.items() if k != "SPLIT"}

    def key(name: str):
        rev = candidates.get(name)
        n_new = len(rev.candidate_principles) if rev else 0
        return (-scores[name], n_new, _TIE_ORDER.index(name))

    selected = sorted(scores, key=key)[0]
    return {
        "artifact": "revision proposal v2",
        "target_principle": target,
        "context_stats": stats,
        "split_trigger": trigger,
        "scores": scores,
        "selection_rule": "max explanation score; ties -> fewer new "
                          "principles -> fixed order "
                          "[no-change, SPECIALIZE, SPLIT, DEPRECATE]",
        "selected": selected,
        "candidates": {k: (v.to_dict() if v else None)
                       for k, v in candidates.items()},
        "rules": dict(rules),
    }
