"""Formal pre-execution validation of a candidate topology.

    validate_topology(topology, contract) -> FormalResult

Deterministic conjunction of the required checks:

    schema                          typed TopologyHypothesis document
    HarnessSpec                     boundary validation (cz.validate_spec)
    LTS compilation                 formal.compile_harness_spec
    authority                       promote only for gate; create only if
                                    contract grants it
    attenuation                     child contract <= governing contract
    budget                          declared model calls within contract
    reachability                    finite-LTS claims (see below)
    candidate/canonical separation  act nodes imply candidate-only authority
    freshness requirements          child creation declares fresh-launcher use
    proposal observability          propose-capable node precedes create/act
    protected laws                  no protected invariant is touched

Reachability is finite LTS reachability only (BFS over the compiled state
graph). Claims checked: a `complete` state is reachable; child topologies
have a return path to the parent (evidence can causally return); every act
node has a verify node causally downstream (verifier can observe the
candidate artifact); no actor other than `gate` can take a promote
transition. No claim of general program verification is made.

Only PASS candidates proceed; model output cannot override a FAIL.
"""
from __future__ import annotations
import importlib.util
import sys
from collections import deque
from pathlib import Path
from typing import Any

_CZROOT = Path(__file__).resolve().parents[1]
if str(_CZROOT) not in sys.path:
    sys.path.insert(0, str(_CZROOT))

from formal.attenuation import check_attenuation           # noqa: E402
from formal.model import FAIL, PASS, FormalResult, LTS     # noqa: E402
from formal.semantics import SemanticsError, compile_harness_spec  # noqa: E402

from .model import ModelValidationError, TopologyHypothesis  # noqa: E402

RELATION = "Candidate admissible under deterministic pre-execution checks"

PROTECTED_PATH_PREFIXES = (
    "experiment-3", "experiment-4", "experiment-4c", "experiment-5",
    "experiment-6",
    "state/experiment-", "state/formal-semantics-", "contracts/root_contract",
)

PROTECTED_LAWS = (
    "gate_monopoly", "historical_immutability", "model_output_not_authority",
    "attenuation", "freshness", "proposal_observability",
    "candidate_before_canonical", "formal_result_integrity",
)


