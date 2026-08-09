"""Deterministic tests for the fresh-child sanitized launcher
(Experiment 5 hardening 2). No model calls: dry runs and a fake CLI."""
from __future__ import annotations
import importlib.util
import json
import os
import stat
import tempfile
import unittest
from pathlib import Path

import _bootstrap  # noqa: F401


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, _bootstrap.E5 / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


FAKE_CLI = r"""#!/usr/bin/env python3
import json, sys
args = sys.argv[1:]
sid = args[args.index("--session-id") + 1] if "--session-id" in args else ""
print(json.dumps({"type": "system", "subtype": "init", "session_id": sid}))
print(json.dumps({"type": "result", "subtype": "success", "is_error": False}))
"""


class FreshLauncherTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fl = _load("e5_fresh_launcher", "runtime/fresh_launcher.py")

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.ws = self.tmp / "ws"
        self.ws.mkdir()
        self.prompt = self.tmp / "prompt.md"
        self.prompt.write_text("hello child\n", encoding="utf-8")

    def _launch(self, **kw):
        base = dict(
            prompt_path=self.prompt, workspace=self.ws,
            allowed_tools=["Read", "Write"],
            log_path=self.tmp / "session.log",
            provenance_path=self.tmp / "provenance.json",
            creator="test-root", purpose="unit test")
        base.update(kw)
        return self.fl.launch_fresh_child(**base)

    # --- sanitization -----------------------------------------------------
    def test_sanitize_strips_exact_and_pattern_vars(self):
        env = {"PATH": "/bin",
               "CLAUDE_CODE_SESSION_ID": "root-sid",
               "CLAUDE_CODE_CHILD_SESSION": "1",
               "CLAUDE_CODE_REMOTE_SESSION_ID": "r",
               "CLAUDE_NEW_SESSION_THING": "x",       # pattern-only
               "CLAUDE_CODE_VERSION": "2.1"}          # legitimately kept
        clean, removed = self.fl.sanitize_environment(env)
        self.assertNotIn("CLAUDE_CODE_SESSION_ID", clean)
        self.assertNotIn("CLAUDE_NEW_SESSION_THING", clean)
        self.assertIn("PATH", clean)
        self.assertIn("CLAUDE_CODE_VERSION", clean)
        self.assertIn("CLAUDE_CODE_SESSION_ID", removed)
        self.assertIn("CLAUDE_NEW_SESSION_THING", removed)

    def test_assert_sanitized_rejects_residual(self):
        with self.assertRaises(self.fl.FreshnessError):
            self.fl.assert_sanitized({"CLAUDE_CODE_SESSION_ID": "sid"})
        self.fl.assert_sanitized({"PATH": "/bin"})  # no raise

    # --- rejection gate (negative control A shape) ------------------------
    def test_tainted_launch_rejected_before_process_creation(self):
        env = {"PATH": os.environ.get("PATH", "/bin"),
               "CLAUDE_CODE_SESSION_ID": "inherited-root-sid"}
        with self.assertRaises(self.fl.FreshnessError) as cm:
            self._launch(env=env, executable="/nonexistent/never-run",
                         _dangerously_skip_sanitization=True)
        self.assertIn("FRESHNESS_FAIL", str(cm.exception))
        refusal = json.loads((self.tmp / "provenance.json").read_text())
        self.assertEqual(refusal["verdict"], "FRESHNESS_FAIL")
        self.assertFalse((self.tmp / "session.log").exists())

    def test_session_id_reuse_rejected(self):
        env = {"PATH": "/bin", "CLAUDE_CODE_SESSION_ID": "root-sid"}
        with self.assertRaises(self.fl.FreshnessError):
            self._launch(env=env, session_id="root-sid",
                         executable="/nonexistent/never-run")

    # --- dry run provenance ----------------------------------------------
    def test_dry_run_provenance_and_fresh_session_id(self):
        env = {"PATH": "/bin", "CLAUDE_CODE_SESSION_ID": "root-sid"}
        rec = self._launch(env=env, dry_run=True)
        self.assertFalse(rec["executed"])
        self.assertNotEqual(rec["session_id"], "root-sid")
        self.assertIn("CLAUDE_CODE_SESSION_ID",
                      rec["environment_sanitization"]["removed_variables"])
        self.assertIn("--session-id", rec["command_display"])
        persisted = json.loads((self.tmp / "provenance.json").read_text())
        self.assertEqual(persisted["session_id"], rec["session_id"])
        res = self.fl.freshness_result(persisted)
        self.assertEqual(res.status, "PASS")

    # --- end-to-end with a fake CLI --------------------------------------
    def test_fake_cli_execution_confirms_session_id(self):
        fake = self.tmp / "fake-claude"
        fake.write_text(FAKE_CLI, encoding="utf-8")
        fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
        env = {"PATH": os.environ.get("PATH", "/bin"),
               "CLAUDE_CODE_SESSION_ID": "root-sid"}
        rec = self._launch(env=env, executable=str(fake))
        self.assertTrue(rec["executed"])
        self.assertEqual(rec["exit_status"], 0)
        self.assertIs(rec["session_id_confirmed"], True)
        res = self.fl.freshness_result(rec)
        self.assertEqual(res.status, "PASS")

    def test_freshness_result_fails_on_wrong_session_id(self):
        rec = {"artifact": "fresh-child launch provenance", "fresh": True,
               "session_id": "abc",
               "environment_sanitization": {
                   "removed_variables": [],
                   "residual_continuity_variables": [],
                   "session_id_reuse": False},
               "session_id_confirmed": False}
        res = self.fl.freshness_result(rec)
        self.assertEqual(res.status, "FAIL")
        self.assertEqual(res.counterexample["violation"], "FRESHNESS_FAIL")


if __name__ == "__main__":
    unittest.main()
