def encode(d):
    """Encode a mapping of string keys to string values as a single line.

    Each pair is written as key=value; pairs are joined with ';' in the
    order they appear in the mapping. Inside keys and values, every ';'
    is written as '\\;' and every '=' as '\\='. An empty mapping encodes
    as the empty string.
    """
    def esc(s):
        out = []
        for ch in s:
            if ch == ";":
                out.append("\\;")
            elif ch == "=":
                out.append("\\=")
            else:
                out.append(ch)
        return "".join(out)

    return ";".join(esc(k) + "=" + esc(v) for k, v in d.items())