def _load_cz():
    spec = importlib.util.spec_from_file_location("cz_boundary",
                                                  _CZROOT / "cz.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_CZ = None


def _cz():
    global _CZ
    if _CZ is None:
        _CZ = _load_cz()
    return _CZ


def reachable_states(lts: LTS) -> set[str]:
    seen = {lts.initial}
    dq = deque([lts.initial])
    adj: dict[str, list[str]] = {}
    for t in lts.transitions:
        adj.setdefault(t.source, []).append(t.target)
    while dq:
        s = dq.popleft()
        for nxt in adj.get(s, ()):
            if nxt not in seen:
                seen.add(nxt)
                dq.append(nxt)
    return seen


def label_reachable(lts: LTS, label: str, actor: str | None = None) -> bool:
    """Is a transition with `label` (and actor, if given) reachable?"""
    seen = reachable_states(lts)
    for t in lts.transitions:
        if t.source in seen and t.label == label:
            if actor is None or t.actor == actor or t.actor == "*":
                return True
    return False


def _downstream(spec: dict[str, Any], start: str) -> set[str]:
    adj: dict[str, list[str]] = {}
    for e in spec.get("edges", []):
        adj.setdefault(e["source"], []).append(e["target"])
    seen: set[str] = set()
    dq = deque([start])
    while dq:
        x = dq.popleft()
        for y in adj.get(x, ()):
            if y not in seen:
                seen.add(y)
                dq.append(y)
    return seen


def _upstream(spec: dict[str, Any], start: str) -> set[str]:
    radj: dict[str, list[str]] = {}
    for e in spec.get("edges", []):
        radj.setdefault(e["target"], []).append(e["source"])
    seen: set[str] = set()
    dq = deque([start])
    while dq:
        x = dq.popleft()
        for y in radj.get(x, ()):
            if y not in seen:
                seen.add(y)
                dq.append(y)
    return seen


def validate_topology(topology: TopologyHypothesis | dict[str, Any],
                      contract: dict[str, Any]) -> FormalResult:
    checks: dict[str, dict[str, Any]] = {}
    evidence: list[str] = []

    def record(name: str, ok: bool, why: str = "") -> bool:
        checks[name] = {"status": PASS if ok else FAIL, "detail": why}
        if ok:
            evidence.append(f"{name}: ok" + (f" ({why})" if why else ""))
        return ok

    # 1. schema
    try:
        if isinstance(topology, dict):
            topology = TopologyHypothesis.from_dict(topology)
        record("schema", True)
    except ModelValidationError as e:
        return _fail({"schema": {"status": FAIL, "detail": str(e)}}, [], None)

    spec = topology.harness_spec
    if not spec:
        return _fail({"harness_spec": {
            "status": FAIL, "detail": "no embedded harness spec"}}, [], topology)

    # 2. HarnessSpec boundary validation
    cz = _cz()
    try:
        cz.validate_spec(spec, contract)
        record("harness_spec", True)
    except cz.BoundaryViolation as e:
        record("harness_spec", False, str(e))
    except (KeyError, TypeError, ValueError) as e:
        record("harness_spec", False, f"malformed spec: {e}")

    # 3. LTS compilation
    lts = None
    if checks["harness_spec"]["status"] == PASS:
        try:
            lts = compile_harness_spec(spec, contract)
            record("lts_compilation", True,
                   f"{len(lts.states)} states, {len(lts.transitions)} "
                   "transitions")
        except (SemanticsError, ValueError) as e:
            record("lts_compilation", False, str(e))
    else:
        checks["lts_compilation"] = {"status": FAIL,
                                     "detail": "skipped: spec invalid"}

    nodes = {n["id"]: n for n in spec.get("nodes", [])}
    act_nodes = [nid for nid, n in nodes.items()
                 if n.get("primitive") == "act"]
    create_nodes = [nid for nid, n in nodes.items()
                    if n.get("primitive") == "create"]
    verify_nodes = [nid for nid, n in nodes.items()
                    if n.get("primitive") == "verify"]

    # 4. authority: promote gate-only; create contract-gated
    if lts is not None:
        non_gate_promote = [t for t in lts.transitions
                            if t.label == "promote" and t.actor != "gate"]
        record("authority",
               not non_gate_promote,
               "promote transitions restricted to actor 'gate'"
               if not non_gate_promote else
               f"non-gate promote transitions: {len(non_gate_promote)}")
    else:
        checks["authority"] = {"status": FAIL,
                               "detail": "skipped: no compiled LTS"}

    # 5. attenuation (only when the topology carries a child contract)
    if topology.child_contract:
        att = check_attenuation(contract, topology.child_contract)
        record("attenuation", att.status == PASS,
               "child contract attenuates" if att.status == PASS
               else str(att.counterexample))
    else:
        checks["attenuation"] = {
            "status": PASS,
            "detail": "no child contract declared" if not create_nodes else
                      "create node present without child contract: "
                      "attenuation deferred to realization-time validation"}

    # 6. budget
    declared = int(spec.get("max_model_calls", 0))
    limit = int(contract.get("max_model_calls", 0))
    record("budget", 1 <= declared <= limit,
           f"declared {declared} <= contract {limit}"
           if 1 <= declared <= limit else
           f"declared {declared} outside contract limit {limit}")

    # 7. reachability (finite LTS only)
    if lts is not None:
        problems = []
        if not label_reachable(lts, "complete"):
            problems.append("no reachable complete transition")
        for cn in create_nodes:
            down = _downstream(spec, cn)
            has_return = any(nodes.get(d, {}).get("primitive") == "return"
                             for d in down)
            if not (has_return and label_reachable(lts, "return")):
                problems.append(
                    f"create node {cn}: no return path — child evidence "
                    "cannot causally return to the parent")
        for an in act_nodes:
            down = _downstream(spec, an)
            if not any(v in down for v in verify_nodes):
                problems.append(
                    f"act node {an}: no verify node causally downstream — "
                    "verifier cannot observe the candidate artifact")
        record("reachability", not problems, "; ".join(problems) or
               "complete reachable; evidence/verify paths present")
    else:
        checks["reachability"] = {"status": FAIL,
                                  "detail": "skipped: no compiled LTS"}

    # 8. candidate/canonical separation
    if act_nodes:
        cwa = str(contract.get("canonical_write_authority", "")).lower()
        ok = (cwa == "" or cwa.startswith("none") or "gate" in cwa)
        record("candidate_canonical_separation", ok,
               "act nodes write candidate state; canonical only via gate"
               if ok else
               f"contract grants canonical write authority: {cwa!r}")
    else:
        record("candidate_canonical_separation", True, "no act nodes")

    # 9. freshness requirements
    if create_nodes:
        fresh = bool(spec.get("freshness", {}).get(
            "fresh_launcher_required", False))
        record("freshness", fresh,
               "child creation routes through the fresh launcher"
               if fresh else
               "create node present but spec does not require the fresh "
               "launcher")
    else:
        record("freshness", True, "no child creation")

    # 10. proposal observability
    problems = []
    for nid in create_nodes + act_nodes:
        up = _upstream(spec, nid)
        if not any(nodes.get(u, {}).get("primitive") == "hypothesize"
                   for u in up):
            problems.append(
                f"{nid}: no propose-capable (hypothesize) node upstream")
    record("proposal_observability", not problems,
           "; ".join(problems) or
           "every create/act node is preceded by an observable proposal")

    # 11. protected laws
    problems = []
    for n in spec.get("nodes", []):
        scope = n.get("filesystem_write_scope", []) or []
        for p in scope:
            norm = str(p)
            while norm.startswith("./"):
                norm = norm[2:]
            if norm.startswith(".creator-zero/"):
                norm = norm[len(".creator-zero/"):]
            if any(norm.startswith(pref) for pref in PROTECTED_PATH_PREFIXES):
                problems.append(f"node {n['id']} writes protected path {p}")
    cwa = str(contract.get("canonical_write_authority", "")).lower()
    if cwa and not (cwa.startswith("none") or "gate" in cwa):
        problems.append(
            f"contract canonical_write_authority bypasses the gate: {cwa!r}")
    record("protected_laws", not problems,
           "; ".join(problems) or "no protected invariant touched")

    failed = sorted(k for k, v in checks.items() if v["status"] != PASS)
    if failed:
        return _fail(checks, evidence, topology)
    return FormalResult(
        check="topology_validation", status=PASS,
        formal_relation=RELATION,
        evidence=evidence,
        assumptions=[
            "Reachability claims are finite-LTS reachability over the "
            "compiled governed state graph; no general program verification "
            "is claimed.",
            "Realization-time checks (child attenuation at creation, "
            "freshness of the actual launch) re-run at execution.",
        ],
        detail={"checks": checks,
                "topology_id": topology.topology_id})


def _fail(checks: dict[str, Any], evidence: list[str],
          topology: TopologyHypothesis | None) -> FormalResult:
    failed = sorted(k for k, v in checks.items() if v["status"] != PASS)
    return FormalResult(
        check="topology_validation", status=FAIL,
        formal_relation=RELATION,
        counterexample={"violation": "TOPOLOGY_VALIDATION_FAIL",
                        "failed_checks": failed,
                        "details": {k: checks[k]["detail"] for k in failed}},
        evidence=evidence,
        detail={"checks": checks,
                "topology_id": topology.topology_id if topology else None})
