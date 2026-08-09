"""Q4b surrogate: canonical solve() plus a MILD super-polynomial cost term.

Wraps the real src/solver.py solve (identical outputs, R1-R7 untouched) but
burns extra work shaped like K * 1.02**n busy-loop iterations, K = 3000.
Genuinely exponential (base 1.02 > 1), yet at the probe sizes it stays tiny:
n=100 -> ~2.2e4 iterations, n=200 -> ~1.6e5, n=400 -> ~8.3e6 (well under a
second each on any plausible machine, far under probes.py's 30s cap).
Purpose: executable demonstration that the r8_scaling wall-clock cap does not
discriminate a mild super-polynomial regression.
"""

import importlib.util
import os

_SRC = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "src", "solver.py")
_spec = importlib.util.spec_from_file_location("_canonical_solver", os.path.abspath(_SRC))
_canonical = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_canonical)

K = 3000
BASE = 1.02


def solve(jobs):
    result = _canonical.solve(jobs)
    if isinstance(jobs, list):
        n = len(jobs)
        sink = 0
        for _ in range(int(K * BASE ** n)):
            sink += 1
    return result
