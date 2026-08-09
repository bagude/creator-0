"""Clean-room implementation of the placeholder-substitution language
specified in inputs/render.md.

A placeholder is exactly '{{' + name + '}}' where name matches [a-z]+.
Anything else, including braces that do not form such a placeholder, is
literal text.
"""

import re

_PLACEHOLDER = re.compile(r"\{\{([a-z]+)\}\}")


def render(p):
    """Render p["template"] using p["context"].

    Every placeholder '{{name}}' (name matching [a-z]+) is replaced by
    context[name], or by the empty string when name is not in the context.
    Replacement is a single pass: inserted values are literal text and are
    never re-scanned for placeholders. No other transformation is applied.
    """
    template = p["template"]
    context = p["context"]

    def _substitute(match):
        name = match.group(1)
        if name in context:
            return context[name]
        return ""

    return _PLACEHOLDER.sub(_substitute, template)
