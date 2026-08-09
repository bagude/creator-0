"""Experiment 7 Phase A: freeze and verify the Experiment 6 lineage checkpoint.

Standalone deterministic bootstrap. The reusable lineage subsystem
(.creator-zero/lineage/) is built later through the governed candidate path;
this script exists so the checkpoint can be created and verified BEFORE any
candidate implementation or theory revision, as Phase A requires. Its output
schema is the schema the promoted lineage package must re-verify byte-for-byte.

    python3 tools/phase_a.py create   -> base-checkpoint.json
    python3 tools/phase_a.py verify   -> checkpoint-verification.json

Any pinned-identity mismatch exits nonzero with LINEAGE_RESUME_FAIL. No model
input reaches any check.
"""
from __future__ import annotations
import hashlib
import json
import subprocess
import sys
from pathlib import Path

E7 = Path(__file__).resolve().parents[1]
CZROOT = E7.parent
REPO = CZROOT.parent

# ---- pinned parent identities (Experiment 6 frozen checkpoint) -------------
PARENT_COMMIT = "bd0cf91e455393d3d601070e5022c565d9ed9ed1"
PARENT_TREE = "3d067bdd3facff3f9e23d4523979cc795677bbb8"
PARENT_BRANCH = "claude/new-session-ltyh1o"
PARENT_EXPERIMENT = "experiment-6"
PARENT_RESULT = "LATENT_TOPOLOGY_ECONOMICS_FAIL"

# protected historical trees at the checkpoint (pre-E7 protected law state)
PROTECTED_PREFIXES = [
    ".creator-zero/experiment-3/",
    ".creator-zero/experiment-4/",
    ".creator-zero/experiment-4c/",
    ".creator-zero/experiment-5/",
]
PROTECTED_FILES = [
    ".creator-zero/state/experiment-2.json",
    ".creator-zero/state/experiment-3.json",
    ".creator-zero/state/experiment-4.json",
    ".creator-zero/state/experiment-4c.json",
    ".creator-zero/state/experiment-5.json",
    ".creator-zero/state/formal-semantics-v0.1.json",
    ".creator-zero/contracts/root_contract.json",
]

FAILURE_CODES = ("COMMIT_MISMATCH", "TREE_MISMATCH", "THEORY_MISMATCH",
                 "EVIDENCE_HEAD_MISMATCH", "ROOT_CONTRACT_MISMATCH",
                 "FORMAL_KERNEL_MISMATCH", "EXPERIMENT_STATE_MISMATCH",
                 "PROTECTED_MANIFEST_MISMATCH")


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def canonical_dumps(obj) -> str:
    return json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True,
                          text=True, check=True).stdout.strip()


def tt_mod(name: str):
    import importlib, importlib.util
    pkg_dir = CZROOT / "topology-theory"
    if "cz_topology_theory" not in sys.modules:
        spec = importlib.util.spec_from_file_location(
            "cz_topology_theory", pkg_dir / "__init__.py",
            submodule_search_locations=[str(pkg_dir)])
        pkg = importlib.util.module_from_spec(spec)
        sys.modules["cz_topology_theory"] = pkg
        spec.loader.exec_module(pkg)
    return importlib.import_module(f"cz_topology_theory.{name}")


def protected_manifest() -> dict:
    return {"protected_prefixes": PROTECTED_PREFIXES,
            "protected_files": PROTECTED_FILES}


def protected_manifest_sha256() -> str:
    return hashlib.sha256(json.dumps(protected_manifest(), sort_keys=True,
                          separators=(",", ":")).encode()).hexdigest()


