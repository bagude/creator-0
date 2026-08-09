# Wire format — flat string map encoding

`encode(d: dict[str, str]) -> str`

A flat map of string keys to string values is encoded as a single line:

- Each entry is rendered as `key=value`.
- Entries are joined with the separator `;`.
- The characters `;` and `=` occurring **in a value** must be escaped by
  preceding them with a backslash (`\`).
