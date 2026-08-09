#!/usr/bin/env python3
"""Preregistered deterministic verifier stub (Experiment 6)."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BANK = HERE.parent
for cand in (BANK.parents[0] / "_shared",
             BANK.parents[2] / "task-bank" / "_shared"):
    if cand.is_dir():
        sys.path.insert(0, str(cand))
        break
import verifylib  # noqa: E402
import verify_altdecomp as V  # noqa: E402

LABEL = json.loads((HERE / "label.json").read_text(encoding="utf-8"))
verifylib.cli(lambda td, out: V.run(td, out, LABEL, BANK / 'public'))
