#!/usr/bin/env python3
"""Experiment 4C — deterministic no-answer-leakage check (protocol §12).

Verifies, before C2' is launched, that the input package (the assembled
prompt) does not contain:
  - corrected-k3-attestation.json (by hash identity of any embedded block),
  - the corrected K3 JSON body (by normalized-substring and by full
    field:value overlap),
  - a copied list of the exact corrected K3 fields beyond the predicate
    requirements (any corrected-K3 key that is NOT predicate-mandated must
    not appear in the prompt with the corrected K3's value).

The formal closure conditions themselves are explicitly permitted.
Writes: input-manifest.json
"""
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
E4 = ROOT / ".creator-zero/experiment-4"
E4C = ROOT / ".creator-zero/experiment-4c"

ALLOWED_INPUTS = [
    ".creator-zero/experiment-4/child-2-contract.json",
    ".creator-zero/experiment-4/closure-correction/closure-predicate-verification.json",
    ".creator-zero/experiment-4/closure-correction/original-mismatch.json",
]
WITHHELD = ".creator-zero/experiment-4/closure-correction/corrected-k3-attestation.json"
PROMPT = E4C / "c2-prime-prompt.md"

# Fields the predicate/protocol itself mandates or constrains for any K3'.
# Overlap on these is the formal closure condition, not answer leakage.
PREDICATE_REQUIRED_FIELDS = {
    "allowed_tools", "allowed_primitives", "allowed_relations",
    "max_model_calls", "max_children", "max_depth",
    "creator_capability", "may_create_creator", "may_realize_creation",
    "filesystem_write_scope", "git_authority",
}


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def norm(s: str) -> str:
    return re.sub(r"\s+", "", s)


def main() -> int:
    prompt_text = PROMPT.read_text(encoding="utf-8")
    prompt_norm = norm(prompt_text)

    checks = []

    def check(name, ok, detail):
        checks.append({"check": name, "pass": bool(ok), "detail": detail})
        return ok

    # 1. Withheld artifact not embedded verbatim (normalized substring).
    withheld_raw = (ROOT / WITHHELD).read_text(encoding="utf-8")
    check("withheld_attestation_not_embedded",
          norm(withheld_raw) not in prompt_norm,
          f"{WITHHELD} (normalized) is not a substring of the prompt")

    # 2. Corrected K3 JSON body not embedded (any draft key variant).
    withheld = json.loads(withheld_raw)
    k3_body = None
    for key in ("k3_draft", "K3_draft", "k3", "draft_child_contract_K3"):
        if isinstance(withheld.get(key), dict):
            k3_body = withheld[key]
            break
    body_ok = True
    body_detail = "no k3 draft found in withheld artifact"
    if k3_body is not None:
        candidates = [
            json.dumps(k3_body),
            json.dumps(k3_body, indent=2),
            json.dumps(k3_body, sort_keys=True),
        ]
        hits = [c for c in candidates if norm(c) in prompt_norm]
        body_ok = not hits
        body_detail = ("corrected K3 body (any serialization, normalized) "
                       "is not a substring of the prompt")
    check("corrected_k3_body_not_embedded", body_ok, body_detail)

    # 3. No corrected-K3 field beyond the predicate requirements appears in
    #    the prompt together with the corrected value (field:value leakage).
    #    A pair that already occurs verbatim inside one of the three ALLOWED
    #    inputs (e.g. K2's own "max_realized_creator_children": 0, which any
    #    attenuated K3 inherits) reaches the prompt through the allowed
    #    artifact, not through the withheld answer; it is recorded as
    #    permitted overlap, not leakage.
    allowed_norms = {rel: norm((ROOT / rel).read_text(encoding="utf-8"))
                     for rel in ALLOWED_INPUTS}
    leaks, overlap_via_allowed = [], []
    if k3_body is not None:
        for field, value in k3_body.items():
            if field in PREDICATE_REQUIRED_FIELDS:
                continue
            pair_variants = [
                norm(json.dumps({field: value}))[1:-1],  # "field":value
                norm(f'"{field}": {json.dumps(value)}'),
            ]
            if any(v in prompt_norm for v in pair_variants):
                srcs = [rel for rel, text in allowed_norms.items()
                        if any(v in text for v in pair_variants)]
                if srcs:
                    overlap_via_allowed.append({"field": field, "sources": srcs})
                else:
                    leaks.append(field)
    check("no_extra_field_value_leakage", not leaks,
          f"corrected-K3 non-predicate field:value pairs reaching the prompt "
          f"from outside the allowed inputs: {leaks or 'none'}; "
          f"permitted overlap via allowed inputs: {overlap_via_allowed or 'none'}")

    # 4. The prompt embeds exactly the three allowed artifacts, verbatim.
    embedded = []
    for rel in ALLOWED_INPUTS:
        raw = (ROOT / rel).read_text(encoding="utf-8")
        present = norm(raw) in prompt_norm
        embedded.append({"path": rel, "sha256": sha256_file(ROOT / rel),
                         "embedded_verbatim": present})
    check("allowed_inputs_embedded_verbatim",
          all(e["embedded_verbatim"] for e in embedded),
          "all three allowed artifacts appear verbatim in the prompt")

    # 5. No other experiment-4 artifact bodies are embedded (spot check the
    #    most answer-adjacent files).
    adjacent = [
        ".creator-zero/experiment-4/closure-correction/correction-report.md",
        ".creator-zero/experiment-4/closure-correction/gate-regression-results.json",
        ".creator-zero/experiment-4/c2/creator-capability-attestation.json",
        ".creator-zero/experiment-4/gate.py",
    ]
    adj_hits = [rel for rel in adjacent
                if norm((ROOT / rel).read_text(encoding="utf-8")) in prompt_norm]
    check("no_adjacent_artifact_embedded", not adj_hits,
          f"adjacent artifacts embedded: {adj_hits or 'none'}")

    ok = all(c["pass"] for c in checks)
    manifest = {
        "record": "Experiment 4C input manifest and no-answer-leakage check (protocol §12)",
        "prompt": {
            "path": ".creator-zero/experiment-4c/c2-prime-prompt.md",
            "sha256": sha256_file(PROMPT),
            "bytes": len(prompt_text.encode("utf-8")),
        },
        "inputs_provided_to_c2_prime": embedded,
        "withheld": {
            "path": WITHHELD,
            "sha256": sha256_file(ROOT / WITHHELD),
            "note": "corrected 4B K3 witness; never embedded, quoted, or paraphrased into the package",
        },
        "predicate_required_fields_permitted_overlap": sorted(PREDICATE_REQUIRED_FIELDS),
        "checks": checks,
        "leakage_check": "PASS" if ok else "FAIL",
    }
    (E4C / "input-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n",
                                             encoding="utf-8")
    print(json.dumps({"leakage_check": manifest["leakage_check"],
                      "failed": [c["check"] for c in checks if not c["pass"]]}))
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
