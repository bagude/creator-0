"""Historical replay: candidate theory versions against frozen cases.

    replay(candidate_theory, frozen_cases) -> ReplayResult

Each frozen case pins historical artifacts by sha256 and names the
principles whose active presence the historical outcome supports. A case is:

    COMPATIBLE     every required principle is active in the candidate theory
                   and every pinned artifact is byte-identical to its pin
    CONTRADICTED   a required principle is missing, retired, or falsified in
                   the candidate theory (the revision contradicts frozen
                   historical evidence)
    INDETERMINATE  a pinned artifact is missing or its hash drifted (the
                   historical record cannot ground the case), or the case is
                   malformed

Replay acceptability for gating: zero CONTRADICTED cases. Historical replay
is evidence, not universal proof: compatibility with five frozen cases does
not establish the revised theory in general.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from typing import Any, Optional

from .model import ReplayResult, TheoryVersion

CORPUS_PATH = Path(__file__).resolve().parent / "replay-corpus.json"


def load_replay_corpus(path: str | Path | None = None) -> list[dict[str, Any]]:
    p = Path(path) if path else CORPUS_PATH
    doc = json.loads(p.read_text(encoding="utf-8"))
    cases = doc.get("cases", [])
    if not cases:
        raise ValueError(f"replay corpus {p} has no cases")
    return cases


def _artifact_state(pins: dict[str, str], root: Path) -> tuple[bool, list[str]]:
    problems = []
    for rel, expect in pins.items():
        f = root / rel
        if not f.exists():
            problems.append(f"missing frozen artifact: {rel}")
            continue
        got = hashlib.sha256(f.read_bytes()).hexdigest()
        if got != expect:
            problems.append(f"frozen artifact drifted: {rel} "
                            f"({got[:12]}... != {expect[:12]}...)")
    return not problems, problems


def replay(candidate_theory: TheoryVersion,
           frozen_cases: Optional[list[dict[str, Any]]] = None,
           repo_root: str | Path | None = None,
           ) -> ReplayResult:
    cases = frozen_cases if frozen_cases is not None else load_replay_corpus()
    root = Path(repo_root) if repo_root else Path(__file__).resolve().parents[1]
    active = {p.id for p in candidate_theory.active_principles()}

    results = []
    compatible = contradicted = indeterminate = 0
    for case in cases:
        cid = case.get("case_id", "<unnamed>")
        required = case.get("required_active_principles", [])
        pins = case.get("pinned_artifacts", {})
        if not required or not pins:
            results.append({"case_id": cid, "result": "INDETERMINATE",
                            "why": "malformed case: missing required "
                                   "principles or pinned artifacts"})
            indeterminate += 1
            continue
        pins_ok, pin_problems = _artifact_state(pins, root)
        if not pins_ok:
            results.append({"case_id": cid, "result": "INDETERMINATE",
                            "why": "; ".join(pin_problems)})
            indeterminate += 1
            continue
        missing = sorted(set(required) - active)
        if missing:
            results.append({
                "case_id": cid, "result": "CONTRADICTED",
                "why": f"candidate theory lacks active principles {missing} "
                       "required by the frozen historical outcome: "
                       + case.get("historical_outcome", "")})
            contradicted += 1
        else:
            results.append({"case_id": cid, "result": "COMPATIBLE",
                            "why": f"required principles {sorted(required)} "
                                   "active; pinned artifacts byte-identical"})
            compatible += 1

    return ReplayResult(
        theory_version=candidate_theory.version,
        case_results=results,
        compatible=compatible,
        contradicted=contradicted,
        indeterminate=indeterminate,
        acceptable=(contradicted == 0),
    )
