# Formal Semantics Kernel v0.1 — attestation document interface

This is the kernel's public interface for a bounded Creator-Closure witness
attestation (`.creator-zero/formal/creator_closure.py`). It documents accepted
key names and required keys only; it contains no witness values.

## Attestation document (top-level JSON object)

The kernel resolves the draft child contract from the first present key of:

```text
draft_child_contract_K3
draft_child_contract
child_contract
```

The kernel resolves the creation command from the first present key of, and
requires a non-empty string:

```text
exact_creation_command_NOT_EXECUTED
exact_creation_command
creation_command
```

The non-execution marker is satisfied by using the key name containing
`NOT_EXECUTED` and/or by a non-empty `architectural_stop_statement` field.

Other top-level fields (e.g. attenuation reasoning, provenance notes) are
permitted and ignored by the kernel check.

## Required child-contract keys (`Valid` clause)

The draft child contract must carry at least:

```text
contract_id
allowed_primitives
allowed_tools
max_children
max_depth
max_model_calls
may_create_creator
creator_capability
may_realize_creation
```

Any additional governed axes present (e.g. allowed_relations,
max_realized_creator_children, max_realized_creator_depth,
filesystem_write_scope, candidate/canonical/git/network authority strings)
are compared against the parent contract by the attenuation check exactly as
defined in `formal-semantics-v0.1.md` §8; a governed axis absent on the child
is treated as inherited from the parent (no escalation), and an axis absent on
the parent is treated as unrestricted at that axis.
