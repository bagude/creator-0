"""Strong and weak bisimulation over finite LTSs.

Observable action = (label, actor) pair; tau is silent regardless of actor.
Actor strings are compared literally here (no wildcard semantics): both LTSs
must use the same actor vocabulary for the governed observation alphabet.

strong_bisimilar: greatest strong bisimulation via naive fixpoint refinement.
weak_bisimilar:   greatest weak bisimulation, where an observable move
                  p --l--> p' is matched by q ==tau*.l.tau*==> q', and a tau
                  move is matched by q ==tau*==> q' (possibly zero steps).

Weak bisimulation is the default notion for artifact-mediated session
equivalence: E_n ~= E_hat_{n->n+1} means behavioral equivalence over the
governed observation alphabet, never equality of hidden epistemic states.
"""
from __future__ import annotations
from typing import Any, Callable

from .labels import Label
from .model import FAIL, PASS, FormalResult, LTS

TAU = Label.TAU.value

Move = tuple[str, str, str]  # (label, actor, target)


def _actions(lts: LTS) -> dict[str, set[Move]]:
    out: dict[str, set[Move]] = {s: set() for s in lts.states}
    for t in lts.transitions:
        out[t.source].add((t.label, t.actor, t.target))
    return out


def _tau_closure(lts: LTS) -> dict[str, frozenset[str]]:
    succ: dict[str, set[str]] = {s: {s} for s in lts.states}
    for t in lts.transitions:
        if t.label == TAU:
            succ[t.source].add(t.target)
    changed = True
    while changed:
        changed = False
        for s in lts.states:
            new = set(succ[s])
            for r in succ[s]:
                new |= succ[r]
            if new != succ[s]:
                succ[s] = new
                changed = True
    return {s: frozenset(v) for s, v in succ.items()}


def _weak_moves(lts: LTS) -> dict[str, set[Move]]:
    """state -> {(l, actor, target) : s ==tau* l tau*==> target, l observable}
    plus {(tau, '*', target) : s ==tau*==> target}."""
    closure = _tau_closure(lts)
    acts = _actions(lts)
    out: dict[str, set[Move]] = {s: set() for s in lts.states}
    for s in lts.states:
        for mid in closure[s]:
            for (lab, actor, tgt) in acts[mid]:
                if lab == TAU:
                    continue
                for end in closure[tgt]:
                    out[s].add((lab, actor, end))
        for end in closure[s]:
            out[s].add((TAU, "*", end))
    return out


def _match_exists(move: Move, answers: set[Move], weak: bool,
                  related: Callable[[str, str], bool]) -> bool:
    lab, actor, tgt = move
    if weak and lab == TAU:
        return any(related(tgt, end) for (l2, _a2, end) in answers if l2 == TAU)
    return any(related(tgt, end) for (l2, a2, end) in answers
               if l2 == lab and a2 == actor)


def _greatest_bisim(a: LTS, b: LTS, weak: bool) -> set[tuple[str, str]]:
    acts_a, acts_b = _actions(a), _actions(b)
    ans_a = _weak_moves(a) if weak else acts_a
    ans_b = _weak_moves(b) if weak else acts_b
    rel: set[tuple[str, str]] = {(p, q) for p in a.states for q in b.states}
    changed = True
    while changed:
        changed = False
        for (p, q) in sorted(rel):
            fwd = all(_match_exists(m, ans_b[q], weak,
                                    lambda x, y: (x, y) in rel)
                      for m in acts_a[p])
            bwd = all(_match_exists(m, ans_a[p], weak,
                                    lambda x, y: (y, x) in rel)
                      for m in acts_b[q])
            if not (fwd and bwd):
                rel.discard((p, q))
                changed = True
    return rel


