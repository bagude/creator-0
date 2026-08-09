"""Deterministic validation of typed topology-decision artifacts and of
proposed child bundles (Experiment 5).

Violations:
    INVALID_DECISION_ARTIFACT — decision.json malformed w.r.t. the schema.
    INVALID_CREATION_DECISION — CREATE without an assigned unresolved
        distinction or expected child contribution (or dangling references).
    INVALID_CHILD_BUNDLE      — CREATE bundle fails deterministic validation
        (contract envelope, kernel compilation, attenuation, input manifest
        containment / clean-room exclusion, integration-plan executability).
"""
from __future__ import annotations
import json
import sys
from pathlib import Path
from typing import Any

_CZROOT = Path(__file__).resolve().parents[2]
if str(_CZROOT) not in sys.path:
    sys.path.insert(0, str(_CZROOT))

from formal.model import FAIL, PASS, FormalResult

CHECK = "topology_decision_validation"
RELATION = "decision artifact conforms to typed chi schema"

GAIN_COST = ("LOW", "MEDIUM", "HIGH")
DECISIONS = ("CREATE", "DO_NOT_CREATE")

REQUIRED_KEYS = (
    "trial_id", "decision", "unresolved_distinctions",
    "expected_child_contribution", "local_resolution_path",
    "expected_information_gain", "expected_cost", "decision_basis",
    "confidence")

_ASSUMPTIONS = [
    "Only the externally inspectable artifact counts as decision evidence; "
    "hidden reasoning is not evidence.",
    "Validation is deterministic and read-only; a failed validation rejects "
    "realization and no LLM may override it.",
]


def _fail(violation: str, problems: list[str],
          detail: dict[str, Any] | None = None) -> FormalResult:
    return FormalResult(
        check=CHECK, status=FAIL, formal_relation=RELATION,
        counterexample={"violation": violation, "problems": problems},
        assumptions=_ASSUMPTIONS, detail=detail or {})


def validate_decision(decision: dict[str, Any],
                      expected_trial_id: str | None = None) -> FormalResult:
    problems: list[str] = []
    if not isinstance(decision, dict):
        return _fail("INVALID_DECISION_ARTIFACT", ["not a JSON object"])
    missing = [k for k in REQUIRED_KEYS if k not in decision]
    if missing:
        problems.append(f"missing keys: {missing}")
    dec = decision.get("decision")
    if dec not in DECISIONS:
        problems.append(f"decision must be one of {DECISIONS}, got {dec!r}")
    if expected_trial_id is not None and decision.get("trial_id") != expected_trial_id:
        problems.append(f"trial_id mismatch: {decision.get('trial_id')!r} != "
                        f"{expected_trial_id!r}")
    for k in ("expected_information_gain", "expected_cost"):
        if decision.get(k) not in GAIN_COST:
            problems.append(f"{k} must be one of {GAIN_COST}")
    conf = decision.get("confidence")
    if not isinstance(conf, (int, float)) or not (0.0 <= float(conf) <= 1.0):
        problems.append("confidence must be a number in [0,1]")
    basis = decision.get("decision_basis")
    if not isinstance(basis, list) or not basis:
        problems.append("decision_basis must be a non-empty list")

    uds = decision.get("unresolved_distinctions", [])
    ecc = decision.get("expected_child_contribution", [])
    lrp = decision.get("local_resolution_path", [])
    for name, v in (("unresolved_distinctions", uds),
                    ("expected_child_contribution", ecc),
                    ("local_resolution_path", lrp)):
        if not isinstance(v, list):
            problems.append(f"{name} must be a list")
    if problems:
        return _fail("INVALID_DECISION_ARTIFACT", problems)

    ud_ids = []
    for i, d in enumerate(uds):
        if not isinstance(d, dict) or not all(
                k in d for k in ("id", "question",
                                 "why_local_evidence_is_insufficient")):
            problems.append(f"unresolved_distinctions[{i}] missing required "
                            "keys (id, question, "
                            "why_local_evidence_is_insufficient)")
        else:
            ud_ids.append(d["id"])
    for i, c in enumerate(ecc):
        if not isinstance(c, dict) or not all(
                k in c for k in ("distinction_id", "expected_evidence",
                                 "why_isolation_matters")):
            problems.append(f"expected_child_contribution[{i}] missing "
                            "required keys (distinction_id, expected_evidence, "
                            "why_isolation_matters)")
    if problems:
        return _fail("INVALID_DECISION_ARTIFACT", problems)

    if dec == "CREATE":
        if not uds:
            problems.append("CREATE requires at least one unresolved "
                            "distinction")
        if not ecc:
            problems.append("CREATE requires at least one expected child "
                            "contribution")
        dangling = [c["distinction_id"] for c in ecc
                    if c["distinction_id"] not in ud_ids]
        if dangling:
            problems.append("expected_child_contribution references unknown "
                            f"distinction ids: {dangling}")
        if problems:
            return _fail("INVALID_CREATION_DECISION", problems,
                         {"decision": dec})
    else:  # DO_NOT_CREATE
        if not lrp:
            problems.append("DO_NOT_CREATE requires a non-empty "
                            "local_resolution_path")
        if ecc:
            problems.append("DO_NOT_CREATE must not carry expected child "
                            "contributions")
        if problems:
            return _fail("INVALID_DECISION_ARTIFACT", problems,
                         {"decision": dec})

    return FormalResult(
        check=CHECK, status=PASS, formal_relation=RELATION,
        evidence=[f"trial_id: {decision['trial_id']}",
                  f"decision: {dec}",
                  f"unresolved_distinctions: {len(uds)}",
                  f"expected_child_contribution: {len(ecc)}",
                  f"local_resolution_path steps: {len(lrp)}",
                  f"confidence: {conf}"],
        assumptions=_ASSUMPTIONS,
        detail={"decision": dec, "distinction_ids": ud_ids})


