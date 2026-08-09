"""Deterministic checkpoint verification.

    Verify(L,X) = v_C ∧ v_T ∧ v_Θ ∧ v_E ∧ v_K ∧ v_G ∧ v_S

Idempotent: verification reads state and writes nothing. Every clause
reports a typed failure code from FAILURE_CODES; any failure maps the whole
result to LINEAGE_RESUME_FAIL. Model output cannot override any clause.
"""
from __future__ import annotations
import json
import subprocess
from pathlib import Path
from typing import Any

from ._common import git, git_ok, protected_manifest_sha256, sha256_file, \
    tt_mod
from .model import CheckpointResult, LineageCheckpoint


def verify_checkpoint(repo_root: str | Path,
                      cp: LineageCheckpoint | dict[str, Any],
                      ) -> CheckpointResult:
    if isinstance(cp, dict):
        cp = LineageCheckpoint.from_dict(cp)
    root = Path(repo_root)
    czroot = root / ".creator-zero"
    checks: dict[str, dict[str, Any]] = {}

    def rec(name: str, code: str, ok: bool, why: str) -> None:
        checks[name] = {"status": "PASS" if ok else "FAIL",
                        "failure_code": None if ok else code, "detail": why}

    # v_C — the pinned commit exists and is an ancestor of the current HEAD
    commit_ok = False
    try:
        commit_ok = git(root, "cat-file", "-t", cp.commit_sha) == "commit"
    except subprocess.CalledProcessError:
        pass
    ancestry = git_ok(root, "merge-base", "--is-ancestor", cp.commit_sha,
                      "HEAD")
    rec("commit", "COMMIT_MISMATCH", commit_ok and ancestry,
        f"commit present={commit_ok}; ancestor_of_HEAD={ancestry}")

    # v_T — the pinned commit's tree matches the pinned tree
    tree = ""
    if commit_ok:
        tree = git(root, "rev-parse", f"{cp.commit_sha}^{{tree}}")
    rec("tree", "TREE_MISMATCH", tree == cp.tree_sha,
        f"tree={tree[:12]} vs pinned {cp.tree_sha[:12]}")

    # v_Θ — theory version identity and status
    store_mod = tt_mod("theory_store")
    store = store_mod.TheoryStore(czroot / "state" / "topology-theory")
    try:
        theory = store.load(cp.theory_version)
        th_hash = store.version_hash(cp.theory_version)
        rec("theory", "THEORY_MISMATCH",
            theory.status == cp.theory_status
            and th_hash == cp.theory_artifact_id,
            f"theta-v{cp.theory_version} status={theory.status} "
            f"hash={th_hash[:24]}…")
    except Exception as e:                       # store/schema failures
        rec("theory", "THEORY_MISMATCH", False, str(e))

    # v_E — the pinned evidence head must be a valid prefix of the current
    # append-only chain (the store legitimately grows after resume; what can
    # never happen is a rewrite of the pinned prefix), and the chain intact.
    length, head = store.evidence_head()
    chain = store.verify_append_only()
    if cp.evidence_length == 0 and not cp.evidence_head_hash:
        prefix_ok = True
        prefix_why = "pinned empty head; any intact chain extends it"
    else:
        prefix_ok = False
        if store.heads_path.exists():
            for line in store.heads_path.read_text(
                    encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                h = json.loads(line)
                if int(h["length"]) == cp.evidence_length and \
                        str(h["hash"]) == cp.evidence_head_hash:
                    prefix_ok = True
                    break
        prefix_why = (f"pinned head ({cp.evidence_length},"
                      f"{cp.evidence_head_hash[:16]}…) "
                      + ("found in" if prefix_ok else "absent from")
                      + " the head chain")
    rec("evidence_head", "EVIDENCE_HEAD_MISMATCH",
        prefix_ok and chain["append_only_intact"],
        f"current head=({length},{head[:16]!r}); {prefix_why}; "
        f"chain_intact={chain['append_only_intact']}")

    # v_G — root contract identity
    rc = sha256_file(czroot / "contracts" / "root_contract.json")
    rec("root_contract", "ROOT_CONTRACT_MISMATCH",
        rc == cp.root_contract_sha256, f"sha256={rc[:16]}…")

    # v_K — formal kernel state identity
    fk = sha256_file(czroot / "state" / "formal-semantics-v0.1.json")
    rec("formal_kernel", "FORMAL_KERNEL_MISMATCH",
        fk == cp.formal_kernel_state_artifact_id, f"sha256={fk[:16]}…")

    # v_S — experiment state identity and result
    ok_s, why_s = False, "experiment state not pinned"
    if cp.experiment_state_path:
        p = root / cp.experiment_state_path
        if p.exists():
            es = sha256_file(p)
            res = json.loads(p.read_text(encoding="utf-8")).get("result")
            ok_s = (es == cp.experiment_state_sha256
                    and res == cp.experiment_result)
            why_s = f"sha256={es[:16]}…; result={res!r}"
        else:
            why_s = f"missing {cp.experiment_state_path}"
    rec("experiment_state", "EXPERIMENT_STATE_MISMATCH", ok_s, why_s)

    # protected manifest + protected-history immutability vs pinned commit
    pm_ok = protected_manifest_sha256(cp.protected_manifest) == \
        cp.protected_manifest_sha256
    mutations: list[str] = []
    if commit_ok:
        targets = [p.rstrip("/") for p in
                   cp.protected_manifest.get("protected_prefixes", [])]
        targets += cp.protected_manifest.get("protected_files", [])
        for t in targets:
            out = git(root, "diff", "--diff-filter=MD", "--name-only",
                      cp.commit_sha, "HEAD", "--", t)
            mutations.extend(out.splitlines())
    rec("protected_manifest", "PROTECTED_MANIFEST_MISMATCH",
        pm_ok and not mutations,
        f"manifest_hash_ok={pm_ok}; historical_mutations={mutations}")

    failed = sorted(k for k, v in checks.items() if v["status"] != "PASS")
    codes = sorted({checks[k]["failure_code"] for k in failed
                    if checks[k]["failure_code"]})
    return CheckpointResult(
        checkpoint_id=cp.checkpoint_id,
        status="PASS" if not failed else "FAIL",
        checks=checks,
        failed=failed,
        failure_codes=codes,
        result=None if not failed else "LINEAGE_RESUME_FAIL",
    )
