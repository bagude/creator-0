"""Existing test suite for src/solver.py (protected: do not weaken)."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from solver import solve


class TestSolve(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(solve([]), (0, []))

    def test_single_job(self):
        self.assertEqual(solve([(1, 4, 7)]), (7, [0]))

    def test_two_overlapping_picks_heavier(self):
        self.assertEqual(solve([(0, 5, 3), (2, 7, 9)]), (9, [1]))

    def test_touching_intervals_compatible(self):
        self.assertEqual(solve([(0, 3, 4), (3, 6, 5)]), (9, [0, 1]))

    def test_classic_instance(self):
        jobs = [(1, 4, 3), (3, 5, 2), (0, 6, 6), (4, 7, 3), (3, 8, 7),
                (5, 9, 4), (6, 10, 5), (8, 11, 2)]
        weight, schedule = solve(jobs)
        self.assertEqual(weight, 11)
        self.assertEqual(sum(jobs[i][2] for i in schedule), 11)

    def test_tie_break_prefers_lower_indices(self):
        # Both {0} and {1} achieve weight 5; schedule must be [0].
        self.assertEqual(solve([(0, 4, 5), (1, 5, 5)]), (5, [0]))

    def test_tie_break_lex_smallest_when_later_index_finishes_first(self):
        # Jobs overlap, so {0} and {1} both achieve W=1; R6 requires [0].
        # Job 1 finishes earlier, so earliest-finish DP reconstructions
        # that do not lexicographically minimize return [1] instead.
        self.assertEqual(solve([(0, 2, 1), (0, 1, 1)]), (1, [0]))

    def test_negative_starts(self):
        self.assertEqual(solve([(-5, -1, 2), (-1, 3, 4)]), (6, [0, 1]))

    def test_rejects_zero_length_interval(self):
        with self.assertRaises(ValueError):
            solve([(2, 2, 1)])

    def test_rejects_nonpositive_weight(self):
        with self.assertRaises(ValueError):
            solve([(0, 1, 0)])

    def test_rejects_bool_fields(self):
        with self.assertRaises(ValueError):
            solve([(False, True, 3)])

    def test_rejects_non_list_input(self):
        with self.assertRaises(ValueError):
            solve(((0, 1, 1),))

    def test_does_not_mutate_input(self):
        jobs = [(0, 2, 3), (2, 4, 1)]
        snapshot = list(jobs)
        solve(jobs)
        self.assertEqual(jobs, snapshot)


    def test_r8_operation_growth_is_polynomial(self):
        # R8: runtime must be polynomial in len(jobs); exhaustive subset
        # enumeration is not acceptable. Wall-clock-free check: trace-event
        # counts during solve() may grow at most 32x (degree 5) per doubling
        # of n. Any per-element branching enumeration exceeds the bound by
        # n=16, so a regression fails fast here instead of hanging at n=64.
        def count_ops(n):
            jobs = [(3 * i, 3 * i + 2, 1 + (i % 3)) for i in range(n)]
            counter = [0]

            def tracer(frame, event, arg):
                counter[0] += 1
                return tracer

            previous = sys.gettrace()
            sys.settrace(tracer)
            try:
                solve(jobs)
            finally:
                sys.settrace(previous)
            return counter[0]

        prev = count_ops(8)
        for n in (16, 32, 64):
            cur = count_ops(n)
            self.assertLessEqual(
                cur,
                32 * prev,
                "super-polynomial operation growth: %d -> %d events over a "
                "doubling to n=%d (R8)" % (prev, cur, n),
            )
            prev = cur


if __name__ == "__main__":
    unittest.main()
