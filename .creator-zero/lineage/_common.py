"""Shared deterministic helpers for the lineage subsystem."""
from __future__ import annotations
import hashlib
import importlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

CZROOT = Path(__file__).resolve().parents[1]


def sha256_file(p: Path | str) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def git(repo_root: Path | str, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=repo_root, capture_output=True,
                          text=True, check=True).stdout.strip()


def git_ok(repo_root: Path | str, *args: str) -> bool:
    return subprocess.run(["git", *args], cwd=repo_root,
                          capture_output=True).returncode == 0


def tt_mod(name: str):
    """Load a topology-theory submodule through the package machinery."""
    pkg_dir = CZROOT / "topology-theory"
    if "cz_topology_theory" not in sys.modules:
        spec = importlib.util.spec_from_file_location(
            "cz_topology_theory", pkg_dir / "__init__.py",
            submodule_search_locations=[str(pkg_dir)])
        pkg = importlib.util.module_from_spec(spec)
        sys.modules["cz_topology_theory"] = pkg
        spec.loader.exec_module(pkg)
    return importlib.import_module(f"cz_topology_theory.{name}")


def protected_manifest_sha256(manifest: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(manifest, sort_keys=True,
                          separators=(",", ":")).encode("utf-8")).hexdigest()
