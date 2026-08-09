# Legacy date migration

Legacy date strings use the form M/D/YY or M/D/YYYY (month and day may be
one or two digits). They are converted to ISO YYYY-MM-DD.

- Months and days are zero-padded to two digits in the output.
- Two-digit years map to a century as follows: 70-99 mean 19xx and 00-69
  mean 20xx.
- Four-digit years are used as-is.

Function contract: transform(s) takes the legacy string and returns the
ISO string.
