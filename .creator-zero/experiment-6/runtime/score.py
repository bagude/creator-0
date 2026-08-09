"""Deterministic per-trial scoring against frozen private labels.

All matching rules are preregistered:

Distinction scoring (S1): each private critical distinction carries a list
of core regex patterns frozen before any primary execution. For each
inferred distinction Q, the matched fraction is (#core patterns matching
Q's combined text)/(#core patterns), combined text = question +
why_unresolved + required_evidence + admissibility_constraints. The best
fraction over inferred Qs decides: 1.0 -> MATCH, >= 0.5 -> PARTIAL,
else MISS. An inferred Q whose best fraction over all critical
distinctions is 0 is SPURIOUS. Critical recall =
(#MATCH + 0.5*#PARTIAL)/#critical.

Principle scoring (S2): ranks are read from the persisted ordered
applicability (feature-match count desc, id asc). top-1/top-2 refer to the
label's primary expected principle; expected-set recall is the fraction of
expected principles present in the abduced applicable set.

Topology correctness (S3/S5): the label lists acceptable (and optionally
partial-credit) causal feature sets; the realized topology's features are
computed mechanically from the trial record. CORRECT if any acceptable set
matches, else PARTIAL if any partial set matches, else INCORRECT.
"""
from __future__ import annotations
import re
from pathlib import Path
from typing import Any

from .common import E6, bank_dir, family_of, jload, jdump


def _combined_text(d: dict[str, Any]) -> str:
    return " ".join([d.get("question", ""), d.get("why_unresolved", ""),
                     d.get("required_evidence", ""),
                     " ".join(d.get("admissibility_constraints", []))])


def score_distinctions(label: dict[str, Any],
                       distinctions: list[dict[str, Any]]) -> dict[str, Any]:
    criticals = label["critical_distinctions"]
    texts = {d["id"]: _combined_text(d) for d in distinctions}
    per_critical = []
    q_best: dict[str, float] = {q: 0.0 for q in texts}
    for cd in criticals:
        core = cd["core_patterns"]
        best_q, best_frac = None, 0.0
        fracs = {}
        for q, text in texts.items():
            hits = sum(1 for p in core
                       if re.search(p, text, re.IGNORECASE))
            frac = hits / len(core) if core else 0.0
            fracs[q] = frac
            q_best[q] = max(q_best[q], frac)
            if frac > best_frac or (frac == best_frac and best_q is None):
                best_q, best_frac = q, frac
        status = ("MATCH" if best_frac >= 1.0 else
                  "PARTIAL" if best_frac >= 0.5 else "MISS")
        per_critical.append({"id": cd["id"], "status": status,
                             "best_inferred": best_q,
                             "best_fraction": round(best_frac, 4)})
    n = len(criticals)
    match = sum(1 for c in per_critical if c["status"] == "MATCH")
    partial = sum(1 for c in per_critical if c["status"] == "PARTIAL")
    spurious = sorted(q for q, f in q_best.items() if f == 0.0)
    return {
        "per_critical": per_critical,
        "critical_recall": round((match + 0.5 * partial) / n, 4) if n else 1.0,
        "match": match, "partial": partial,
        "miss": n - match - partial,
        "spurious": spurious,
        "spurious_count": len(spurious),
    }


def score_principles(label: dict[str, Any],
                     applicability: dict[str, Any]) -> dict[str, Any]:
    expected = label["expected_principles"]
    ordered = applicability["ordered_applicability"]
    ranks = {r["principle_id"]: r["rank"] for r in ordered
             if r["feature_match_count"] > 0}
    applicable_ids = {a["principle_id"]
                      for a in applicability.get("applicable", [])}
    primary = expected[0]
    top1 = ranks.get(primary) == 1
    top2 = ranks.get(primary, 99) <= 2
    recall = (sum(1 for p in expected if p in applicable_ids)
              / len(expected)) if expected else 1.0
    return {
        "expected": expected,
        "primary_expected": primary,
        "primary_rank": ranks.get(primary),
        "top1_hit": top1,
        "top2_hit": top2,
        "expected_set_recall": round(recall, 4),
        "feature_ranked": {p: ranks.get(p) for p in expected},
    }


def computed_features(td: Path, topo: dict[str, Any],
                      label: dict[str, Any]) -> dict[str, Any]:
    has_create = any(n.get("primitive") == "create"
                     for n in topo["harness_spec"].get("nodes", []))
    child_launched = (td / "child" / "launch-provenance.json").exists()
    examiner = (td / "examiner" / "launch-provenance.json").exists()
    role = ""
    clean_room = False
    if child_launched and (td / "child" / "integration-plan.json").exists():
        plan = jload(td / "child" / "integration-plan.json")
        role = str(plan.get("role", ""))
        man = jload(td / "child" / "child-input-manifest.json")
        exclusions = label.get("clean_room_exclusions", [])
        clean_room = all(x not in man.get("files", []) for x in exclusions)
    return {
        "child": child_launched,
        "child_role": role,
        "clean_room": clean_room,
        "independent_examiner": examiner,
        "distinct_verification_path": examiner or (
            child_launched and role in ("independent_verifier",
                                        "adversarial_searcher")),
        "independent_decomposition_path":
            child_launched and role == "independent_decomposer",
        "adversarial_path": (child_launched and
                             role == "adversarial_searcher") or examiner,
        "no_extra_path": not child_launched and not examiner,
        "family": family_of(topo["topology_id"]),
    }


