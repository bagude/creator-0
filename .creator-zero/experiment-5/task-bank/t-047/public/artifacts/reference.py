def next_order(jobs):
    indexed = list(enumerate(jobs))
    indexed.sort(key=lambda p: (-p[1]["priority"], -p[0]))
    return [j["id"] for _, j in indexed]
