"""Shared paths, loaders, and condition plumbing for the E7 runtime."""
from __future__ import annotations
import hashlib
import importlib
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

E7 = Path(__file__).resolve().parents[1]
CZROOT = E7.parent
REPO = CZROOT.parent
E6 = CZROOT / "experiment-6"

SCRATCH = Path("/tmp/claude-0/-home-user-creator-0/"
               "87cd2a2d-a4f9-585b-836f-2648df7a6284/scratchpad/e7run")

SESSION_TOOLS = ["Read", "Write"]
CONDITIONS = ("A", "B")

# condition A: frozen E6 family economics (utility-operationalization.md)
FAMILY_CALLS_A = {
    "local": {"model_calls": 1, "child_calls": 0},
    "local-independent-verify": {"model_calls": 2, "child_calls": 0},
    "isolated-child": {"model_calls": 2, "child_calls": 1},
    "branching": {"model_calls": 2, "child_calls": 1},
}
# condition B: grammar v2 (generate2.FAMILY_CALLS_V2 mirrors this)
FAMILY_CALLS_B = {
    "local": {"model_calls": 1, "child_calls": 0},
    "local-independent-examiner": {"model_calls": 2, "child_calls": 0},
    "local-method-disjoint-verifier": {"model_calls": 2, "child_calls": 0},
    "isolated-clean-room-author": {"model_calls": 2, "child_calls": 1},
    "isolated-decomposer": {"model_calls": 2, "child_calls": 1},
    "isolated-searcher": {"model_calls": 2, "child_calls": 1},
    "branching": {"model_calls": 2, "child_calls": 1},
}
COST_DENOMINATOR = 8

EXAMINER_FAMILIES = ("local-independent-verify",
                     "local-independent-examiner",
                     "local-method-disjoint-verifier")
CHILD_FAMILIES = ("isolated-child", "isolated-clean-room-author",
                  "isolated-decomposer", "isolated-searcher")

# integration-plan role vocabularies: frozen E6 + canonical v2
ROLES_ACCEPTED = ("clean_room_implementer", "adversarial_searcher",
                  "independent_decomposer", "independent_verifier",
                  "clean_room_author", "non_author_examiner",
                  "method_disjoint_verifier")


def family_of(topology_id: str, condition: str) -> str:
    fams = (FAMILY_CALLS_A if condition == "A" else FAMILY_CALLS_B)
    for fam in sorted(fams, key=len, reverse=True):
        if topology_id.endswith(fam):
            return fam
    raise ValueError(f"cannot derive family from {topology_id!r} "
                     f"(condition {condition})")


def predicted_cost(family: str, condition: str) -> float:
    c = (FAMILY_CALLS_A if condition == "A" else FAMILY_CALLS_B)[family]
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


def load_mod(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def e6_runtime(name: str):
    """Import a frozen Experiment 6 runtime module (read-only reuse).

    Loaded under the distinct package name `e6_runtime_pkg` so it never
    collides with this experiment's own `runtime` package."""
    pkg_name = "e6_runtime_pkg"
    if pkg_name not in sys.modules:
        spec = importlib.util.spec_from_file_location(
            pkg_name, E6 / "runtime" / "__init__.py",
            submodule_search_locations=[str(E6 / "runtime")])
        pkg = importlib.util.module_from_spec(spec)
        sys.modules[pkg_name] = pkg
        spec.loader.exec_module(pkg)
    return importlib.import_module(f"{pkg_name}.{name}")


def e5_runtime(name: str):
    return load_mod(f"e7_uses_e5_{name}",
                    CZROOT / "experiment-5" / "runtime" / f"{name}.py")


_TT_CACHE: dict[str, Any] = {}


def tt_mod(name: str):
    if name in _TT_CACHE:
        return _TT_CACHE[name]
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


def trial_contract() -> dict[str, Any]:
    return jload(E6 / "contracts" / "trial-contract.json")


def child_envelope() -> dict[str, Any]:
    return jload(E6 / "contracts" / "child-contract-envelope.json")


def load_theta(condition: str):
    """Condition A: promoted theta-v1. Condition B: candidate theta-v2."""
    model = tt_mod("model")
    if condition == "A":
        doc = jload(CZROOT / "state" / "topology-theory" / "theta-v1.json")
    else:
        doc = jload(E7 / "candidate-revisions" / "candidate-theta-v2.json")
    return model.TheoryVersion.from_dict(doc)


def bank_dir(tid: str) -> Path:
    d = E7 / "task-bank" / tid
    if not d.is_dir():
        d = E7 / "pilot" / "task-bank" / tid
    return d


def is_pilot(tid: str) -> bool:
    return (E7 / "pilot" / "task-bank" / tid).is_dir()


def trial_dir(tid: str, condition: str, shadow: bool = False) -> Path:
    base = E7 / ("pilot/trials" if is_pilot(tid) else "trials")
    d = base / condition / tid
    if shadow:
        d = d / "shadow"
    d.mkdir(parents=True, exist_ok=True)
    return d


def ws_root(tid: str, condition: str) -> Path:
    return SCRATCH / condition / tid


def ws(tid: str, condition: str, shadow: bool, name: str) -> Path:
    root = ws_root(tid, condition)
    if name == "infer-ws":
        return root / "infer-ws"
    return root / ("shadow" if shadow else "primary") / name


def canonical_role_of(raw_role: str, examiner: bool = False) -> str:
    adm = tt_mod("admissibility")
    return adm.canonical_role(raw_role, examiner=examiner)
