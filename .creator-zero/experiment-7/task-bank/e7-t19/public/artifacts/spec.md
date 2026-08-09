# Stack program semantics

A program is a list of instructions over an integer stack, initially
empty. Result: the top of the stack after the last instruction, or
"EMPTY" if the stack is empty, or "ERROR" if the program halted early.

- PUSH n: push the integer n.
- ADD: pop two values, push their sum. Fewer than two values: the
  program halts immediately with "ERROR".
- DUP: duplicate the top value. Empty stack: halt with "ERROR".
- SWAP: exchange the top two values. Fewer than two values: halt with
  "ERROR".
- POP: remove the top value. Empty stack: the stack stays empty and the
  program continues.
