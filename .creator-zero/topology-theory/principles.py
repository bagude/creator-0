"""Seed causal-design principles for Theta_H version 1.

Every seeded principle is SUPPORTED only by frozen, hash-pinned historical
Creator-0 artifacts (Experiments 3, 4, 4C, 5). No principle is seeded on
intuition alone; citations carry the exact sha256 of the frozen file so any
later mutation of the historical record is detectable during replay.

Precondition DSL (deterministically matched by abduct.py):
    feature:<name>   — applicable to a distinction whose features[<name>] is true
    topology:<name>  — generation-time structural constraint (mutation, creates_child)
    always           — applies to every task/topology
"""
from __future__ import annotations
from typing import Any

from .model import Principle, TheoryVersion
from .serialization import object_artifact_id

# path (non-authoritative metadata) -> pinned content sha256 (authoritative)
FROZEN = {
    "experiment-3/execution-ledger.jsonl":
        "bb561f728cc7e991266c9a33865894cfa528051dd825f4bcce40ceff415f3446",
    "experiment-3/final-harness.json":
        "6a8eec1bb5bc999d57e93c6d2f37c2ee53c2d90f58e940e713f12f9772a73fd0",
    "experiment-4/c1/execution-ledger.jsonl":
        "53657a2c59c4efa7e477c1aa751218225f419f5e22fc1e248e022e5eb206edec",
    "experiment-4/c1/final-harness.json":
        "9d00267fcbbd4aef4aee8732f3222605b9475897d41a63872ee9716430a33a19",
    "experiment-4/root-contract.json":
        "17bb0c888c1366d2ef49f884743027afec179c6fbed8b67cbf4e701fc1f4f382",
    "experiment-4/child-1-contract.json":
        "4a0d935115089ff5d77abdb225f25e1d11ed32a3fdc26dc9aa0bf153c905f90c",
    "experiment-4/child-2-contract.json":
        "4f6865fec22eada3eb73ed537ca23a0a1461abdb095501230fc75d7a883d04d9",
    "experiment-4/closure-correction/corrected-k3-attestation.json":
        "5ff1a8502cdd7e325d21c00af14e50f1579492219a08d08136d1bf603213e92a",
    "experiment-4c/witness-provenance.json":
        "0b75cf88949525a825dcc624b070a48cb2258bda022c00ec9f333eb29c830b38",
    "experiment-4c/formal/runtime-refinement-result.json":
        "2c189669fed569e639596114159c02c223f4499aaec2dfc34ad2594e7ccbf0f1",
    "experiment-4c/formal/weak-bisimulation-result.json":
        "137786bb22eeb93933a7fe0a1d1375555912480c7832aaba5f421edffdcd42ca",
    "experiment-4c/formal/negative-controls.json":
        "20dd7c581d7fa3f2947bac9276ab19462f1f5b22786c84dd1e8158a03bf21ea9",
    "experiment-5/harness-template.json":
        "9a7ddc83d5dd19908819a3172ae683c89347af57c668198dee30e1d5b6b5eb91",
    "experiment-5/trials/t-074/decision.json":
        "f7f77ce2c827adba4afc50d1f2f7cb935ecfaad94b6540fe650a44a1b494a928",
    "experiment-5/trials/t-074/result.json":
        "3ed63b5ddc27e61d884b0f22a5f6c136361924c1637e31437db03c4e9d361571",
    "experiment-5/trials/t-031/decision.json":
        "36611ccc00073203ca5430e5cd52481b79ecbe9d58f48f56b1ff3f677b90aaa5",
    "experiment-5/trials/t-031/child/launch-provenance.json":
        "9cb765b6b2c970188b2fa86e71cc5564d773c3dbc72a721b4d5caf489e4cbf05",
    "experiment-5/controls/shadow-a/launch-provenance.json":
        "32ab5c3ed5287d7b5daa5460560a14802b82e43912dccaa702780e1064480513",
    "experiment-5/preregistration.md":
        "56661be158def12c6488fbe5a77c9df5b55d527ca7b7f2676c4ac6bab1d1b6e8",
    "experiment-5/aggregate-results.json":
        "635621885c398b308228dc9bafabb39c5ab65a2f7b928cab663f57a6a60af185",
    "tests/formal/fixtures/e4-c1-inprocess-lts.json":
        "3ca6ae43222873e91b708e03f96c4d616e1c2b7da11b6783b40f88fcfee53d83",
    "tests/formal/fixtures/e4-c1-continuation-lts.json":
        "a861d89bd87c167faf406340ab307f5e481b2ac9bb07c74d0e42936853ea02ad",
}


