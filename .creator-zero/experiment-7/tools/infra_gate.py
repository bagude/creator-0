"""E7 infrastructure-patch verification driver (root-side, deterministic).

Assembles the promoted self_modify gate's required inputs for the
candidate/e7-infra patch:

    attenuation          K-E7-infra contract vs root contract
    refinement           infra-build ledger vs compiled infra harness
    tests_existing/new   full suite results in the candidate worktree
    historical_replay    theta-v1 seed theory vs v0.1 corpus + frozen E6 cases
    protected_laws       candidate patch paths vs protected history (E6 incl.)
    frozen_trees         no modification/deletion under protected trees
    independent_verifier collected fresh-session verification (info-only)
    patch_manifest       exact artifact identity of every changed file

Usage:
    python3 tools/infra_gate.py prepare      # everything except verifier+gate
    python3 tools/infra_gate.py gate         # after the verifier session

The gate itself is the promoted deterministic self_modify.gate() running
FROM THE CANDIDATE WORKTREE code (the patch does not alter gate semantics;
the conjunction and PASS shape are byte-compatible with v0.1).
"""
from __future__ import annotations
import json
import subprocess
import sys
from pathlib import Path

E7 = Path(__file__).resolve().parents[1]
CZROOT = E7.parent
REPO = CZROOT.parent
W = Path("/tmp/claude-0/-home-user-creator-0/"
         "87cd2a2d-a4f9-585b-836f-2648df7a6284/scratchpad/e7-infra")
WCZ = W / ".creator-zero"
OUT = E7 / "infrastructure"
BASE_REF = "de82043"          # Phase A freeze commit (candidate branch base)

sys.path.insert(0, str(WCZ))


def jdump(p: Path, obj) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n",
                 encoding="utf-8")


