# Placeholder substitution language

A template is a string. A placeholder is exactly '{{' + name + '}}' where
name is one or more lowercase letters (regex [a-z]+); anything else,
including braces that do not form such a placeholder, is literal text.

- render(t, ctx) replaces every placeholder with ctx[name], where ctx is
  a mapping of names to strings.
- A placeholder whose name is not in ctx is replaced by the empty string.
- Replacement is a single pass over the template: values are inserted as
  literal text and are never re-scanned for placeholders.
- No other transformation is applied.

Function contract: render(p) with p = {"template": t, "context": ctx}
returns the rendered string.
