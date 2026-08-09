"""Experiment 5 runtime modules.

Deterministic governance machinery for endogenous topology growth:
proposal observability, fresh-child launching, decision validation,
conditional topology guarding, and decision scoring.

These modules are read-only with respect to canonical task state, in the
same sense as the Formal Semantics Kernel: they parse, check, reject and
emit evidence; they never promote or mutate historical artifacts. No LLM
may override a failed check emitted here.
"""
from __future__ import annotations
import sys
from pathlib import Path

# .creator-zero root, so `formal` (the kernel package) is importable.
CREATOR_ZERO_ROOT = Path(__file__).resolve().parents[2]
if str(CREATOR_ZERO_ROOT) not in sys.path:
    sys.path.insert(0, str(CREATOR_ZERO_ROOT))
