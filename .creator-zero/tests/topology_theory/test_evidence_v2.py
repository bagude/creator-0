"""Evidence schema v2 + import layer (spec §20.2, NC4-NC6)."""
from __future__ import annotations
import json
import tempfile
import unittest
from pathlib import Path

import _bootstrap
from _bootstrap import CZROOT, TT

E6_SOURCE = CZROOT / "experiment-6" / "theory-evidence-events.jsonl"
PINS = json.loads((CZROOT / "experiment-7" / "frozen-inputs" /
                   "e6-input-pins.json").read_text(encoding="utf-8"))


def _labels():
    out = {}
    for d in sorted((CZROOT / "experiment-6" / "task-bank").iterdir()):
        lab = d / "private" / "label.json"
        if lab.exists():
            out[d.name] = json.loads(lab.read_text(encoding="utf-8"))
    return out


class SchemaV2Test(unittest.TestCase):
    def test_v1_event_parses(self):
        e = TT.PrincipleEvidence.from_dict({
            "principle_id": "P-LOCALITY", "topology_id": "H-x-local",
            "prediction_id": "H-x-local-pr01", "effect": "SUPPORT"})
        self.assertEqual(e.trial_id, "")
        self.assertEqual(e.context, {})

    def test_v2_context_round_trips_exactly(self):
        d = {"principle_id": "P-INDEPENDENCE", "topology_id": "H-t-iso",
             "prediction_id": "H-t-iso-pr02", "effect": "FALSIFY",
             "evidence_refs": [{"k": 1}], "event_id": "ev-1",
             "source_experiment": "experiment-6",
             "source_commit": "bd0cf91e455393d3d601070e5022c565d9ed9ed1",
             "trial_id": "e6-t08", "run": "shadow",
             "context": {"context_status": "OK",
                         "admissibility_kind": "NON_AUTHOR_SEARCH",
                         "latent_class": "COUNTEREXAMPLE"},
             "source_artifact_id": "sha256:abc"}
        e = TT.PrincipleEvidence.from_dict(d)
        self.assertEqual(e.to_dict(), d)

    def test_unknown_top_level_field_is_typed_rejection(self):
        # NC6: a context-stripping parser cannot pass — nothing is silently
        # dropped
        with self.assertRaises(TT.ModelValidationError):
            TT.PrincipleEvidence.from_dict({
                "principle_id": "P-X", "topology_id": "t",
                "prediction_id": "p", "effect": "SUPPORT",
                "surprise_context_field": {"x": 1}})

    def test_e6_source_lines_parse_with_trial_and_run(self):
        lines = [json.loads(l) for l in
                 E6_SOURCE.read_text(encoding="utf-8").splitlines()
                 if l.strip()]
        self.assertEqual(len(lines), 264)
        for raw in lines[:5]:
            e = TT.PrincipleEvidence.from_dict(raw)
            self.assertTrue(e.trial_id.startswith("e6-t"))
            self.assertIn(e.run, ("primary", "shadow"))


class ImportLayerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.store = TT.TheoryStore(self.tmp)
        self.pin = PINS["e6_evidence_source"]

    def test_source_pin_verifies(self):
        r = TT.ingest.verify_source_pin(E6_SOURCE, self.pin)
        self.assertEqual(r["status"], "PASS", r)

    def test_mutated_source_fails_pin(self):
        # NC4
        mutated = Path(self.tmp) / "mutated.jsonl"
        text = E6_SOURCE.read_text(encoding="utf-8")
        mutated.write_text(text.replace("SUPPORT", "FALSIFY", 1),
                           encoding="utf-8")
        r = TT.ingest.verify_source_pin(mutated, self.pin)
        self.assertEqual(r["status"], "FAIL")
        self.assertEqual(r["failure_code"], "EVIDENCE_SOURCE_MISMATCH")

    def test_enrichment_joins_context_and_preserves_provenance(self):
        raw = TT.ingest.load_source_events(E6_SOURCE)
        enriched = TT.ingest.enrich_e6_events(
            raw, _labels(), source_commit="bd0cf91", source_path="x",
            source_artifact_id="sha256:src")
        self.assertEqual(len(enriched), 264)
        ok = [e for e in enriched
              if e["context"].get("context_status") == "OK"]
        self.assertEqual(len(ok), 264)
        kinds = {e["context"]["admissibility_kind"] for e in ok}
        self.assertLessEqual(
            kinds, {"LOCAL", "CLEAN_ROOM_AUTHORSHIP", "NON_AUTHOR_SEARCH",
                    "INDEPENDENT_DECOMPOSITION",
                    "METHOD_DISJOINT_VERIFICATION"})
        for e in enriched[:10]:
            self.assertTrue(e["trial_id"])
            self.assertIn(e["run"], ("primary", "shadow"))

    def test_idempotent_import_and_conflict(self):
        raw = TT.ingest.load_source_events(E6_SOURCE)[:6]
        enriched = TT.ingest.enrich_e6_events(
            raw, _labels(), source_commit="c", source_path="p",
            source_artifact_id="sha256:s")
        m1 = TT.ingest.ingest_evidence(self.store, enriched)
        self.assertEqual(m1["imported"], 6)
        self.assertTrue(m1["append_only_intact"])
        m2 = TT.ingest.ingest_evidence(self.store, enriched)
        self.assertEqual(m2["imported"], 0)
        self.assertEqual(m2["skipped_identical"], 6)
        # NC5: same id, different content
        bad = dict(enriched[0])
        bad["effect"] = "FALSIFY" if bad["effect"] != "FALSIFY" else "SUPPORT"
        with self.assertRaises(TT.ingest.EvidenceImportError):
            TT.ingest.ingest_evidence(self.store, [bad])
        chain = self.store.verify_append_only()
        self.assertTrue(chain["append_only_intact"])
        self.assertEqual(chain["log_length"], 6)


if __name__ == "__main__":
    unittest.main()
