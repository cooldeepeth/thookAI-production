---
phase: 34-security-gdpr
plan: 02
status: complete
retroactive: true
commit: 02697c3
requirements:
  - SECR-06
  - SECR-07
---

# Plan 34-02: Sentry PII Scrub + os.environ.get Removal — SUMMARY

> Retroactive summary reconstructed from `.planning/phases/34-security-gdpr/34-VERIFICATION.md` and commit `02697c3` (`feat(34-02): add Sentry PII scrub callback and remove os.environ.get from server.py __main__ block`).

## Files Modified
- `backend/server.py`

## Changes — backend/server.py

**1. Sentry PII scrub callback added** (before `sentry_sdk.init()` call):
```python
def _scrub_pii(event, hint):
    """Remove PII fields from Sentry error events (GDPR + SECR-07 compliance)."""
    pii_keys = frozenset({
        'email', 'password', 'hashed_password', 'access_token',
        'refresh_token', 'session_token', 'csrf_token', 'name',
        'google_id', 'stripe_customer_id',
    })
    if 'request' in event and isinstance(event['request'].get('data'), dict):
        for key in pii_keys:
            event['request']['data'].pop(key, None)
    if isinstance(event.get('extra'), dict):
        for key in pii_keys:
            event['extra'].pop(key, None)
    return event
```

`before_send=_scrub_pii` wired into the existing `sentry_sdk.init(...)` call. No other Sentry parameters changed.

**2. `if __name__ == "__main__"` block removed** — contained the lone `os.environ.get("PORT", 8000)` violation. Rationale: server is started via `backend/Procfile` (`uvicorn server:app --host 0.0.0.0 --port $PORT`), so the block never executed in production. Replaced with inline comment pointing at Procfile.

## Audit — auth_google.py and vector_store.py
Research flagged both as "FIXED — verify only." Both confirmed clean:
- `backend/routes/auth_google.py` — no `os.environ.get()` calls; only a legacy `# FIXED` comment string.
- `backend/services/vector_store.py` — same; only the documentation comment remains.

## SECR-07 — stack trace leakage
The production/dev branch in `global_exception_handler` (already present before Phase 34) returns:
```
{"detail": "An internal error occurred", "error_code": "INTERNAL_ERROR"}
```
when `settings.app.is_production == True`. Plan 34-02 added the Sentry PII scrub callback as the remaining SECR-07 gap — stack-trace suppression was already correct.

## Verification
```
$ grep -rn 'os.environ.get' backend/ --include='*.py' | grep -v 'config.py' | grep -v tests/ | grep -v '.venv'
(zero matches outside config.py)

$ grep -n '_scrub_pii\|before_send' backend/server.py
(function defined + wired into sentry_sdk.init)

$ grep -n '__main__' backend/server.py
(zero matches)

$ python -c "import server" 
(OK — no SyntaxError)
```

## Requirements Satisfied
- **SECR-06** — Zero `os.environ.get()` outside config.py: PASS
- **SECR-07** — No stack trace leakage + Sentry PII scrub: PASS

## Notes
- Remaining `os.environ.get` calls exist only in `backend/tests/*` and `.venv/` — out of scope per requirement definition.
- Inline execution by orchestrator (same hook constraint as 34-01).
