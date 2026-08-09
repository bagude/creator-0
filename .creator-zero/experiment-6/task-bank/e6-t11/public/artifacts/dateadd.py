DAYS = [31, 28, 31, 30, 31, 30, 31, 30, 30, 31, 30, 31]


def _leap(y):
    return y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)


def _dim(y, m):
    if m == 2 and _leap(y):
        return 29
    return DAYS[m - 1]


def add_days(iso, n):
    """Add n days to an ISO date string, returning an ISO date string."""
    y, m, d = (int(x) for x in iso.split("-"))
    for _ in range(n):
        d += 1
        if d > _dim(y, m):
            d = 1
            m += 1
            if m > 12:
                m = 1
                y += 1
    return f"{y:04d}-{m:02d}-{d:02d}"
