"""Shared test bootstrap: loads the hyphenated topology-theory package as
`topology_theory` and puts .creator-zero on sys.path for `formal`."""
from __future__ import annotations
import importlib.util
import sys
from pathlib import Path

CZROOT = Path(__file__).resolve().parents[2]      # .creator-zero/
REPO = CZROOT.parent
PKG_DIR = CZROOT / "topology-theory"

if str(CZROOT) not in sys.path:
    sys.path.insert(0, str(CZROOT))


def load_topology_theory():
    if "topology_theory" in sys.modules:
        return sys.modules["topology_theory"]
    spec = importlib.util.spec_from_file_location(
        "topology_theory", PKG_DIR / "__init__.py",
        submodule_search_locations=[str(PKG_DIR)])
    mod = importlib.util.module_from_spec(spec)
    sys.modules["topology_theory"] = mod
    spec.loader.exec_module(mod)
    return mod


TT = load_topology_theory()
