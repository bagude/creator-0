"""Shared paths, IO, and loading for the Experiment 6 runtime.

All modules here are root-side deterministic orchestration: they sequence the
frozen topology-theory and formal-kernel modules, copy artifacts, and append
preregistered realization events. They never solve substantive tasks and
never override a deterministic judgment.
"""
from __future__ import annotations
import hashlib
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

E6 = Path(__file__).resolve().parents[1]
CZROOT = E6.parent
if str(CZROOT) not in sys.path:
    sys.path.insert(0, str(CZROOT))

SCRATCH = Path("/tmp/claude-0/-home-user-creator-0/"
               "113f7cc5-237e-5d6a-8867-a97fd89c58dd/scratchpad/e6")

SESSION_TOOLS = ["Read", "Write"]

# Deterministic expected-call structure per candidate family, frozen in
# utility-operationalization.md. Cost = (model_sessions + child_sessions) / 8.
FAMILY_CALLS = {
    "local": {"model_calls": 1, "child_calls": 0},
    "local-independent-verify": {"model_calls": 2, "child_calls": 0},
    "isolated-child": {"model_calls": 2, "child_calls": 1},
    "branching": {"model_calls": 2, "child_calls": 1},
}
COST_DENOMINATOR = 8  # 2 * K-E6-trial.max_model_calls


def family_of(topology_id: str) -> str:
    for fam in ("local-independent-verify", "isolated-child", "branching",
                "local"):
        if topology_id.endswith(fam):
            return fam
    raise ValueError(f"cannot derive family from topology id {topology_id!r}")


def predicted_cost(family: str) -> float:
    c = FAMILY_CALLS[family]
    return round((c["model_calls"] + c["child_calls"]) / COST_DENOMINATOR, 4)


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def jload(p: str | Path) -> Any:
    return json.loads(Path(p).read_text(encoding="utf-8"))


def jdump(p: str | Path, obj: Any) -> None:
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    Path(p).write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")


def sha256_file(p: str | Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def load_mod(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def e5_runtime(name: str):
    """Load a frozen Experiment 5 runtime module (fresh launcher v0.2 etc.)."""
    return load_mod(f"e6_uses_e5_{name}",
                    CZROOT / "experiment-5" / "runtime" / f"{name}.py")


def trial_contract() -> dict[str, Any]:
    return jload(E6 / "contracts" / "trial-contract.json")


def child_envelope() -> dict[str, Any]:
    return jload(E6 / "contracts" / "child-contract-envelope.json")


def load_theta_v1():
    """Load the promoted theory version 1 (read-only)."""
    model = tt_mod("model")
    doc = jload(CZROOT / "state" / "topology-theory" / "theta-v1.json")
    return model.TheoryVersion.from_dict(doc)


_TT_CACHE: dict[str, Any] = {}


def tt_mod(name: str):
    """Import a topology-theory submodule through the package machinery."""
    if name in _TT_CACHE:
        return _TT_CACHE[name]
    import importlib
    pkg_dir = CZROOT / "topology-theory"
    if "cz_topology_theory" not in sys.modules:
        spec = importlib.util.spec_from_file_location(
            "cz_topology_theory", pkg_dir / "__init__.py",
            submodule_search_locations=[str(pkg_dir)])
        pkg = importlib.util.module_from_spec(spec)
        sys.modules["cz_topology_theory"] = pkg
        spec.loader.exec_module(pkg)
    mod = importlib.import_module(f"cz_topology_theory.{name}")
    _TT_CACHE[name] = mod
    return mod


def trial_dir(tid: str, shadow: bool = False) -> Path:
    d = E6 / "trials" / tid
    if shadow:
        d = d / "shadow"
    d.mkdir(parents=True, exist_ok=True)
    return d


def pilot_trial_dir(tid: str) -> Path:
    d = E6 / "pilot" / "trials" / tid
    d.mkdir(parents=True, exist_ok=True)
    return d


def bank_dir(tid: str) -> Path:
    d = E6 / "task-bank" / tid
    if not d.is_dir():
        d = E6 / "pilot" / "task-bank" / tid
    return d


def ws_root(tid: str) -> Path:
    return SCRATCH / tid
