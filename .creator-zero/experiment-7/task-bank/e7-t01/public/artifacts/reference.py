def encode(d):
    def esc(s):
        return (s.replace("\\", "\\\\")
                 .replace(";", "\\;")
                 .replace("=", "\\="))
    return ";".join(f"{esc(k)}={esc(v)}" for k in sorted(d)
                    for v in [d[k]])
