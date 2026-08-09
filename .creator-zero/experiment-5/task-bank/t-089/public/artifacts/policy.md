# Service Change Policy

A proposed configuration is evaluated against the current baseline
configuration. All rules are mandatory; each is deterministic.

- **R1** — Every service present in both configurations must keep the same
  `owner` in the proposal as in the baseline.
- **R2** — No service may have `debug: true` in the proposal while its
  proposed `tier` is `"prod"`.
- **R3** — For every service present in both configurations, proposed
  `replicas` must be greater than or equal to baseline `replicas`.
- **R4** — Every service with proposed `public: true` must have proposed
  `tls: true`.
- **R5** — Every service present in the proposal but absent from the
  baseline must have proposed `tier: "staging"`.
