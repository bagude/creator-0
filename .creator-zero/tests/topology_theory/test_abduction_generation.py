"""Abduction (independence/locality) and candidate generation."""
from __future__ import annotations
import json
import unittest

import _bootstrap
from _bootstrap import CZROOT, TT

CONTRACT = json.loads(
    (CZROOT / "contracts/root_contract.json").read_text(encoding="utf-8"))
TASK = {"task_id": "t-abd"}

D_LOCAL = [{"id": "Q1", "question": "is the invariant satisfied?",
            "features": {"locally_resolvable": True}}]
D_ISO = [{"id": "Q1", "question": "does a clean-room impl diverge?",
          "features": {"requires_isolation": True, "contamination": True}},
         {"id": "Q2", "question": "is the local artifact well-formed?",
          "features": {"locally_resolvable": True}}]


class AbductionTest(unittest.TestCase):
    def setUp(self):
        self.theory = TT.build_seed_theory()

    def _app(self, dist, **kw):
        return TT.abduce(TASK, dist, contract=CONTRACT, theory=self.theory,
                         **kw)

    def test_independence_abduction(self):
        app = self._app(D_ISO)
        by = {a["principle_id"]: a for a in app.applicable}
        self.assertIn("P-INDEPENDENCE", by)
        self.assertEqual(by["P-INDEPENDENCE"]["distinction_ids"], ["Q1"])
        self.assertEqual(app.sources["P-INDEPENDENCE"], "deterministic")

    def test_locality_abduction(self):
        app = self._app(D_LOCAL)
        by = {a["principle_id"]: a for a in app.applicable}
        self.assertIn("P-LOCALITY", by)
        self.assertEqual(by["P-LOCALITY"]["distinction_ids"], ["Q1"])
        self.assertNotIn("P-INDEPENDENCE",
                         [a["principle_id"] for a in app.applicable
                          if a["distinction_ids"]])

    def test_model_applicability_is_serialized_and_validated(self):
        app = self._app(D_LOCAL,
                        model_applicability={"P-INDEPENDENCE": ["Q1"]})
        by = {a["principle_id"]: a for a in app.applicable}
        self.assertIn("P-INDEPENDENCE", by)
        self.assertEqual(app.sources["P-INDEPENDENCE"], "model")

    def test_model_applicability_unknown_principle_rejected(self):
        with self.assertRaises(TT.ModelValidationError):
            self._app(D_LOCAL, model_applicability={"P-NONEXISTENT": ["Q1"]})

    def test_model_applicability_unknown_distinction_rejected(self):
        with self.assertRaises(TT.ModelValidationError):
            self._app(D_LOCAL, model_applicability={"P-LOCALITY": ["Q99"]})


class GenerationTest(unittest.TestCase):
    def setUp(self):
        self.theory = TT.build_seed_theory()

    def _cands(self, dist, contract=CONTRACT, **kw):
        app = TT.abduce(TASK, dist, contract=contract, theory=self.theory)
        return TT.generate_candidates(TASK, dist, app, contract, **kw)

    def test_multiple_candidates_generated(self):
        cands = self._cands(D_ISO)
        self.assertGreaterEqual(len(cands), 2)
        self.assertLessEqual(len(cands), 4)
        ids = [c.topology_id for c in cands]
        self.assertEqual(len(ids), len(set(ids)))

    def test_isolation_yields_child_bearing_candidate(self):
        cands = self._cands(D_ISO)
        kinds = {c.topology_id: c for c in cands}
        self.assertTrue(any("isolated-child" in t or "branching" in t
                            for t in kinds))
        child = kinds["H-t-abd-isolated-child"]
        self.assertEqual(child.resolution_map["Q1"], "child-return")

    def test_no_create_candidates_when_contract_forbids(self):
        c = dict(CONTRACT)
        c["may_create_creator"] = False
        cands = self._cands(D_ISO, contract=c)
        for cand in cands:
            for n in cand.harness_spec["nodes"]:
                self.assertNotEqual(n["primitive"], "create",
                                    f"{cand.topology_id} creates despite "
                                    "contract denial")

    def test_max_candidates_respected(self):
        self.assertLessEqual(len(self._cands(D_ISO, max_candidates=2)), 2)

    def test_every_candidate_has_resolution_map_and_falsifiers(self):
        for c in self._cands(D_ISO):
            self.assertEqual(set(c.resolution_map), {"Q1", "Q2"})
            self.assertTrue(c.falsifiers)
            self.assertTrue(c.harness_spec_ref.startswith("sha256:"))


if __name__ == "__main__":
    unittest.main()
