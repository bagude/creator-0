def merge(intervals):
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