def cite(*paths: str) -> list[dict[str, Any]]:
    out = []
    for p in paths:
        out.append({"frozen_artifact": p, "sha256": FROZEN[p]})
    return out


def seed_principles() -> list[Principle]:
    return [
        Principle(
            id="P-INDEPENDENCE",
            statement="When a distinction requires evidence that the current "
                      "session cannot produce without contaminating it (clean-"
                      "room, independent authorship, adversarial check), an "
                      "isolated fresh descendant or independent examiner adds "
                      "epistemic value that local work cannot.",
            status="SUPPORTED",
            scope=["topology-decision", "verification"],
            preconditions=["feature:requires_isolation",
                           "feature:contamination"],
            predicted_topology_effects=[
                "adds an isolated fresh child (or independent verifier) node",
                "child evidence is novel, not a duplicate of parent evidence",
                "child resolves the assigned distinctions"],
            supporting_evidence=cite(
                "experiment-5/trials/t-031/decision.json",
                "experiment-5/trials/t-031/child/launch-provenance.json",
                "experiment-5/aggregate-results.json",
                "experiment-3/execution-ledger.jsonl"),
        ),
        Principle(
            id="P-LOCALITY",
            statement="When every unresolved distinction is resolvable from "
                      "evidence already inside the governed boundary, no "
                      "descendant is epistemically justified; a forced child "
                      "duplicates local evidence.",
            status="SUPPORTED",
            scope=["topology-decision"],
            preconditions=["feature:locally_resolvable"],
            predicted_topology_effects=[
                "no child creation",
                "local resolve/verify chain resolves all distinctions",
                "a counterfactual forced child would duplicate parent evidence"],
            supporting_evidence=cite(
                "experiment-5/trials/t-074/decision.json",
                "experiment-5/trials/t-074/result.json",
                "experiment-5/controls/shadow-a/launch-provenance.json",
                "experiment-5/aggregate-results.json"),
        ),
        Principle(
            id="P-VERIFY",
            statement="Any topology holding mutation capability must contain "
                      "a verification node causally after the mutation; model "
                      "self-checks are non-authoritative.",
            status="SUPPORTED",
            scope=["governance", "topology-structure"],
            preconditions=["topology:mutation"],
            predicted_topology_effects=[
                "verify node downstream of every act node",
                "verification can observe the candidate artifact"],
            supporting_evidence=cite(
                "experiment-3/final-harness.json",
                "experiment-3/execution-ledger.jsonl",
                "experiment-4/root-contract.json"),
        ),
        Principle(
            id="P-AUTHORITY-SEPARATION",
            statement="Model output is a proposal, never authorization: no "
                      "Actor other than the deterministic Gate can reach "
                      "canonical promotion, and rejection by a deterministic "
                      "check cannot be overridden by model output.",
            status="SUPPORTED",
            scope=["governance"],
            preconditions=["always"],
            predicted_topology_effects=[
                "promote transitions exist only for the gate actor",
                "act nodes write candidate state only"],
            supporting_evidence=cite(
                "experiment-3/execution-ledger.jsonl",
                "experiment-4/root-contract.json",
                "experiment-4c/formal/negative-controls.json"),
        ),
        Principle(
            id="P-PROPOSAL-OBSERVABILITY",
            statement="Every capability-bearing artifact (decision, child "
                      "bundle, candidate patch) must cross an observable "
                      "propose transition before realization; return cannot "
                      "substitute for propose.",
            status="SUPPORTED",
            scope=["governance", "topology-structure"],
            preconditions=["feature:capability_bearing_artifact",
                           "topology:creates_child", "topology:mutation"],
            predicted_topology_effects=[
                "a hypothesize/propose node precedes every create or act node"],
            supporting_evidence=cite(
                "experiment-4c/witness-provenance.json",
                "experiment-4c/formal/negative-controls.json",
                "experiment-5/harness-template.json"),
        ),
        Principle(
            id="P-FRESHNESS",
            statement="A descendant session must be provably fresh: sanitized "
                      "environment, explicit new session identity, and — for "
                      "executed sessions — stream-confirmed session id.",
            status="SUPPORTED",
            scope=["child-creation"],
            preconditions=["topology:creates_child"],
            predicted_topology_effects=[
                "child creation routes through the deterministic fresh launcher",
                "launch provenance persists sanitization and identity evidence"],
            supporting_evidence=cite(
                "experiment-4c/witness-provenance.json",
                "experiment-5/trials/t-031/child/launch-provenance.json",
                "experiment-5/preregistration.md"),
        ),
        Principle(
            id="P-STATE-MEDIATED-CONTINUITY",
            statement="Governed continuation across process/session death is "
                      "behaviorally equivalent (weak bisimulation) to in-"
                      "process execution when all governed state is "
                      "externalized and reconstructed.",
            status="SUPPORTED",
            scope=["continuity"],
            preconditions=["feature:spans_sessions"],
            predicted_topology_effects=[
                "persist/reconstruct transitions around session boundaries",
                "continuation trace weakly bisimilar to in-process trace"],
            supporting_evidence=cite(
                "experiment-4/c1/execution-ledger.jsonl",
                "tests/formal/fixtures/e4-c1-inprocess-lts.json",
                "tests/formal/fixtures/e4-c1-continuation-lts.json",
                "experiment-4c/formal/weak-bisimulation-result.json"),
        ),
        Principle(
            id="P-MINIMALITY",
            statement="The admissible topology is the minimum causal "
                      "organization that resolves the unresolved "
                      "distinctions; nodes and recursion beyond that add "
                      "cost and redundancy, not epistemic value.",
            status="SUPPORTED",
            scope=["topology-decision", "economics"],
            preconditions=["always"],
            predicted_topology_effects=[
                "candidate ranking penalizes node count and redundancy",
                "no recursion added merely to demonstrate recursion"],
            supporting_evidence=cite(
                "experiment-5/controls/shadow-a/launch-provenance.json",
                "experiment-5/aggregate-results.json"),
        ),
        Principle(
            id="P-ATTENUATION",
            statement="Every descendant contract is monotonically attenuated: "
                      "no authority axis may increase from parent to child, "
                      "checked locally at every creation.",
            status="SUPPORTED",
            scope=["child-creation", "governance"],
            preconditions=["topology:creates_child"],
            predicted_topology_effects=[
                "child contract passes check_attenuation against its parent"],
            supporting_evidence=cite(
                "experiment-4/root-contract.json",
                "experiment-4/child-1-contract.json",
                "experiment-4/child-2-contract.json",
                "experiment-4/closure-correction/corrected-k3-attestation.json"),
        ),
    ]


SEED_PRINCIPLE_IDS = tuple(p.id for p in seed_principles())


def build_seed_theory(provenance: dict[str, Any] | None = None) -> TheoryVersion:
    """Theta_H version 1: seed principles + provenance, no revisions yet."""
    principles = [p.to_dict() for p in seed_principles()]
    theory = TheoryVersion(
        version=1,
        principles=principles,
        revision_graph=[],
        evidence_log_length=0,
        predecessor_hash="",
        provenance=provenance or {
            "seeded_from": "frozen Experiment 3/4/4C/5 artifacts",
            "seed_rule": "only principles supported by pinned prior "
                         "Creator-0 evidence are seeded",
        },
        status="CANDIDATE",
    )
    return theory


def theory_hash(theory: TheoryVersion) -> str:
    return object_artifact_id(
        theory.to_dict(),
        f"creator-0/topology-theory/theta-v{theory.version}")
