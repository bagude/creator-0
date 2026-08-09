# Build notes — summary.txt

`summary.txt` is produced from `records.csv` as follows:

1. Keep only the rows whose `status` field is `active`.
2. Group the remaining rows by `region`.
3. Sum the `amount` field within each group.
4. Write one line per region in the form `REGION: TOTAL`.
