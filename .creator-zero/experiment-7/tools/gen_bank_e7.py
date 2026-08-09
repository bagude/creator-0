"""Experiment 7 held-out bank generator (root-side, pre-freeze).

Authors 20 new primary tasks (5 classes x 4, >=2 surface domains per class)
plus 2 pilot tasks by driving the FROZEN Experiment 6 class generators under
the new frozen seed `creator-0-experiment-7-bank-v1`: every data table,
reference implementation, probe set, ground truth, and claim parameter is
freshly drawn, so every task instance is new and disjoint from the E6 bank
(E6 ∩ Heldout7 = ∅ at the task level; the E6 generator module is imported
read-only and nothing under experiment-6/ is written).

E7 label extensions written post-generation (pre-freeze):
    admissibility_kind        the class's required admissibility kind
    required_role             canonical evidence role for typed scoring
    expected_principles_v2    theta-v2 vocabulary expectation

Blinding: every public package must pass the E6 label-leak/class-token/
topology-cue scan PLUS the E7 class-token set. Salted commitments are
emitted for every label.
"""
from __future__ import annotations
import hashlib
import importlib.util
import json
import random
import re
import sys
from pathlib import Path

E7 = Path(__file__).resolve().parents[1]
CZROOT = E7.parent
E6 = CZROOT / "experiment-6"

BANK_SEED = "creator-0-experiment-7-bank-v1"
SALT_SEED = "creator-0-experiment-7-salts-v1"
SHADOW_SEED = "creator-0-experiment-7-shadows-v1"
ORDER_SEED = "creator-0-experiment-7-order-v1"

KIND_OF_CLASS = {
    "LOCAL": "LOCAL",
    "ISOLATION": "CLEAN_ROOM_AUTHORSHIP",
    "COUNTEREXAMPLE": "NON_AUTHOR_SEARCH",
    "ALTERNATIVE_DECOMPOSITION": "INDEPENDENT_DECOMPOSITION",
    "SPECIALIZED_VERIFICATION": "METHOD_DISJOINT_VERIFICATION",
}
ROLE_OF_CLASS = {
    "LOCAL": "local_author",
    "ISOLATION": "clean_room_author",
    "COUNTEREXAMPLE": "non_author_examiner",
    "ALTERNATIVE_DECOMPOSITION": "independent_decomposer",
    "SPECIALIZED_VERIFICATION": "method_disjoint_verifier",
}
V2_PRINCIPLE = {
    "LOCAL": ["P-LOCALITY"],
    "ISOLATION": ["P-AUTHORSHIP-INDEPENDENCE"],
    "COUNTEREXAMPLE": ["P-NONAUTHOR-SEARCH"],
    "ALTERNATIVE_DECOMPOSITION": ["P-INDEPENDENT-DECOMPOSITION"],
    "SPECIALIZED_VERIFICATION": ["P-METHOD-DISJOINT-VERIFICATION"],
}

E7_CLASS_TOKENS = [
    r"\bCLEAN_ROOM_AUTHORSHIP\b", r"\bNON_AUTHOR_SEARCH\b",
    r"\bINDEPENDENT_DECOMPOSITION\b", r"\bMETHOD_DISJOINT_VERIFICATION\b",
    r"admissibility[-_ ]?kind", r"required[-_ ]?role",
]


