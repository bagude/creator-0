"""E7 Phases H-I: evidence-driven revision proposal, historical replay,
independent verification, stage-1 evaluation authorization.

    python3 tools/revision.py draft-ws     build the wording-drafter workspace
    python3 tools/revision.py propose      deterministic candidates + selection
    python3 tools/revision.py verify-ws    build the revision-verifier workspace
    python3 tools/revision.py authorize    stage-1 evaluation authorization

Wording for the split children may come from the fresh drafting session
(draft-ws -> launch -> wording.json); structure, evidence attribution,
scoring, selection, and replay are deterministic and cannot be overridden.
"""
from __future__ import annotations
import json
import shutil
import subprocess
import sys
from pathlib import Path

E7 = Path(__file__).resolve().parents[1]
CZROOT = E7.parent
REPO = CZROOT.parent
SC = Path("/tmp/claude-0/-home-user-creator-0/"
          "87cd2a2d-a4f9-585b-836f-2648df7a6284/scratchpad/e7")
sys.path.insert(0, str(CZROOT))

DENY = {"permissions": {"deny": [
    "Read(/home/user/creator-0/**)", "Write(/home/user/creator-0/**)",
    "Edit(/home/user/creator-0/**)", "Read(/root/.claude/uploads/**)",
    "Bash", "Grep", "Glob", "Edit", "Task", "Agent", "WebFetch",
    "WebSearch", "NotebookEdit"]}}


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
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n",
                 encoding="utf-8")


