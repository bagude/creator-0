def build_index(text: str) -> str:
    index = {}
    for line_no, line in enumerate(text.splitlines(), start=1):
        for token in line.split():
            term = token.lower().strip(".,;:")
            if not term:
                continue
            lines = index.setdefault(term, [])
            if line_no not in lines:
                lines.append(line_no)
    rendered = [
        "{}: {}".format(term, ",".join(str(n) for n in index[term]))
        for term in sorted(index)
    ]
    return "\n".join(rendered) + "\n"
