#!/usr/bin/env python3
"""Experiment 4C no-answer-leakage gate + input manifest builder.

Deterministically verifies that the C2' input package contains no direct
transmission of the Experiment 4B corrected K3 witness:
  (a) no occurrence of the corrected attestation's artifact path;
  (b) no occurrence of its sha256;
  (c) no exact copy of its body (raw, whitespace-normalized, or canonical JSON);
  (d) no embedded JSON object structurally equal to its draft child contract
      or to the whole attestation;
  (e) no long prose string (>= 40 chars) unique to the corrected attestation
      (strings also present in generic allowed sources — K2, SEMANTICS.md,
      creator_closure.py — are the rules under test, not leakage).

The script reads the forbidden artifact only to derive signatures; it never
prints its content. Run from the repository root:
    python3 .creator-zero/experiment-4c/leakage-scan.py <workspace-dir>
"""
from __future__ import annotations
import hashlib, json, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
FORBIDDEN = REPO / ".creator-zero/experiment-4/closure-correction/corrected-k3-attestation.json"
FORBIDDEN_PATH_STR = ".creator-zero/experiment-4/closure-correction/corrected-k3-attestation.json"
GENERIC_SOURCES = [
    REPO / ".creator-zero/experiment-4/child-2-contract.json",
    REPO / ".creator-zero/formal/SEMANTICS.md",
    REPO / ".creator-zero/formal/creator_closure.py",
]
CHILD_CONTRACT_KEYS = ("draft_child_contract_K3", "draft_child_contract", "child_contract")

SUPPLIED = [
    # (workspace-relative path, source repo-relative path or None if root-authored, transform)
    ("c2-prime-prompt.md", ".creator-zero/experiment-4c/c2-prime-prompt.md", "verbatim-copy (root-authored protocol)"),
    ("inputs/k2-contract.json", ".creator-zero/experiment-4/child-2-contract.json", "verbatim-copy"),
    ("inputs/original-mismatch.json", ".creator-zero/experiment-4/closure-correction/original-mismatch.json", "verbatim-copy"),
    ("inputs/closure-predicate-verification.redacted.json", ".creator-zero/experiment-4/closure-correction/closure-predicate-verification.json", "redacted-copy: evaluations[subject~CORRECTED].attestation and .attestation_sha256 replaced with redaction markers; redaction_note added; all other content verbatim"),
    ("inputs/formal-semantics-v0.1.md", ".creator-zero/formal/SEMANTICS.md", "verbatim-copy"),
    ("inputs/attestation-interface.md", ".creator-zero/experiment-4c/attestation-interface.md", "verbatim-copy (root-authored kernel-interface excerpt)"),
    ("inputs/c2-prime-harness.json", ".creator-zero/experiment-4c/c2-prime-harness.json", "verbatim-copy (root-authored governance envelope)"),
    (".claude/settings.json", None, "root-authored access-control deny rules"),
]


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def norm_ws(s: str) -> str:
    return " ".join(s.split())


def collect_strings(obj, out: list[str]) -> None:
    if isinstance(obj, str):
        out.append(obj)
    elif isinstance(obj, dict):
        for k, v in obj.items():
            out.append(k)
            collect_strings(v, out)
    elif isinstance(obj, list):
        for v in obj:
            collect_strings(v, out)


