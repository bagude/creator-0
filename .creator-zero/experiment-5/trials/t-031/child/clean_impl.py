"""Wire-format encoder implemented strictly from format.md.

format.md states:
  - encode(d: dict[str, str]) -> str
  - Each entry is rendered as `key=value`.
  - Entries are joined with the separator `;`.
  - The characters `;` and `=` occurring *in a value* must be escaped by
    preceding them with a backslash (`\\`).

Nothing else is stated. In particular the spec says nothing about entry
ordering (so we use the dict's own iteration order) and nothing about
escaping literal backslashes (so we escape only `;` and `=`, exactly as
written, and leave any existing backslash untouched).
"""


def encode(d: dict) -> str:
    entries = []
    for key, value in d.items():
        # Escape only the characters the spec names, only in the value.
        escaped_value = value.replace(";", "\\;").replace("=", "\\=")
        entries.append(key + "=" + escaped_value)
    return ";".join(entries)
