"""Typed admissibility + grammar v2 + utility v2 (spec §20.3-20.5)."""
from __future__ import annotations
import json
import unittest

import _bootstrap
from _bootstrap import CZROOT, TT

A = TT.admissibility

CONTRACT = json.loads((CZROOT / "experiment-6" / "contracts" /
                       "trial-contract.json").read_text(encoding="utf-8"))


def req(kind, qid="Q1", method=""):
    vec, roles = A.KIND_REQUIREMENT[kind]
    return A.EvidenceRequirement(
        requirement_id=f"req-{qid}", distinction_id=qid, kind=kind,
        independence=A.IndependenceVector.of(vec), allowed_roles=roles,
        primary_method_family=method)


def prov(role, node="n1", method=""):
    return A.provision_for_role(node, role, method_family=method)


class AdmissibilityMatrixTest(unittest.TestCase):
    def test_local_satisfies_local_requirement(self):
        ok, _ = A.admissible(prov("local_author"), req("LOCAL"))
        self.assertTrue(ok)

    def test_clean_room_author_satisfies_authorship(self):
        ok, _ = A.admissible(prov("clean_room_author"),
                             req("CLEAN_ROOM_AUTHORSHIP"))
        self.assertTrue(ok)

    def test_clean_room_author_does_not_imply_decomposition(self):
        ok, cl = A.admissible(prov("clean_room_author"),
                              req("INDEPENDENT_DECOMPOSITION"))
        self.assertFalse(ok)
        self.assertFalse(cl["vector_satisfies"])

    def test_examiner_satisfies_search(self):
        ok, _ = A.admissible(prov("non_author_examiner"),
                             req("NON_AUTHOR_SEARCH"))
        self.assertTrue(ok)

    def test_verifier_does_not_imply_decomposition_or_search(self):
        self.assertFalse(A.admissible(prov("method_disjoint_verifier",
                                           method="alt"),
                                      req("INDEPENDENT_DECOMPOSITION"))[0])
        self.assertFalse(A.admissible(prov("method_disjoint_verifier",
                                           method="alt"),
                                      req("NON_AUTHOR_SEARCH"))[0])

    def test_decomposer_does_not_imply_method_disjoint(self):
        self.assertFalse(A.admissible(prov("independent_decomposer"),
                                      req("METHOD_DISJOINT_VERIFICATION"))[0])

    def test_right_graph_wrong_role_fails(self):
        # NC7: an isolated clean-room child (correct shape for isolation)
        # is inadmissible for a search requirement — wrong epistemic role
        ok, cl = A.admissible(prov("clean_room_author", node="child-return"),
                              req("NON_AUTHOR_SEARCH"))
        self.assertFalse(ok)

    def test_right_role_prohibited_source_fails(self):
        p = A.EvidenceProvision(
            node_id="n", role="non_author_examiner",
            independence=A.IndependenceVector.of((0, 1, 0, 0)),
            source="contaminated")
        r = A.EvidenceRequirement(
            requirement_id="r", distinction_id="Q1",
            kind="NON_AUTHOR_SEARCH",
            independence=A.IndependenceVector.of((0, 1, 0, 0)),
            allowed_roles=("non_author_examiner",),
            prohibited_sources=("contaminated",))
        self.assertFalse(A.admissible(p, r)[0])

    def test_method_disjointness_enforced(self):
        r = req("METHOD_DISJOINT_VERIFICATION", method="primary")
        self.assertFalse(A.admissible(
            prov("method_disjoint_verifier", method="primary"), r)[0])
        self.assertTrue(A.admissible(
            prov("method_disjoint_verifier", method="secondary"), r)[0])

    def test_vector_coverage_without_role_is_insufficient(self):
        p = A.EvidenceProvision(
            node_id="n", role="clean_room_author",
            independence=A.IndependenceVector.of((1, 1, 1, 1)))
        self.assertFalse(A.admissible(p, req("NON_AUTHOR_SEARCH"))[0])


def _distinction(qid, feature=None):
    feats = {"locally_resolvable": feature is None,
             "requires_isolation": False, "contamination": False,
             "capability_bearing_artifact": False, "spans_sessions": False,
             "requires_clean_room_authorship": False,
             "requires_nonauthor_search": False,
             "requires_independent_decomposition": False,
             "requires_method_disjoint_verification": False}
    if feature:
        feats[feature] = True
    return {"id": qid, "features": feats}


