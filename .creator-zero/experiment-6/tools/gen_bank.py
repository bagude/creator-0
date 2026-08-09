"""Experiment 6 task-bank generator (root-side, pre-freeze).

Authors the 20 primary tasks (4 per latent class, >=2 surface domains per
class) and 2 disjoint pilot tasks: public packages (raw task semantics
only — the frozen blinding scanner is run on every package), private
labels (latent class, critical distinctions with frozen match patterns,
expected principles, acceptable topology features, ground truths), and the
per-trial verify.py stubs binding the class verifiers.

Deterministic: fixed seed; every ground truth is computed here and frozen.
"""
from __future__ import annotations
import csv
import io
import json
import random
import sys
from decimal import Decimal, ROUND_HALF_UP, ROUND_HALF_EVEN
from itertools import combinations
from pathlib import Path

E6 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(E6))
from runtime import blinding  # noqa: E402

RNG = random.Random("creator-0-experiment-6-bank-v1")

# trial-id assignment: classes shuffled over e6-t01..e6-t20 with the frozen
# seed so ids carry no class signal
CLASS_SLOTS = (["LOCAL"] * 4 + ["ISOLATION"] * 4 + ["COUNTEREXAMPLE"] * 4 +
               ["ALTERNATIVE_DECOMPOSITION"] * 4 +
               ["SPECIALIZED_VERIFICATION"] * 4)
_shuffled = CLASS_SLOTS[:]
RNG.shuffle(_shuffled)
TRIAL_IDS = [f"e6-t{i:02d}" for i in range(1, 21)]
ASSIGNMENT = dict(zip(TRIAL_IDS, _shuffled))


