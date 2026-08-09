def transform(s):
    s = s.strip()
    m, d, y = s.split("/")
    y = int(y)
    if y < 100:
        y = 2000 + y if y < 50 else 1900 + y
    return f"{y:04d}-{int(m):02d}-{int(d):02d}"
