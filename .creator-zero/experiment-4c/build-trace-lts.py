#!/usr/bin/env python3
"""Experiment 4C — deterministic trace-LTS construction for H6 bisimulation.

Builds linear observation LTSs (kernel serialization format) from:
  (a) the immutable historical C2 raw execution ledger, via the committed
      mapping in historical-c2-ledger-mapping.json (full granularity), and
  (b) the C2' normalized execution ledger (already in the formal schema).

Each trace becomes a linear LTS: states s0..sN, transition i carries the
i-th event's (label, actor). No events are dropped or invented; tau lines
remain tau transitions (weak bisimulation may absorb them).

A --role view applies the documented role abstraction: actor -> 'c2-role',
and the mapping's tau_hidden_event_classes become tau. This is data
preparation only; the bisimulation itself is computed by the kernel
(cz.py bisim --mode weak).
"""
from __future__ import annotations
import json, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
HIST_RAW = REPO / ".creator-zero/experiment-4/c2/execution-ledger.jsonl"

ROLE_ACTOR = "c2-role"
# role view: labels hidden as tau per historical-c2-ledger-mapping.json
ROLE_TAU_LABELS = {"consult", "validate", "persist"}
# historical propose events produced by intra-session model roles are hidden
# in the role view; a witness-authoring propose by a harness node is NOT.
ROLE_TAU_PROPOSE_ACTORS = {"decomposer", "composer"}


def normalize_historical() -> list[dict]:
    """Apply the committed full-granularity mapping to the raw C2 ledger."""
    node_primitive_label = {"evidence-and-surrogates": "observe",
                            "independent-rederivation": "verify",
                            "compile-result": "return"}
    out = []
    for line in HIST_RAW.read_text().splitlines():
        if not line.strip():
            continue
        raw = json.loads(line)
        ev, ts = raw.get("event"), raw.get("ts", "")
        def emit(label, actor):
            out.append({"event_id": f"h{len(out)}", "label": label,
                        "actor": actor, "timestamp": ts,
                        "metadata": {"raw_event": ev}})
        if ev == "c2_start":
            emit("observe", "creator")
        elif ev == "model_invocation_start":
            emit("consult", "creator")
        elif ev == "model_invocation_end":
            emit("propose", raw["role"])
        elif ev in ("phase_a_synthesis_complete", "phase_b_start",
                    "node_start", "anomaly", "deterministic_coverage_check"):
            emit("validate" if ev == "deterministic_coverage_check" else "tau",
                 "creator")
        elif ev == "node_end":
            n = raw["node"]
            emit(node_primitive_label[n], f"node:{n}")
        elif ev == "c2_complete":
            emit("return", "node:compile-result")
            emit("complete", "creator")
        else:
            raise SystemExit(f"unmapped raw event: {ev!r}")
    return out


def load_normalized(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


def to_role_view(events: list[dict]) -> list[dict]:
    out = []
    for e in events:
        label, actor = e["label"], e["actor"]
        if label in ROLE_TAU_LABELS or (
                label == "propose" and actor in ROLE_TAU_PROPOSE_ACTORS):
            label = "tau"
        out.append({**e, "label": label, "actor": ROLE_ACTOR})
    return out


def linear_lts(events: list[dict], origin: str, view: str) -> dict:
    states = [f"s{i}" for i in range(len(events) + 1)]
    transitions = [{"source": f"s{i}", "label": e["label"],
                    "target": f"s{i+1}", "actor": e["actor"]}
                   for i, e in enumerate(events)]
    # terminal tau self-loop so weak closure is well-defined at the end state
    transitions.append({"source": states[-1], "label": "tau",
                        "target": states[-1], "actor": "*"})
    labels = sorted({t["label"] for t in transitions})
    return {"formal_object": "lts", "version": "0.1", "initial": "s0",
            "states": states, "labels": labels, "transitions": transitions,
            "metadata": {"origin": origin, "view": view,
                         "construction": "linear trace-LTS, one transition per ledger event, nothing dropped or invented",
                         "mapping_record": ".creator-zero/experiment-4c/historical-c2-ledger-mapping.json"}}


def main() -> int:
    outdir = REPO / ".creator-zero/experiment-4c/bisim"
    outdir.mkdir(exist_ok=True)
    c2p_ledger = Path(sys.argv[1])

    hist_full = normalize_historical()
    c2p_full = load_normalized(c2p_ledger)

    (outdir / "historical-c2-normalized-ledger.jsonl").write_text(
        "\n".join(json.dumps(e, sort_keys=True) for e in hist_full) + "\n")

    for name, events in [
        ("historical-c2-lts-full.json", linear_lts(hist_full, str(HIST_RAW), "full-granularity")),
        ("c2-prime-lts-full.json", linear_lts(c2p_full, str(c2p_ledger), "full-granularity")),
        ("historical-c2-lts-role.json", linear_lts(to_role_view(hist_full), str(HIST_RAW), "role-abstraction")),
        ("c2-prime-lts-role.json", linear_lts(to_role_view(c2p_full), str(c2p_ledger), "role-abstraction")),
    ]:
        (outdir / name).write_text(json.dumps(events, indent=2, sort_keys=True) + "\n")
        print(name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