def jload(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def tt(name: str):
    import importlib
    import importlib.util
    if "cz_topology_theory" not in sys.modules:
        spec = importlib.util.spec_from_file_location(
            "cz_topology_theory", WCZ / "topology-theory" / "__init__.py",
            submodule_search_locations=[str(WCZ / "topology-theory")])
        pkg = importlib.util.module_from_spec(spec)
        sys.modules["cz_topology_theory"] = pkg
        spec.loader.exec_module(pkg)
    return importlib.import_module(f"cz_topology_theory.{name}")


INFRA_CONTRACT = {
    "contract_id": "K-E7-infra",
    "version": "0.1-e7",
    "description": "Envelope for the E7 infrastructure self-modification: "
                   "candidate-only mutation, one information-only fresh "
                   "verifier session, gate-only promotion.",
    "allowed_primitives": ["observe", "hypothesize", "act", "verify",
                           "create", "return"],
    "allowed_relations": ["observe", "consult", "request_response",
                          "verify", "authorize", "create", "return"],
    "allowed_tools": ["Read", "Write", "Bash", "Edit", "Grep", "Glob"],
    "max_children": 1,
    "max_depth": 1,
    "max_model_calls": 4,
    "may_create_creator": True,
    "may_realize_creation": True,
    "required_primitives_for_mutation": ["verify"],
    "canonical_write_authority": "none (gate only)",
}

INFRA_HARNESS = {
    "task_id": "e7-infra",
    "goal": "Implement and verify the E7 lineage/admissibility/revision "
            "infrastructure in an isolated candidate worktree; promote only "
            "under the deterministic gate.",
    "max_depth": 1,
    "max_model_calls": 4,
    "nodes": [
        {"id": "propose-patch", "primitive": "hypothesize",
         "tools": ["Write"], "can_create": False,
         "instructions": "Observable proposal: preregistration §13 + typed "
                         "proposal document."},
        {"id": "implement-candidate", "primitive": "act",
         "tools": ["Read", "Write", "Edit"], "can_create": False,
         "instructions": "Mutate only inside the candidate worktree."},
        {"id": "verify-tests", "primitive": "verify",
         "tools": ["Bash", "Read"], "can_create": False,
         "instructions": "Full existing + new test suites."},
        {"id": "verify-replay", "primitive": "verify",
         "tools": ["Read"], "can_create": False,
         "instructions": "Historical replay incl. frozen E6 cases."},
        {"id": "launch-verifier", "primitive": "create",
         "tools": ["Bash"], "can_create": True,
         "instructions": "Fresh information-only verifier via the "
                         "deterministic launcher."},
        {"id": "verifier-return", "primitive": "return",
         "tools": ["Read"], "can_create": False,
         "instructions": "Collect the verifier's serialized report."},
        {"id": "gate-decision", "primitive": "verify",
         "tools": ["Read"], "can_create": False,
         "instructions": "Deterministic gate over serialized inputs."},
    ],
    "edges": [
        {"source": "propose-patch", "target": "implement-candidate",
         "relation": "authorize", "requires_response": False,
         "response_changes_parent_state": False,
         "transfers_authority": False},
        {"source": "implement-candidate", "target": "verify-tests",
         "relation": "verify", "requires_response": True,
         "response_changes_parent_state": False,
         "transfers_authority": False},
        {"source": "verify-tests", "target": "verify-replay",
         "relation": "verify", "requires_response": True,
         "response_changes_parent_state": False,
         "transfers_authority": False},
        {"source": "verify-replay", "target": "launch-verifier",
         "relation": "authorize", "requires_response": False,
         "response_changes_parent_state": False,
         "transfers_authority": False},
        {"source": "launch-verifier", "target": "verifier-return",
         "relation": "request_response", "requires_response": True,
         "response_changes_parent_state": True,
         "transfers_authority": False},
        {"source": "verifier-return", "target": "gate-decision",
         "relation": "verify", "requires_response": True,
         "response_changes_parent_state": False,
         "transfers_authority": False},
    ],
    "freshness": {"fresh_launcher_required": True},
}


def ledger_event(eid: str, label: str, node: str, refs: list[str],
                 note: str = "") -> dict:
    from datetime import datetime, timezone
    return {"event_id": eid, "label": label, "actor": f"node:{node}",
            "timestamp": datetime.now(timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"),
            "artifact_refs": refs,
            "metadata": {"completes_node": node,
                         **({"note": note} if note else {})}}


def append_ledger(events: list[dict]) -> None:
    p = OUT / "infra-ledger.jsonl"
    existing = set()
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip():
                existing.add(json.loads(line)["event_id"])
    with p.open("a", encoding="utf-8") as f:
        for ev in events:
            if ev["event_id"] not in existing:
                f.write(json.dumps(ev) + "\n")


def run_tests() -> dict:
    out = {}
    suites = {
        "topology_theory": ["-m", "unittest", "discover", "-s",
                            "tests/topology_theory", "-p", "test_*.py"],
        "formal": ["-m", "unittest", "discover", "-s", "tests/formal",
                   "-p", "test_*.py"],
        "experiment5": ["-m", "unittest", "discover", "-s",
                        "tests/experiment5", "-p", "test_*.py"],
        "creator_zero": ["-m", "unittest", "tests.test_creator_zero"],
    }
    for name, args in suites.items():
        r = subprocess.run([sys.executable, *args], cwd=WCZ,
                           capture_output=True, text=True)
        tail = (r.stderr or r.stdout).strip().splitlines()[-3:]
        out[name] = {"returncode": r.returncode,
                     "ok": r.returncode == 0, "tail": tail}
    return out


def cmd_prepare() -> None:
    OUT.mkdir(exist_ok=True)
    sm = tt("self_modify")

    # observable proposal (content frozen in preregistration §13)
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=W,
                          capture_output=True, text=True).stdout.strip()
    proposal = {
        "artifact": "E7 infrastructure self-modification proposal",
        "proposal_source": ".creator-zero/experiment-7/preregistration.md "
                           "§13 (frozen at Phase A, before the candidate "
                           "worktree existed)",
        "candidate_branch": "candidate/e7-infra",
        "candidate_base": BASE_REF,
        "candidate_head": head,
        "scope": ["lineage/", "topology-theory/{model,validate,self_modify,"
                  "__init__}.py", "topology-theory/{admissibility,ingest,"
                  "governance,theory_gate,generate2,revise2,predict2}.py",
                  "topology-theory/replay-corpus-e6.json",
                  "tests/topology_theory/test_{lineage,evidence_v2,"
                  "admissibility_grammar_v2,revision_governance_v2}.py"],
        "canonical_write_before_gate": False,
    }
    jdump(OUT / "self-modification-proposal.json", proposal)
    jdump(OUT / "infra-contract.json", INFRA_CONTRACT)
    jdump(OUT / "infra-harness.json", INFRA_HARNESS)
    append_ledger([
        ledger_event("e7i-propose", "propose", "propose-patch",
                     ["experiment-7/infrastructure/"
                      "self-modification-proposal.json",
                      "experiment-7/preregistration.md"]),
        ledger_event("e7i-implement", "act", "implement-candidate",
                     [f"candidate/e7-infra@{head}"],
                     "all mutations inside the candidate worktree"),
    ])

    sys.path.insert(0, str(CZROOT))
    import formal

    # attenuation: K-E7-infra <= root contract
    root_contract = jload(CZROOT / "contracts" / "root_contract.json")
    att = formal.check_attenuation(root_contract, INFRA_CONTRACT)
    jdump(OUT / "attenuation.json", att.to_dict())

    # compile the infra harness (structural validity under the contract)
    lts = formal.compile_harness_spec(INFRA_HARNESS, INFRA_CONTRACT)
    from formal.serialization import lts_to_json
    (OUT / "infra-lts.json").write_text(lts_to_json(lts), encoding="utf-8")

    # tests
    tests = run_tests()
    ok_all = all(v["ok"] for v in tests.values())
    jdump(OUT / "test-results.json", {
        "check": "tests", "status": "PASS" if ok_all else "FAIL",
        "suites": tests})
    append_ledger([ledger_event(
        "e7i-tests", "verify", "verify-tests",
        ["experiment-7/infrastructure/test-results.json"],
        "existing + new suites in the candidate worktree")])

    # historical replay: seed theory vs v0.1 corpus + frozen E6 cases
    TT_replay = tt("replay")
    TT_principles = tt("principles")
    theory = TT_principles.build_seed_theory()
    cases = TT_replay.load_replay_corpus(
        WCZ / "topology-theory" / "replay-corpus.json")
    cases += TT_replay.load_replay_corpus(
        WCZ / "topology-theory" / "replay-corpus-e6.json")
    rep = TT_replay.replay(theory, cases, repo_root=WCZ)
    jdump(OUT / "historical-replay.json", rep.to_dict())
    append_ledger([ledger_event(
        "e7i-replay", "verify", "verify-replay",
        ["experiment-7/infrastructure/historical-replay.json"])])

    # patch manifest + protected laws + frozen trees
    manifest = sm.build_patch_manifest(W, BASE_REF, "HEAD",
                                       provenance="creator-0/e7-infra")
    jdump(OUT / "candidate-patch-manifest.json", manifest)
    paths = [f["path"] for f in manifest["files"]]
    jdump(OUT / "protected-laws.json", sm.check_protected_laws(paths))
    mutated = []
    for tree in (".creator-zero/experiment-3", ".creator-zero/experiment-4",
                 ".creator-zero/experiment-4c", ".creator-zero/experiment-5",
                 ".creator-zero/experiment-6",
                 ".creator-zero/state/experiment-6.json",
                 ".creator-zero/contracts"):
        r = subprocess.run(["git", "diff", "--diff-filter=MD", "--name-only",
                            BASE_REF, "HEAD", "--", tree], cwd=W,
                           capture_output=True, text=True)
        mutated.extend(r.stdout.strip().splitlines())
    jdump(OUT / "frozen-trees.json", {
        "check": "frozen_trees", "status": "FAIL" if mutated else "PASS",
        "mutations": mutated})
    print("prepare done:",
          "attenuation", att.status,
          "| tests", "PASS" if ok_all else "FAIL",
          "| replay", f"c={rep.compatible} x={rep.contradicted} "
                      f"i={rep.indeterminate}",
          "| protected", jload(OUT / 'protected-laws.json')["status"],
          "| frozen", "FAIL" if mutated else "PASS",
          "| files", manifest["file_count"])


def cmd_gate() -> None:
    sm = tt("self_modify")
    verifier = jload(OUT / "independent-verification.json")
    inputs = {
        "attenuation": jload(OUT / "attenuation.json"),
        "refinement": jload(OUT / "refinement.json"),
        "tests_existing": {"status": jload(OUT / "test-results.json")
                           ["status"]},
        "tests_new": {"status": jload(OUT / "test-results.json")["status"]},
        "historical_replay": jload(OUT / "historical-replay.json"),
        "protected_laws": jload(OUT / "protected-laws.json"),
        "frozen_trees": jload(OUT / "frozen-trees.json"),
        "independent_verifier": verifier,
        "patch_manifest": jload(OUT / "candidate-patch-manifest.json"),
    }
    gate_result = sm.gate(inputs)
    jdump(OUT / "gate-inputs.json", {k: {"status": sm._input_status(v)}
                                     for k, v in inputs.items()})
    jdump(OUT / "gate-result.json", gate_result)
    if gate_result["status"] == "PASS":
        auth = sm.authorize_promotion(gate_result)
        jdump(OUT / "promotion-authorization.json", auth)
    append_ledger([ledger_event(
        "e7i-gate", "verify", "gate-decision",
        ["experiment-7/infrastructure/gate-result.json"])])
    print("gate:", gate_result["status"])


def cmd_refinement() -> None:
    """Check the infra ledger against the compiled harness (after the
    verifier events are appended)."""
    sys.path.insert(0, str(CZROOT))
    import formal
    from formal.trace import parse_runtime_ledger
    lts = formal.compile_harness_spec(INFRA_HARNESS, INFRA_CONTRACT)
    trace = parse_runtime_ledger(OUT / "infra-ledger.jsonl", strict=False)
    res = formal.check_refinement(trace, lts, require_completion=False)
    jdump(OUT / "refinement.json", res.to_dict())
    print("refinement:", res.status)


def main() -> None:
    {"prepare": cmd_prepare, "gate": cmd_gate,
     "refinement": cmd_refinement}[sys.argv[1]]()


if __name__ == "__main__":
    main()
