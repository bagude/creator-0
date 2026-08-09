#!/usr/bin/env python3
"""Experiment 4C — persist the C2' witness and its provenance (protocol §10).

Copies the raw invocation evidence out of the launch directory into
.creator-zero/experiment-4c/ and writes witness-provenance.json binding the
K3' attestation to the fresh C2' invocation by hash.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
E4C = ROOT / ".creator-zero/experiment-4c"
LAUNCH = Path("/tmp/claude-0/-home-user-creator-0/e1cfb41d-e45c-583f-a2cd-d317df1f1c2c/scratchpad/c2-prime-cwd")

ALLOWED_INPUTS = [
    ".creator-zero/experiment-4/child-2-contract.json",
    ".creator-zero/experiment-4/closure-correction/closure-predicate-verification.json",
    ".creator-zero/experiment-4/closure-correction/original-mismatch.json",
]


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


raw_path = LAUNCH / "raw-output.json"
raw_bytes = raw_path.read_bytes()
envelope = json.loads(raw_bytes)
result_text = envelope["result"]
attestation = json.loads(result_text)  # must parse: C2' was told raw JSON only

start = (LAUNCH / "invocation-start.txt").read_text().strip()
end = (LAUNCH / "invocation-end.txt").read_text().strip()
fresh_id = (LAUNCH / "fresh-session-id.txt").read_text().strip()
exit_status = (LAUNCH / "exit-status.txt").read_text().strip()
probe_hash = sha256_file(LAUNCH / "probe-discarded-raw-output.json")

# 1. Session log: the full CLI JSON envelope, byte-identical copy.
(E4C / "c2-prime-session.log").write_bytes(raw_bytes)

# 2. The K3' attestation exactly as authored by C2' (verbatim result text,
#    so its hash is the hash of what the model returned).
(E4C / "c2-prime-k3-attestation.json").write_text(result_text, encoding="utf-8")

output_hash = sha256_bytes(result_text.encode("utf-8"))

invocation_command = (
    'env -u CLAUDE_CODE_SESSION_ID claude -p --model claude-sonnet-5 '
    f'--output-format json --session-id "{fresh_id}" '
    '--disallowedTools "Bash" "Read" "Write" "Edit" "Glob" "Grep" "WebFetch" '
    '"WebSearch" "Task" "TodoWrite" "NotebookEdit" '
    '< .creator-zero/experiment-4c/c2-prime-prompt.md > raw-output.json 2> stderr.txt'
)

# 3. Structured result envelope.
result = {
    "record": "Experiment 4C C2' invocation result",
    "session_id": envelope.get("session_id"),
    "subtype": envelope.get("subtype"),
    "is_error": envelope.get("is_error"),
    "num_turns": envelope.get("num_turns"),
    "duration_ms": envelope.get("duration_ms"),
    "started_utc": start,
    "ended_utc": end,
    "exit_status": exit_status,
    "stderr_bytes": (LAUNCH / "stderr.txt").stat().st_size,
    "output_parses_as_single_json_object": True,
    "attestation_artifact": ".creator-zero/experiment-4c/c2-prime-k3-attestation.json",
    "attestation_sha256": output_hash,
}
(E4C / "c2-prime-result.json").write_text(json.dumps(result, indent=2) + "\n",
                                          encoding="utf-8")

# 4. Witness provenance.
provenance = {
    "record": "Experiment 4C witness provenance (protocol §10)",
    "witness": {
        "artifact": ".creator-zero/experiment-4c/c2-prime-k3-attestation.json",
        "sha256": output_hash,
        "byte_identity": "file content is the verbatim `result` field of the CLI JSON envelope in c2-prime-session.log; sha256(result) binds the witness to that invocation",
    },
    "invocation": {
        "command": invocation_command,
        "cwd": "empty scratch directory outside the repository (no CLAUDE.md, no repo files reachable; all tools disallowed)",
        "model_requested": "claude-sonnet-5",
        "models_reported_by_cli": sorted(envelope.get("modelUsage", {}).keys()),
        "model_note": "claude-sonnet-5 is the primary model (same model original C2 used for its invocations); the haiku entry is the CLI's internal auxiliary usage, not a task turn",
        "allowed_tools": [],
        "disallowed_tools": ["Bash", "Read", "Write", "Edit", "Glob", "Grep",
                             "WebFetch", "WebSearch", "Task", "TodoWrite",
                             "NotebookEdit"],
        "session_id": envelope.get("session_id"),
        "started_utc": start,
        "ended_utc": end,
        "exit_status": exit_status,
        "num_turns": envelope.get("num_turns"),
    },
    "freshness_declaration": {
        "C2_prime_fresh": True,
        "resume_used": False,
        "prior_session_reused": False,
        "flags_absent": ["--continue", "--resume"],
        "session_id_source": "freshly generated UUID passed via --session-id, with the orchestrator's inherited CLAUDE_CODE_SESSION_ID env var explicitly unset",
        "prompt_delivery": "stdin only; single turn; empty working directory; all tools disallowed, so no file, network, or repo access was possible during the invocation",
    },
    "discarded_probe": {
        "note": "a first, otherwise-identical invocation was discarded because the claude CLI inherited the orchestrator's CLAUDE_CODE_SESSION_ID env var and labeled the child session with the orchestrator's UUID; its conversation was fresh (num_turns=1, stdin prompt) but the label made freshness non-demonstrable, so its output was not used for any artifact",
        "raw_envelope_sha256": probe_hash,
        "used_in_witness": False,
    },
    "prompt": {
        "path": ".creator-zero/experiment-4c/c2-prime-prompt.md",
        "sha256": sha256_file(E4C / "c2-prime-prompt.md"),
    },
    "input_artifacts": [
        {"path": rel, "sha256": sha256_file(ROOT / rel)} for rel in ALLOWED_INPUTS
    ],
    "withheld_answer_key": {
        "path": ".creator-zero/experiment-4/closure-correction/corrected-k3-attestation.json",
        "sha256": sha256_file(ROOT / ".creator-zero/experiment-4/closure-correction/corrected-k3-attestation.json"),
        "provided_to_c2_prime": False,
        "leakage_check": ".creator-zero/experiment-4c/input-manifest.json",
    },
    "session_log": {
        "path": ".creator-zero/experiment-4c/c2-prime-session.log",
        "sha256": sha256_bytes(raw_bytes),
    },
}
(E4C / "witness-provenance.json").write_text(json.dumps(provenance, indent=2) + "\n",
                                             encoding="utf-8")
print(json.dumps({"witness_sha256": output_hash,
                  "session_id": envelope.get("session_id"),
                  "persisted": ["c2-prime-session.log", "c2-prime-k3-attestation.json",
                                 "c2-prime-result.json", "witness-provenance.json"]},
                 indent=2))