def _feature_set_matches(required: dict[str, Any],
                         computed: dict[str, Any]) -> bool:
    return all(computed.get(k) == v for k, v in required.items())


def score_topology(label: dict[str, Any],
                   computed: dict[str, Any]) -> dict[str, Any]:
    acceptable = label["acceptable_topology_features"]
    partial = label.get("partial_topology_features", [])
    if any(_feature_set_matches(fs, computed) for fs in acceptable):
        verdict = "TOPOLOGY_CORRECT"
    elif any(_feature_set_matches(fs, computed) for fs in partial):
        verdict = "TOPOLOGY_PARTIAL"
    else:
        verdict = "TOPOLOGY_INCORRECT"
    return {"verdict": verdict, "computed_features": computed,
            "acceptable": acceptable, "partial": partial}


def candidate_generation_coverage(label: dict[str, Any], td: Path,
                                  pipeline_dir: Path) -> dict[str, Any]:
    """Did the (validated) candidate set contain a topology whose
    STRUCTURAL features could satisfy the label? Structural check only:
    role/clean-room are execution properties, so coverage asks whether a
    family capable of the needed causal shape was generated and valid."""
    ranking = jload(pipeline_dir / "candidate-ranking.json")
    valid = [t for t, s in ranking.get("validation", {}).items()
             if s == "PASS"]
    fams = {family_of(t) for t in valid}
    needed = set()
    for fs in label["acceptable_topology_features"]:
        if fs.get("no_extra_path"):
            needed.add("local")
        if fs.get("independent_examiner"):
            needed.add("local-independent-verify")
        if fs.get("child"):
            needed.add("isolated-child")
    covered = bool(needed & fams) if needed else True
    return {"valid_families": sorted(fams), "capable_families":
            sorted(needed), "covered": covered}


def score_trial(tid: str) -> dict[str, Any]:
    if (E6 / "pilot" / "task-bank" / tid).is_dir():
        td = E6 / "pilot" / "trials" / tid
    else:
        td = E6 / "trials" / tid
    label = jload(bank_dir(tid) / "private" / "label.json")
    distinctions = jload(td / "distinctions.json")["unresolved_distinctions"]
    applicability = jload(td / "applicability.json")
    ranking = jload(td / "candidate-ranking.json")
    selected = ranking["selected"]
    topo = jload(td / "candidates" / f"{selected}.json")
    calib = jload(td / "calibration.json")
    observed = jload(td / "observed-value.json")
    verification = jload(td / "verification.json")

    ds = score_distinctions(label, distinctions)
    ps = score_principles(label, applicability)
    feats = computed_features(td, topo, label)
    ts = score_topology(label, feats)
    cov = candidate_generation_coverage(label, td, td)

    failures = []
    if ds["critical_recall"] < 0.75:
        failures.append("S1_DISTINCTION_FAIL")
    if not ps["top2_hit"]:
        failures.append("S2_PRINCIPLE_FAIL")
    if not cov["covered"]:
        failures.append("S3_GENERATION_FAIL")
    if calib["calibration_error"]["utility_error"] > 0.25:
        failures.append("S4_PREDICTION_FAIL")
    if cov["covered"] and ts["verdict"] == "TOPOLOGY_INCORRECT":
        failures.append("S5_RANKING_FAIL")
    if observed["governance"]["violations"]:
        failures.append("S6_RUNTIME_FAIL")
        failures.append("FORMAL_GOVERNANCE_FAIL")
    if not verification.get("requirements"):
        failures.append("S7_OBSERVATION_FAIL")

    doc = {
        "trial_id": tid,
        "latent_class": label["latent_class"],
        "surface_domain": label.get("surface_domain", ""),
        "selected_topology": selected,
        "distinction_score": ds,
        "principle_score": ps,
        "topology_score": ts,
        "candidate_coverage": cov,
        "predicted_utility": calib["predicted_utility"],
        "observed_utility": calib["observed_utility"],
        "calibration_error": calib["calibration_error"],
        "task_verified": verification.get("task_verified"),
        "failure_tags": failures,
    }
    jdump(td / "trial-score.json", doc)
    return doc


if __name__ == "__main__":
    import sys
    print(jdump, score_trial(sys.argv[1]))