def walk_dicts(obj):
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            yield from walk_dicts(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from walk_dicts(v)


def main() -> int:
    ws = Path(sys.argv[1]).resolve()
    raw = FORBIDDEN.read_text(encoding="utf-8")
    att = json.loads(raw)
    forbidden_sha = sha256(FORBIDDEN)

    child = None
    for k in CHILD_CONTRACT_KEYS:
        if isinstance(att.get(k), dict):
            child = att[k]
            break

    generic_text = "\n".join(p.read_text(encoding="utf-8") for p in GENERIC_SOURCES)
    generic_norm = norm_ws(generic_text)

    att_strings: list[str] = []
    collect_strings(att, att_strings)
    unique_long = sorted({norm_ws(s) for s in att_strings
                          if len(norm_ws(s)) >= 40 and norm_ws(s) not in generic_norm})

    signatures = {
        "forbidden_path": [FORBIDDEN_PATH_STR],
        "forbidden_sha256": [forbidden_sha],
        "exact_body": [norm_ws(raw), canonical(att)],
        "child_contract_canonical": [canonical(child)] if child else [],
        "unique_long_strings": unique_long,
    }

    scanned, matches = [], []
    for f in sorted(ws.rglob("*")):
        if not f.is_file():
            continue
        rel = str(f.relative_to(ws))
        text = f.read_text(encoding="utf-8", errors="replace")
        tnorm = norm_ws(text)
        scanned.append(rel)
        for cls, sigs in signatures.items():
            for i, sig in enumerate(sigs):
                if sig and sig in tnorm:
                    matches.append({"file": rel, "signature_class": cls, "signature_index": i})
        # structural check: any embedded JSON object equal to the forbidden
        # child contract or the whole attestation
        if f.suffix == ".json":
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError:
                continue
            for d in walk_dicts(parsed):
                if d == att or (child is not None and d == child):
                    matches.append({"file": rel, "signature_class": "structural_json_equality"})

    manifest_entries = []
    for rel, src, transform in SUPPLIED:
        wf = ws / rel
        entry = {
            "workspace_path": rel,
            "supplied_sha256": sha256(wf),
            "source_path": src,
            "source_sha256": sha256(REPO / src) if src else None,
            "transform": transform,
        }
        manifest_entries.append(entry)

    extra = [p for p in scanned if p not in {e[0] for e in SUPPLIED}]

    manifest = {
        "experiment": "4C",
        "workspace": str(ws),
        "supplied_files": manifest_entries,
        "unexpected_workspace_files": extra,
        "forbidden_answer_source": {
            "path": FORBIDDEN_PATH_STR,
            "sha256": forbidden_sha,
            "supplied": False,
        },
        "access_controls": {
            "allowed_tools": ["Read", "Write"],
            "denied": json.loads((ws / ".claude/settings.json").read_text())["permissions"]["deny"],
            "note": "C2' runs with cwd=workspace, Read/Write only (no Bash/Grep/Glob/Edit/Task/Web), and deny rules blocking the entire repository and uploads paths; the forbidden artifact is therefore not readable by C2' even by path guessing.",
        },
    }

    result = {
        "check": "no_answer_leakage",
        "verdict": ("NO_ANSWER_LEAKAGE_PASS" if not matches and not extra
                    else "NO_ANSWER_LEAKAGE_FAIL"),
        "files_scanned": scanned,
        "signature_classes_checked": {k: len(v) for k, v in signatures.items()},
        "structural_check": "every embedded JSON object compared for equality with the forbidden attestation and its draft child contract",
        "matches": matches,
        "unexpected_workspace_files": extra,
        "leakage_definition": [
            "prior corrected K3 JSON supplied",
            "exact copied K3 body",
            "answer-key artifact path plus readable access",
            "transcript containing the corrected solution",
            "resume/continue from a session containing it",
        ],
        "non_leakage_note": "The abstract predicate conjuncts (CreatorCapable, Attenuated, CreationMechanismValid, ExternalStopOnly) and the 4B clause outcomes restate the rules being tested and are not leakage (engineering spec section 6).",
    }

    (REPO / ".creator-zero/experiment-4c/input-manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n")
    (REPO / ".creator-zero/experiment-4c/no-answer-leakage.json").write_text(
        json.dumps(result, indent=2) + "\n")
    print(f"input-manifest.json: {len(manifest_entries)} supplied files")
    print(result["verdict"])
    return 0 if result["verdict"].endswith("PASS") else 2


if __name__ == "__main__":
    sys.exit(main())