def jload(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def store():
    return tt("theory_store").TheoryStore(
        CZROOT / "state" / "topology-theory")


def parent_events():
    return [e for e in store().read_evidence()
            if e.principle_id == "P-INDEPENDENCE"]


def cmd_draft_ws() -> None:
    r2 = tt("revise2")
    stats = r2.context_stats([e.to_dict() for e in parent_events()],
                             "P-INDEPENDENCE")
    theory = store().load(1)
    parent = theory.principle("P-INDEPENDENCE")
    ws = SC / "revision-draft-ws"
    if ws.exists():
        shutil.rmtree(ws)
    ws.mkdir(parents=True)
    jdump(ws / "parent-principle.json", parent.to_dict())
    jdump(ws / "context-evidence-stats.json", stats)
    jdump(ws / "required-children.json", {
        k: {"id": v["id"], "feature": v["feature"], "role": v["role"]}
        for k, v in r2.SPLIT_BASIS["P-INDEPENDENCE"].items()})
    (ws / ".claude").mkdir()
    (ws / ".claude" / "settings.json").write_text(
        json.dumps(DENY, indent=2), encoding="utf-8")
    (ws / "prompt.md").write_text("""You are R-E7-DRAFT, a fresh governed drafting session.

Creator-0's promoted principle P-INDEPENDENCE (parent-principle.json) accumulated mixed evidence in Experiment 6: context-evidence-stats.json shows SUPPORT/FALSIFY counts per admissibility context. A governed SPLIT revision will replace the coarse principle with one child principle per context; required-children.json gives each child's mandatory id, precondition feature, and canonical evidence role.

Your only job is wording: draft one precise, falsifiable STATEMENT (2-4 sentences, >= 60 characters) for each child principle. Each statement must:
- name the epistemic relation the context requires (clean-room authorship / non-author search / independent decomposition / method-disjoint verification),
- say what topology element supplies admissible evidence for it,
- say explicitly what does NOT satisfy it (the wrong-role case),
- avoid claiming value for isolation beyond what the relation requires.

Write exactly one file, wording.json, using the Write tool:
{"P-AUTHORSHIP-INDEPENDENCE": "...", "P-NONAUTHOR-SEARCH": "...", "P-INDEPENDENT-DECOMPOSITION": "...", "P-METHOD-DISJOINT-VERIFICATION": "..."}

Your text is a proposal only; deterministic validation and the Gate decide everything else. Use only Read and Write, only in this directory.
""", encoding="utf-8")
    print("draft ws:", ws)


def cmd_propose() -> None:
    r2 = tt("revise2")
    revise = tt("revise")
    model = tt("model")
    st = store()
    theory = st.load(1)
    events = [e.to_dict() for e in parent_events()]

    wording = None
    wpath = SC / "revision-draft-ws" / "wording.json"
    wording_source = "deterministic default templates"
    if wpath.exists():
        try:
            w = jload(wpath)
            if (isinstance(w, dict)
                    and all(isinstance(v, str) and len(v.strip()) >= 60
                            for v in w.values())):
                wording = {k: v.strip() for k, v in w.items()}
                wording_source = ("fresh drafting session R-E7-DRAFT "
                                  "(serialized wording.json)")
        except (json.JSONDecodeError, AttributeError):
            pass

    doc = r2.propose_revision_v2(theory, events, "P-INDEPENDENCE",
                                 wording=wording)
    doc["wording_source"] = wording_source
    outdir = E7 / "candidate-revisions"
    jdump(outdir / "proposal.json", doc)
    for name, cand in doc["candidates"].items():
        jdump(outdir / f"candidate-{name.lower().replace(' ', '')}.json",
              cand if cand else {"candidate": name, "revision": None,
                                 "note": "no structural change"})

    # theory-revision-evidence.jsonl: the grounding events, verbatim
    with (E7 / "theory-revision-evidence.jsonl").open(
            "w", encoding="utf-8") as f:
        for e in events:
            f.write(json.dumps(e, sort_keys=True) + "\n")

    selected = doc["selected"]
    print("selected:", selected, "scores:", doc["scores"])
    if selected != "SPLIT":
        print("preregistered outcome path: no SPLIT; candidate theta-v2 "
              "not built")
        return

    rev = model.Revision.from_dict(doc["candidates"]["SPLIT"])
    pred_hash = st.version_hash(1)
    candidate = revise.apply_revision(theory, rev, pred_hash)
    jdump(outdir / "candidate-theta-v2.json", candidate.to_dict())

    # historical replay of the candidate (v0.1 corpus + frozen E6 cases)
    replay = tt("replay")
    cases = replay.load_replay_corpus()
    cases += replay.load_replay_corpus(
        CZROOT / "topology-theory" / "replay-corpus-e6.json")
    rep = replay.replay(candidate, cases, repo_root=CZROOT)
    jdump(E7 / "historical-replay" / "candidate-theta-v2-replay.json",
          rep.to_dict())
    print("replay:", f"compatible={rep.compatible} "
          f"contradicted={rep.contradicted} "
          f"indeterminate={rep.indeterminate} acceptable={rep.acceptable}")


def cmd_verify_ws() -> None:
    ws = SC / "revision-verify-ws"
    if ws.exists():
        shutil.rmtree(ws)
    ws.mkdir(parents=True)
    for src, dst in (
            (E7 / "candidate-revisions" / "proposal.json", "proposal.json"),
            (E7 / "candidate-revisions" / "candidate-theta-v2.json",
             "candidate-theta-v2.json"),
            (E7 / "historical-replay" / "candidate-theta-v2-replay.json",
             "replay-result.json"),
            (E7 / "evidence-import-manifest.json",
             "evidence-import-manifest.json"),
            (E7 / "preregistration.md", "preregistration.md"),
            (CZROOT / "state" / "topology-theory" / "theta-v1.json",
             "theta-v1.json")):
        shutil.copy(src, ws / dst)
    (ws / ".claude").mkdir()
    (ws / ".claude" / "settings.json").write_text(
        json.dumps(DENY, indent=2), encoding="utf-8")
    (ws / "prompt.md").write_text("""You are IV-E7-REV, an independent information-only verifier in a fresh governed session. No write access to canonical state; no promotion authority; your report is evidence, never authorization.

Review the Experiment 7 candidate theory revision:
- preregistration.md sections 6-8 define the frozen revision rules, replay requirements, and two-stage gate.
- proposal.json is the deterministic candidate family with context stats, trigger, scores, and selection.
- candidate-theta-v2.json is the successor theory document built from the selected revision.
- replay-result.json is the historical replay of the candidate.
- evidence-import-manifest.json documents the provenance of the grounding evidence.
- theta-v1.json is the promoted predecessor.

Adversarially check, at minimum:
1. The SPLIT trigger clauses are actually satisfied by the context stats (recompute the support-rate spread and context coverage yourself from the counts).
2. The explanation scores follow preregistration section 6 exactly; the selection follows the frozen rule.
3. Each child principle: unique id, parent linkage to P-INDEPENDENCE, distinct precondition feature, distinct predicted effects, explicit falsifier, non-empty motivating evidence drawn only from its own context.
4. candidate-theta-v2: version 2, status CANDIDATE, predecessor_hash present, parent P-INDEPENDENCE marked REVISED (still active), all nine v1 principles retained.
5. Replay: zero CONTRADICTED, zero INDETERMINATE.
6. Nothing in these artifacts claims or performs promotion.

Write exactly two files using the Write tool:
1. independent-verification.json: {"verifier": "IV-E7-REV", "verdict": "PASS" or "FAIL", "checks": [...], "findings": [...], "summary": "..."}
2. execution-ledger.jsonl: one line per verification step, actor "node:verify-independent", metadata.completes_node "verify-independent".

Use only Read and Write, only in this directory.
""", encoding="utf-8")
    print("verify ws:", ws)


def cmd_authorize() -> None:
    tg = tt("theory_gate")
    model = tt("model")
    sm = tt("self_modify")
    candidate = jload(E7 / "candidate-revisions" / "candidate-theta-v2.json")
    try:
        model.TheoryVersion.from_dict(candidate)
        schema = {"status": "PASS", "detail": "TheoryVersion closed-schema "
                  "validation"}
    except model.ModelValidationError as e:
        schema = {"status": "FAIL", "detail": str(e)}
    imp = jload(E7 / "evidence-import-manifest.json")
    prov = {"status": "PASS" if (imp.get("append_only_intact")
                                 and imp.get("conflicts") == 0
                                 and imp.get("source_pin_verification",
                                             {}).get("status") == "PASS")
            else "FAIL"}
    tests = jload(E7 / "infrastructure" / "test-results.json")
    protected = sm.check_protected_laws(
        [str(p.relative_to(REPO)) for p in
         sorted((E7 / "candidate-revisions").glob("*.json"))]
        + [".creator-zero/experiment-7/theory-revision-evidence.jsonl"])
    inputs = {
        "candidate_schema": schema,
        "evidence_provenance": prov,
        "historical_replay": jload(E7 / "historical-replay" /
                                   "candidate-theta-v2-replay.json"),
        "protected_laws": protected,
        "tests_existing": {"status": tests["status"]},
        "tests_new": {"status": tests["status"]},
        "independent_verifier": jload(E7 / "independent-verification" /
                                      "revision-verification.json"),
    }
    auth = tg.evaluation_authorization(inputs)
    jdump(E7 / "candidate-revisions" / "evaluation-authorization.json", auth)
    print("evaluation authorization:", auth["status"])
    for line in auth["evidence"]:
        print(" ", line)


def main() -> None:
    {"draft-ws": cmd_draft_ws, "propose": cmd_propose,
     "verify-ws": cmd_verify_ws, "authorize": cmd_authorize}[sys.argv[1]]()


if __name__ == "__main__":
    main()
