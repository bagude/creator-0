"""Lineage subsystem: checkpoint create/verify/resume (spec §20.1)."""
from __future__ import annotations
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import _bootstrap
from _bootstrap import CZROOT, REPO

import importlib.util
import sys


def _load_lineage():
    if "lineage" in sys.modules:
        return sys.modules["lineage"]
    spec = importlib.util.spec_from_file_location(
        "lineage", CZROOT / "lineage" / "__init__.py",
        submodule_search_locations=[str(CZROOT / "lineage")])
    mod = importlib.util.module_from_spec(spec)
    sys.modules["lineage"] = mod
    spec.loader.exec_module(mod)
    return mod


LIN = _load_lineage()
BASE_CP = CZROOT / "experiment-7" / "base-checkpoint.json"


def _rebuild(doc: dict, **edits) -> dict:
    from lineage.model import checkpoint_id_for
    d = {k: v for k, v in doc.items() if k != "checkpoint_id"}
    d.update(edits)
    d["checkpoint_id"] = checkpoint_id_for(d)
    return d


class CheckpointModelTest(unittest.TestCase):
    def setUp(self):
        self.doc = json.loads(BASE_CP.read_text(encoding="utf-8"))

    def test_base_checkpoint_parses_and_id_is_content_bound(self):
        cp = LIN.LineageCheckpoint.from_dict(self.doc)
        self.assertEqual(cp.commit_sha,
                         "bd0cf91e455393d3d601070e5022c565d9ed9ed1")
        self.assertEqual(cp.theory_version, 1)

    def test_edited_body_without_new_id_is_rejected(self):
        bad = dict(self.doc)
        bad["experiment_result"] = "SOMETHING_ELSE"
        with self.assertRaises(LIN.LineageError):
            LIN.LineageCheckpoint.from_dict(bad)

    def test_unknown_fields_rejected(self):
        bad = _rebuild(self.doc)
        bad["surprise"] = 1
        with self.assertRaises(LIN.LineageError):
            LIN.LineageCheckpoint.from_dict(bad)

    def test_deterministic_serialization(self):
        cp = LIN.LineageCheckpoint.from_dict(self.doc)
        self.assertEqual(cp.serialize(), cp.serialize())
        again = LIN.LineageCheckpoint.from_dict(
            json.loads(cp.serialize()))
        self.assertEqual(again.checkpoint_id, cp.checkpoint_id)


class VerifyCheckpointTest(unittest.TestCase):
    def setUp(self):
        self.doc = json.loads(BASE_CP.read_text(encoding="utf-8"))

    def test_exact_checkpoint_passes_and_is_idempotent(self):
        r1 = LIN.verify_checkpoint(REPO, self.doc)
        r2 = LIN.verify_checkpoint(REPO, self.doc)
        self.assertEqual(r1.status, "PASS", r1.to_dict())
        self.assertEqual(r1.to_dict(), r2.to_dict())

    def test_commit_mismatch_fails(self):
        bad = _rebuild(self.doc,
                       commit_sha="0" * 40)
        r = LIN.verify_checkpoint(REPO, bad)
        self.assertEqual(r.status, "FAIL")
        self.assertIn("COMMIT_MISMATCH", r.failure_codes)
        self.assertEqual(r.result, "LINEAGE_RESUME_FAIL")

    def test_tree_mismatch_fails(self):
        bad = _rebuild(self.doc, tree_sha="f" * 40)
        r = LIN.verify_checkpoint(REPO, bad)
        self.assertIn("TREE_MISMATCH", r.failure_codes)

    def test_theory_mismatch_fails(self):
        bad = _rebuild(self.doc, theory_artifact_id="sha256:" + "0" * 64)
        r = LIN.verify_checkpoint(REPO, bad)
        self.assertIn("THEORY_MISMATCH", r.failure_codes)

    def test_evidence_head_mismatch_fails(self):
        bad = _rebuild(self.doc, evidence_length=7,
                       evidence_head_hash="deadbeef" * 8)
        r = LIN.verify_checkpoint(REPO, bad)
        self.assertIn("EVIDENCE_HEAD_MISMATCH", r.failure_codes)

    def test_experiment_state_mismatch_fails(self):
        bad = _rebuild(self.doc, experiment_state_sha256="0" * 64)
        r = LIN.verify_checkpoint(REPO, bad)
        self.assertIn("EXPERIMENT_STATE_MISMATCH", r.failure_codes)

    def test_root_contract_and_kernel_mismatch_fail(self):
        bad = _rebuild(self.doc, root_contract_sha256="1" * 64)
        r = LIN.verify_checkpoint(REPO, bad)
        self.assertIn("ROOT_CONTRACT_MISMATCH", r.failure_codes)
        bad = _rebuild(self.doc, formal_kernel_state_artifact_id="2" * 64)
        r = LIN.verify_checkpoint(REPO, bad)
        self.assertIn("FORMAL_KERNEL_MISMATCH", r.failure_codes)

    def test_protected_manifest_mismatch_fails(self):
        bad = _rebuild(self.doc, protected_manifest_sha256="3" * 64)
        r = LIN.verify_checkpoint(REPO, bad)
        self.assertIn("PROTECTED_MANIFEST_MISMATCH", r.failure_codes)


class ResumeTest(unittest.TestCase):
    def setUp(self):
        self.doc = json.loads(BASE_CP.read_text(encoding="utf-8"))
        self.dest = Path(tempfile.mkdtemp()) / "resume-wt"

    def tearDown(self):
        subprocess.run(["git", "worktree", "remove", "--force",
                        str(self.dest)], cwd=REPO, capture_output=True)
        shutil.rmtree(self.dest.parent, ignore_errors=True)

    def test_resume_lands_on_exact_commit_and_source_unmoved(self):
        before = subprocess.run(
            ["git", "rev-parse", "origin/claude/new-session-ltyh1o"],
            cwd=REPO, capture_output=True, text=True).stdout.strip()
        rec = LIN.resume_from_checkpoint(REPO, self.doc, self.dest)
        self.assertEqual(rec["head"], self.doc["commit_sha"])
        self.assertEqual(rec["tree"], self.doc["tree_sha"])
        self.assertTrue(rec["source_branch_unmodified"])
        after = subprocess.run(
            ["git", "rev-parse", "origin/claude/new-session-ltyh1o"],
            cwd=REPO, capture_output=True, text=True).stdout.strip()
        self.assertEqual(before, after)

    def test_resume_refused_on_bad_checkpoint(self):
        bad = _rebuild(self.doc, tree_sha="a" * 40)
        with self.assertRaises(LIN.LineageError):
            LIN.resume_from_checkpoint(REPO, bad, self.dest)
        self.assertFalse(self.dest.exists())


if __name__ == "__main__":
    unittest.main()
