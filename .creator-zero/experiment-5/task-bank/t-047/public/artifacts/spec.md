# Specification — next_order

`next_order(jobs: list[dict]) -> list[str]`

`jobs` is a list of job records in submission order. Each record has:

- `id` — a unique string identifier;
- `priority` — an integer; larger means more urgent.

Return the list of job `id`s in processing order: a job with higher
`priority` is processed before every job with lower `priority`.
