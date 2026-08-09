# Record encoding format

A mapping of string keys to string values is encoded as a single line.

- Each pair is written as key=value.
- Pairs are joined with the separator character ';'.
- Pairs appear in the encoded line in the order in which they appear in
  the mapping.
- Inside keys and values, every ';' is written as the two characters
  backslash-semicolon and every '=' as backslash-equals.
- An empty mapping encodes as the empty line.

Function contract: encode(d) takes the mapping and returns the encoded
line as a string.
