"""E7 Phase C: import the 264 frozen E6 theory-evidence events with
provenance into the canonical theory store (promoted ingest layer).

Deterministic sequence (per preregistration §3 and the infra verifier's
composition note): source-pin verification PASS is recorded adjacent to the
import manifest, label pins are re-verified before the enrichment join, the
ingest is idempotent, and the checkpoint is re-verified afterward (the
pinned empty head is a valid prefix of the extended chain).
"""
from __future__ import annotations
import hashlib
import json
import subprocess
import sys
from pathlib import Path

E7 = Path(__file__).resolve().parents[1]
CZROOT = E7.parent
REPO = CZROOT.parent
sys.path.insert(0, str(CZROOT))


def tt(name: str):
    import importlib
    import importlib.util
    if "cz_topology_theory" not in sys.modules:
        spec = importlib.util.spec_from_file_location(
            "cz_topology_theory", CZROOT / "topology-theory" / "__init__.py",
            submodule_search_locations=[str(CZROOT / "topology-theory")])
        pkg = importlib.util.module_from_spec(spec)
        sys.modules["cz_topology_theory"] = pkg
        spec.loader.exec_module(pkg)
    return importlib.import_module(f"cz_topology_theory.{name}")


def jdump(p: Path, obj) -> None:
    p.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n",
                 encoding="utf-8")


def main() -> int:
    ingest = tt("ingest")
    store_mod = tt("theory_store")
    pins = json.loads((E7 / "frozen-inputs" / "e6-input-pins.json"
                       ).read_text(encoding="utf-8"))
    src_pin = pins["e6_evidence_source"]
    src = REPO / src_pin["path"]

    # 1. source pin (NC4 guard) — recorded adjacent to the manifest
    pin_result = ingest.verify_source_pin(src, src_pin)
    if pin_result["status"] != "PASS":
        jdump(E7 / "evidence-import-manifest.json", {
            "artifact": "evidence import manifest",
            "status": "FAIL", "source_pin": pin_result})
        print("IMPORT REFUSED:", pin_result["failure_code"])
        return 2

    # 2. label truth-artifact pins re-verified before the join
    labels = {}
    for rel, pin in pins["e6_truth_artifacts"].items():
        p = REPO / rel
        got = hashlib.sha256(p.read_bytes()).hexdigest()
        if got != pin["sha256"]:
            print(f"IMPORT REFUSED: label drifted: {rel}")
            return 2
        labels[rel.split("/")[-3]] = json.loads(
            p.read_text(encoding="utf-8"))

    # 3. deterministic enrichment + idempotent ingest
    raw = ingest.load_source_events(src)
    source_artifact_id = ingest.pin_source_artifact(
        src,
        "creator-0/experiment-6/theory-evidence-events")["artifact_id"]
    enriched = ingest.enrich_e6_events(
        raw, labels,
        source_commit=src_pin["source_commit"],
        source_path=src_pin["path"],
        source_artifact_id=source_artifact_id)
    n_ok = sum(1 for e in enriched
               if e["context"].get("context_status") == "OK")
    store = store_mod.TheoryStore(CZROOT / "state" / "topology-theory")
    manifest = ingest.ingest_evidence(store, enriched, {
        "artifact": "evidence import manifest (E6 -> theory store)",
        "source": {
            "path": src_pin["path"],
            "sha256": src_pin["sha256"],
            "git_blob_sha": src_pin["git_blob_sha"],
            "source_commit": src_pin["source_commit"],
            "artifact_id": source_artifact_id,
        },
        "source_pin_verification": pin_result,
        "expected_event_count": src_pin["expected_event_count"],
        "context_resolved_events": n_ok,
        "enrichment": {
            "join_key": "trial_id",
            "truth_artifacts": sorted(pins["e6_truth_artifacts"]),
            "class_to_kind": pins["e6_class_to_admissibility_kind"],
        },
        "normalized_event_hashes_sha256": hashlib.sha256(
            json.dumps([ingest.normalized_event_hash(e) for e in enriched],
                       separators=(",", ":")).encode()).hexdigest(),
    })
    jdump(E7 / "evidence-import-manifest.json", manifest)

    # 4. checkpoint re-verification (prefix semantics)
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "lineage", CZROOT / "lineage" / "__init__.py",
        submodule_search_locations=[str(CZROOT / "lineage")])
    lin = importlib.util.module_from_spec(spec)
    sys.modules["lineage"] = lin
    spec.loader.exec_module(lin)
    cp = json.loads((E7 / "base-checkpoint.json").read_text(encoding="utf-8"))
    res = lin.verify_checkpoint(REPO, cp)
    jdump(E7 / "checkpoint-verification-post-import.json", res.to_dict())

    print(f"imported={manifest['imported']} "
          f"skipped={manifest['skipped_identical']} "
          f"conflicts={manifest['conflicts']} "
          f"context_ok={n_ok}/{len(enriched)} "
          f"head_after={manifest['evidence_head_after']} "
          f"chain_intact={manifest['append_only_intact']} "
          f"checkpoint_reverify={res.status}")
    return 0 if res.status == "PASS" else 2


if __name__ == "__main__":
    sys.exit(main())
