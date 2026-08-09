def tokenize(s):
    """Split s into tokens: space-separated; a double-quoted region is one
    token and backslash escapes the next character inside quotes."""
    tokens, cur, i, in_q, started = [], "", 0, False, False
    while i < len(s):
        c = s[i]
        if in_q:
            if c == "\\" and i + 1 < len(s):
                cur += s[i + 1]
                i += 2
                continue
            if c == '"':
                in_q = False
                i += 1
                continue
            cur += c
            i += 1
        else:
            if c == '"':
                in_q = True
                started = True
                i += 1
            elif c == " ":
                if cur or started:
                    tokens.append(cur)
                cur, started = "", False
                i += 1
            else:
                cur += c
                started = True
                i += 1
    if cur or started:
        tokens.append(cur)
    return tokens


def detokenize(tokens):
    """Join tokens into a string that tokenize maps back to the tokens."""
    parts = []
    for t in tokens:
        if '"' in t or " " in t or t == "":
            parts.append('"' + t.replace('"', '\\"') + '"')
        else:
            parts.append(t)
    return " ".join(parts)
