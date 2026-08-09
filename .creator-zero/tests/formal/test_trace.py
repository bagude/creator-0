from __future__ import annotations
import json
import tempfile
import unittest
from pathlib import Path

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parent))
import _bootstrap  # noqa: F401,E402
from _bootstrap import CZROOT, FIXTURES  # noqa: F401,E402
from formal.trace import TraceParseError, parse_runtime_ledger


def write_ledger(lines) -> Path:
    f = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False)
    for l in lines:
        f.write((json.dumps(l) if not isinstance(l, str) else l) + "\n")
    f.close()
    return Path(f.name)


class TestParse(unittest.TestCase):
    def test_normalized_fixture_parses(self):
        t = parse_runtime_ledger(FIXTURES / "experiment3-normalized-ledger.jsonl")
        self.assertEqual(len(t.events), 9)
        self.assertEqual(t.unmapped_events, [])
        labels = [e.label for e in t.events]
        self.assertIn("promote", labels)
        self.assertIn("act_candidate", labels)

    def test_missing_required_keys_strict(self):
        p = write_ledger([{"label": "observe"}])  # no actor
        with self.assertRaises(TraceParseError):
            parse_runtime_ledger(p)

    def test_unmapped_label_strict(self):
        p = write_ledger([{"label": "telepathy", "actor": "x"}])
        with self.assertRaises(TraceParseError):
            parse_runtime_ledger(p)

    def test_non_strict_records_unmapped_never_silently_ignores(self):
        p = write_ledger([{"label": "observe", "actor": "x"},
                          {"label": "telepathy", "actor": "x"},
                          "not-json{{{"])
        t = parse_runtime_ledger(p, strict=False)
        self.assertEqual(len(t.events), 1)
        self.assertEqual(len(t.unmapped_events), 2)
        reasons = " ".join(u["reason"] for u in t.unmapped_events)
        self.assertIn("unmapped label", reasons)
        self.assertIn("invalid JSON", reasons)

    def test_missing_file(self):
        with self.assertRaises(TraceParseError):
            parse_runtime_ledger("/nonexistent/ledger.jsonl")

    def test_tau_excluded_from_observable(self):
        p = write_ledger([{"label": "tau", "actor": "x"},
                          {"label": "observe", "actor": "x"}])
        t = parse_runtime_ledger(p)
        self.assertEqual(len(t.events), 2)
        self.assertEqual([e.label for e in t.observable()], ["observe"])

    def test_metadata_and_ordering_preserved(self):
        p = write_ledger([
            {"label": "observe", "actor": "a", "timestamp": "2099-01-01",
             "metadata": {"completes_node": "n1"}},
            {"label": "verify", "actor": "b", "timestamp": "1970-01-01"}])
        t = parse_runtime_ledger(p)
        # causal order is trace position, not timestamp
        self.assertEqual([e.label for e in t.events], ["observe", "verify"])
        self.assertEqual(t.events[0].meta()["completes_node"], "n1")


if __name__ == "__main__":
    unittest.main()
