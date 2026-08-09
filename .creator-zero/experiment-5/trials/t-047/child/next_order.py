def next_order(jobs: list[dict]) -> list[str]:
    """Return job ids in processing order: higher priority first.

    The spec does not determine the relative order of jobs with equal
    priority. Concrete choice made here: equal-priority jobs keep their
    submission order (stable sort).
    """
    return [job["id"] for job in sorted(jobs, key=lambda j: -j["priority"])]
