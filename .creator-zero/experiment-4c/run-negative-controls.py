#!/usr/bin/env python3
"""Experiment 4C negative controls.

Each control deterministically perturbs the actual C2'-authored witness (or
its runtime ledger) and must produce its preregistered failure through the
Formal Semantics Kernel CLI. Control artifacts are persisted under
formal/controls/; results are aggregated into formal/negative-controls.json.

Run from the repository root after the main pipeline:
    python3 .creator-zero/experiment-4c/run-negative-controls.py
"""
from __future__ import annotations
import copy, json, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
E4C = REPO / ".creator-zero/experiment-4c"
K2 = REPO / ".creator-zero/experiment-4/child-2-contract.json"
CZ = REPO / ".creator-zero/cz.py"
ATT = E4C / "c2-prime-k3-attestation.json"
HARNESS = E4C / "c2-prime-harness.json"
LEDGER = E4C / "c2-prime-execution-ledger.jsonl"
CTRL = E4C / "formal/controls"

CHILD_KEYS = ("draft_child_contract_K3", "draft_child_contract", "child_contract")


def child_key(att: dict) -> str:
    for k in CHILD_KEYS:
        if isinstance(att.get(k), dict):
            return k
    raise SystemExit("no child contract in attestation")


def run(cmd: list[str], json_out: Path):
    p = subprocess.run(cmd + ["--json-out", str(json_out)],
                       capture_output=True, text=True)
    status = json.loads(json_out.read_text())["status"] if json_out.exists() else None
    return p.returncode, status, p.stdout.strip()


