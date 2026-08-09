"""Shared test bootstrap: puts .creator-zero on sys.path and exposes paths."""
from __future__ import annotations
import sys
from pathlib import Path

CZROOT = Path(__file__).resolve().parents[2]      # .creator-zero/
REPO = CZROOT.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures"

if str(CZROOT) not in sys.path:
    sys.path.insert(0, str(CZROOT))
