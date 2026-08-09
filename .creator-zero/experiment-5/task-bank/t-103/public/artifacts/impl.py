def normalize_tags(tags):
    cleaned = [t.strip().lower() for t in tags]
    cleaned = [t for t in cleaned if t]
    return sorted(set(cleaned))
