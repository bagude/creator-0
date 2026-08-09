# Creator-0 Architecture

```text
Task
  -> Creator C_n
  -> proposed HarnessSpec
  -> deterministic boundary/compiler
  -> Runtime Harness H_n
       -> terminal functional nodes
       -> optional Creator C_(n+1)
```

Three independent types are preserved:

1. boundary type — what may cross;
2. message type — what payload crossed;
3. relationship type — what causal authority the crossing carries.

Creator Closure is capability preservation, not cloning:

`C_n -> H_n[C_(n+1)]`, with `kappa(C_(n+1)) = 1`.

The MVP uses mediated closure: descendants reuse a protected trusted compiler under attenuated contracts.