def _counterexample(a: LTS, b: LTS, rel: set[tuple[str, str]],
                    weak: bool) -> dict[str, Any]:
    """Smallest practical distinguishing evidence: BFS from the initial pair
    through jointly-matchable actions to the first pair where matching fails."""
    acts_a, acts_b = _actions(a), _actions(b)
    ans_a = _weak_moves(a) if weak else acts_a
    ans_b = _weak_moves(b) if weak else acts_b

    def immediate_fail(p: str, q: str):
        """An action with no same-(label, actor) response at all — the
        sharpest distinguishing evidence."""
        always = lambda _x, _y: True
        for m in sorted(acts_a[p]):
            if not _match_exists(m, ans_b[q], weak, always):
                return {"side": "A", "state_pair": [p, q],
                        "unmatched_action": {"label": m[0], "actor": m[1]},
                        "note": "B has no move with this label/actor"}
        for m in sorted(acts_b[q]):
            if not _match_exists(m, ans_a[p], weak, always):
                return {"side": "B", "state_pair": [p, q],
                        "unmatched_action": {"label": m[0], "actor": m[1]},
                        "note": "A has no move with this label/actor"}
        return None

    def related_fail(p: str, q: str):
        for m in sorted(acts_a[p]):
            if not _match_exists(m, ans_b[q], weak, lambda x, y: (x, y) in rel):
                return {"side": "A", "state_pair": [p, q],
                        "unmatched_action": {"label": m[0], "actor": m[1]},
                        "note": "B has no matching move to a related pair"}
        for m in sorted(acts_b[q]):
            if not _match_exists(m, ans_a[p], weak, lambda x, y: (y, x) in rel):
                return {"side": "B", "state_pair": [p, q],
                        "unmatched_action": {"label": m[0], "actor": m[1]},
                        "note": "A has no matching move to a related pair"}
        return None

    start = (a.initial, b.initial)
    seen = {start}
    frontier: list[tuple[tuple[str, str], list[dict[str, str]]]] = [(start, [])]
    fallback = None
    while frontier:
        (p, q), path = frontier.pop(0)
        reason = immediate_fail(p, q)
        if reason is not None:
            reason["path_from_initial"] = path
            return reason
        if fallback is None:
            rf = related_fail(p, q)
            if rf is not None:
                rf["path_from_initial"] = path
                fallback = rf
        for (lab, actor, p2) in sorted(acts_a[p]):
            for (l2, a2, q2) in sorted(acts_b[q]):
                if l2 == lab and a2 == actor and (p2, q2) not in seen:
                    seen.add((p2, q2))
                    frontier.append(((p2, q2),
                                     path + [{"label": lab, "actor": actor}]))
    if fallback is not None:
        return fallback
    return {"state_pair": [a.initial, b.initial],
            "note": "initial states are not related by the greatest bisimulation"}


def _run(a: LTS, b: LTS, weak: bool) -> FormalResult:
    kind = "weak_bisimulation" if weak else "strong_bisimulation"
    rel_sym = "~=" if weak else "~"
    rel = _greatest_bisim(a, b, weak)
    ok = (a.initial, b.initial) in rel
    assumptions = [
        "Observable action = (label, actor); actor strings compared literally.",
        "Finite explicitly-modeled state spaces only; no claim about hidden "
        "epistemic states or unrestricted future models.",
    ]
    if weak:
        assumptions.append("Weak matching: tau* observable tau*; tau moves may "
                           "be matched by zero or more tau steps.")
    if ok:
        return FormalResult(
            check=kind, status=PASS, formal_relation=f"A {rel_sym} B",
            evidence=[f"greatest bisimulation contains initial pair "
                      f"({a.initial!r}, {b.initial!r})",
                      f"relation size: {len(rel)} pairs"],
            assumptions=assumptions,
            detail={"relation_size": len(rel)})
    return FormalResult(
        check=kind, status=FAIL, formal_relation=f"A {rel_sym} B",
        counterexample=_counterexample(a, b, rel, weak),
        evidence=[f"relation size: {len(rel)} pairs; initial pair absent"],
        assumptions=assumptions)


def strong_bisimilar(a: LTS, b: LTS) -> FormalResult:
    return _run(a, b, weak=False)


def weak_bisimilar(a: LTS, b: LTS, silent_label: str = TAU) -> FormalResult:
    if silent_label != TAU:
        raise ValueError("v0.1 supports only tau as the silent label")
    return _run(a, b, weak=True)
