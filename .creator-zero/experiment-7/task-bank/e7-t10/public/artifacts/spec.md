# W371 check digits

An identifier is a string of digits followed by one check digit.

- Weights cycle 3, 7, 1, 3, 7, 1, ... assigned to the payload digits from
  RIGHT to LEFT (the rightmost payload digit has weight 3).
- The weighted sum S is the sum of digit x weight over the payload.
- The check digit is (10 - (S mod 10)) mod 10.
- An identifier is VALID when its last digit equals the check digit of
  the payload before it.
