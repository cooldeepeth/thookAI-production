---
phase: 34-security-gdpr
plan: 04
status: complete
retroactive: true
commit: 8443f58
requirements:
  - SECR-08
---

# Plan 34-04: Dependency CVE Audit + Safe Bumps + Exceptions Register — SUMMARY

> Retroactive summary reconstructed from `.planning/phases/34-security-gdpr/34-VERIFICATION.md` and commit `8443f58` (`feat(34-04): bump cryptography + black for CVE fixes, document langgraph and react-scripts exceptions`).

## Files Modified
- `backend/requirements.txt`
- `SECURITY-EXCEPTIONS.md` (new — repo root)

## pip-audit (Python)

| Package | CVEs | Action | New version constraint |
|---|---|---|---|
| `cryptography` 43.0.3 | 3 CVEs | **FIXED** | `>=46.0.6,<47.0` |
| `black` 24.10.0 | 1 CVE | **FIXED** (dev-only formatter) | `>=26.3.1,<27.0` |
| `langgraph` 0.6.11 | 1 CVE | **ACCEPTED** | Fix requires major version bump to 1.x (pipeline migration); exploit vector not reachable from API surface |
| `langgraph-checkpoint` 3.0.1 | 1 CVE | **ACCEPTED** | Checkpoint feature not enabled in ThookAI |

Both accepted exceptions documented in `SECURITY-EXCEPTIONS.md` with review dates and remediation plans.

## npm audit (Frontend)

Results: 14 high / 3 moderate / 9 low — **all transitive through `react-scripts`** (CRA 5.0.1 build toolchain: webpack, SVGO, PostCSS, `serialize-javascript` inside rollup, `underscore` via `bfj`/`jsonpath`).

- All vulnerabilities ship only in the build environment — none ship in the production browser bundle.
- `npm audit fix --force` would install `react-scripts@0.0.0` and break the build entirely.
- **Accepted** in `SECURITY-EXCEPTIONS.md`. Long-term remediation: CRA → Vite migration (deferred to a post-launch modernization phase).

No runtime `"dependencies"` packages had unaddressed high/critical CVEs.

## SECURITY-EXCEPTIONS.md

Created at repo root with:
- Python exception table (`langgraph`, `langgraph-checkpoint`)
- npm exception summary (`react-scripts` transitive chain)
- Review dates set to 2026-04-13
- Next review trigger: before Phase 35 launch checklist / first post-launch maintenance window

## Verification
```
$ pip-audit -r backend/requirements.txt 2>&1 | tail -10
(cryptography + black resolved; only documented exceptions remain)

$ npm audit --audit-level=high --omit=dev 2>&1 | tail -5
(no runtime-dependency findings)

$ python -c "import fastapi, motor, stripe, anthropic"
(OK — no import regressions from version bumps)
```

## Requirements Satisfied
- **SECR-08** — Zero unaddressed critical/high CVEs in runtime dependencies: PASS (all fixable bumped, all accepted documented)

## Notes
- `pip-audit` installed as a dev-only CLI tool; NOT added to `requirements.txt`.
- `black` is dev-only but bumped anyway for CI hygiene.
- Inline execution by orchestrator.
