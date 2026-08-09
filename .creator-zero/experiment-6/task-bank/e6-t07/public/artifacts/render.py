import re

def render(p):
    t, ctx = p["template"], p["context"]
    return re.sub(r"\{\{([a-z]+)\}\}",
                  lambda m: str(ctx.get(m.group(1), "")), t)
