# Indexing rules

`build_index(text: str) -> str`

Build a term index of the document:

1. A **term** is a whitespace-separated token, lowercased, with the
   characters `.,;:` stripped from both ends. Tokens that become empty are
   ignored.
2. For each unique term, list the line numbers of every line on which it
   occurs. Each line number appears at most once per term.
3. Render one line per term in the form `term: n1,n2,n3` (line numbers
   comma-separated, ascending).
4. Return the rendered lines joined with newlines, with a trailing newline.
