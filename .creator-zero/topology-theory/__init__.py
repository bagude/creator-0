"""Creator-0 Topology Theory + Reverse-ITP Self-Modification v0.1.

An explicit, versioned, evidence-bearing theory of causal-design principles
Theta_H = (P, E+, E-, R, V, L), from which candidate topologies are abduced as
provisional causal hypotheses, formally validated, deterministically ranked,
executed, evaluated against frozen predictions, falsified prediction-by-
prediction, and revised through governed proposal-only revisions.

Determinism boundary (kept explicit; see README.md §Determinism):
  deterministic  — schema validation, LTS compilation, reachability,
                   attenuation, protected-law checking, utility arithmetic,
                   tie-breaking, mechanical prediction comparison, historical
                   replay on mechanical cases, the Gate;
  model-mediated — principle applicability suggestions, candidate topology
                   synthesis heuristics, expected epistemic value estimates,
                   candidate principle wording, revision proposal wording.
Model-mediated content must be serialized into typed artifacts before use and
can never override a deterministic rejection.

The package directory is `.creator-zero/topology-theory/` (hyphenated, per the
architecture layout); import it via `importlib` with explicit submodule search
locations — see `tests/topology_theory/_bootstrap.py` or `cz.py`.
"""
from .model import (Principle, PrincipleEvidence, Prediction,
                    TopologyHypothesis, Revision, TheoryVersion,
                    ApplicabilityResult, TopologyEvaluation,
                    FalsificationResult, ReplayResult, ModelValidationError)
from .serialization import artifact_id, canonical_dumps, file_artifact_id
from .theory_store import TheoryStore, TheoryStoreError, PromotionError
from .principles import build_seed_theory, SEED_PRINCIPLE_IDS
from .abduct import abduce
from .generate import generate_candidates
from .predict import freeze_predictions, PredictionError
from .validate import validate_topology
from .utility import (load_utility_config, predicted_utility, observed_utility,
                      rank_candidates, calibration_error)
from .evaluate import evaluate_topology, PredictionIntegrityError
from .falsify import falsify, principle_evidence_events
from .revise import propose_revision
from .replay import replay, load_replay_corpus
from . import self_modify
from . import admissibility
from . import ingest
from . import governance
from . import theory_gate
from .generate2 import generate_candidates_v2, family_of_v2, FAMILIES_V2
from .predict2 import freeze_predictions_v2
from .revise2 import (propose_revision_v2, context_stats, split_trigger,
                      explanation_scores)

__all__ = [
    "Principle", "PrincipleEvidence", "Prediction", "TopologyHypothesis",
    "Revision", "TheoryVersion", "ApplicabilityResult", "TopologyEvaluation",
    "FalsificationResult", "ReplayResult", "ModelValidationError",
    "artifact_id", "canonical_dumps", "file_artifact_id",
    "TheoryStore", "TheoryStoreError", "PromotionError",
    "build_seed_theory", "SEED_PRINCIPLE_IDS",
    "abduce", "generate_candidates", "freeze_predictions", "PredictionError",
    "validate_topology", "load_utility_config", "predicted_utility",
    "observed_utility", "rank_candidates", "calibration_error",
    "evaluate_topology", "PredictionIntegrityError",
    "falsify", "principle_evidence_events", "propose_revision",
    "replay", "load_replay_corpus", "self_modify",
    "admissibility", "ingest", "governance", "theory_gate",
    "generate_candidates_v2", "family_of_v2", "FAMILIES_V2",
    "freeze_predictions_v2",
    "propose_revision_v2", "context_stats", "split_trigger",
    "explanation_scores",
]

__version__ = "0.1"
