# Cart discount rules

The final price factor of a cart starts at 1.0 and every applicable rule
multiplies it:

- BULK: quantity of 5 or more -> factor x 0.90
- LOYALTY: loyalty_member true -> factor x 0.85
- SEASONAL: category is 'outdoor' -> factor x 0.80
- COUPON: coupon_code_applied true -> factor x 0.95

The total discount of a cart is 1.0 minus its final factor. A cart is
{"quantity": int, "loyalty_member": bool, "category": str,
"coupon_code_applied": bool}.
