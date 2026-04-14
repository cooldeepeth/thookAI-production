---
phase: 260414-n1i
plan: "01"
subsystem: backend-entrypoint
tags: [hotfix, server, procfile, railway, uvicorn]
dependency_graph:
  requires: []
  provides: ["__main__ entry-point for python server.py"]
  affects: [backend/server.py]
tech_stack:
  added: []
  patterns: ["__main__ guard", "uvicorn programmatic start"]
key_files:
  created: []
  modified:
    - backend/server.py
decisions:
  - "`os.environ.get()` is acceptable in a `__main__` entry-point guard — CLAUDE.md ban covers route/agent/service files only"
metrics:
  duration: "< 5 min"
  completed: "2026-04-14"
---

# Phase 260414-n1i Plan 01: Restore __main__ Block in backend/server.py — Summary

**One-liner:** Restored 4-line `__main__` uvicorn guard deleted by 02697c3, fixing Railway crash-loops where `python server.py` exited 0 without binding $PORT.

## What Was Done

### Task 1: Restore __main__ block in backend/server.py

Replaced the two stale comment lines at EOF (lines 534-535) with the correct `__main__` guard:

```python
# Procfile: `web: python server.py` — the __main__ block below starts uvicorn.
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("server:app", host="0.0.0.0", port=port)
```

**Commit:** `e562324`

## Verification

```
INFO:     Started server process [36994]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8765 (Press CTRL+C to quit)
```

All four uvicorn startup signals confirmed. Process binds $PORT correctly.

## Root Cause

Commit `02697c3` (Apr 13) titled "remove os.environ.get from server.py __main__ block" deleted the entire `__main__` guard and replaced it with an incorrect comment claiming `uvicorn server:app` was the Procfile command. The actual Procfile command is `web: python server.py` — without the `__main__` block Python imports the module and exits 0, causing Railway crash-loops.

## Deviations from Plan

None — plan executed exactly as written.

## Threat Flags

None — PORT is a non-sensitive integer read from the Railway environment. No new attack surface introduced.

## Self-Check: PASSED

- [x] `backend/server.py` modified with `__main__` block present at line 535
- [x] Commit `e562324` exists: `git log --oneline | grep e562324`
- [x] Uvicorn startup confirmed: `Started server process`, `Waiting for application startup`, `Application startup complete`, `Uvicorn running on http://0.0.0.0:8765`
- [x] Only 1 file changed (`backend/server.py`, 5 insertions, 2 deletions)
