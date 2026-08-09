# Amount formatting

format(x) renders a decimal amount string x as follows:

- Round to exactly 2 decimal places, ties to the even neighbor: an
  amount exactly halfway between two candidates takes the one whose last
  digit is even (2.675 lies between 2.67 and 2.68; 8 is even, so 2.68).
- Group the integer part with commas every three digits.
- Negative amounts are wrapped in parentheses and lose their sign:
  -1234.5 -> (1,234.50).
- Always show exactly two decimals.
