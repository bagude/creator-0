"""C2's low-base exponential surrogate (Q4a) — discriminator evasion probe.

Canonical-equivalent output (delegates to src/solver.py) plus a deliberate
Python-level busy loop of int(3000 * 1.02**n) iterations: genuinely
exponential asymptotically (base 1.02), but tiny at every n the
discriminator samples (n=8: ~3516 iters; n=64: ~10683 iters). Probes whether
C1's 32x-per-doubling trace-event bound catches or misses the near-1-base
class C1's E10(a) concedes is unreachable by any fixed finite test.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "..", "src"))

import solver as _canonical


def solve(jobs):
    result = _canonical.solve(jobs)
    n = len(jobs)
    sink = 0
    for _ in range(int(3000 * (1.02 ** n))):
        sink += 1
    return result
