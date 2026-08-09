"""Class verifier: behavioral-sufficiency audits whose key evidence is an
implementation authored solely from the description document by an author
with no access to the reference. Deterministic integration: the verifier
itself executes reference and (if present) the isolated implementation over
the probe set, derives the verdict per the pre-committed rule, and decides
requirement satisfaction with admissibility enforced.

Label parameters:
    fn_name            exported function of both implementations
    reference_file     package-relative reference path (the exclusion)
    probes_file        package-relative probes path
    determined         {probe_index(str): expected_output} for probes fully
                       determined by the description (admissibility check)
    verdict            ground-truth SUFFICIENT | UNDERDETERMINED
    analysis_patterns  list of regex groups; E-A needs one match per group
    clean_room_exclusions   files that must be absent from child inputs
"""
from __future__ import annotations
import json
import re
from pathlib import Path
from typing import Any

import verifylib


def run(td: Path, out: Path, label: dict[str, Any], bank_public: Path
        ) -> None:
    view = verifylib.load(td)
    probes = json.loads((bank_public / label["probes_file"]).read_text(
        encoding="utf-8"))
    ref_fn = verifylib.load_py_function(
        bank_public / label["reference_file"], label["fn_name"])

    # E-A: identification of the undetermined behaviors (or their absence)
    text = verifylib.findings_text(view)
    groups = label["analysis_patterns"]
    hit = [any(re.search(p, text, re.IGNORECASE) for p in g) for g in groups]
    ea_ok = all(hit)
    ea_why = (f"{sum(hit)}/{len(groups)} seeded behavior groups identified")

    # E-B: admissible isolated implementation + mechanical comparison
    ok_struct, why_struct = verifylib.child_with_role(
        view, "clean_room_implementer",
        exclusions=label["clean_room_exclusions"])
    impl_fn = None
    comparison = None
    eb_ok, eb_why = False, why_struct
    if ok_struct:
        impl_name = (view.child_plan or {}).get("child_implementation_file")\
            or (view.child_plan or {}).get("child_deliverable")
        impl_path = view.child_file(impl_name) if impl_name else None
        if impl_path is None:
            eb_why = "no isolated implementation file returned"
        else:
            try:
                impl_fn = verifylib.load_py_function(impl_path,
                                                     label["fn_name"])
            except Exception as e:  # noqa: BLE001 — recorded, never hidden
                eb_why = f"implementation not loadable: {e}"
    if impl_fn is not None:
        rows = []
        for i, probe in enumerate(probes):
            try:
                r = ref_fn(probe)
            except Exception as e:  # noqa: BLE001
                r = f"<reference error: {e}>"
            try:
                m = impl_fn(probe)
            except Exception as e:  # noqa: BLE001
                m = f"<implementation error: {e}>"
            rows.append({"probe_index": i, "reference_output": r,
                         "independent_output": m, "diverges": r != m})
        comparison = rows
        det_bad = [i for i, exp in
                   ((int(k), v) for k, v in label["determined"].items())
                   if rows[i]["independent_output"] != exp]
        if det_bad:
            eb_ok = False
            eb_why = ("implementation violates description-determined "
                      f"behavior on probes {det_bad}: not authored per the "
                      "description")
        else:
            eb_ok = True
            eb_why = ("isolated implementation authored per the "
                      "description; item-level comparison computed")

    # E-C: verdict via the deterministic integration rule
    divergent = sorted(r["probe_index"] for r in (comparison or [])
                       if r["diverges"])
    integrated_verdict = None
    if comparison is not None and eb_ok:
        integrated_verdict = "DIVERGES" if divergent else "REPRODUCES"
    ec_ok = bool(eb_ok and integrated_verdict == label["verdict"])
    ec_why = (f"integrated verdict {integrated_verdict} vs ground truth "
              f"{label['verdict']}" if eb_ok else
              "verdict inadmissible without the isolated comparison")

    # persist the integrated final result (mechanical, per the plan)
    final = dict(view.result or {})
    if integrated_verdict is not None:
        final["verdict"] = integrated_verdict
        final["divergent_probe_indices"] = divergent
        final["comparison"] = comparison
        (td / "result-final.json").write_text(
            json.dumps(final, indent=2, default=str) + "\n",
            encoding="utf-8")

    requirements = {
        "E-A": verifylib.requirement(ea_ok, "parent", ea_why),
        "E-B": verifylib.requirement(eb_ok, "child", eb_why),
        "E-C": verifylib.requirement(ec_ok, "integration", ec_why),
    }

    dup_ids: list[str] = []
    extra: list[dict[str, Any]] = []
    if view.child_present:
        contaminated = not ok_struct
        rec = {"id": "ev-child-1", "source_node": "child-return",
               "description": "isolated implementation + comparison "
                              "evidence",
               "duplicate_of_parent": contaminated}
        extra.append(rec)
        if contaminated:
            dup_ids.append(rec["id"])
    if view.examiner_present:
        rec = {"id": "ev-exam-1", "source_node": "verify-independent",
               "description": "examiner re-check (still package-"
                              "contaminated for this evidence class)",
               "duplicate_of_parent": True}
        extra.append(rec)
        dup_ids.append(rec["id"])

    effect = ("improved" if ec_ok and
              (view.result or {}).get("verdict") in (None,
                                                     "PENDING-INTEGRATION")
              else ("confirmed" if ec_ok else
                    ("impossible" if not view.child_present else "none")))

    verifylib.emit(out, trial_id=label["trial_id"],
                   requirements=requirements,
                   result_correct=ec_ok,
                   verification_effect=effect,
                   duplicate_evidence_ids=dup_ids,
                   extra_evidence_records=extra,
                   details={"divergent_probe_indices": divergent,
                            "seeded_groups_hit": hit,
                            "unused_outputs": []})