def load_e6_gen():
    spec = importlib.util.spec_from_file_location(
        "e6_gen_bank", E6 / "tools" / "gen_bank.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["e6_gen_bank"] = mod
    spec.loader.exec_module(mod)
    return mod


def scan_package(blinding, pkg: Path) -> list[dict]:
    scan = blinding.scan_package(pkg)
    hits = list(scan["hits"])
    for f in sorted(pkg.rglob("*")):
        if not f.is_file():
            continue
        try:
            text = f.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for pat in E7_CLASS_TOKENS:
            m = re.search(pat, text)
            if m:
                hits.append({"file": str(f.relative_to(pkg)),
                             "set": "e7_class_token", "pattern": pat,
                             "match": m.group(0)})
    return hits


def main() -> None:
    gen = load_e6_gen()
    # re-seed the frozen generator machinery for E7
    gen.RNG = random.Random(BANK_SEED)
    slots = (["LOCAL"] * 4 + ["ISOLATION"] * 4 + ["COUNTEREXAMPLE"] * 4 +
             ["ALTERNATIVE_DECOMPOSITION"] * 4 +
             ["SPECIALIZED_VERIFICATION"] * 4)
    shuffled = slots[:]
    gen.RNG.shuffle(shuffled)
    trial_ids = [f"e7-t{i:02d}" for i in range(1, 21)]
    assignment = dict(zip(trial_ids, shuffled))
    gen.ASSIGNMENT = assignment
    gen.TRIAL_IDS = trial_ids

    sys.path.insert(0, str(E6))
    from runtime import blinding

    salt_rng = random.Random(SALT_SEED)
    commitments = {}
    counters = {cls: 0 for cls in gen.GENERATORS}
    all_specs = []
    for tid in trial_ids:
        cls = assignment[tid]
        g = gen.GENERATORS[cls][counters[cls]]
        counters[cls] += 1
        bank = E7 / "task-bank" / tid
        g(tid, bank)
        # E7 label extensions (pre-freeze; labels are then frozen)
        lab_path = bank / "private" / "label.json"
        label = json.loads(lab_path.read_text(encoding="utf-8"))
        label["admissibility_kind"] = KIND_OF_CLASS[cls]
        label["required_role"] = ROLE_OF_CLASS[cls]
        label["expected_principles_v2"] = V2_PRINCIPLE[cls]
        lab_path.write_text(json.dumps(label, indent=2) + "\n",
                            encoding="utf-8")
        # salt + commitment: sha256(salt || canonical(label))
        salt = "%032x" % salt_rng.getrandbits(128)
        (bank / "private" / "salt.txt").write_text(salt + "\n",
                                                   encoding="utf-8")
        canonical = json.dumps(label, sort_keys=True,
                               separators=(",", ":"))
        commitments[tid] = hashlib.sha256(
            (salt + canonical).encode("utf-8")).hexdigest()
        hits = scan_package(blinding, bank / "public")
        if hits:
            raise SystemExit(f"{tid}: BLINDING_FAIL {hits}")
        all_specs.append((tid, cls, g.__name__,
                          label.get("surface_domain", "")))
        print(f"{tid}: {cls} ({g.__name__}) blinding PASS")

    for tid, g in (("e7-p01", gen.gen_pilot_local),
                   ("e7-p02", gen.gen_pilot_iso)):
        bank = E7 / "pilot" / "task-bank" / tid
        g(tid, bank)
        lab_path = bank / "private" / "label.json"
        label = json.loads(lab_path.read_text(encoding="utf-8"))
        cls = label["latent_class"]
        label["admissibility_kind"] = KIND_OF_CLASS[cls]
        label["required_role"] = ROLE_OF_CLASS[cls]
        label["expected_principles_v2"] = V2_PRINCIPLE[cls]
        lab_path.write_text(json.dumps(label, indent=2) + "\n",
                            encoding="utf-8")
        hits = scan_package(blinding, bank / "public")
        if hits:
            raise SystemExit(f"{tid}: BLINDING_FAIL {hits}")
        print(f"{tid}: pilot ({cls}) blinding PASS")

    # domains per class check (frozen design minimum: >=2)
    domains: dict[str, set] = {}
    for tid, cls, gname, dom in all_specs:
        domains.setdefault(cls, set()).add(dom or gname)
    for cls, ds in domains.items():
        if len(ds) < 2:
            raise SystemExit(f"{cls}: fewer than 2 surface domains: {ds}")

    # shadow draw: 2 per class, seeded, stratified
    shadow_rng = random.Random(SHADOW_SEED)
    shadows = []
    for cls in sorted(gen.GENERATORS):
        members = sorted(t for t in trial_ids if assignment[t] == cls)
        shadows.extend(shadow_rng.sample(members, 2))
    shadows.sort()

    # condition order per task, seeded
    order_rng = random.Random(ORDER_SEED)
    cond_order = {t: order_rng.choice(["AB", "BA"]) for t in trial_ids}

    def wj(p: Path, obj):
        p.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n",
                     encoding="utf-8")

    wj(E7 / "trial-manifest.json", {
        "artifact": "Experiment 7 trial manifest",
        "primary_trials": trial_ids,
        "pilot_trials": ["e7-p01", "e7-p02"],
        "class_assignment_seed": BANK_SEED,
        "classes": assignment,
        "domains_per_class": {c: sorted(d) for c, d in domains.items()},
        "note": "classes/domains recorded here are private-side "
                "bookkeeping; public packages carry no class information",
    })
    (E7 / "heldout").mkdir(exist_ok=True)
    wj(E7 / "heldout" / "commitments.json", {
        "artifact": "Experiment 7 held-out label commitments",
        "rule": "sha256(salt || canonical_json(label.json)) per trial; "
                "salts live in the private bank directories",
        "commitments": commitments,
    })
    wj(E7 / "randomization.json", {
        "artifact": "Experiment 7 randomization",
        "shadow_seed": SHADOW_SEED,
        "shadow_trials": shadows,
        "shadow_rule": "2 per class, stratified seeded sample; shadows "
                       "executed in BOTH conditions as that condition's "
                       "runner-up, CONTROL_ONLY",
        "condition_order_seed": ORDER_SEED,
        "condition_order": cond_order,
    })
    print("shadows:", shadows)
    print("bank generation complete")


if __name__ == "__main__":
    main()
