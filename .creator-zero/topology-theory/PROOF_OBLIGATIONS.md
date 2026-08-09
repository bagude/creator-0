# Topology Theory v0.1 — Proof Obligations and Their Status

What is deterministically checked, what is assumed, and what is *not*
claimed. Obligations marked MECHANICAL are enforced by code that a model
cannot override; ASSUMED obligations are inherited from the runtime's
instrumentation honesty.

## Mechanical obligations

| # | Obligation | Where |
|---|---|---|
| O1 | Theory versions are write-once; promoted versions immutable; lineage by predecessor artifact id | `theory_store.write_version` |
| O2 | Evidence log is append-only under a running hash chain | `theory_store.verify_append_only` |
| O3 | Promotion requires the Gate's own PASS (`check="gate"`, `issued_by="gate"`) | `theory_store.promote`, `self_modify.authorize_promotion` |
| O4 | Every prediction carries a falsifier; every claimed resolved distinction is covered by a falsifiable prediction | `model.Prediction`, `predict.validate_frozen_coverage` |
| O5 | Frozen predictions are hash-bound; retrospective edits detected | `predict.predictions_hash`, `evaluate.PredictionIntegrityError` |
| O6 | Invalid candidates are rejected pre-execution by a deterministic conjunction | `validate.validate_topology` |
| O7 | Reachability claims are decided by finite BFS over the compiled LTS | `validate.reachable_states/label_reachable` |
| O8 | Promote transitions exist only for the gate actor | kernel `semantics.py` (unchanged law) + `validate` re-check |
| O9 | Utility and ranking are pure arithmetic with a total deterministic order | `utility.rank_candidates` |
| O10 | Prediction outcomes are decided mechanically per kind; prose predictions are INDETERMINATE | `evaluate._outcome` |
| O11 | Branch exclusivity and branch completion are encoded in the state space | kernel `semantics.py` |
| O12 | Executed launches require stream-confirmed session identity | `formal/freshness.py` |
| O13 | Artifact identity is exact content+provenance hashing | `serialization.artifact_id` |
| O14 | Self-modification writes stay inside the candidate workspace | `self_modify.candidate_only_guard` |
| O15 | Candidate patches cannot touch protected paths | `self_modify.check_protected_laws` |
| O16 | The Gate is a pure conjunction over serialized inputs | `self_modify.gate` |

## Assumed obligations (explicit, not proven)

- **A1 Instrumentation completeness**: runtime records (ledgers, resource
  use, evidence provenance) faithfully describe execution. The kernel
  refuses INDETERMINATE traces with unmapped events but cannot detect
  unrecorded actions (inherited from Formal Semantics Kernel v0.1).
- **A2 Frozen-artifact custody**: sha256 pins detect mutation of historical
  files but not substitution of the entire repository before pinning.
- **A3 Predicted-value honesty**: predicted components are model-mediated
  estimates; the theory constrains them only through calibration error and
  falsification after execution.
- **A4 Verifier independence**: the independent verifier runs without write
  or promotion authority; its independence from the implementer's biases is
  organizational, not mechanical.

## Non-claims

- No general program verification: reachability is finite-LTS reachability
  over compiled governed configurations, nothing more.
- No universal topology optimality: utility ranks a finite candidate set
  under an explicit config; it proves nothing about unexplored topologies.
- No unrestricted recursive self-improvement: self-modification is bounded,
  candidate-first, replay-checked, independently verified, and promotable
  only by the deterministic Gate; protected laws are outside its reach and
  changing them requires a separate kernel-law protocol.
- Historical replay compatibility over five frozen cases is regression
  evidence, not proof of the revised theory.