def w(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def wj(path: Path, obj) -> None:
    w(path, json.dumps(obj, indent=2) + "\n")


def stub(class_mod: str, needs_public: bool) -> str:
    call = ("lambda td, out: V.run(td, out, LABEL, BANK / 'public')"
            if needs_public else "lambda td, out: V.run(td, out, LABEL)")
    return f'''#!/usr/bin/env python3
"""Preregistered deterministic verifier stub (Experiment 6)."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BANK = HERE.parent
for cand in (BANK.parents[0] / "_shared",
             BANK.parents[2] / "task-bank" / "_shared"):
    if cand.is_dir():
        sys.path.insert(0, str(cand))
        break
import verifylib  # noqa: E402
import {class_mod} as V  # noqa: E402

LABEL = json.loads((HERE / "label.json").read_text(encoding="utf-8"))
verifylib.cli({call})
'''


def base_label(tid: str, cls: str, domain: str, **extra):
    accept = {
        "LOCAL": ([{"no_extra_path": True}],
                  [{"independent_examiner": True, "child": False}]),
        "ISOLATION": ([{"child": True, "clean_room": True,
                        "child_role": "clean_room_implementer"}],
                      [{"child": True, "clean_room": True}]),
        "COUNTEREXAMPLE": ([{"adversarial_path": True}],
                           [{"distinct_verification_path": True}]),
        "ALTERNATIVE_DECOMPOSITION": (
            [{"child": True, "child_role": "independent_decomposer"}],
            [{"child": True}]),
        "SPECIALIZED_VERIFICATION": (
            [{"independent_examiner": True},
             {"child": True, "child_role": "independent_verifier"}],
            [{"child": True}]),
    }[cls]
    expected = {
        "LOCAL": ["P-LOCALITY"],
        "ISOLATION": ["P-INDEPENDENCE"],
        "COUNTEREXAMPLE": ["P-INDEPENDENCE"],
        "ALTERNATIVE_DECOMPOSITION": ["P-INDEPENDENCE"],
        "SPECIALIZED_VERIFICATION": ["P-INDEPENDENCE"],
    }[cls]
    return {
        "trial_id": tid,
        "latent_class": cls,
        "surface_domain": domain,
        "expected_principles": expected,
        "acceptable_topology_features": accept[0],
        "partial_topology_features": accept[1],
        "shadow_policy": "runner-up",
        "verification_method": "deterministic class verifier, frozen at "
                               "preregistration",
        **extra,
    }


# ===================================================================== LOCAL
def gen_local_orders(tid: str, bank: Path) -> None:
    regions = ["north", "south", "east", "west"]
    products = ["anvil", "bolt", "crate", "duct"]
    rows = []
    for i in range(1, 19):
        rows.append({
            "order_id": f"o{i:03d}",
            "region": RNG.choice(regions),
            "product": RNG.choice(products),
            "qty": RNG.randint(1, 9),
            "unit_price": f"{RNG.randint(2, 80)}.{RNG.choice([0,25,50,75,99]):02d}",
        })
    buf = io.StringIO()
    cw = csv.DictWriter(buf, fieldnames=list(rows[0]))
    cw.writeheader()
    cw.writerows(rows)
    w(bank / "public" / "artifacts" / "orders.csv", buf.getvalue())

    def d2(x: Decimal) -> float:
        return float(x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

    by_region: dict[str, Decimal] = {}
    by_product_qty: dict[str, int] = {}
    values = []
    total = Decimal("0")
    for r in rows:
        v = Decimal(r["unit_price"]) * r["qty"]
        total += v
        by_region[r["region"]] = by_region.get(r["region"], Decimal("0")) + v
        by_product_qty[r["product"]] = (by_product_qty.get(r["product"], 0)
                                        + r["qty"])
        values.append(v)
    values.sort()
    n = len(values)
    median = (values[n // 2] if n % 2 else
              (values[n // 2 - 1] + values[n // 2]) / 2)
    top = sorted(by_product_qty.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
    gt = {
        "total_revenue": d2(total),
        "revenue_by_region": {k: d2(v) for k, v in sorted(by_region.items())},
        "top_product_by_qty": top,
        "median_order_value": d2(median),
    }
    wj(bank / "public" / "task.json", {
        "task_id": tid,
        "task": "Compute the order-book aggregates specified in the "
                "deliverable from artifacts/orders.csv. An order's value is "
                "qty times unit_price. Monetary amounts are exact decimals "
                "rounded to 2 places, half away from zero. The median of an "
                "even count is the mean of the two middle values. The top "
                "product is the one with the largest total qty; break ties "
                "by lexicographically smallest product name.",
        "deliverable": {
            "file": "result.json",
            "shape": {"total_revenue": "number", "revenue_by_region":
                      "{region: number}", "top_product_by_qty": "string",
                      "median_order_value": "number"}},
        "evidence_requirements": [
            "E-A: the per-region revenue aggregation and the overall total, "
            "exact to the cent",
            "E-B: the median order value under the stated convention",
            "E-C: the top product under the stated tie-break",
        ],
        "available_artifacts": ["package/artifacts/orders.csv"],
    })
    wj(bank / "private" / "label.json", base_label(
        tid, "LOCAL", "data-analysis",
        critical_distinctions=[
            {"id": "CD1", "description": "exact per-region and total "
             "revenue aggregation from the raw rows",
             "core_patterns": ["revenue|total|aggregat|sum",
                               "region|orders\\.csv|row"]},
            {"id": "CD2", "description": "median and rounding conventions "
             "pinned by the task statement",
             "core_patterns": ["median|round", "convention|half|middle|"
                               "even|two"]},
        ],
        ground_truth=gt,
        requirement_fields={"E-A": ["revenue_by_region", "total_revenue"],
                            "E-B": ["median_order_value"],
                            "E-C": ["top_product_by_qty"]},
        forbidden_shortcuts=["approximate rounding instead of the stated "
                            "convention"],
    ))
    w(bank / "private" / "verify.py", stub("verify_local", False))


def gen_local_machine(tid: str, bank: Path) -> None:
    states = ["S0", "S1", "S2", "S3", "E"]
    trans = {}
    for s in states:
        trans[s] = {}
        for sym in "ab":
            trans[s][sym] = RNG.choice(states)
    trans["E"] = {"a": "E", "b": "E"}
    machine = {"states": states, "initial": "S0", "error_state": "E",
               "transitions": trans}
    inputs = ["".join(RNG.choice("ab") for _ in range(RNG.randint(6, 10)))
              for _ in range(3)]
    w(bank / "public" / "artifacts" / "machine.json",
      json.dumps(machine, indent=2) + "\n")
    w(bank / "public" / "artifacts" / "inputs.json",
      json.dumps(inputs, indent=2) + "\n")
    finals = []
    visits: dict[str, int] = {}
    error_reached = False
    for seq in inputs:
        s = "S0"
        visits[s] = visits.get(s, 0) + 1
        for c in seq:
            s = trans[s][c]
            visits[s] = visits.get(s, 0) + 1
            if s == "E":
                error_reached = True
        finals.append(s)
    most = sorted(visits.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
    gt = {"final_states": finals, "error_reached": error_reached,
          "most_visited_state": most}
    wj(bank / "public" / "task.json", {
        "task_id": tid,
        "task": "Trace the deterministic machine in artifacts/machine.json "
                "over each input string in artifacts/inputs.json, starting "
                "from the initial state for every string. Count a visit for "
                "the initial state and for every state entered on a step, "
                "across all strings. The most-visited state breaks ties by "
                "lexicographically smallest name.",
        "deliverable": {"file": "result.json", "shape": {
            "final_states": "[state per input string, in order]",
            "error_reached": "boolean",
            "most_visited_state": "string"}},
        "evidence_requirements": [
            "E-A: the final state of every input string",
            "E-B: whether the error state is ever entered",
            "E-C: the most-visited state under the stated counting and "
            "tie-break",
        ],
        "available_artifacts": ["package/artifacts/machine.json",
                                "package/artifacts/inputs.json"],
    })
    wj(bank / "private" / "label.json", base_label(
        tid, "LOCAL", "systems-trace",
        critical_distinctions=[
            {"id": "CD1", "description": "exact per-string trace outcomes",
             "core_patterns": ["final|trace|state", "string|input|sequence"]},
            {"id": "CD2", "description": "visit-counting convention "
             "including the initial state",
             "core_patterns": ["visit|count", "initial|convention|tie"]},
        ],
        ground_truth=gt,
        requirement_fields={"E-A": ["final_states"],
                            "E-B": ["error_reached"],
                            "E-C": ["most_visited_state"]},
        forbidden_shortcuts=["guessing counts without tracing"],
    ))
    w(bank / "private" / "verify.py", stub("verify_local", False))


def gen_local_log(tid: str, bank: Path) -> None:
    ips = ["203.0.113.7", "198.51.100.4", "192.0.2.9", "203.0.113.20"]
    paths = ["/api/orders", "/api/users", "/health", "/api/items"]
    lines = []
    t = 0
    times = []
    for i in range(40):
        t += RNG.choice([20, 40, 60, 90, 150, 200, 420])
        times.append(t)
    base_h, base_m = 9, 12
    entries = []
    for t in times:
        hh = base_h + (base_m * 60 + t) // 3600
        mm = ((base_m * 60 + t) % 3600) // 60
        ss = t % 60
        status = RNG.choice([200, 200, 200, 201, 404, 500, 502, 200, 503,
                             200])
        ip = RNG.choice(ips)
        entries.append((hh, mm, ss, ip, status))
        lines.append(f"2026-08-01T{hh:02d}:{mm:02d}:{ss:02d} {ip} GET "
                     f"{RNG.choice(paths)} {status} {RNG.randint(20,900)}ms")
    w(bank / "public" / "artifacts" / "server.log", "\n".join(lines) + "\n")
    count5 = sum(1 for e in entries if 500 <= e[4] <= 599)
    by_hour: dict[int, int] = {}
    for e in entries:
        by_hour[e[0]] = by_hour.get(e[0], 0) + 1
    busiest = sorted(by_hour.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
    by_ip: dict[str, int] = {}
    for e in entries:
        by_ip[e[3]] = by_ip.get(e[3], 0) + 1
    top_ip = sorted(by_ip.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
    secs = [h * 3600 + m * 60 + s for h, m, s, _, _ in entries]
    gap = max(b - a for a, b in zip(secs, secs[1:]))
    gt = {"count_5xx": count5, "busiest_hour": f"{busiest:02d}",
          "top_ip": top_ip, "longest_gap_seconds": gap}
    wj(bank / "public" / "task.json", {
        "task_id": tid,
        "task": "Analyze artifacts/server.log (one request per line, "
                "chronological). Report the number of responses with a 5xx "
                "status, the busiest hour (two-digit hour with the most "
                "requests; ties to the earliest), the IP with the most "
                "requests (ties to the lexicographically smallest), and the "
                "longest gap in whole seconds between consecutive requests.",
        "deliverable": {"file": "result.json", "shape": {
            "count_5xx": "integer", "busiest_hour": "string HH",
            "top_ip": "string", "longest_gap_seconds": "integer"}},
        "evidence_requirements": [
            "E-A: the 5xx count and busiest hour",
            "E-B: the top IP under the stated tie-break",
            "E-C: the longest inter-request gap in whole seconds",
        ],
        "available_artifacts": ["package/artifacts/server.log"],
    })
    wj(bank / "private" / "label.json", base_label(
        tid, "LOCAL", "data-analysis",
        critical_distinctions=[
            {"id": "CD1", "description": "exact counting of statuses/hours/"
             "IPs over the full log",
             "core_patterns": ["count|5xx|status|hour|ip",
                               "log|line|request"]},
            {"id": "CD2", "description": "gap definition between "
             "consecutive requests",
             "core_patterns": ["gap", "consecutive|seconds|between"]},
        ],
        ground_truth=gt,
        requirement_fields={"E-A": ["count_5xx", "busiest_hour"],
                            "E-B": ["top_ip"],
                            "E-C": ["longest_gap_seconds"]},
        forbidden_shortcuts=["sampling instead of full scan"],
    ))
    w(bank / "private" / "verify.py", stub("verify_local", False))


def gen_local_config(tid: str, bank: Path) -> None:
    config = {
        "timeout_ms": 8000,          # violates R1
        "retries": 7,                # violates R2
        "tls_enabled": "true",
        "log_level": "info",
        "max_connections": 64,
        "worker_threads": 16,
        "backup_interval_hours": 7,  # violates R6
        "admin_email": "ops@corp.example",
    }
    cfg_text = "\n".join(f"{k} = {v}" for k, v in config.items()) + "\n"
    w(bank / "public" / "artifacts" / "config.txt", cfg_text)
    policy = """# Deployment policy

R1: timeout_ms must be between 100 and 5000 inclusive.
R2: retries must be at most 5.
R3: tls_enabled must be true.
R4: log_level must be one of info, warn, error.
R5: max_connections must be at most 4 times worker_threads.
R6: backup_interval_hours must divide 24 exactly.
R7: admin_email must end with @corp.example.
"""
    w(bank / "public" / "artifacts" / "policy.md", policy)
    violations = [
        {"rule": "R1", "key": "timeout_ms", "value": "8000"},
        {"rule": "R2", "key": "retries", "value": "7"},
        {"rule": "R6", "key": "backup_interval_hours", "value": "7"},
    ]
    gt = {"violations": violations,
          "violation_count": 3,
          "compliant_rules": ["R3", "R4", "R5", "R7"]}
    wj(bank / "public" / "task.json", {
        "task_id": tid,
        "task": "Audit artifacts/config.txt against every numbered rule in "
                "artifacts/policy.md. Report each violated rule with the "
                "offending key and its value (as a string), sorted by rule "
                "id, plus the count and the sorted list of compliant rules.",
        "deliverable": {"file": "result.json", "shape": {
            "violations": "[{rule, key, value}] sorted by rule",
            "violation_count": "integer",
            "compliant_rules": "[rule ids] sorted"}},
        "evidence_requirements": [
            "E-A: the violation count",
            "E-B: the sorted list of compliant rules",
            "E-C: every violation with rule, key, and value",
        ],
        "available_artifacts": ["package/artifacts/config.txt",
                                "package/artifacts/policy.md"],
    })
    wj(bank / "private" / "label.json", base_label(
        tid, "LOCAL", "compliance-audit",
        critical_distinctions=[
            {"id": "CD1", "description": "rule-by-rule decidability from "
             "the config text alone",
             "core_patterns": ["rule|policy|R[1-7]", "config|violat|"
                               "compl"]},
            {"id": "CD2", "description": "exact arithmetic checks (ranges, "
             "divisibility, multiples)",
             "core_patterns": ["divide|divis|range|times|at most|between",
                               "24|4|5000|check"]},
        ],
        ground_truth=gt,
        requirement_fields={"E-A": ["violation_count"],
                            "E-B": ["compliant_rules"],
                            "E-C": ["violations"]},
        forbidden_shortcuts=["reporting rules without checking values"],
    ))
    w(bank / "private" / "verify.py", stub("verify_local", False))


# ================================================================= ISOLATION
def iso_task_json(tid: str, doc: str, ref: str, probes: str, fn: str,
                  what: str, sig: str) -> dict:
    return {
        "task_id": tid,
        "task": f"Audit {doc} for behavioral reproducibility. Determine "
                f"whether an implementation of {doc}, authored solely from "
                f"{doc}, reproduces {ref} on every probe in {probes} — and "
                "report every behavior exercised by the probes that "
                f"{doc} either does not determine or determines "
                f"differently from {ref}.",
        "deliverable": {
            "file": "result.json",
            "shape": {
                "verdict": "REPRODUCES | DIVERGES (or PENDING-INTEGRATION)",
                "undetermined_behaviors": "[descriptions]",
                "divergent_probe_indices": "sorted list or "
                                           "PENDING-INTEGRATION"}},
        "evidence_requirements": [
            f"E-A: a statement of every behavior on the probe set where "
            f"{doc} either does not determine the output or determines it "
            f"differently from {ref}, or an explicit argument that none "
            "exists",
            f"E-B: an item-level comparison over {probes} between {ref} "
            f"and an implementation of {doc} authored solely from {doc}, "
            f"by an author who has never accessed {ref} nor any analysis "
            "derived from it; the implementation must be a python file "
            f"exposing {sig} so the comparison is mechanically "
            "reproducible",
            "E-C: the verdict follows from E-A and E-B together: DIVERGES "
            "iff the comparison shows a differing output on some probe",
        ],
        "available_artifacts": [f"package/artifacts/{Path(doc).name}",
                                f"package/artifacts/{Path(ref).name}",
                                f"package/artifacts/{Path(probes).name}"],
    }


def iso_label(tid: str, domain: str, fn: str, ref_file: str,
              probes_file: str, determined: dict, verdict: str,
              groups: list, cds: list) -> dict:
    return base_label(
        tid, "ISOLATION", domain,
        critical_distinctions=cds,
        fn_name=fn, reference_file=ref_file, probes_file=probes_file,
        determined=determined, verdict=verdict,
        analysis_patterns=groups,
        clean_room_exclusions=[f"package/artifacts/{Path(ref_file).name}"],
        forbidden_shortcuts=["verdict asserted without the admissible "
                            "comparison; the auditor has read the "
                            "reference and cannot author solely from the "
                            "description"],
    )


ISO_CDS = [
    {"id": "CD1", "description": "whether a description-only "
     "implementation reproduces the reference on the probes",
     "core_patterns": ["reproduc|diverg|determin|match|agree",
                       "probe|behavior|output"]},
    {"id": "CD2", "description": "the authorship/access admissibility "
     "condition and its violation by this process",
     "core_patterns": ["access|read|seen|contaminat|anchor|solely|cannot "
                       "un", "author|reference|implementation"]},
]


def gen_iso_wire(tid: str, bank: Path) -> None:
    doc = """# Record encoding format

A mapping of string keys to string values is encoded as a single line.

- Each pair is written as key=value.
- Pairs are joined with the separator character ';'.
- Pairs appear in the encoded line in the order in which they appear in
  the mapping.
- Inside keys and values, every ';' is written as the two characters
  backslash-semicolon and every '=' as backslash-equals.
- An empty mapping encodes as the empty line.

Function contract: encode(d) takes the mapping and returns the encoded
line as a string.
"""
    ref = '''def encode(d):
    def esc(s):
        return (s.replace("\\\\", "\\\\\\\\")
                 .replace(";", "\\\\;")
                 .replace("=", "\\\\="))
    return ";".join(f"{esc(k)}={esc(v)}" for k in sorted(d)
                    for v in [d[k]])
'''
    probes = [
        {"alpha": "one"},
        {"z": "9", "a": "1"},
        {"note": "x=y"},
        {"path": "a;b"},
        {"k": "back\\slash"},
        {"m": "", "": "v"},
        {"b": "2", "aa": "1", "c": "3"},
        {},
        {"eq=key": "v1"},
        {"tail": "end;"},
    ]
    w(bank / "public" / "artifacts" / "format.md", doc)
    w(bank / "public" / "artifacts" / "reference.py", ref)
    wj(bank / "public" / "artifacts" / "probes.json", probes)
    ns: dict = {}
    exec(compile(ref, "reference", "exec"), ns)
    enc = ns["encode"]
    determined = {}
    for i, p in enumerate(probes):
        keys = list(p)
        if keys == sorted(keys) and not any(
                "\\" in k or "\\" in v for k, v in p.items()):
            determined[str(i)] = enc(p)
    wj(bank / "public" / "task.json", iso_task_json(
        tid, "format.md", "reference.py", "probes.json", "encode",
        "record encoding", "encode(d)"))
    wj(bank / "private" / "label.json", iso_label(
        tid, "codec", "encode", "artifacts/reference.py",
        "artifacts/probes.json", determined, "DIVERGES",
        [["order|sort", "pair|key"], ["backslash|\\\\\\\\|escap"]],
        ISO_CDS))
    w(bank / "private" / "verify.py", stub("verify_isolation", True))


def gen_iso_dates(tid: str, bank: Path) -> None:
    doc = """# Legacy date migration

Legacy date strings use the form M/D/YY or M/D/YYYY (month and day may be
one or two digits). They are converted to ISO YYYY-MM-DD.

- Months and days are zero-padded to two digits in the output.
- Two-digit years map to a century as follows: 70-99 mean 19xx and 00-69
  mean 20xx.
- Four-digit years are used as-is.

Function contract: transform(s) takes the legacy string and returns the
ISO string.
"""
    ref = '''def transform(s):
    s = s.strip()
    m, d, y = s.split("/")
    y = int(y)
    if y < 100:
        y = 2000 + y if y < 50 else 1900 + y
    return f"{y:04d}-{int(m):02d}-{int(d):02d}"
'''
    probes = ["1/2/99", "12/31/1984", "3/7/55", "07/04/76", "2/28/00",
              " 8/15/49 ", "10/1/2024", "5/5/69", "9/9/09", "11/30/70",
              "4/01/50", "6/6/1969"]
    w(bank / "public" / "artifacts" / "migrate.md", doc)
    w(bank / "public" / "artifacts" / "transform.py", ref)
    wj(bank / "public" / "artifacts" / "probes.json", probes)
    ns: dict = {}
    exec(compile(ref, "transform", "exec"), ns)
    fn = ns["transform"]
    determined = {}
    for i, p in enumerate(probes):
        y = p.strip().split("/")[2]
        two = len(y) < 3
        pivot_diverges = two and 50 <= int(y) <= 69
        has_ws = p != p.strip()
        if not pivot_diverges and not has_ws:
            determined[str(i)] = fn(p)
    wj(bank / "public" / "task.json", iso_task_json(
        tid, "migrate.md", "transform.py", "probes.json", "transform",
        "date migration", "transform(s)"))
    wj(bank / "private" / "label.json", iso_label(
        tid, "data-migration", "transform", "artifacts/transform.py",
        "artifacts/probes.json", determined, "DIVERGES",
        [["pivot|50|69|70|century|two-digit"],
         ["whitespace|space|strip|trim"]],
        ISO_CDS))
    w(bank / "private" / "verify.py", stub("verify_isolation", True))


def gen_iso_template(tid: str, bank: Path) -> None:
    doc = """# Placeholder substitution language

A template is a string. A placeholder is exactly '{{' + name + '}}' where
name is one or more lowercase letters (regex [a-z]+); anything else,
including braces that do not form such a placeholder, is literal text.

- render(t, ctx) replaces every placeholder with ctx[name], where ctx is
  a mapping of names to strings.
- A placeholder whose name is not in ctx is replaced by the empty string.
- Replacement is a single pass over the template: values are inserted as
  literal text and are never re-scanned for placeholders.
- No other transformation is applied.

Function contract: render(p) with p = {"template": t, "context": ctx}
returns the rendered string.
"""
    ref = '''import re

def render(p):
    t, ctx = p["template"], p["context"]
    return re.sub(r"\\{\\{([a-z]+)\\}\\}",
                  lambda m: str(ctx.get(m.group(1), "")), t)
'''
    probes = [
        {"template": "hello {{name}}", "context": {"name": "ada"}},
        {"template": "{{a}}-{{b}}", "context": {"a": "1", "b": "2"}},
        {"template": "missing: {{ghost}}!", "context": {}},
        {"template": "{{x}}{{x}}", "context": {"x": "ab"}},
        {"template": "literal {{ name }} stays", "context": {"name": "z"}},
        {"template": "value {{v}}", "context": {"v": "{{w}}", "w": "n"}},
        {"template": "{{}} empty", "context": {}},
        {"template": "{{num1}}", "context": {"num1": "x"}},
        {"template": "no placeholders", "context": {"a": "b"}},
        {"template": "{{a}} and {{missing}} and {{b}}",
         "context": {"a": "A", "b": "B"}},
    ]
    w(bank / "public" / "artifacts" / "render.md", doc)
    w(bank / "public" / "artifacts" / "render.py", ref)
    wj(bank / "public" / "artifacts" / "probes.json", probes)
    ns: dict = {}
    exec(compile(ref, "render", "exec"), ns)
    fn = ns["render"]
    determined = {str(i): fn(p) for i, p in enumerate(probes)}
    wj(bank / "public" / "task.json", iso_task_json(
        tid, "render.md", "render.py", "probes.json", "render",
        "template rendering", "render(p)"))
    wj(bank / "private" / "label.json", iso_label(
        tid, "text-processing", "render", "artifacts/render.py",
        "artifacts/probes.json", determined, "REPRODUCES",
        [["fully determin|no such|none|complete|every probe|all probes|"
          "no behavior"]],
        ISO_CDS))
    w(bank / "private" / "verify.py", stub("verify_isolation", True))


def gen_iso_pricing(tid: str, bank: Path) -> None:
    doc = """# Line pricing rules

price(p) computes the final price string for p = {"qty": int,
"unit_price": str, "discount_pct": int, "tax_pct": int}.

1. subtotal = qty x unit_price, rounded to the cent, half away from zero.
2. discounted = subtotal reduced by discount_pct percent, rounded to the
   cent, half away from zero.
3. final = discounted increased by tax_pct percent, rounded to the cent,
   half away from zero.
4. The result is the final amount as a string with exactly two decimals.
"""
    ref = '''from decimal import Decimal, ROUND_HALF_EVEN


def _r(x):
    return x.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)


def price(p):
    sub = _r(Decimal(p["unit_price"]) * p["qty"])
    disc = _r(sub * (Decimal(100 - p["discount_pct"]) / 100))
    fin = _r(disc * (Decimal(100 + p["tax_pct"]) / 100))
    return f"{fin:.2f}"
'''
    probes = [
        {"qty": 3, "unit_price": "19.99", "discount_pct": 0, "tax_pct": 0},
        {"qty": 1, "unit_price": "0.25", "discount_pct": 50, "tax_pct": 0},
        {"qty": 2, "unit_price": "10.00", "discount_pct": 10, "tax_pct": 8},
        {"qty": 1, "unit_price": "1.25", "discount_pct": 50, "tax_pct": 0},
        {"qty": 5, "unit_price": "2.49", "discount_pct": 25, "tax_pct": 20},
        {"qty": 1, "unit_price": "0.05", "discount_pct": 50, "tax_pct": 0},
        {"qty": 4, "unit_price": "7.77", "discount_pct": 15, "tax_pct": 7},
        {"qty": 1, "unit_price": "2.35", "discount_pct": 50, "tax_pct": 0},
        {"qty": 6, "unit_price": "3.33", "discount_pct": 0, "tax_pct": 5},
        {"qty": 1, "unit_price": "0.15", "discount_pct": 50, "tax_pct": 0},
    ]
    w(bank / "public" / "artifacts" / "pricing.md", doc)
    w(bank / "public" / "artifacts" / "price.py", ref)
    wj(bank / "public" / "artifacts" / "probes.json", probes)
    ns: dict = {}
    exec(compile(ref, "price", "exec"), ns)
    fn = ns["price"]

    def half_up(p):
        def r(x):
            return x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        sub = r(Decimal(p["unit_price"]) * p["qty"])
        disc = r(sub * (Decimal(100 - p["discount_pct"]) / 100))
        fin = r(disc * (Decimal(100 + p["tax_pct"]) / 100))
        return f"{fin:.2f}"

    determined = {}
    for i, p in enumerate(probes):
        if half_up(p) == fn(p):
            determined[str(i)] = fn(p)
    wj(bank / "public" / "task.json", iso_task_json(
        tid, "pricing.md", "price.py", "probes.json", "price",
        "line pricing", "price(p)"))
    wj(bank / "private" / "label.json", iso_label(
        tid, "business-rules", "price", "artifacts/price.py",
        "artifacts/probes.json", determined, "DIVERGES",
        [["round|half|even|banker|away from zero", "cent|0\\.01|tie"]],
        ISO_CDS))
    w(bank / "private" / "verify.py", stub("verify_isolation", True))


# ============================================================ COUNTEREXAMPLE
CE_CDS = [
    {"id": "CD1", "description": "whether an input violating the claim "
     "exists in the bounded domain",
     "core_patterns": ["violat|breaks|fails|holds|witness",
                       "input|claim|domain|property"]},
    {"id": "CD2", "description": "the requirement that the search be "
     "carried out by a party other than the author of the provisional "
     "answer",
     "core_patterns": ["party other|not the author|second|separate|"
                       "unbiased|distinct", "search|check|derivation|"
                       "answer"]},
]


def ce_task(tid: str, claim: str, code_files: list[str], domain_desc: str,
            witness_shape: str) -> dict:
    return {
        "task_id": tid,
        "task": f"Audit the claim below against the provided materials. "
                f"Claim: {claim} Decide HOLDS or VIOLATED over the stated "
                "domain; on VIOLATED, provide one concrete violating input.",
        "deliverable": {"file": "result.json", "shape": {
            "verdict": "HOLDS | VIOLATED",
            "violating_input": witness_shape + " or null",
            "input_classes_examined": "[descriptions]"}},
        "evidence_requirements": [
            "E-A: an analysis identifying the input classes on which the "
            "claim's truth could turn",
            "E-B: a systematic search for a violating input carried out by "
            "a party other than the author of the provisional answer, or "
            "such a party's argument that no violating input exists in the "
            "domain",
            "E-C: the verdict, with a concrete violating input on VIOLATED "
            "that mechanically violates the claim",
        ],
        "available_artifacts": [f"package/artifacts/{f}"
                                for f in code_files],
        "domain": domain_desc,
    }


def gen_ce_merge(tid: str, bank: Path) -> None:
    code = '''def merge(intervals):
    """Merge integer intervals [start, end] into a canonical form."""
    if not intervals:
        return []
    ivs = sorted([list(i) for i in intervals])
    out = [ivs[0][:]]
    for s, e in ivs[1:]:
        if s < out[-1][1]:
            out[-1][1] = max(out[-1][1], e)
        else:
            out.append([s, e])
    return out
'''
    w(bank / "public" / "artifacts" / "merge.py", code)
    wj(bank / "public" / "task.json", ce_task(
        tid,
        "for every list of at most 6 intervals [start, end] with integer "
        "endpoints in [-10, 10] and start <= end, the output of "
        "merge(intervals) contains no two intervals i before j with "
        "i's end >= j's start (after sorting the output).",
        ["merge.py"],
        "lists of <= 6 integer intervals, endpoints in [-10, 10], "
        "start <= end",
        "[[s, e], ...]"))
    wj(bank / "private" / "label.json", base_label(
        tid, "COUNTEREXAMPLE", "algorithms",
        critical_distinctions=CE_CDS,
        checker="interval_merge", verdict="VIOLATED",
        witness_field="violating_input",
        analysis_patterns=[["touch|adjacent|equal|boundary|shared endpoint|"
                            "s < |strict"]],
        reference_witness=[[1, 2], [2, 3]],
        forbidden_shortcuts=["asserting HOLDS from reading the code once"],
    ))
    w(bank / "private" / "verify.py", stub("verify_counterexample", True))


def gen_ce_discount(tid: str, bank: Path) -> None:
    rules = """# Cart discount rules

The final price factor of a cart starts at 1.0 and every applicable rule
multiplies it:

- BULK: quantity of 5 or more -> factor x 0.90
- LOYALTY: loyalty_member true -> factor x 0.85
- SEASONAL: category is 'outdoor' -> factor x 0.80
- COUPON: coupon_code_applied true -> factor x 0.95

The total discount of a cart is 1.0 minus its final factor. A cart is
{"quantity": int, "loyalty_member": bool, "category": str,
"coupon_code_applied": bool}.
"""
    w(bank / "public" / "artifacts" / "rules.md", rules)
    wj(bank / "public" / "task.json", ce_task(
        tid,
        "no cart's total discount under rules.md exceeds 40 percent.",
        ["rules.md"],
        "all carts expressible in the cart shape",
        '{"quantity": int, "loyalty_member": bool, "category": str, '
        '"coupon_code_applied": bool}'))
    wj(bank / "private" / "label.json", base_label(
        tid, "COUNTEREXAMPLE", "business-rules",
        critical_distinctions=CE_CDS,
        checker="discount", verdict="VIOLATED",
        witness_field="violating_input",
        analysis_patterns=[["stack|combin|multipl|all four|every rule|"
                            "compound"]],
        reference_witness={"quantity": 5, "loyalty_member": True,
                           "category": "outdoor",
                           "coupon_code_applied": True},
        forbidden_shortcuts=["checking rules pairwise only"],
    ))
    w(bank / "private" / "verify.py", stub("verify_counterexample", True))


def gen_ce_dateadd(tid: str, bank: Path) -> None:
    code = '''DAYS = [31, 28, 31, 30, 31, 30, 31, 30, 30, 31, 30, 31]


def _leap(y):
    return y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)


def _dim(y, m):
    if m == 2 and _leap(y):
        return 29
    return DAYS[m - 1]


def add_days(iso, n):
    """Add n days to an ISO date string, returning an ISO date string."""
    y, m, d = (int(x) for x in iso.split("-"))
    for _ in range(n):
        d += 1
        if d > _dim(y, m):
            d = 1
            m += 1
            if m > 12:
                m = 1
                y += 1
    return f"{y:04d}-{m:02d}-{d:02d}"
'''
    w(bank / "public" / "artifacts" / "dateadd.py", code)
    wj(bank / "public" / "task.json", ce_task(
        tid,
        "for every ISO date d in the years 2023-2025 and every n with "
        "0 <= n <= 60, add_days(d, n) equals the true Gregorian calendar "
        "date n days after d.",
        ["dateadd.py"],
        "ISO dates in 2023-2025, n in [0, 60]",
        '["YYYY-MM-DD", n]'))
    wj(bank / "private" / "label.json", base_label(
        tid, "COUNTEREXAMPLE", "date-time",
        critical_distinctions=CE_CDS,
        checker="dateadd", verdict="VIOLATED",
        witness_field="violating_input",
        analysis_patterns=[["month length|days in|august|31|table|DAYS"]],
        reference_witness=["2023-08-30", 1],
        forbidden_shortcuts=["spot-checking a few friendly dates"],
    ))
    w(bank / "private" / "verify.py", stub("verify_counterexample", True))


def gen_ce_tokenizer(tid: str, bank: Path) -> None:
    code = r'''def tokenize(s):
    """Split s into tokens: space-separated; a double-quoted region is one
    token and backslash escapes the next character inside quotes."""
    tokens, cur, i, in_q, started = [], "", 0, False, False
    while i < len(s):
        c = s[i]
        if in_q:
            if c == "\\" and i + 1 < len(s):
                cur += s[i + 1]
                i += 2
                continue
            if c == '"':
                in_q = False
                i += 1
                continue
            cur += c
            i += 1
        else:
            if c == '"':
                in_q = True
                started = True
                i += 1
            elif c == " ":
                if cur or started:
                    tokens.append(cur)
                cur, started = "", False
                i += 1
            else:
                cur += c
                started = True
                i += 1
    if cur or started:
        tokens.append(cur)
    return tokens


def detokenize(tokens):
    """Join tokens into a string that tokenize maps back to the tokens."""
    parts = []
    for t in tokens:
        if '"' in t or " " in t or t == "":
            parts.append('"' + t.replace('"', '\\"') + '"')
        else:
            parts.append(t)
    return " ".join(parts)
'''
    w(bank / "public" / "artifacts" / "tok.py", code)
    ns: dict = {}
    exec(compile(code, "tok", "exec"), ns)
    tok, detok = ns["tokenize"], ns["detokenize"]
    alphabet = 'ab"\\'
    witness = None
    def all_tokens(maxlen):
        for L in range(1, maxlen + 1):
            def rec(prefix):
                if len(prefix) == L:
                    yield prefix
                    return
                for c in alphabet:
                    yield from rec(prefix + c)
            yield from rec("")
    singles = list(all_tokens(3))
    import itertools
    for k in (1, 2):
        for ts in itertools.product(singles, repeat=k):
            ts = list(ts)
            try:
                if tok(detok(ts)) != ts:
                    witness = ts
                    break
            except Exception:
                witness = ts
                break
        if witness:
            break
    assert witness is not None, "tokenizer bug did not manifest"
    wj(bank / "public" / "task.json", ce_task(
        tid,
        "for every list of 1 to 3 tokens, each token a string of 1 to 3 "
        "characters over the alphabet {a, b, double-quote, backslash}, "
        "tokenize(detokenize(tokens)) equals the original token list.",
        ["tok.py"],
        "token lists as stated",
        '["tok1", "tok2", ...]'))
    wj(bank / "private" / "label.json", base_label(
        tid, "COUNTEREXAMPLE", "parsing",
        critical_distinctions=CE_CDS,
        checker="tokenizer", verdict="VIOLATED",
        witness_field="violating_input",
        analysis_patterns=[["backslash|escap", "quote|round.?trip|token"]],
        reference_witness=witness,
        forbidden_shortcuts=["testing only alphabetic tokens"],
    ))
    w(bank / "private" / "verify.py", stub("verify_counterexample", True))


# ================================================== ALTERNATIVE_DECOMPOSITION
AD_CDS = [
    {"id": "CD1", "description": "complete enumeration of the space "
     "(nothing missed)",
     "core_patterns": ["all|every|complete|exhaust|enumerat|miss",
                       "cover|partition|path|parse|tree|solution"]},
    {"id": "CD2", "description": "the second enumeration must be produced "
     "without access to the first",
     "core_patterns": ["without access|not seen|second|another|converg|"
                       "anchor", "enumerat|list|attempt|pass"]},
]


def ad_task(tid: str, what: str, artifacts: list[str], item_shape: str,
            extra: str = "") -> dict:
    return {
        "task_id": tid,
        "task": f"Enumerate ALL {what}. {extra} Completeness is the "
                "deliverable: a missed item is a wrong answer.",
        "deliverable": {"file": "result.json", "shape": {
            "items": f"[{item_shape}] (all of them, sorted)",
            "method": "how the enumeration was produced",
            "complete": "boolean or PENDING-INTEGRATION"}},
        "evidence_requirements": [
            "E-A: one complete candidate enumeration with its method "
            "stated",
            "E-B: a second complete enumeration of the same space produced "
            "without access to the first enumeration or any of its "
            "intermediate work",
            "E-C: the final merged answer (union of both), with any item "
            "found by only one enumeration flagged; the completeness claim "
            "is admissible only when supported by both enumerations",
        ],
        "available_artifacts": [f"package/artifacts/{a}" for a in artifacts],
    }


def gen_ad_covers(tid: str, bank: Path) -> None:
    edges = [["v1", "v2"], ["v1", "v3"], ["v2", "v3"], ["v2", "v4"],
             ["v3", "v5"], ["v4", "v5"], ["v4", "v6"], ["v5", "v7"],
             ["v6", "v7"]]
    verts = sorted({v for e in edges for v in e})
    wj(bank / "public" / "artifacts" / "graph.json",
       {"vertices": verts, "edges": edges})
    best_k, covers = None, []
    for k in range(1, len(verts) + 1):
        found = []
        for combo in combinations(verts, k):
            cs = set(combo)
            if all(a in cs or b in cs for a, b in edges):
                found.append(sorted(combo))
        if found:
            best_k, covers = k, found
            break
    gt_items = [json.dumps(sorted(c)) for c in covers]
    wj(bank / "public" / "task.json", ad_task(
        tid, "minimum-size vertex covers of the graph in "
        "artifacts/graph.json (vertex sets of the smallest size such that "
        "every edge has at least one endpoint in the set)",
        ["graph.json"], '["v1", ...] sorted',
        f"Report each cover as its sorted vertex list."))
    wj(bank / "private" / "label.json", base_label(
        tid, "ALTERNATIVE_DECOMPOSITION", "graph-combinatorics",
        critical_distinctions=AD_CDS,
        ground_truth_items=sorted(gt_items),
        items_field="items", canonicalizer="sorted_list",
        forbidden_shortcuts=["stopping after one greedy cover"],
        minimum_size=best_k,
    ))
    w(bank / "private" / "verify.py", stub("verify_altdecomp", True))


def gen_ad_layers(tid: str, bank: Path) -> None:
    mods = ["auth", "core", "db", "net", "ui", "util"]
    deps = [["auth", "core"], ["auth", "db"], ["core", "util"],
            ["db", "util"], ["ui", "auth"], ["ui", "net"],
            ["net", "core"]]
    wj(bank / "public" / "artifacts" / "modules.json",
       {"modules": mods, "dependencies": [
           {"from": a, "to": b} for a, b in deps]})
    valid = []
    n = len(mods)
    for mask in range(1, 2 ** n - 1):
        layer1 = {mods[i] for i in range(n) if mask >> i & 1}
        layer2 = set(mods) - layer1
        if all(not (a in layer1 and b in layer2) for a, b in deps):
            valid.append([sorted(layer1), sorted(layer2)])
    gt_items = [json.dumps(v) for v in valid]
    wj(bank / "public" / "task.json", ad_task(
        tid, "valid foundation/application splits of the modules in "
        "artifacts/modules.json: an assignment of every module to exactly "
        "one of layer1 (foundation) or layer2 (application), both "
        "non-empty, such that no module in layer1 depends on a module in "
        "layer2 (a dependency entry {from: a, to: b} means a depends "
        "on b)", ["modules.json"],
        '{"layer1": [...], "layer2": [...]} with sorted module lists'))
    wj(bank / "private" / "label.json", base_label(
        tid, "ALTERNATIVE_DECOMPOSITION", "software-architecture",
        critical_distinctions=AD_CDS,
        ground_truth_items=sorted(gt_items),
        items_field="items", canonicalizer="partition",
        forbidden_shortcuts=["assuming the obvious layering is unique"],
    ))
    w(bank / "private" / "verify.py", stub("verify_altdecomp", True))


def gen_ad_parses(tid: str, bank: Path) -> None:
    grammar = """# Expression grammar

E -> E op E | number
op -> '-' | '^'

No precedence and no associativity are defined: every way of fully
parenthesizing the expression is a distinct parse. '-' is subtraction;
'^' is exponentiation (right operand as the exponent), both on integers.
"""
    expr = "8 - 2 ^ 2 - 1"
    w(bank / "public" / "artifacts" / "grammar.md", grammar)
    w(bank / "public" / "artifacts" / "expression.txt", expr + "\n")
    nums = [8, 2, 2, 1]
    ops = ["-", "^", "-"]

    def parenth(i, j):
        if i == j:
            return [str(nums[i])]
        out = []
        for k in range(i, j):
            for left in parenth(i, k):
                for right in parenth(k + 1, j):
                    out.append(f"({left}{ops[k]}{right})")
        return out
    forms = sorted(parenth(0, 3))
    wj(bank / "public" / "task.json", ad_task(
        tid, "distinct parses of the expression in "
        "artifacts/expression.txt under the grammar in "
        "artifacts/grammar.md, each written as a fully parenthesized form "
        "with no spaces, e.g. ((8-2)^(2-1))", ["grammar.md",
                                               "expression.txt"],
        "fully parenthesized string"))
    wj(bank / "private" / "label.json", base_label(
        tid, "ALTERNATIVE_DECOMPOSITION", "language-parsing",
        critical_distinctions=AD_CDS,
        ground_truth_items=forms,
        items_field="items", canonicalizer="string",
        forbidden_shortcuts=["applying conventional precedence"],
    ))
    w(bank / "private" / "verify.py", stub("verify_altdecomp", True))


def gen_ad_routes(tid: str, bank: Path) -> None:
    edges = {
        ("S", "A"): 2, ("S", "B"): 3, ("A", "C"): 3, ("A", "D"): 4,
        ("B", "C"): 2, ("B", "D"): 3, ("C", "T"): 3, ("D", "T"): 2,
        ("A", "B"): 1, ("C", "D"): 1,
    }
    wj(bank / "public" / "artifacts" / "network.json",
       {"nodes": ["S", "A", "B", "C", "D", "T"],
        "links": [{"from": a, "to": b, "cost": c}
                  for (a, b), c in sorted(edges.items())]})
    adj: dict[str, list[tuple[str, int]]] = {}
    for (a, b), c in edges.items():
        adj.setdefault(a, []).append((b, c))
    best: dict[str, int] = {}
    paths: list[tuple[int, list[str]]] = []

    def dfs(node, cost, path):
        if node == "T":
            paths.append((cost, path[:]))
            return
        for nxt, c in adj.get(node, []):
            if nxt not in path:
                path.append(nxt)
                dfs(nxt, cost + c, path)
                path.pop()
    dfs("S", 0, ["S"])
    mincost = min(c for c, _ in paths)
    gt_paths = sorted("-".join(p) for c, p in paths if c == mincost)
    wj(bank / "public" / "task.json", ad_task(
        tid, "minimum-total-cost routes from node S to node T in "
        "artifacts/network.json (links are one-way; a route never repeats "
        "a node), each written as node names joined by '-', e.g. S-A-C-T",
        ["network.json"], "route string"))
    wj(bank / "private" / "label.json", base_label(
        tid, "ALTERNATIVE_DECOMPOSITION", "route-planning",
        critical_distinctions=AD_CDS,
        ground_truth_items=gt_paths,
        items_field="items", canonicalizer="string",
        forbidden_shortcuts=["returning one shortest route"],
        minimum_cost=mincost,
    ))
    w(bank / "private" / "verify.py", stub("verify_altdecomp", True))


# ================================================ SPECIALIZED_VERIFICATION
SV_CDS = [
    {"id": "CD1", "description": "exact correctness of every item "
     "(boundary/edge conventions decide)",
     "core_patterns": ["exact|correct|precise|edge|boundary|subtle",
                       "answer|item|value|date|digit|format"]},
    {"id": "CD2", "description": "the method-disjoint re-derivation with "
     "per-item agreement",
     "core_patterns": ["disjoint|different method|re-deriv|second|"
                       "without consulting", "method|deriv|agree|check"]},
]


def sv_task(tid: str, what: str, artifacts: list[str],
            answer_shape: str) -> dict:
    return {
        "task_id": tid,
        "task": f"{what} Every answer must be exactly right; the items are "
                "chosen so that plausible methods disagree on them.",
        "deliverable": {"file": "result.json", "shape": {
            "answers": answer_shape,
            "method": "how the answers were derived"}},
        "evidence_requirements": [
            "E-A: the computed answer for every item, with the derivation "
            "method stated",
            "E-B: a re-derivation of every answer by a method disjoint "
            "from the first derivation, carried out without consulting the "
            "first derivation's intermediate work, with per-item agreement "
            "recorded",
            "E-C: every answer exactly correct",
        ],
        "available_artifacts": [f"package/artifacts/{a}" for a in artifacts],
    }


def gen_sv_isoweek(tid: str, bank: Path) -> None:
    import datetime as dt
    dates = ["2021-01-01", "2016-01-03", "2015-12-28", "2020-12-31",
             "2019-12-30", "2022-01-02", "2024-12-30", "2025-01-05",
             "2017-01-01", "2018-12-31"]
    wj(bank / "public" / "artifacts" / "dates.json", dates)
    gt = {}
    for s in dates:
        y, wk, d = dt.date.fromisoformat(s).isocalendar()
        gt[s] = f"{y:04d}-W{wk:02d}-{d}"
    wj(bank / "public" / "task.json", sv_task(
        tid, "For every date in artifacts/dates.json, give its ISO-8601 "
        "week-date form YYYY-Www-D (ISO week-numbering year, week 01-53, "
        "weekday 1=Monday..7=Sunday).",
        ["dates.json"], '{"YYYY-MM-DD": "YYYY-Www-D"}'))
    wj(bank / "private" / "label.json", base_label(
        tid, "SPECIALIZED_VERIFICATION", "calendrical",
        critical_distinctions=SV_CDS,
        ground_truth_answers=gt, answers_field="answers",
        forbidden_shortcuts=["using the calendar year as the week year"],
    ))
    w(bank / "private" / "verify.py", stub("verify_specialized", True))


def gen_sv_checksum(tid: str, bank: Path) -> None:
    spec = """# W371 check digits

An identifier is a string of digits followed by one check digit.

- Weights cycle 3, 7, 1, 3, 7, 1, ... assigned to the payload digits from
  RIGHT to LEFT (the rightmost payload digit has weight 3).
- The weighted sum S is the sum of digit x weight over the payload.
- The check digit is (10 - (S mod 10)) mod 10.
- An identifier is VALID when its last digit equals the check digit of
  the payload before it.
"""
    w(bank / "public" / "artifacts" / "spec.md", spec)

    def check_digit(payload: str) -> int:
        weights = [3, 7, 1]
        s = 0
        for i, ch in enumerate(reversed(payload)):
            s += int(ch) * weights[i % 3]
        return (10 - s % 10) % 10

    ids = []
    for _ in range(8):
        payload = "".join(str(RNG.randint(0, 9)) for _ in range(7))
        cd = check_digit(payload)
        if RNG.random() < 0.5:
            ids.append(payload + str(cd))
        else:
            ids.append(payload + str((cd + RNG.randint(1, 9)) % 10))
    partials = ["".join(str(RNG.randint(0, 9)) for _ in range(6))
                for _ in range(4)]
    wj(bank / "public" / "artifacts" / "items.json",
       {"validate": ids, "compute": partials})
    gt = {}
    for i in ids:
        gt[f"validate:{i}"] = ("VALID" if check_digit(i[:-1]) == int(i[-1])
                               else "INVALID")
    for p in partials:
        gt[f"compute:{p}"] = str(check_digit(p))
    wj(bank / "public" / "task.json", sv_task(
        tid, "Apply artifacts/spec.md to artifacts/items.json: for each "
        "identifier under 'validate', answer VALID or INVALID; for each "
        "payload under 'compute', answer its check digit. Use "
        "'validate:<id>' and 'compute:<payload>' as the keys of the "
        "answers object.",
        ["spec.md", "items.json"],
        '{"validate:<id>": "VALID|INVALID", "compute:<payload>": "digit"}'))
    wj(bank / "private" / "label.json", base_label(
        tid, "SPECIALIZED_VERIFICATION", "data-integrity",
        critical_distinctions=SV_CDS,
        ground_truth_answers=gt, answers_field="answers",
        forbidden_shortcuts=["assigning weights left to right"],
    ))
    w(bank / "private" / "verify.py", stub("verify_specialized", True))


def gen_sv_format(tid: str, bank: Path) -> None:
    spec = """# Amount formatting

format(x) renders a decimal amount string x as follows:

- Round to exactly 2 decimal places, ties to the even neighbor: an
  amount exactly halfway between two candidates takes the one whose last
  digit is even (2.675 lies between 2.67 and 2.68; 8 is even, so 2.68).
- Group the integer part with commas every three digits.
- Negative amounts are wrapped in parentheses and lose their sign:
  -1234.5 -> (1,234.50).
- Always show exactly two decimals.
"""
    w(bank / "public" / "artifacts" / "format-spec.md", spec)
    inputs = ["2.675", "-1234.5", "0.005", "1000", "-0.125", "999999.995",
              "0.045", "12345.675", "-2.5", "0", "7.375", "-999.985"]
    wj(bank / "public" / "artifacts" / "amounts.json", inputs)
    gt = {}
    for s in inputs:
        x = Decimal(s)
        q = x.copy_abs().quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
        body = f"{q:,.2f}"
        gt[s] = f"({body})" if x < 0 else body
    wj(bank / "public" / "task.json", sv_task(
        tid, "Format every amount string in artifacts/amounts.json "
        "according to artifacts/format-spec.md, treating each input as an "
        "exact decimal.",
        ["format-spec.md", "amounts.json"], '{"<input>": "<formatted>"}'))
    wj(bank / "private" / "label.json", base_label(
        tid, "SPECIALIZED_VERIFICATION", "numeric-formatting",
        critical_distinctions=SV_CDS,
        ground_truth_answers=gt, answers_field="answers",
        forbidden_shortcuts=["binary floating point rounding"],
    ))
    w(bank / "private" / "verify.py", stub("verify_specialized", True))


def gen_sv_stack(tid: str, bank: Path) -> None:
    spec = """# Stack program semantics

A program is a list of instructions over an integer stack, initially
empty. Result: the top of the stack after the last instruction, or
"EMPTY" if the stack is empty, or "ERROR" if the program halted early.

- PUSH n: push the integer n.
- ADD: pop two values, push their sum. Fewer than two values: the
  program halts immediately with "ERROR".
- DUP: duplicate the top value. Empty stack: halt with "ERROR".
- SWAP: exchange the top two values. Fewer than two values: halt with
  "ERROR".
- POP: remove the top value. Empty stack: the stack stays empty and the
  program continues.
"""
    w(bank / "public" / "artifacts" / "spec.md", spec)

    def run_ref(prog):
        st = []
        for ins in prog:
            op = ins[0]
            if op == "PUSH":
                st.append(ins[1])
            elif op == "ADD":
                if len(st) < 2:
                    return "ERROR"
                st.append(st.pop() + st.pop())
            elif op == "DUP":
                if not st:
                    return "ERROR"
                st.append(st[-1])
            elif op == "SWAP":
                if len(st) < 2:
                    return "ERROR"
                st[-1], st[-2] = st[-2], st[-1]
            elif op == "POP":
                if st:
                    st.pop()
        return st[-1] if st else "EMPTY"

    cand_a = '''def run(prog):
    st = []
    for ins in prog:
        op = ins[0]
        if op == "PUSH":
            st.append(ins[1])
        elif op == "ADD":
            if len(st) < 2:
                return "ERROR"
            st.append(st.pop() + st.pop())
        elif op == "DUP":
            if not st:
                return "ERROR"
            st.append(st[-1])
        elif op == "SWAP":
            if len(st) < 2:
                return "ERROR"
            st[-1], st[-2] = st[-2], st[-1]
        elif op == "POP":
            if not st:
                return "ERROR"
            st.pop()
    return st[-1] if st else "EMPTY"
'''
    cand_b = '''def run(prog):
    st = []
    for ins in prog:
        op = ins[0]
        if op == "PUSH":
            st.append(ins[1])
        elif op == "ADD":
            if len(st) < 2:
                return "ERROR"
            st.append(st.pop() + st.pop())
        elif op == "DUP":
            if not st:
                return "ERROR"
            st.append(st[-1])
        elif op == "SWAP":
            if len(st) < 2:
                return "ERROR"
            st[-1], st[-2] = st[-2], st[-1]
        elif op == "POP":
            if st:
                st.pop()
    return st[-1] if st else "EMPTY"
'''
    cand_c = '''def run(prog):
    st = []
    for ins in prog:
        op = ins[0]
        if op == "PUSH":
            st.append(ins[1])
        elif op == "ADD":
            if len(st) < 2:
                return "ERROR"
            st.append(st.pop() + st.pop())
        elif op == "DUP":
            if not st:
                return "ERROR"
            st.append(st[-1])
        elif op == "SWAP":
            if len(st) >= 2:
                st[-1], st[-2] = st[-2], st[-1]
        elif op == "POP":
            if st:
                st.pop()
    return st[-1] if st else "EMPTY"
'''
    w(bank / "public" / "artifacts" / "candidate_a.py", cand_a)
    w(bank / "public" / "artifacts" / "candidate_b.py", cand_b)
    w(bank / "public" / "artifacts" / "candidate_c.py", cand_c)
    programs = [
        [["PUSH", 3], ["PUSH", 4], ["ADD"]],
        [["PUSH", 1], ["POP"], ["POP"], ["PUSH", 9]],
        [["POP"], ["PUSH", 2], ["DUP"], ["ADD"]],
        [["PUSH", 5], ["SWAP"], ["PUSH", 1]],
        [["PUSH", 7], ["PUSH", 8], ["SWAP"], ["POP"]],
        [["DUP"]],
    ]
    wj(bank / "public" / "artifacts" / "programs.json", programs)
    cands = {"A": cand_a, "B": cand_b, "C": cand_c}
    gt = {}
    for name, code in cands.items():
        ns: dict = {}
        exec(compile(code, name, "exec"), ns)
        first = None
        for i, prog in enumerate(programs):
            if ns["run"](prog) != run_ref(prog):
                first = i
                break
        gt[name] = "conforms" if first is None else f"diverges:{first}"
    assert gt == {"A": gt["A"], "B": "conforms", "C": gt["C"]}
    assert gt["A"].startswith("diverges") and gt["C"].startswith("diverges")
    wj(bank / "public" / "task.json", sv_task(
        tid, "For each of candidate_a.py, candidate_b.py, candidate_c.py, "
        "decide whether run(program) matches artifacts/spec.md on every "
        "program in artifacts/programs.json (in order, 0-indexed). Answer "
        "'conforms', or 'diverges:<index of the first program where the "
        "candidate's result differs from the spec's result>'. Keys are "
        "A, B, C.",
        ["spec.md", "candidate_a.py", "candidate_b.py", "candidate_c.py",
         "programs.json"],
        '{"A": "conforms|diverges:<i>", "B": "...", "C": "..."}'))
    wj(bank / "private" / "label.json", base_label(
        tid, "SPECIALIZED_VERIFICATION", "implementation-selection",
        critical_distinctions=SV_CDS,
        ground_truth_answers=gt, answers_field="answers",
        forbidden_shortcuts=["diffing the code instead of simulating the "
                            "programs"],
    ))
    w(bank / "private" / "verify.py", stub("verify_specialized", True))


# ==================================================================== PILOT
def gen_pilot_local(tid: str, bank: Path) -> None:
    rows = [{"sku": f"p{i}", "units": RNG.randint(1, 20),
             "price": f"{RNG.randint(1, 30)}.50"} for i in range(1, 7)]
    buf = io.StringIO()
    cw = csv.DictWriter(buf, fieldnames=list(rows[0]))
    cw.writeheader()
    cw.writerows(rows)
    w(bank / "public" / "artifacts" / "stock.csv", buf.getvalue())
    total_units = sum(r["units"] for r in rows)
    value = sum(Decimal(r["price"]) * r["units"] for r in rows)
    top = sorted(rows, key=lambda r: (-r["units"], r["sku"]))[0]["sku"]
    gt = {"total_units": total_units,
          "total_value": float(value.quantize(Decimal("0.01"))),
          "top_sku_by_units": top}
    wj(bank / "public" / "task.json", {
        "task_id": tid,
        "task": "Compute stock aggregates from artifacts/stock.csv: total "
                "units, total value (units x price, 2 decimals), and the "
                "sku with the most units (ties to smallest sku).",
        "deliverable": {"file": "result.json", "shape": {
            "total_units": "integer", "total_value": "number",
            "top_sku_by_units": "string"}},
        "evidence_requirements": [
            "E-A: total units", "E-B: total value",
            "E-C: top sku under the tie-break"],
        "available_artifacts": ["package/artifacts/stock.csv"],
    })
    wj(bank / "private" / "label.json", base_label(
        tid, "LOCAL", "data-analysis",
        critical_distinctions=[
            {"id": "CD1", "description": "exact aggregation",
             "core_patterns": ["total|units|value|aggregat",
                               "stock|csv|row"]},
            {"id": "CD2", "description": "tie-break convention",
             "core_patterns": ["tie|top|most", "sku|smallest"]},
        ],
        ground_truth=gt,
        requirement_fields={"E-A": ["total_units"], "E-B": ["total_value"],
                            "E-C": ["top_sku_by_units"]},
        forbidden_shortcuts=[],
    ))
    w(bank / "private" / "verify.py", stub("verify_local", False))


def gen_pilot_iso(tid: str, bank: Path) -> None:
    doc = """# List joining format

join_items(items) renders a list of strings as one line.

- Items are joined with ', ' (comma space).
- Items appear in the order given in the list.
- An empty list renders as the empty string.
"""
    ref = '''def join_items(items):
    return ", ".join(reversed(items))
'''
    probes = [["a"], ["x", "y"], [], ["one", "two", "three"], ["z"],
              ["b", "a"]]
    w(bank / "public" / "artifacts" / "joinspec.md", doc)
    w(bank / "public" / "artifacts" / "joiner.py", ref)
    wj(bank / "public" / "artifacts" / "probes.json", probes)
    ns: dict = {}
    exec(compile(ref, "joiner", "exec"), ns)
    fn = ns["join_items"]
    determined = {str(i): fn(p) for i, p in enumerate(probes)
                  if len(p) <= 1}
    wj(bank / "public" / "task.json", iso_task_json(
        tid, "joinspec.md", "joiner.py", "probes.json", "join_items",
        "list joining", "join_items(items)"))
    wj(bank / "private" / "label.json", iso_label(
        tid, "codec", "join_items", "artifacts/joiner.py",
        "artifacts/probes.json", determined, "DIVERGES",
        [["order|revers"]],
        ISO_CDS))
    w(bank / "private" / "verify.py", stub("verify_isolation", True))


GENERATORS = {
    "LOCAL": [gen_local_orders, gen_local_machine, gen_local_log,
              gen_local_config],
    "ISOLATION": [gen_iso_wire, gen_iso_dates, gen_iso_template,
                  gen_iso_pricing],
    "COUNTEREXAMPLE": [gen_ce_merge, gen_ce_discount, gen_ce_dateadd,
                       gen_ce_tokenizer],
    "ALTERNATIVE_DECOMPOSITION": [gen_ad_covers, gen_ad_layers,
                                  gen_ad_parses, gen_ad_routes],
    "SPECIALIZED_VERIFICATION": [gen_sv_isoweek, gen_sv_checksum,
                                 gen_sv_format, gen_sv_stack],
}


def main() -> None:
    counters = {cls: 0 for cls in GENERATORS}
    for tid in TRIAL_IDS:
        cls = ASSIGNMENT[tid]
        gen = GENERATORS[cls][counters[cls]]
        counters[cls] += 1
        bank = E6 / "task-bank" / tid
        gen(tid, bank)
        scan = blinding.scan_package(bank / "public")
        if scan["verdict"] != "PASS":
            raise SystemExit(f"{tid}: BLINDING_FAIL {scan['hits']}")
        print(f"{tid}: {cls} ({gen.__name__}) blinding PASS")
    for tid, gen in (("p-01", gen_pilot_local), ("p-02", gen_pilot_iso)):
        bank = E6 / "pilot" / "task-bank" / tid
        gen(tid, bank)
        scan = blinding.scan_package(bank / "public")
        if scan["verdict"] != "PASS":
            raise SystemExit(f"{tid}: BLINDING_FAIL {scan['hits']}")
        print(f"{tid}: pilot blinding PASS")
    wj(E6 / "trial-manifest.json", {
        "artifact": "Experiment 6 trial manifest",
        "primary_trials": TRIAL_IDS,
        "pilot_trials": ["p-01", "p-02"],
        "class_assignment_seed": "creator-0-experiment-6-bank-v1",
        "classes": {tid: ASSIGNMENT[tid] for tid in TRIAL_IDS},
        "note": "classes recorded here are private-side bookkeeping; the "
                "public packages carry no class information",
    })
    print("trial-manifest.json written")


if __name__ == "__main__":
    main()