def build_checkpoint() -> dict:
    store_mod = tt_mod("theory_store")
    store = store_mod.TheoryStore(CZROOT / "state" / "topology-theory")
    theory = store.load(1)
    length, head = store.evidence_head()
    state_path = ".creator-zero/state/experiment-6.json"
    doc = {
        "artifact": "Experiment 7 base lineage checkpoint (L6)",
        "schema_version": "lineage-checkpoint-v1",
        "commit_sha": PARENT_COMMIT,
        "tree_sha": PARENT_TREE,
        "source_branch": PARENT_BRANCH,
        "theory_version": theory.version,
        "theory_artifact_id": store.version_hash(1),
        "theory_status": theory.status,
        "evidence_length": length,
        "evidence_head_hash": head,
        "root_contract_sha256": sha256_file(
            CZROOT / "contracts" / "root_contract.json"),
        "formal_kernel_state_artifact_id": sha256_file(
            CZROOT / "state" / "formal-semantics-v0.1.json"),
        "protected_manifest_sha256": protected_manifest_sha256(),
        "protected_manifest": protected_manifest(),
        "experiment_id": PARENT_EXPERIMENT,
        "experiment_state_path": state_path,
        "experiment_state_sha256": sha256_file(REPO / state_path),
        "experiment_result": PARENT_RESULT,
        "parent_checkpoint_id": None,
        "provenance": {
            "created_by": "experiment-7 phase A deterministic bootstrap",
            "parent_experiment_base_state":
                ".creator-zero/experiment-6/base-state.json",
            "e6_theory_evidence_source": {
                "path": ".creator-zero/experiment-6/"
                        "theory-evidence-events.jsonl",
                "sha256": sha256_file(
                    E7.parent / "experiment-6" /
                    "theory-evidence-events.jsonl"),
            },
            "prior_state_manifests": {
                ".creator-zero/state/topology-theory-v0.1.json": sha256_file(
                    CZROOT / "state" / "topology-theory-v0.1.json"),
            },
        },
    }
    body = dict(doc)
    body.pop("checkpoint_id", None)
    cid = hashlib.sha256(
        (json.dumps(body, sort_keys=True, separators=(",", ":"))
         + "\x00creator-0/lineage/checkpoint").encode()).hexdigest()
    doc["checkpoint_id"] = "sha256:" + cid
    return doc


