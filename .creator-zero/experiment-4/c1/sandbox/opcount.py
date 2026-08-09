"""Deterministic operation counting via sys.settrace.

Counts every Python-level trace event (call, line, return, exception) executed
inside a callable. Wall-clock independent: identical input to a deterministic
callable yields an identical count on any machine and any run. Line events
make inline loops (e.g. `for mask in range(2**n)`) count work even when they
make no function calls, closing the evasion route a pure call-counter leaves
open. Residual blind spot (recorded in the evidence): work executed entirely
inside C extensions produces no trace events.
"""

import sys


def count_ops(fn, *args, **kwargs):
    counter = 0

    def tracer(frame, event, arg):
        nonlocal counter
        counter += 1
        return tracer

    old = sys.gettrace()
    sys.settrace(tracer)
    try:
        result = fn(*args, **kwargs)
    finally:
        sys.settrace(old)
    return counter, result


def disjoint_instance(n):
    """Deterministic all-compatible instance family used for growth probes."""
    return [(3 * i, 3 * i + 2, 1 + (i % 3)) for i in range(n)]
