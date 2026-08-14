# Establishing the Difference — creator-0 and genesis

Two repositories by the same steward realize the **same abstract
operator grammar under different ontologies**. This document establishes
what is shared, and then the difference — what each system governs, what
each conserves, and which substitution each exists to forbid.

## The shared grammar

Both systems refuse to let a language model's output act directly on the
world. Each interposes a typed pipeline in which *proposing*,
*authorizing*, and *realizing* are distinct operators with distinct
capability sets:

    creator-0:  Task -> Creator -> proposed HarnessSpec
                  -> deterministic boundary/compiler
                  -> authorized Harness -> optional child Creator

    genesis:    B_t -> BuildProposal -> Repo_t
                  -> Verification -> BuildGrounding -> B_{t+1}

Each states the same core invariant in its own vocabulary:

| creator-0                          | genesis                          |
|------------------------------------|----------------------------------|
| LLM output                         | Proposal `p`                     |
| typed intent (HarnessSpec)         | candidate action `ã`             |
| authorized topology (Harness)      | admitted action `a`              |
| world transition                   | ledger event `e`                 |

`LLM output != typed intent != authorized topology != world transition`
and `p != ã != a != e` are the same law. In both systems, rejection is
an event, not a mutation: an inadmissible candidate leaves the
authoritative state unchanged while the record grows.

## The difference

The systems differ not in grammar but in **what quantity the law
conserves** — which substitution each is built to make impossible.

### 1. Object of governance: capability vs. evidence

- **creator-0 governs authority.** Its pipeline decides *what an agent
  may become and do*. The deterministic boundary/compiler authorizes a
  capability topology; three independent types (boundary, message,
  relationship) keep "what may cross", "what crossed", and "what
  causal authority the crossing carries" from collapsing into each
  other. The forbidden substitution is **deontic**: nothing executes
  with authority it was not compiled to have. A Creator may propose
  composition but cannot rewrite the root rules that authorize
  composition.

- **genesis governs knowledge.** Its pipeline decides *what may be
  called measured*. The verifier derives every property from repository
  evidence (git history, probe execution) and refuses builder
  narrative; the measurement law is "no property is called measured
  unless `R_B` derives it from repository evidence." The forbidden
  substitution is **epistemic**: nothing enters the record as observed
  that was merely claimed. A builder may propose a difference but
  cannot declare it realized — the grounding must restate the
  prediction verbatim and cover it with derived measurements.

One system conserves *bounded authority*; the other conserves *truthful
attribution of change*.

### 2. Where the law lives

- In **creator-0** the law is *in front of* action: a protected
  compiler and a `PreToolUse` hook block unauthorized writes before
  they happen. Prevention-shaped. Maintenance requires an explicit
  out-of-band capability (`CREATOR_ZERO_MAINTENANCE=1`).

- In **genesis** the law is *behind* action: any commit can physically
  occur, but the verifier, gate (`G_B`), and promotion (`P_B`)
  determine what becomes canonical, and violations are permanent ledger
  facts. Detection-and-admission-shaped; capability-level prevention is
  explicitly declared a platform limitation, not a pretense.

### 3. Shape of growth

- **creator-0 grows by descent.** It is a self-installing overlay
  (`install.py` carries a payload of itself); Creator Closure preserves
  capability across generations — `C_n -> H_n[C_{n+1}]` with mediated
  closure through the one trusted compiler. Its lineage is a tree of
  installations.

- **genesis grows by accretion.** It is a single canonical lineage with
  an add-only ledger: proposals, groundings, audits, receipts, and
  rejections are only ever appended, and closed records are immutable.
  Its lineage is one chain of admitted transitions (BUILD-000 through
  BUILD-003 closed; BUILD-004 designated for Phase 0).

### 4. Relation between the loops

genesis's ALGEBRA.md already states that its build loop instantiates
the same grammar as the laboratory runtime loop it is constructing.
creator-0 is a third realization of that grammar — over *agent
composition* rather than repository state or world state:

| Realization        | Substrate           | Admitting authority          |
|--------------------|---------------------|------------------------------|
| laboratory runtime | world state `W_t`   | lawful transition `T̄_W`     |
| construction       | repository `Repo_t` | verifier/gate/promotion      |
| creator-0          | harness topology    | boundary/compiler            |

## Establishment

Establishing a difference, in the shared grammar, is itself a lawful
act: propose it, realize it under law, measure it, record it. This
document is the record on the creator-0 side. On the genesis side the
same directive is realized in that repository's own vocabulary: the
BUILD-004 proposal (Phase 0 — Genesis / contracts), committed on the
branch `claude/establish-difference-6nwj98`, whose content is precisely
the frozen set of typed differences the laboratory must never allow to
collapse.