def main() -> int:
    CTRL.mkdir(parents=True, exist_ok=True)
    att = json.loads(ATT.read_text())
    ck = child_key(att)
    results = []

    def record(name, expected, artifact, cmd_desc, exit_code, status, stdout, extra=None):
        ok = expected(exit_code, status)
        results.append({
            "control": name,
            "artifact": artifact,
            "command": cmd_desc,
            "kernel_status": status,
            "exit_code": exit_code,
            "stdout": stdout,
            "preregistered_expectation": extra,
            "matches_preregistered_expectation": ok,
        })
        print(f"{name}: status={status} exit={exit_code} expected_met={ok}")

    # 1. Terminal child: strips Creator capability -> closure FAIL (CreatorCapable)
    t = copy.deepcopy(att)
    t[ck]["creator_capability"] = False
    t[ck]["may_create_creator"] = False
    t[ck]["contract_id"] = t[ck].get("contract_id", "K3'") + "-terminal-control"
    f = CTRL / "control-terminal-child-attestation.json"
    f.write_text(json.dumps(t, indent=2) + "\n")
    code, status, out = run([sys.executable, str(CZ), "closure", str(K2), str(f)],
                            CTRL / "control-terminal-child-result.json")
    record("terminal_child", lambda c, s: c == 2 and s == "FAIL", str(f.relative_to(REPO)),
           "cz.py closure K2 <terminal-child attestation>", code, status, out,
           "closure FAIL, failed clause CreatorCapable (Experiment 4B lesson)")

    # 2. Realization re-enabled: positive child budget + realization -> closure FAIL
    #    (ExternalStopOnly) and attenuation FAIL (max_children, may_realize_creation)
    r = copy.deepcopy(att)
    r[ck]["may_realize_creation"] = True
    r[ck]["max_children"] = 1
    r[ck]["contract_id"] = r[ck].get("contract_id", "K3'") + "-realization-control"
    f = CTRL / "control-realization-enabled-attestation.json"
    f.write_text(json.dumps(r, indent=2) + "\n")
    code, status, out = run([sys.executable, str(CZ), "closure", str(K2), str(f)],
                            CTRL / "control-realization-enabled-closure-result.json")
    record("realization_enabled_closure", lambda c, s: c == 2 and s == "FAIL",
           str(f.relative_to(REPO)), "cz.py closure K2 <realization-enabled attestation>",
           code, status, out, "closure FAIL (ExternalStopOnly and/or Attenuated)")
    fc = CTRL / "control-realization-enabled-contract.json"
    fc.write_text(json.dumps(r[ck], indent=2) + "\n")
    code, status, out = run([sys.executable, str(CZ), "attenuation", str(K2), str(fc)],
                            CTRL / "control-realization-enabled-attenuation-result.json")
    record("realization_enabled_attenuation", lambda c, s: c == 2 and s == "FAIL",
           str(fc.relative_to(REPO)), "cz.py attenuation K2 <realization-enabled contract>",
           code, status, out, "ATTENUATION_FAIL (max_children 1>0, may_realize_creation true over false)")

    # 3. Authority escalation: tool + model-call budget above K2 -> ATTENUATION_FAIL
    a = copy.deepcopy(att)
    a[ck]["allowed_tools"] = sorted(set(a[ck].get("allowed_tools", [])) | {"Edit"})
    a[ck]["max_model_calls"] = 8
    a[ck]["contract_id"] = a[ck].get("contract_id", "K3'") + "-escalation-control"
    fc = CTRL / "control-authority-escalation-contract.json"
    fc.write_text(json.dumps(a[ck], indent=2) + "\n")
    code, status, out = run([sys.executable, str(CZ), "attenuation", str(K2), str(fc)],
                            CTRL / "control-authority-escalation-result.json")
    record("authority_escalation", lambda c, s: c == 2 and s == "FAIL",
           str(fc.relative_to(REPO)), "cz.py attenuation K2 <escalated contract>",
           code, status, out, "ATTENUATION_FAIL naming allowed_tools (Edit) and max_model_calls (8>4)")

    # 4. Synthetic runtime escape: inject an act_candidate event the declared
    #    C2' LTS does not permit -> REFINEMENT_VIOLATION
    lines = [l for l in LEDGER.read_text().splitlines() if l.strip()]
    inject = json.dumps({"event_id": "escape-injected", "label": "act_candidate",
                         "actor": "node:construct-witness",
                         "timestamp": "synthetic",
                         "metadata": {"synthetic_control": "runtime escape: candidate mutation never granted to C2'"}})
    f = CTRL / "control-runtime-escape-ledger.jsonl"
    f.write_text("\n".join(lines[:2] + [inject] + lines[2:]) + "\n")
    code, status, out = run([sys.executable, str(CZ), "check-runtime", str(HARNESS), str(f),
                             "--contract", str(K2), "--require-completion"],
                            CTRL / "control-runtime-escape-result.json")
    record("runtime_escape", lambda c, s: c == 2 and s == "FAIL",
           str(f.relative_to(REPO)),
           "cz.py check-runtime <C2' harness> <ledger with injected act_candidate> --contract K2 --require-completion",
           code, status, out, "REFINEMENT_VIOLATION on the injected act_candidate event")

    # 5. Positive control: the actual C2'-authored witness must PASS closure
    code, status, out = run([sys.executable, str(CZ), "closure", str(K2), str(ATT)],
                            CTRL / "control-positive-closure-result.json")
    record("valid_c2prime_witness", lambda c, s: c == 0 and s == "PASS",
           str(ATT.relative_to(REPO)), "cz.py closure K2 <actual C2' attestation>",
           code, status, out, "closure PASS (identical to primary pipeline result)")

    all_ok = all(r["matches_preregistered_expectation"] for r in results)
    doc = {
        "record": "Experiment 4C negative controls",
        "derivation": "controls 1-3 are deterministic single-purpose perturbations of the actual C2'-authored witness; control 4 injects a synthetic forbidden event into a copy of the actual C2' ledger; control 5 re-runs the unmodified witness. Originals untouched.",
        "controls": results,
        "all_match_preregistered_expectations": all_ok,
    }
    (E4C / "formal/negative-controls.json").write_text(json.dumps(doc, indent=2) + "\n")
    print("ALL_CONTROLS_MATCH" if all_ok else "CONTROL_MISMATCH")
    return 0 if all_ok else 2


if __name__ == "__main__":
    sys.exit(main())
