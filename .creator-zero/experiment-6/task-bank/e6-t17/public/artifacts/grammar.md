# Expression grammar

E -> E op E | number
op -> '-' | '^'

No precedence and no associativity are defined: every way of fully
parenthesizing the expression is a distinct parse. '-' is subtraction;
'^' is exponentiation (right operand as the exponent), both on integers.
