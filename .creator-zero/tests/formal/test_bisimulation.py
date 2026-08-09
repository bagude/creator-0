from __future__ import annotations
import unittest

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parent))
import _bootstrap  # noqa: F401,E402
from _bootstrap import CZROOT, FIXTURES  # noqa: F401,E402
from formal.bisimulation import strong_bisimilar, weak_bisimilar
from formal.model import Transition, make_lts


def lts(transitions, initial):
    return make_lts([Transition(*t) for t in transitions], initial=initial)


A = lts([("a0", "create", "a1", "creator"),
         ("a1", "return", "a2", "creator"),
         ("a2", "complete", "a3", "creator")], "a0")

# identical visible behavior, tau steps inserted
B = lts([("b0", "create", "b1", "creator"),
         ("b1", "tau", "b1x", "*"),
         ("b1x", "return", "b2", "creator"),
         ("b2", "complete", "b3", "creator")], "b0")

# different visible behavior: no return
C = lts([("c0", "create", "c1", "creator"),
         ("c1", "complete", "c2", "creator")], "c0")

# same labels, different actor on an observable action
D = lts([("d0", "create", "d1", "creator"),
         ("d1", "return", "d2", "impostor"),
         ("d2", "complete", "d3", "creator")], "d0")


class TestStrong(unittest.TestCase):
    def test_identical_systems_pass(self):
        r = strong_bisimilar(A, A)
        self.assertEqual(r.status, "PASS")

    def test_visible_label_mismatch_fails(self):
        r = strong_bisimilar(A, C)
        self.assertEqual(r.status, "FAIL")
        self.assertIsNotNone(r.counterexample)
        self.assertIn("unmatched_action", r.counterexample)

    def test_tau_difference_fails_strong(self):
        r = strong_bisimilar(A, B)
        self.assertEqual(r.status, "FAIL")

    def test_actor_is_part_of_observation(self):
        r = strong_bisimilar(A, D)
        self.assertEqual(r.status, "FAIL")
        self.assertEqual(r.counterexample["unmatched_action"]["label"], "return")


class TestWeak(unittest.TestCase):
    def test_tau_only_difference_passes_weak(self):
        r = weak_bisimilar(A, B)
        self.assertEqual(r.status, "PASS")

    def test_observable_difference_fails_weak(self):
        r = weak_bisimilar(A, C)
        self.assertEqual(r.status, "FAIL")
        self.assertIn("unmatched_action", r.counterexample)

    def test_weak_is_symmetric(self):
        self.assertEqual(weak_bisimilar(B, A).status, "PASS")

    def test_weak_actor_mismatch_fails(self):
        self.assertEqual(weak_bisimilar(A, D).status, "FAIL")

    def test_only_tau_supported_as_silent(self):
        with self.assertRaises(ValueError):
            weak_bisimilar(A, B, silent_label="skip")


if __name__ == "__main__":
    unittest.main()
