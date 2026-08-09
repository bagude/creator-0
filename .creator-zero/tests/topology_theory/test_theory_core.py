"""Theory core: principle validation, append-only evidence, version lineage."""
from __future__ import annotations
import json
import tempfile
import unittest
from pathlib import Path

import _bootstrap
from _bootstrap import TT


class PrincipleValidationTest(unittest.TestCase):
    def test_valid_seed_principles(self):
        ps = TT.principles.seed_principles()
        self.assertEqual(len(ps), 9)
        for p in ps:
            self.assertTrue(p.id.startswith("P-"))
            self.assertTrue(p.supporting_evidence,
                            f"{p.id} seeded without frozen evidence")
            for e in p.supporting_evidence:
                self.assertRegex(e["sha256"], r"^[0-9a-f]{64}$")

    def test_invalid_status_rejected(self):
        with self.assertRaises(TT.ModelValidationError):
            TT.Principle(id="P-X", statement="s", status="MAYBE")

    def test_bad_id_and_empty_statement_rejected(self):
        with self.assertRaises(TT.ModelValidationError):
            TT.Principle(id="X-1", statement="s")
        with self.assertRaises(TT.ModelValidationError):
            TT.Principle(id="P-X", statement="   ")

    def test_evidence_effect_closed(self):
        with self.assertRaises(TT.ModelValidationError):
            TT.PrincipleEvidence(principle_id="P-X", topology_id="t",
                                 prediction_id="p", effect="MAYBE")


class TheoryStoreTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.store = TT.TheoryStore(self.tmp)
        self.theory = TT.build_seed_theory()

    def _evidence(self, n=1, effect="SUPPORT"):
        return TT.PrincipleEvidence(
            principle_id="P-LOCALITY", topology_id="H-x",
            prediction_id=f"pr{n}", effect=effect, event_id=f"ev{n}")

    def test_append_only_evidence_chain(self):
        self.store.append_evidence(self._evidence(1))
        self.store.append_evidence(self._evidence(2, "CHALLENGE"))
        chk = self.store.verify_append_only()
        self.assertTrue(chk["append_only_intact"])
        self.assertEqual(chk["log_length"], 2)

    def test_prefix_rewrite_detected(self):
        self.store.append_evidence(self._evidence(1))
        self.store.append_evidence(self._evidence(2))
        # tamper with the first line (historical evidence rewrite)
        lines = self.store.evidence_path.read_text().splitlines()
        tampered = json.loads(lines[0])
        tampered["effect"] = "FALSIFY"
        lines[0] = json.dumps(tampered, sort_keys=True, separators=(",", ":"))
        self.store.evidence_path.write_text("\n".join(lines) + "\n")
        chk = self.store.verify_append_only()
        self.assertFalse(chk["append_only_intact"])

    def test_version_lineage_and_write_once(self):
        p1 = self.store.write_version(self.theory)
        self.assertTrue(p1.exists())
        # write-once: same version cannot be overwritten
        with self.assertRaises(TT.TheoryStoreError):
            self.store.write_version(self.theory)
        # v2 must link its predecessor by the stored artifact hash
        v1_hash = self.store.version_hash(1)
        v2 = TT.TheoryVersion.from_dict(
            {**self.theory.to_dict(), "version": 2,
             "predecessor_hash": v1_hash})
        self.store.write_version(v2)
        loaded = self.store.load(2)
        self.assertEqual(loaded.predecessor_hash, v1_hash)

    def test_version_with_wrong_lineage_rejected(self):
        self.store.write_version(self.theory)
        bad = TT.TheoryVersion.from_dict(
            {**self.theory.to_dict(), "version": 2,
             "predecessor_hash": "sha256:" + "0" * 64})
        with self.assertRaises(TT.TheoryStoreError):
            self.store.write_version(bad)

    def test_version_without_lineage_rejected(self):
        self.store.write_version(self.theory)
        bad = TT.TheoryVersion.from_dict(
            {**self.theory.to_dict(), "version": 2})
        with self.assertRaises(TT.TheoryStoreError):
            self.store.write_version(bad)


if __name__ == "__main__":
    unittest.main()
