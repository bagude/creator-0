"""Line pricing rules, implemented exactly as specified in pricing.md.

price(p) computes the final price string for
p = {"qty": int, "unit_price": str, "discount_pct": int, "tax_pct": int}:

1. subtotal   = qty x unit_price, rounded to the cent, half away from zero.
2. discounted = subtotal reduced by discount_pct percent, rounded to the
   cent, half away from zero.
3. final      = discounted increased by tax_pct percent, rounded to the
   cent, half away from zero.
4. The result is the final amount as a string with exactly two decimals.
"""

from decimal import Decimal, ROUND_HALF_UP

_CENT = Decimal("0.01")


def _round_cent(amount):
    # ROUND_HALF_UP in the decimal module rounds ties away from zero,
    # which is precisely the "half away from zero" discipline the spec states.
    return amount.quantize(_CENT, rounding=ROUND_HALF_UP)


def price(p):
    qty = Decimal(p["qty"])
    unit_price = Decimal(p["unit_price"])
    discount_pct = Decimal(p["discount_pct"])
    tax_pct = Decimal(p["tax_pct"])

    subtotal = _round_cent(qty * unit_price)
    discounted = _round_cent(subtotal - subtotal * discount_pct / Decimal(100))
    final = _round_cent(discounted + discounted * tax_pct / Decimal(100))

    return f"{final:.2f}"
