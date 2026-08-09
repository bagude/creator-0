"""Experiment 6 root-side deterministic runtime.

Modules:
    common       shared paths/IO, frozen family economics, theory loading
    blinding     preregistered blinding scanner (label-leak + topology-cue)
    package_ws   blinded workspace packaging (infer/exec/examiner/child)
    launch       fresh-session launches through the frozen launcher v0.2
    collect      closed-schema validation of blinded-session outputs
    pipeline     S2-S5: abduce -> generate -> freeze -> validate -> rank
    infer_driver S1 orchestration (prepare/after + pipeline)
    exec_driver  S6-S7 orchestration (prepare/collect/finalize)
    score        per-trial scoring against frozen private labels
    aggregate    experiment-level metrics, thresholds, result label
    controls     preregistered deterministic negative controls
"""
