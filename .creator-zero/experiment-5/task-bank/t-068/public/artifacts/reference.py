def build_index(text):
    order = []
    where = {}
    for lineno, line in enumerate(text.splitlines()):
        for raw in line.split():
            term = raw.lower().strip(".,;:")
            if not term:
                continue
            if term not in where:
                where[term] = []
                order.append(term)
            if lineno not in where[term]:
                where[term].append(lineno)
    return "".join(f"{t}: {','.join(str(n) for n in sorted(where[t]))}\n"
                   for t in order)
