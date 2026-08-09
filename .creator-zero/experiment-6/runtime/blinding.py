"""Experiment 6 deterministic blinding scanner.

Two pattern sets, frozen at preregistration:

1. LABEL_LEAK_PATTERNS — scanned over EVERY text file of a blinded
   workspace. Anything naming the private label schema, a latent class,
   an expected principle/topology, or the private bank voids the package
   (BLINDING_FAIL). Latent class names are matched case-sensitively as
   uppercase tokens so that ordinary words ('local work') do not trip the
   scan while label vocabulary ('LOCAL', 'ISOLATION') does.

2. TOPOLOGY_CUE_PATTERNS — scanned over the public task package files
   only (package/ subtree). Public packages must contain raw task
   semantics with no explicit topology instructions; any cue such as
   'requires_isolation', 'child', 'clean-room', or 'counterexample'
   rejects the package. Uniform governance files (protocols, schemas,
   harnesses) legitimately speak about topology and are exempt from this
   second set, but never from the first.
"""
from __future__ import annotations
import re
from pathlib import Path
from typing import Any

LABEL_LEAK_PATTERNS = [
    r"latent[-_ ]?class",
    r"expected[-_ ]?(decision|topology|class|principles?)",
    r"acceptable[-_ ]?topology",
    r"forbidden[-_ ]?shortcuts?",
    r"shadow[-_ ]?policy",
    r"private[-_ ]?label",
    r"answer[-_ ]?key",
    r"ground[-_ ]?truth",
    r"task-bank/.*private",
    r"critical[-_ ]?distinction",
]

# case-sensitive uppercase class tokens
CLASS_TOKEN_PATTERNS = [
    r"\bLOCAL\b", r"\bISOLATION\b", r"\bCOUNTEREXAMPLE\b",
    r"\bALTERNATIVE_DECOMPOSITION\b", r"\bSPECIALIZED_VERIFICATION\b",
    r"\bPARALLEL_INDEPENDENT\b",
]

TOPOLOGY_CUE_PATTERNS = [
    r"requires?[-_ ]?isolation",
    r"needs?[-_ ]?verifier",
    r"counter[-_ ]?example",
    r"create[-_ ]?child",
    r"topolog",
    r"condition[-_ ]?[ab]\b",
    r"\bchild(ren)?\b",
    r"\bisolat",
    r"clean[-_ ]?room",
    r"\bsession\b",
    r"\bverifier\b",
    r"\bindependent(ly)?\b",
    r"\bfresh\b",
    r"\blocal(ly)?\b",
    r"\bspawn",
    r"\bdelegate",
    r"\bagent\b",
    r"\bsub-?task\b",
    r"\bdecompos",
    r"\badversar",
]


def _scan_text(text: str, patterns: list[str], flags: int
               ) -> list[dict[str, str]]:
    hits = []
    for raw in patterns:
        m = re.search(raw, text, flags)
        if m:
            hits.append({"pattern": raw, "match": m.group(0)})
    return hits


def scan_workspace(root: str | Path,
                   package_subdir: str = "package") -> dict[str, Any]:
    """Full blinding scan. Returns {'verdict': 'PASS'|'BLINDING_FAIL',
    'hits': [...]}. Deterministic; text files only."""
    root = Path(root)
    hits: list[dict[str, Any]] = []
    for f in sorted(root.rglob("*")):
        if not f.is_file():
            continue
        try:
            text = f.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        rel = str(f.relative_to(root))
        for h in _scan_text(text, LABEL_LEAK_PATTERNS, re.IGNORECASE):
            hits.append({"file": rel, "set": "label_leak", **h})
        for h in _scan_text(text, CLASS_TOKEN_PATTERNS, 0):
            hits.append({"file": rel, "set": "class_token", **h})
        if rel.startswith(package_subdir + "/") or rel == package_subdir:
            for h in _scan_text(text, TOPOLOGY_CUE_PATTERNS, re.IGNORECASE):
                hits.append({"file": rel, "set": "topology_cue", **h})
    return {"verdict": "PASS" if not hits else "BLINDING_FAIL", "hits": hits}


def scan_package(pkg_dir: str | Path) -> dict[str, Any]:
    """Scan a bare public package directory (both pattern sets apply)."""
    pkg_dir = Path(pkg_dir)
    hits: list[dict[str, Any]] = []
    for f in sorted(pkg_dir.rglob("*")):
        if not f.is_file():
            continue
        try:
            text = f.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        rel = str(f.relative_to(pkg_dir))
        for h in _scan_text(text, LABEL_LEAK_PATTERNS, re.IGNORECASE):
            hits.append({"file": rel, "set": "label_leak", **h})
        for h in _scan_text(text, CLASS_TOKEN_PATTERNS, 0):
            hits.append({"file": rel, "set": "class_token", **h})
        for h in _scan_text(text, TOPOLOGY_CUE_PATTERNS, re.IGNORECASE):
            hits.append({"file": rel, "set": "topology_cue", **h})
    return {"verdict": "PASS" if not hits else "BLINDING_FAIL", "hits": hits}