def verify(cp: dict) -> dict:
    checks = {}

    def rec(name: str, code: str, ok: bool, why: str):
        checks[name] = {"status": "PASS" if ok else "FAIL",
                        "failure_code": None if ok else code, "detail": why}

    # v_C: commit exists, is the branch tip, and is an ancestor of HEAD
    commit_ok = True
    try:
        typ = git("cat-file", "-t", cp["commit_sha"])
        commit_ok = (typ == "commit")
    except subprocess.CalledProcessError:
        commit_ok = False
    remote_tip = ""
    try:
        remote_tip = git("rev-parse", f"origin/{cp['source_branch']}")
    except subprocess.CalledProcessError:
        pass
    ancestry = subprocess.run(
        ["git", "merge-base", "--is-ancestor", cp["commit_sha"], "HEAD"],
        cwd=REPO).returncode == 0
    rec("commit", "COMMIT_MISMATCH",
        commit_ok and remote_tip == cp["commit_sha"] and ancestry,
        f"commit object present={commit_ok}; origin/{cp['source_branch']}="
        f"{remote_tip[:12]}; ancestor_of_HEAD={ancestry}")

    # v_T: tree of the pinned commit matches the pinned tree
    tree = ""
    try:
        tree = git("rev-parse", f"{cp['commit_sha']}^{{tree}}")
    except subprocess.CalledProcessError:
        pass
    rec("tree", "TREE_MISMATCH", tree == cp["tree_sha"],
        f"tree({cp['commit_sha'][:12]})={tree[:12]} vs pinned "
        f"{cp['tree_sha'][:12]}")

    # v_Theta: theory version identity
    store_mod = tt_mod("theory_store")
    store = store_mod.TheoryStore(CZROOT / "state" / "topology-theory")
    try:
        theory = store.load(cp["theory_version"])
        th_hash = store.version_hash(cp["theory_version"])
        ok = (theory.status == cp["theory_status"]
              and th_hash == cp["theory_artifact_id"])
        rec("theory", "THEORY_MISMATCH", ok,
            f"theta-v{cp['theory_version']} status={theory.status} "
            f"hash={th_hash[:20]}...")
    except Exception as e:
        rec("theory", "THEORY_MISMATCH", False, str(e))

    # v_E: evidence head
    length, head = store.evidence_head()
    chain = store.verify_append_only()
    rec("evidence_head", "EVIDENCE_HEAD_MISMATCH",
        length == cp["evidence_length"] and head == cp["evidence_head_hash"]
        and chain["append_only_intact"],
        f"store head=({length},{head!r}); pinned=({cp['evidence_length']},"
        f"{cp['evidence_head_hash']!r}); chain_intact="
        f"{chain['append_only_intact']}")

    # v_G: root contract
    rc = sha256_file(CZROOT / "contracts" / "root_contract.json")
    rec("root_contract", "ROOT_CONTRACT_MISMATCH",
        rc == cp["root_contract_sha256"], f"sha256={rc[:16]}...")

    # v_K: formal kernel state manifest
    fk = sha256_file(CZROOT / "state" / "formal-semantics-v0.1.json")
    rec("formal_kernel", "FORMAL_KERNEL_MISMATCH",
        fk == cp["formal_kernel_state_artifact_id"], f"sha256={fk[:16]}...")

    # v_S: experiment state manifest
    es = sha256_file(REPO / cp["experiment_state_path"])
    rec("experiment_state", "EXPERIMENT_STATE_MISMATCH",
        es == cp["experiment_state_sha256"]
        and json.loads((REPO / cp["experiment_state_path"]).read_text())
        ["result"] == cp["experiment_result"],
        f"sha256={es[:16]}...; result pinned={cp['experiment_result']}")

    # protected manifest + protected trees byte-identical to pinned commit
    pm = protected_manifest_sha256()
    mutations = []
    for tree_prefix in [p.rstrip("/") for p in
                        cp["protected_manifest"]["protected_prefixes"]] + \
            cp["protected_manifest"]["protected_files"]:
        out = git("diff", "--diff-filter=MD", "--name-only",
                  cp["commit_sha"], "HEAD", "--", tree_prefix)
        mutations.extend(out.splitlines())
    rec("protected_manifest", "PROTECTED_MANIFEST_MISMATCH",
        pm == cp["protected_manifest_sha256"] and not mutations,
        f"manifest sha match={pm == cp['protected_manifest_sha256']}; "
        f"historical mutations={mutations}")

    # E6 evidence-source pin (provenance-level; import re-verifies later)
    src = cp["provenance"]["e6_theory_evidence_source"]
    got = sha256_file(REPO / src["path"])
    checks["e6_evidence_source"] = {
        "status": "PASS" if got == src["sha256"] else "FAIL",
        "failure_code": None if got == src["sha256"]
        else "EVIDENCE_SOURCE_MISMATCH",
        "detail": f"sha256={got[:16]}... vs pinned {src['sha256'][:16]}..."}

    failed = sorted(k for k, v in checks.items() if v["status"] != "PASS")
    return {
        "artifact": "Experiment 7 checkpoint verification (VerifyCheckpoint)",
        "checkpoint_id": cp["checkpoint_id"],
        "formal_relation": "Verify(L6,X) = v_C ^ v_T ^ v_Theta ^ v_E ^ v_K "
                           "^ v_G ^ v_S (conjunction; any mismatch is "
                           "LINEAGE_RESUME_FAIL)",
        "checks": checks,
        "status": "PASS" if not failed else "FAIL",
        "result": None if not failed else "LINEAGE_RESUME_FAIL",
        "failed": failed,
    }


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "verify"
    cp_path = E7 / "base-checkpoint.json"
    if cmd == "create":
        if cp_path.exists():
            print("base-checkpoint.json already exists; checkpoint is "
                  "write-once", file=sys.stderr)
            return 1
        doc = build_checkpoint()
        cp_path.write_text(canonical_dumps(doc), encoding="utf-8")
        print(f"checkpoint created: {doc['checkpoint_id']}")
        return 0
    cp = json.loads(cp_path.read_text(encoding="utf-8"))
    res = verify(cp)
    (E7 / "checkpoint-verification.json").write_text(
        canonical_dumps(res), encoding="utf-8")
    print(f"checkpoint verification: {res['status']}")
    for k, v in sorted(res["checks"].items()):
        print(f"  {k}: {v['status']} ({v['detail']})")
    if res["status"] != "PASS":
        print("LINEAGE_RESUME_FAIL", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
