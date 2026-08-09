import re

# A placeholder is exactly '{{' + name + '}}' where name matches [a-z]+.
_PLACEHOLDER = re.compile(r"\{\{([a-z]+)\}\}")


def render(p):
    template = p["template"]
    context = p["context"]
    # Single left-to-right pass; a function replacement inserts values as
    # literal text (no backreference interpretation) and re.sub continues
    # scanning after the match, so inserted values are never re-scanned.
    return _PLACEHOLDER.sub(lambda m: context.get(m.group(1), ""), template)
