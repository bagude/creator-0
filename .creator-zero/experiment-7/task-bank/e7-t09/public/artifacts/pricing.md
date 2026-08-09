# Line pricing rules

price(p) computes the final price string for p = {"qty": int,
"unit_price": str, "discount_pct": int, "tax_pct": int}.

1. subtotal = qty x unit_price, rounded to the cent, half away from zero.
2. discounted = subtotal reduced by discount_pct percent, rounded to the
   cent, half away from zero.
3. final = discounted increased by tax_pct percent, rounded to the cent,
   half away from zero.
4. The result is the final amount as a string with exactly two decimals.
