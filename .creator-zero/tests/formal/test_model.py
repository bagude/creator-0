from __future__ import annotations
import unittest

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parent))
import _bootstrap  # noqa: F401,E402
from _bootstrap import CZROOT, FIXTURES  # noqa: F401,E402
from formal.model import (ANY_ACTOR, FAIL, INDETERMINATE, PASS, FormalResult,
                          LTS, Transition, make_lts)


class TestTransition(unittest.TestCase):
    def test_closed_alphabet(self):
        with self.assertRaises(ValueError):
            Transition("a", "telepathy", "b")

    def test_valid(self):
        t = Transition("a", "observe", "b", "node:x")
        self.assertEqual(t.to_dict(),
                         {"source": "a", "label": "observe", "target": "b",
                          "actor": "node:x"})


class TestLTS(unittest.TestCase):
    def make(self):
        return make_lts([Transition("a", "observe", "b", "node:x"),
                         Transition("b", "verify", "b", "node:y"),
                         Transition("a", "tau", "a")], initial="a")

    def test_initial_must_exist(self):
        with self.assertRaises(ValueError):
            LTS(states=frozenset({"a"}), labels=frozenset({"tau"}),
                transitions=frozenset(), initial="zzz")

    def test_transition_states_must_exist(self):
        with self.assertRaises(ValueError):
            LTS(states=frozenset({"a"}), labels=frozenset({"observe"}),
                transitions=frozenset({Transition("a", "observe", "ghost")}),
                initial="a")

    def test_enabled_actor_matching(self):
        lts = self.make()
        self.assertTrue(lts.enabled("a", "observe", "node:x"))
        self.assertFalse(lts.enabled("a", "observe", "node:other"))
        # wildcard spec actor admits any runtime actor
        self.assertTrue(lts.enabled("a", "tau", "anyone"))

    def test_allowed_labels_sorted_deterministic(self):
        lts = self.make()
        self.assertEqual(lts.allowed_labels("a"), ["observe", "tau"])


class TestFormalResult(unittest.TestCase):
    def test_status_validation(self):
        with self.assertRaises(ValueError):
            FormalResult(check="x", status="MAYBE", formal_relation="r")

    def test_exit_codes(self):
        self.assertEqual(FormalResult("c", PASS, "r").exit_code, 0)
        self.assertEqual(FormalResult("c", FAIL, "r").exit_code, 2)
        self.assertEqual(FormalResult("c", INDETERMINATE, "r").exit_code, 3)

    def test_result_shape(self):
        d = FormalResult("c", PASS, "r").to_dict()
        for k in ("check", "status", "formal_relation", "counterexample",
                  "evidence", "assumptions", "unmapped_events"):
            self.assertIn(k, d)


if __name__ == "__main__":
    unittest.main()