CHILD_BUNDLE_FILES = ("child-contract.json", "child-harness.json",
                     "child-prompt.md", "child-input-manifest.json",
                     "integration-plan.json")


def validate_child_bundle(bundle_dir: str | Path,
                          trial_contract: dict[str, Any],
                          child_envelope: dict[str, Any],
                          package_files: list[str],
                          clean_room_exclusions: list[str],
                          ) -> tuple[FormalResult, dict[str, Any]]:
    """Deterministic CREATE-path validation. Returns (result, artifacts)
    where artifacts carries parsed pieces for the realization step."""
    from formal import compile_harness_spec, check_attenuation

    bundle_dir = Path(bundle_dir)
    problems: list[str] = []
    artifacts: dict[str, Any] = {}

    missing = [f for f in CHILD_BUNDLE_FILES
               if not (bundle_dir / f).exists()]
    if missing:
        return (_fail("INVALID_CHILD_BUNDLE",
                      [f"missing bundle files: {missing}"]), artifacts)

    def _load(name):
        try:
            return json.loads((bundle_dir / name).read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            problems.append(f"{name}: invalid JSON: {e}")
            return None

    child_contract = _load("child-contract.json")
    child_harness = _load("child-harness.json")
    manifest = _load("child-input-manifest.json")
    plan = _load("integration-plan.json")
    if problems:
        return (_fail("INVALID_CHILD_BUNDLE", problems), artifacts)
    artifacts.update(child_contract=child_contract,
                     child_harness=child_harness,
                     manifest=manifest, plan=plan)

    # Attenuation against the trial contract AND against the child envelope.
    att_trial = check_attenuation(trial_contract, child_contract)
    att_env = check_attenuation(child_envelope, child_contract)
    artifacts["attenuation_vs_trial"] = att_trial
    artifacts["attenuation_vs_envelope"] = att_env
    if att_trial.status != PASS:
        problems.append("child contract fails attenuation against "
                        "K-E5-trial")
    if att_env.status != PASS:
        problems.append("child contract exceeds the child envelope "
                        "K-E5-child-max")

    # Kernel compilation of the proposed child topology under its contract.
    try:
        artifacts["child_lts"] = compile_harness_spec(child_harness,
                                                      child_contract)
    except Exception as e:  # SemanticsError or validation error
        problems.append(f"child harness does not compile under child "
                        f"contract: {e}")

    # Input manifest: files must exist in the package and respect clean-room
    # exclusions.
    files = manifest.get("files") if isinstance(manifest, dict) else None
    if not isinstance(files, list) or not files:
        problems.append("child-input-manifest.json must carry a non-empty "
                        "'files' list")
    else:
        unknown = [f for f in files if f not in package_files]
        leaked = [f for f in files if f in clean_room_exclusions]
        if unknown:
            problems.append(f"manifest references files outside the public "
                            f"package: {unknown}")
        if leaked:
            problems.append("manifest includes clean-room-excluded "
                            f"contamination sources: {leaked}")

    # Integration plan must be mechanically executable.
    if isinstance(plan, dict):
        method = plan.get("method")
        if method not in ("clean_room_comparison", "direct"):
            problems.append("integration-plan method must be "
                            "'clean_room_comparison' or 'direct'")
        if not isinstance(plan.get("verdict_rule"), dict) or not plan["verdict_rule"]:
            problems.append("integration-plan must carry a non-empty "
                            "verdict_rule object")
        if not plan.get("child_deliverable"):
            problems.append("integration-plan must name the child_deliverable "
                            "file")
    else:
        problems.append("integration-plan.json must be an object")

    if problems:
        return (_fail("INVALID_CHILD_BUNDLE", problems,
                      {"bundle_dir": str(bundle_dir)}), artifacts)

    return (FormalResult(
        check="child_bundle_validation", status=PASS,
        formal_relation="child bundle deterministically valid for realization",
        evidence=[f"bundle: {bundle_dir}",
                  "attenuation vs K-E5-trial: PASS",
                  "attenuation vs K-E5-child-max: PASS",
                  f"child LTS: {len(artifacts['child_lts'].states)} states, "
                  f"{len(artifacts['child_lts'].transitions)} transitions",
                  f"manifest files: {files}",
                  f"integration method: {plan.get('method')}"],
        assumptions=_ASSUMPTIONS), artifacts)
