"""Typed evidence admissibility: independence vectors, roles, requirements.

    I = (I_A, I_S, I_D, I_M) ∈ {0,1}^4

    Adm(p, r) = VectorSatisfies(p,r) ∧ RoleCompatible(p,r)
                ∧ SourceCompatible(p,r) ∧ MethodCompatible(p,r)

No coordinate entails another; canonical roles are epistemic relations, not
node placements, and are never aliases. Vector coverage is necessary but not
sufficient: a correct answer from the wrong role is inadmissible for the
targeted distinction (the Experiment 6 'right shape, wrong role' failure).

Deterministic utility-v2 component computation lives here too: saturating
epistemic value (admissible coverage; extra isolation adds nothing),
marginal-coverage redundancy, and structural governance risk. The macro
utility form and its frozen weights are unchanged (utility.py).
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any, Optional

from .model import ModelValidationError

# ---- kinds and roles -------------------------------------------------------

KINDS = ("LOCAL", "CLEAN_ROOM_AUTHORSHIP", "NON_AUTHOR_SEARCH",
         "INDEPENDENT_DECOMPOSITION", "METHOD_DISJOINT_VERIFICATION")

ROLES = ("local_author", "clean_room_author", "non_author_examiner",
         "independent_decomposer", "method_disjoint_verifier")

# role -> provided independence vector (I_A, I_S, I_D, I_M); no entailment
ROLE_VECTOR = {
    "local_author": (0, 0, 0, 0),
    "clean_room_author": (1, 0, 0, 0),
    "non_author_examiner": (0, 1, 0, 0),
    "independent_decomposer": (0, 0, 1, 0),
    "method_disjoint_verifier": (0, 0, 0, 1),
}

# kind -> (required vector, allowed roles)
KIND_REQUIREMENT = {
    "LOCAL": ((0, 0, 0, 0), ("local_author",)),
    "CLEAN_ROOM_AUTHORSHIP": ((1, 0, 0, 0), ("clean_room_author",)),
    "NON_AUTHOR_SEARCH": ((0, 1, 0, 0), ("non_author_examiner",)),
    "INDEPENDENT_DECOMPOSITION": ((0, 0, 1, 0), ("independent_decomposer",)),
    "METHOD_DISJOINT_VERIFICATION": ((0, 0, 0, 1),
                                     ("method_disjoint_verifier",)),
}

# S1-inferred typed feature -> required admissibility kind
FEATURE_TO_KIND = {
    "requires_clean_room_authorship": "CLEAN_ROOM_AUTHORSHIP",
    "requires_nonauthor_search": "NON_AUTHOR_SEARCH",
    "requires_independent_decomposition": "INDEPENDENT_DECOMPOSITION",
    "requires_method_disjoint_verification": "METHOD_DISJOINT_VERIFICATION",
}
TYPED_FEATURES = tuple(sorted(FEATURE_TO_KIND))

# frozen E6 vocabulary -> canonical roles (enrichment/scoring joins)
E6_ROLE_MAP = {
    "clean_room_implementer": "clean_room_author",
    "adversarial_searcher": "non_author_examiner",
    "independent_decomposer": "independent_decomposer",
    "independent_verifier": "method_disjoint_verifier",
    "examiner_session": "non_author_examiner",
    "none": "local_author",
}

# frozen E6 latent class -> admissibility kind
E6_CLASS_TO_KIND = {
    "LOCAL": "LOCAL",
    "ISOLATION": "CLEAN_ROOM_AUTHORSHIP",
    "COUNTEREXAMPLE": "NON_AUTHOR_SEARCH",
    "ALTERNATIVE_DECOMPOSITION": "INDEPENDENT_DECOMPOSITION",
    "SPECIALIZED_VERIFICATION": "METHOD_DISJOINT_VERIFICATION",
}


@dataclass(frozen=True)
class IndependenceVector:
    i_a: int = 0
    i_s: int = 0
    i_d: int = 0
    i_m: int = 0

    def __post_init__(self):
        for k in ("i_a", "i_s", "i_d", "i_m"):
            if getattr(self, k) not in (0, 1):
                raise ModelValidationError(
                    f"independence coordinate {k} must be 0 or 1")

    def as_tuple(self) -> tuple[int, int, int, int]:
        return (self.i_a, self.i_s, self.i_d, self.i_m)

    def dominates(self, other: "IndependenceVector") -> bool:
        """∀k: self.I_k >= other.I_k (VectorSatisfies)."""
        return all(a >= b for a, b in zip(self.as_tuple(), other.as_tuple()))

    @classmethod
    def of(cls, t) -> "IndependenceVector":
        if isinstance(t, IndependenceVector):
            return t
        return cls(*[int(x) for x in t])


@dataclass(frozen=True)
class EvidenceRequirement:
    requirement_id: str
    distinction_id: str
    kind: str
    independence: IndependenceVector
    allowed_roles: tuple[str, ...]
    prohibited_sources: tuple[str, ...] = ()
    primary_method_family: str = ""     # nonempty => method-disjointness bind

    def __post_init__(self):
        if self.kind not in KINDS:
            raise ModelValidationError(f"unknown admissibility kind "
                                       f"{self.kind!r}")
        bad = [r for r in self.allowed_roles if r not in ROLES]
        if bad:
            raise ModelValidationError(f"unknown roles {bad}")

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["independence"] = list(self.independence.as_tuple())
        d["allowed_roles"] = list(self.allowed_roles)
        d["prohibited_sources"] = list(self.prohibited_sources)
        return d


@dataclass(frozen=True)
class EvidenceProvision:
    node_id: str
    role: str
    independence: IndependenceVector
    provenance_refs: tuple[str, ...] = ()
    method_family: str = ""
    source: str = ""                    # provenance source tag

    def __post_init__(self):
        if self.role not in ROLES:
            raise ModelValidationError(f"unknown canonical role "
                                       f"{self.role!r}")

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["independence"] = list(self.independence.as_tuple())
        d["provenance_refs"] = list(self.provenance_refs)
        return d


def provision_for_role(node_id: str, role: str, *, method_family: str = "",
                       source: str = "") -> EvidenceProvision:
    return EvidenceProvision(
        node_id=node_id, role=role,
        independence=IndependenceVector.of(ROLE_VECTOR[role]),
        method_family=method_family, source=source)


def requirement_for_distinction(d: dict[str, Any],
                                primary_method_family: str = "",
                                ) -> EvidenceRequirement:
    """Deterministic requirement from a distinction's typed features.

    Exactly one typed feature may be set; none => LOCAL. More than one is a
    typed-schema violation (bank tasks carry a single latent kind)."""
    feats = d.get("features", {})
    kinds = sorted(FEATURE_TO_KIND[f] for f in TYPED_FEATURES
                   if bool(feats.get(f, False)))
    if len(kinds) > 1:
        raise ModelValidationError(
            f"distinction {d.get('id')!r} sets multiple typed independence "
            f"features {kinds}; requirements are single-kind")
    kind = kinds[0] if kinds else "LOCAL"
    vec, roles = KIND_REQUIREMENT[kind]
    return EvidenceRequirement(
        requirement_id=f"req-{d['id']}",
        distinction_id=d["id"],
        kind=kind,
        independence=IndependenceVector.of(vec),
        allowed_roles=roles,
        primary_method_family=(primary_method_family
                               if kind == "METHOD_DISJOINT_VERIFICATION"
                               else ""),
    )


# ---- the admissibility equation -------------------------------------------

def admissible(p: EvidenceProvision, r: EvidenceRequirement,
               ) -> tuple[bool, dict[str, bool]]:
    clauses = {
        "vector_satisfies": p.independence.dominates(r.independence),
        "role_compatible": p.role in r.allowed_roles,
        "source_compatible": (not p.source
                              or p.source not in r.prohibited_sources),
        "method_compatible": (not r.primary_method_family
                              or (bool(p.method_family)
                                  and p.method_family
                                  != r.primary_method_family)),
    }
    return all(clauses.values()), clauses


def topology_admissible(provisions: list[EvidenceProvision],
                        requirements: list[EvidenceRequirement],
                        ) -> dict[str, Any]:
    """Valid_Adm(H,Q): every requirement has >=1 admissible provision."""
    per_req: dict[str, Any] = {}
    ok_all = True
    for r in requirements:
        winners = []
        for p in provisions:
            ok, clauses = admissible(p, r)
            if ok:
                winners.append(p.node_id)
        per_req[r.requirement_id] = {
            "kind": r.kind, "distinction_id": r.distinction_id,
            "admissible_provisions": winners, "admissible": bool(winners)}
        ok_all &= bool(winners)
    return {"admissible": ok_all, "per_requirement": per_req}


def marginal_coverage(provisions: list[EvidenceProvision],
                      requirements: list[EvidenceRequirement],
                      ) -> dict[str, list[str]]:
    """Requirements each provision covers beyond all earlier provisions
    (declared order). A provision with an empty list adds no admissible
    coverage: MarginalCoverage(p_k | p_1..p_{k-1}) = 0."""
    covered: set[str] = set()
    out: dict[str, list[str]] = {}
    for p in provisions:
        adds = []
        for r in requirements:
            if r.requirement_id in covered:
                continue
            if admissible(p, r)[0]:
                adds.append(r.requirement_id)
        covered.update(adds)
        out[p.node_id] = sorted(adds)
    return out


# ---- deterministic utility-v2 components ----------------------------------

def predicted_components(provisions: list[EvidenceProvision],
                         requirements: list[EvidenceRequirement],
                         value_by_distinction: dict[str, float],
                         *, model_sessions: int, child_sessions: int,
                         cost_denominator: int = 8) -> dict[str, float]:
    """Saturating ΔE + marginal-coverage redundancy + structural governance.

        ΔE_hat = Σ_q v_q·Adm(H,q) / Σ_q v_q          (0 if Σ v_q = 0)
        C      = (model_sessions + child_sessions) / 8
        R      = |provisions with zero marginal coverage| / |provisions|
        G      = min(1, 0.05·(model_sessions−1) + 0.10·child_sessions)

    Once a requirement is admissibly covered its value saturates: a second,
    more isolated provider adds redundancy, never value (b(H,q)=0)."""
    adm = topology_admissible(provisions, requirements)
    tot = 0.0
    got = 0.0
    for r in requirements:
        v = float(value_by_distinction.get(r.distinction_id, 0.0))
        if not (0.0 <= v <= 1.0):
            raise ModelValidationError(
                f"value estimate for {r.distinction_id} outside [0,1]: {v}")
        tot += v
        if adm["per_requirement"][r.requirement_id]["admissible"]:
            got += v
    delta_e = round(got / tot, 4) if tot > 0 else 0.0
    mc = marginal_coverage(provisions, requirements)
    n_prov = max(1, len(provisions))
    redundant = sum(1 for adds in mc.values() if not adds)
    redundancy = round(redundant / n_prov, 4)
    governance = round(min(1.0, 0.05 * max(0, model_sessions - 1)
                           + 0.10 * child_sessions), 4)
    cost = round((model_sessions + child_sessions) / cost_denominator, 4)
    return {"delta_e": delta_e, "cost": cost, "redundancy": redundancy,
            "governance_risk": governance}


# ---- serialization helpers for embedded specs -----------------------------

def provisions_from_spec(spec: dict[str, Any]) -> list[EvidenceProvision]:
    out = []
    for p in spec.get("evidence_provisions", []):
        out.append(EvidenceProvision(
            node_id=p["node_id"], role=p["role"],
            independence=IndependenceVector.of(p["independence"]),
            provenance_refs=tuple(p.get("provenance_refs", ())),
            method_family=p.get("method_family", ""),
            source=p.get("source", "")))
    return out


def canonical_role(e6_role: str, *, examiner: bool = False) -> str:
    """Map frozen E6 role vocabulary to canonical roles."""
    if examiner:
        return "non_author_examiner"
    if e6_role in ROLES:
        return e6_role
    return E6_ROLE_MAP.get(e6_role or "none", "local_author")
