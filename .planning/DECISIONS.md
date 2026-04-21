# Decision log

Format:

- **YYYY-MM-DD — [Title]**
  - Context:
  - Options considered:
  - Decision:
  - Rationale:
  - Revisit date (optional):

## Decisions

- **2026-04-21 — Adopted wedge-only development mode**
  - Context: Codebase at 820+ commits, many half-built features, no validated paying users. Decision paralysis + bug regressions across full platform.
  - Options considered: (a) Continue audit-and-fix all phases per PLATFORM-REBUILD.md. (b) Fresh repo rebuild. (c) Gut current repo to a single wedge with feature flags.
  - Decision: (c). Gut to LinkedIn text wedge, feature-flag everything else off.
  - Rationale: Preserves sunk cost code, deployed infra, auth, billing. Reduces audit surface ~80%. Enables real user validation in 4 weeks instead of 3 months.
