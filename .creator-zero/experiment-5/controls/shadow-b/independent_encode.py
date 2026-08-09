# Simulated clean-room implementation of package/artifacts/format.md.
#
# CONTAMINATION NOTICE (evidence requirement E-B): the author of this file had
# already read reference.py when it was written (forced-local control run,
# CONTROL_ONLY), so it does NOT satisfy E-B's isolation requirement. It follows
# only the literal text of format.md; the two choices format.md leaves open are
# resolved canonically rather than by copying reference.py:
#   - entries are emitted in the dict's insertion order (format.md gives no order)
#   - exactly ';' and '=' are escaped, and only in values (format.md mandates
#     nothing else; in particular it says nothing about escaping '\' itself,
#     and scopes escaping to characters "occurring in a value")

def encode(d):
    def esc(s):
        return s.replace(";", "\\;").replace("=", "\\=")
    return ";".join(f"{k}={esc(v)}" for k, v in d.items())
