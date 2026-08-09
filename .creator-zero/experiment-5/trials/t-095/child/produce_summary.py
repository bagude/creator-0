"""Clean-room implementation of the transformation described in build-notes.md.

The notes state, verbatim:
  1. Keep only the rows whose `status` field is `active`.
  2. Group the remaining rows by `region`.
  3. Sum the `amount` field within each group.
  4. Write one line per region in the form `REGION: TOTAL`.

Where the notes are silent on byte-level details, the most literal, minimal
reading was taken (each such free choice is recorded in reproduction.json):
  - Line ordering: regions emitted in order of first appearance among the
    kept (active) rows.
  - Label case: region written exactly as it appears in the CSV (no case
    change; `REGION`/`TOTAL` in the notes are read as placeholders).
  - Number formatting: amounts summed exactly with decimal.Decimal and
    rendered with str(), preserving the input's decimal scale.
  - Separator: literal ": " (colon + one space), as shown in the form.
  - Line terminator: LF; no trailing newline (lines joined with "\n").
"""

import csv
import io
from decimal import Decimal


def produce_summary(csv_text: str) -> str:
    reader = csv.DictReader(io.StringIO(csv_text))
    order = []
    totals = {}
    for row in reader:
        if row["status"] != "active":
            continue
        region = row["region"]
        if region not in totals:
            order.append(region)
            totals[region] = Decimal("0")
        totals[region] += Decimal(row["amount"])
    return "\n".join(f"{region}: {totals[region]}" for region in order)
