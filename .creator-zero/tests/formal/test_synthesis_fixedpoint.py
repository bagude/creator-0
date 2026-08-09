from __future__ import annotations
import unittest

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parent))
import _bootstrap  # noqa: F401,E402
from _bootstrap import CZROOT, FIXTURES  # noqa: F401,E402
from formal.synthesis_fixedpoint import (CLOSED, FIXED_POINT, PROGRESS,
                                         REGRESSION, classify_synthesis)


class TestClassification(unittest.TestCase):
    def cls_of(self, before, after):
        return classify_synthesis(before, after).detail["classification"]

    def test_empty_after_closes(self):
        self.assertEqual(self.cls_of(["Q1", "Q2"], []), CLOSED)
        self.assertEqual(self.cls_of([], []), CLOSED)

    def test_strict_subset_progresses(self):
        self.assertEqual(self.cls_of(["Q1", "Q2", "Q3"], ["Q3"]), PROGRESS)

    def test_unchanged_nonempty_fixed_point(self):
        self.assertEqual(self.cls_of(["Q1"], ["Q1"]), FIXED_POINT)

    def test_new_distinctions_regress(self):
        self.assertEqual(self.cls_of(["Q1"], ["Q1", "Q9"]), REGRESSION)
        self.assertEqual(self.cls_of(["Q1"], ["Q9"]), REGRESSION)

    def test_statuses_and_exit_codes(self):
        self.assertEqual(classify_synthesis(["Q1"], []).exit_code, 0)
        self.assertEqual(classify_synthesis(["Q1", "Q2"], ["Q1"]).exit_code, 0)
        self.assertEqual(classify_synthesis(["Q1"], ["Q1"]).status,
                         "INDETERMINATE")
        self.assertEqual(classify_synthesis(["Q1"], ["Q2"]).status, "FAIL")

    def test_counterexamples(self):
        r = classify_synthesis(["Q1"], ["Q1", "Q9"])
        self.assertEqual(r.counterexample["new_unresolved_distinctions"], ["Q9"])
        r2 = classify_synthesis(["Q1"], ["Q1"])
        self.assertEqual(r2.counterexample["unchanged_nonempty_set"], ["Q1"])

    def test_order_insensitive_deterministic(self):
        a = classify_synthesis(["Q2", "Q1"], ["Q1"]).to_dict()
        b = classify_synthesis(["Q1", "Q2"], ["Q1"]).to_dict()
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
