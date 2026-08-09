# Topology theory store

- `theta-v<N>.json` — immutable theory versions (write-once; promotion via
  the deterministic Gate only; lineage by predecessor artifact id).
- `evidence.jsonl` — append-only principle-evidence log.
- `evidence-heads.jsonl` — append-only running-hash chain over the log.

Managed exclusively by `topology-theory/theory_store.py`.
