"""Creator-0 Formal Semantics Kernel v0.1.

Deterministic formal layer: labelled transition systems, simulation/refinement,
strong/weak bisimulation, inductive attenuation invariants, bounded coinductive
Creator-Closure witnesses, and finite fixed-point synthesis classification.

The formal layer is read-only with respect to canonical task state: it parses,
compiles, compares, verifies, rejects, and emits evidence. It never promotes,
edits canonical artifacts, weakens contracts, or modifies historical evidence.
No LLM may override a failed formal check.
"""
from .labels import Label, TAU, OBSERVABLE_LABELS, primitive_label, relation_label
from .model import LTS, Transition, FormalResult, RuntimeEvent, Trace
from .semantics import compile_harness_spec, SemanticsError
from .trace import parse_runtime_ledger, TraceParseError
from .refinement import check_refinement
from .bisimulation import strong_bisimilar, weak_bisimilar
from .attenuation import check_attenuation
from .creator_closure import check_creator_closure
from .freshness import check_freshness
from .synthesis_fixedpoint import classify_synthesis
from .serialization import lts_to_json, lts_from_json, result_to_json

__all__ = [
    "Label", "TAU", "OBSERVABLE_LABELS", "primitive_label", "relation_label",
    "LTS", "Transition", "FormalResult", "RuntimeEvent", "Trace",
    "compile_harness_spec", "SemanticsError",
    "parse_runtime_ledger", "TraceParseError",
    "check_refinement", "strong_bisimilar", "weak_bisimilar",
    "check_attenuation", "check_creator_closure", "check_freshness",
    "classify_synthesis",
    "lts_to_json", "lts_from_json", "result_to_json",
]

__version__ = "0.1"
