"""C2's C-level exponential surrogate (Q4b) — tracer-invisibility probe.

Canonical-equivalent output plus exponential combinatorial work executed
ENTIRELY inside CPython C code: collections.deque(iterator, maxlen=0)
consumes itertools.combinations(range(n), n//2) — C(n, n//2) items — with
ZERO Python-level frames per item, so sys.settrace sees a constant number of
events regardless of the exponential iteration count. Wall-clock cost is
genuinely exponential: C(32,16) ~ 6.0e8 (seconds in C), C(64,32) ~ 1.8e18
(infeasible — centuries). Probes C1's E10(b) residual-risk concession.
"""

import os
import sys
from collections import deque
from itertools import combinations

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "..", "src"))

import solver as _canonical


def solve(jobs):
    result = _canonical.solve(jobs)
    n = len(jobs)
    deque(combinations(range(n), n // 2), maxlen=0)
    return result
