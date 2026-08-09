"""Shared deterministic verification helpers for Experiment 6 task verifiers.

Every per-task verify.py is a preregistered deterministic program: it loads
the trial record, decides per-requirement satisfaction (including
admissibility/authorship conditions), flags duplicate evidence, computes
the verification effect, and emits verification.json. It never solves the
task judgmentally — all ground truths are frozen (in the private label or
recomputed mechanically from the package's own reference artifacts).

Requirement satisfaction semantics (frozen in utility-operationalization.md):
  satisfied_by in {"parent", "child", "examiner", "integration", "none"}.
Duplicate rule: a child/examiner evidence record that adds no new item, no
material divergence, and no changed deliverable field duplicates parent
evidence; a dissent, a new item, or a settled pending field is novel.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from typing import Any, Callable, Optional


class TrialView:
    def __init__(self, td: Path):
        self.td = td
        self.task = self._j("task.json")
        self.result = self._j("result.json")
        self.resolution = self._j("resolution.json")
        self.evidence = self._j("evidence.json") or []
        self.child_dir = td / "child"
        self.child_present = (self.child_dir / "launch-provenance.json"
                              ).exists()
        self.child_plan = (self._j("child/integration-plan.json")
                           if (self.child_dir /
                               "integration-plan.json").exists() else None)
        self.child_manifest = (self._j("child/child-input-manifest.json")
                               if (self.child_dir /
                                   "child-input-manifest.json").exists()
                               else None)
        exam = td / "examiner" / "independent-verification.json"
        self.examiner_present = (td / "examiner" /
                                 "launch-provenance.json").exists()
        self.examiner_doc = (json.loads(exam.read_text(encoding="utf-8"))
                             if exam.exists() else None)

    def _j(self, rel: str) -> Any:
        p = self.td / rel
        if not p.exists():
            return None
        return json.loads(p.read_text(encoding="utf-8"))

    def bank_private(self) -> Path:
        """Locate this trial's private bank directory from the label copy
        placed beside verify.py (verify.py lives in it)."""
        raise NotImplementedError  # unused; verify.py knows its own dir

    def child_file(self, name: str) -> Optional[Path]:
        p = self.child_dir / name
        return p if p.exists() else None


def load(trial_dir: str | Path) -> TrialView:
    return TrialView(Path(trial_dir))


def child_with_role(view: TrialView, *roles: str,
                    exclusions: Optional[list[str]] = None
                    ) -> tuple[bool, str]:
    """Structural check: a realized child with one of the given roles whose
    input manifest honors the exclusions."""
    if not view.child_present:
        return False, "no realized child"
    if view.child_plan is None or view.child_manifest is None:
        return False, "child bundle incomplete"
    role = str(view.child_plan.get("role", ""))
    # Experiment 7: canonical role names are declared equivalents of the
    # E6 vocabulary (preregistration §2 role map, frozen at Phase A)
    _CANON_TO_E6 = {"clean_room_author": "clean_room_implementer",
                    "non_author_examiner": "adversarial_searcher",
                    "method_disjoint_verifier": "independent_verifier",
                    "independent_decomposer": "independent_decomposer"}
    role = _CANON_TO_E6.get(role, role)
    if role not in roles:
        return False, f"child role {role!r} not in {roles}"
    files = [str(f) for f in view.child_manifest.get("files", [])]
    for x in (exclusions or []):
        if x in files:
            return False, f"excluded artifact {x} present in child inputs"
    return True, f"child role {role}; manifest honors exclusions"


def examiner_ok(view: TrialView) -> tuple[bool, str]:
    if not view.examiner_present:
        return False, "no examiner launched"
    doc = view.examiner_doc
    if not isinstance(doc, dict):
        return False, "examiner produced no verification document"
    if not str(doc.get("method", "")).strip():
        return False, "examiner document lacks a method statement"
    if doc.get("overall") not in ("CONFIRMED", "DISPUTED"):
        return False, "examiner document lacks an overall verdict"
    return True, f"examiner {doc.get('overall')}"


def load_py_function(path: Path, fn_name: str) -> Callable:
    """Execute a small task-artifact python file and return a function.
    Used only on preregistered package references and on child-authored
    implementation files inside the governed experiment."""
    ns: dict[str, Any] = {}
    code = path.read_text(encoding="utf-8")
    exec(compile(code, str(path), "exec"), ns)  # noqa: S102
    fn = ns.get(fn_name)
    if not callable(fn):
        raise RuntimeError(f"{path} does not define {fn_name}()")
    return fn


def requirement(satisfied: bool, satisfied_by: str, why: str
                ) -> dict[str, Any]:
    return {"satisfied": bool(satisfied),
            "satisfied_by": satisfied_by if satisfied else "none",
            "why": why}


def emit(out: str | Path, *, trial_id: str, requirements: dict[str, Any],
         result_correct: bool, verification_effect: str,
         duplicate_evidence_ids: list[str],
         extra_evidence_records: list[dict[str, Any]],
         details: dict[str, Any]) -> dict[str, Any]:
    doc = {
        "trial_id": trial_id,
        "task_verified": all(r["satisfied"] for r in requirements.values()),
        "result_correct": bool(result_correct),
        "requirements": requirements,
        "verification_effect": verification_effect,
        "duplicate_evidence_ids": sorted(duplicate_evidence_ids),
        "extra_evidence_records": extra_evidence_records,
        "details": details,
    }
    Path(out).write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    return doc


def cli(main_fn: Callable[[Path, Path], Any]) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--trial-dir", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    main_fn(Path(a.trial_dir), Path(a.out))


def text_of_result(view: TrialView) -> str:
    return json.dumps(view.result or {}, sort_keys=True)


def findings_text(view: TrialView) -> str:
    """Combined free text of the worker's findings for pattern checks."""
    parts = [json.dumps(view.result or {}, sort_keys=True)]
    for r in (view.resolution or {}).get("resolutions", []):
        parts.append(str(r.get("answer", "")))
    for e in view.evidence:
        parts.append(str(e.get("description", "")))
    return " ".join(parts)
