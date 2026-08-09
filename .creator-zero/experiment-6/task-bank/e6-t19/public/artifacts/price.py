from decimal import Decimal, ROUND_HALF_EVEN


def _r(x):
    return x.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)


def price(p):
    sub = _r(Decimal(p["unit_price"]) * p["qty"])
    disc = _r(sub * (Decimal(100 - p["discount_pct"]) / 100))
    fin = _r(disc * (Decimal(100 + p["tax_pct"]) / 100))
    return f"{fin:.2f}"