class GrammarV2Test(unittest.TestCase):
    def _gen(self, distinctions, values=None):
        values = values or {d["id"]: 0.8 for d in distinctions}
        return TT.generate_candidates_v2(
            {"task_id": "tX"}, distinctions, {"applicable": []},
            CONTRACT, values)

    def test_all_required_families_compile_and_validate(self):
        seen = set()
        for feature in (None, "requires_nonauthor_search",
                        "requires_clean_room_authorship",
                        "requires_independent_decomposition",
                        "requires_method_disjoint_verification"):
            cands = self._gen([_distinction("Q1", feature)])
            for c in cands:
                fam = TT.family_of_v2(c.topology_id)
                seen.add(fam)
                res = TT.validate_topology(c, CONTRACT)
                self.assertEqual(res.status, "PASS",
                                 f"{c.topology_id}: {res.counterexample}")
        self.assertEqual(seen, set(TT.FAMILIES_V2))

    def test_admissibility_filter_rejects_local_for_typed_task(self):
        cands = self._gen([_distinction("Q1", "requires_nonauthor_search")])
        by_fam = {TT.family_of_v2(c.topology_id): c for c in cands}
        reqs = [A.requirement_for_distinction(
            _distinction("Q1", "requires_nonauthor_search"))]
        local = by_fam["local"]
        adm = A.topology_admissible(
            A.provisions_from_spec(local.harness_spec), reqs)
        self.assertFalse(adm["admissible"])
        exam = by_fam["local-independent-examiner"]
        adm = A.topology_admissible(
            A.provisions_from_spec(exam.harness_spec), reqs)
        self.assertTrue(adm["admissible"])

    def test_examiner_beats_isolated_child_on_same_search_requirement(self):
        # spec §20.5 key regression + NC8: equal admissibility, lower cost,
        # zero marginal coverage => strictly higher utility
        cands = self._gen([_distinction("Q1", "requires_nonauthor_search")])
        by_fam = {TT.family_of_v2(c.topology_id): c for c in cands}
        exam, child = by_fam["local-independent-examiner"], \
            by_fam["isolated-searcher"]
        cfg = TT.load_utility_config()
        u_e = TT.predicted_utility(exam, cfg)
        u_c = TT.predicted_utility(child, cfg)
        self.assertEqual(exam.predicted_value["delta_e"],
                         child.predicted_value["delta_e"])
        self.assertLess(exam.predicted_value["cost"],
                        child.predicted_value["cost"])
        self.assertGreater(u_e, u_c)

    def test_inadmissible_candidate_has_zero_epistemic_value(self):
        cands = self._gen([_distinction("Q1",
                                        "requires_clean_room_authorship")])
        by_fam = {TT.family_of_v2(c.topology_id): c for c in cands}
        self.assertEqual(by_fam["local"].predicted_value["delta_e"], 0.0)

    def test_examiner_only_case_needs_no_child_under_minimality(self):
        cands = self._gen([_distinction("Q1", "requires_nonauthor_search"),
                           _distinction("Q2")])
        rank = TT.rank_candidates(
            [c for c in cands
             if c.harness_spec.get("admissibility_precheck")])
        self.assertEqual(TT.family_of_v2(rank[0]["topology_id"]),
                         "local-independent-examiner")

    def test_local_wins_for_pure_local_task(self):
        cands = self._gen([_distinction("Q1"), _distinction("Q2")])
        rank = TT.rank_candidates(cands)
        self.assertEqual(TT.family_of_v2(rank[0]["topology_id"]), "local")

    def test_redundant_examiner_penalized_on_local_task(self):
        cands = self._gen([_distinction("Q1")])
        by_fam = {TT.family_of_v2(c.topology_id): c for c in cands}
        self.assertGreater(
            by_fam["local-independent-examiner"]
            .predicted_value["redundancy"],
            by_fam["local"].predicted_value["redundancy"])

    def test_deterministic_tie_break(self):
        cands = self._gen([_distinction("Q1")])
        r1 = TT.rank_candidates(cands)
        r2 = TT.rank_candidates(list(reversed(cands)))
        self.assertEqual([r["topology_id"] for r in r1],
                         [r["topology_id"] for r in r2])

    def test_v2_predictions_typed_attribution_and_role_falsifier(self):
        d = [_distinction("Q1", "requires_nonauthor_search")]
        cands = self._gen(d)
        by_fam = {TT.family_of_v2(c.topology_id): c for c in cands}
        exam = by_fam["local-independent-examiner"]
        preds = TT.freeze_predictions_v2(exam, d)
        resolves = [p for p in preds if p.kind == "resolves"]
        self.assertEqual(resolves[0].principles, ["P-NONAUTHOR-SEARCH"])
        role_preds = [p for p in preds
                      if p.subject.get("checks") == ["ROLE_TYPE"]]
        self.assertEqual(len(role_preds), 1)
        self.assertTrue(exam.predictions_hash)


if __name__ == "__main__":
    unittest.main()
