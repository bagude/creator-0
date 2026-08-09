"""Typed transition alphabet for the Creator-0 formal semantics kernel.

The alphabet is a closed enum. Every runtime event used by the formal checker
must map deterministically into one of these labels or be rejected as unmapped.
`tau` is the silent/internal label: it may participate in weak equivalence but
never in external observation traces.
"""
from __future__ import annotations
import enum


class Label(str, enum.Enum):
    OBSERVE = "observe"            # acquire governed evidence
    PROPOSE = "propose"            # emit typed candidate/specification
    VALIDATE = "validate"          # deterministic validation
    REJECT = "reject"              # deterministic rejection
    CONSULT = "consult"            # information-only interaction
    DELEGATE = "delegate"          # bounded authority transfer
    CREATE = "create"              # instantiate or propose descendant Creator
    RETURN = "return"              # child/worker result returned
    ACT_CANDIDATE = "act_candidate"  # mutate candidate workspace
    VERIFY = "verify"              # verify evidence/candidate
    AUTHORIZE = "authorize"        # authorize next bounded transition
    PROMOTE = "promote"            # candidate becomes canonical
    PERSIST = "persist"            # write externalized durable state
    RECONSTRUCT = "reconstruct"    # reconstruct governed state from artifacts
    COMPLETE = "complete"          # resolve a logical computation
    TAU = "tau"                    # silent internal step


TAU = Label.TAU

ALL_LABELS = frozenset(l.value for l in Label)
OBSERVABLE_LABELS = frozenset(l.value for l in Label if l is not Label.TAU)

# Deterministic mapping: HarnessSpec node primitive -> execution label.
# `observe` covers evidence acquisition, so both observe and test primitives
# (deterministic evidence-gathering executions) map to it. `hypothesize`
# emits a typed proposal.
PRIMITIVE_LABEL = {
    "observe": Label.OBSERVE,
    "hypothesize": Label.PROPOSE,
    "test": Label.OBSERVE,
    "act": Label.ACT_CANDIDATE,
    "verify": Label.VERIFY,
    "create": Label.CREATE,
    "return": Label.RETURN,
}

# Deterministic mapping: HarnessSpec edge relation -> interaction label.
# `request_response` is information exchange (the response itself is a
# `return`), so it maps to consult.
RELATION_LABEL = {
    "observe": Label.OBSERVE,
    "consult": Label.CONSULT,
    "request_response": Label.CONSULT,
    "delegate": Label.DELEGATE,
    "verify": Label.VERIFY,
    "authorize": Label.AUTHORIZE,
    "create": Label.CREATE,
    "return": Label.RETURN,
}

# Labels that carry no governed authority: they are permitted as wildcard
# self-loops for any actor in every compiled non-terminal state. Authority-
# bearing labels (act_candidate, create, delegate, authorize, verify, promote,
# complete) are only introduced by nodes, edges, contract capability, or the
# gate, respectively.
NON_AUTHORITY_LABELS = frozenset({
    Label.OBSERVE.value, Label.PROPOSE.value, Label.VALIDATE.value,
    Label.REJECT.value, Label.CONSULT.value, Label.RETURN.value,
    Label.PERSIST.value, Label.RECONSTRUCT.value,
})


class UnmappedLabelError(ValueError):
    """A runtime event label or spec primitive/relation has no deterministic mapping."""


def coerce_label(value: str) -> Label:
    try:
        return Label(value)
    except ValueError:
        raise UnmappedLabelError(f"unmapped label: {value!r}")


def primitive_label(primitive: str) -> Label:
    if primitive not in PRIMITIVE_LABEL:
        raise UnmappedLabelError(f"unmapped node primitive: {primitive!r}")
    return PRIMITIVE_LABEL[primitive]


def relation_label(relation: str) -> Label:
    if relation not in RELATION_LABEL:
        raise UnmappedLabelError(f"unmapped edge relation: {relation!r}")
    return RELATION_LABEL[relation]
