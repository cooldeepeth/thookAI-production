# Security Exception Register

> Documented CVE findings from `pip-audit` and `npm audit` that are accepted risks
> (not blocking) with rationale and remediation plan. Reviewed each GSD milestone.

Last reviewed: **2026-04-13** (Phase 34 — Security & GDPR)

## Policy

- **Critical / High runtime CVEs** — must be fixed before ship. Fixed via version bump in `requirements.txt` or `package.json` on the same day they are discovered.
- **High CVEs in dev-only / build-only dependencies** — may be accepted if the fix requires a breaking change and the vulnerable code path never reaches the production runtime.
- **Transitive CVEs fixable only via `npm audit fix --force`** — rejected by default because `--force` can install breaking major-version bumps. Triage to either a direct pin or an entry in this file.
- Every entry must include: package, version, CVE ID, severity, runtime-vs-dev, rationale, review date.

---

## Backend — Python (pip-audit)

### `langgraph` 0.6.11 — CVE-2026-28277 — HIGH

**Fix version:** 1.0.10 (major version bump)
**Runtime impact:** The agent pipeline (`backend/agents/pipeline.py`) uses `langgraph` for orchestration.
**Rationale:** Upgrading to langgraph 1.x is a breaking change that requires migrating the graph API, state schemas, and retry semantics. A full test pass against the 5-agent content pipeline (Commander → Scout → Thinker → Writer → QC) is required before the bump can ship. The vulnerability's exploit vector requires an attacker to supply a malicious state value directly into a langgraph node — ThookAI's pipeline state is fully constructed server-side from validated Pydantic inputs, so the exploit vector is not reachable from the external API surface.
**Remediation plan:** Schedule as Phase 35 task or a dedicated follow-up phase. Migration guide: https://langchain-ai.github.io/langgraph/ (track breaking changes).
**Review again:** End of Phase 35.

### `langgraph-checkpoint` 3.0.1 — CVE-2026-27794 — HIGH

**Fix version:** 4.0.0 (major version bump)
**Runtime impact:** Used as a transitive dep of langgraph for checkpoint persistence. ThookAI does not configure or use the langgraph checkpoint feature (agents run in-memory per request).
**Rationale:** Same as langgraph above — the vulnerable code path is not reachable because we don't enable langgraph checkpoints. Bumping is coupled with the langgraph 1.x migration.
**Remediation plan:** Upgrade alongside langgraph 1.x migration.
**Review again:** End of Phase 35.

---

## Frontend — npm (npm audit)

### `react-scripts` 5.0.1 transitive CVEs — 14 HIGH / 3 MODERATE / 9 LOW

**Packages affected (all transitive):** `nth-check`, `css-select`, `svgo`, `@svgr/plugin-svgo`, `@svgr/webpack`, `postcss`, `resolve-url-loader`, `serialize-javascript`, `css-minimizer-webpack-plugin`, `rollup-plugin-terser`, `workbox-build`, `workbox-webpack-plugin`, `webpack-dev-server`, `underscore`, `jsonpath`, `bfj`.
**Fix available via:** `npm audit fix --force` — **installs react-scripts@0.0.0**, which is a breaking change that removes CRA entirely.
**Runtime impact:** ZERO. Every one of these packages ships at BUILD TIME only (webpack, SVGO, PostCSS, workbox, serialize-javascript, underscore inside bfj/jsonpath which is only used by the dev toolchain). None of these packages appear in the production bundle that Vercel serves to end-users. Confirmed by checking `package.json` — none are listed as direct `dependencies`.
**Rationale:** Accepting these CVEs is the industry-standard posture for any CRA project. The proposed "fix" (`--force` → react-scripts@0.0.0) would destroy the build system. Facebook deprecated CRA in 2023, so these findings will never be officially fixed upstream. The correct long-term remediation is a full migration from CRA to Vite, which is tracked separately as a future phase.
**Mitigation:** The build runs in CI inside a sandboxed container — no production secrets are exposed to build-time-only exploit surfaces.
**Remediation plan:** Long-term: migrate `frontend/` from CRA to Vite in a dedicated future phase. Short-term: accept.
**Review again:** End of milestone v3.0.

---

## Backend — Python (fixed in Phase 34)

These CVEs were fixed in Plan 34-04 of Phase 34 (2026-04-13):

| Package      | Old version | New version      | CVEs fixed                                     |
| ------------ | ----------- | ---------------- | ---------------------------------------------- |
| cryptography | 43.0.3      | 46.0.6           | CVE-2024-12797, CVE-2026-26007, CVE-2026-34073 |
| black        | 24.10.0     | 26.3.1           | CVE-2026-32274                                 |
| starlette    | 0.47.2      | (already pinned) | CVE-2024-47874, CVE-2025-54121                 |

---

## Audit Commands

Run both audits at the start of every security phase:

```bash
# Backend
pip install pip-audit
cd backend && pip-audit -r requirements.txt

# Frontend
cd frontend && npm audit --audit-level=high
```

**Never run `npm audit fix --force` on the CRA frontend** — it will break the build.
