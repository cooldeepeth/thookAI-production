# Agent: Google OAuth — Config Verification + Error Handling
Sprint: 2 | Branch: fix/google-auth-config | PR target: dev
Depends on: Sprint 1 merged
Note: Can run in parallel with Agents 3 and 4 in Sprint 2

## Context
backend/routes/auth_google.py is fully registered in server.py (confirmed) and uses
Authlib for the OAuth flow. However there is no startup validation that GOOGLE_CLIENT_ID
and GOOGLE_CLIENT_SECRET are set, no graceful error if they are missing, and the
SessionMiddleware in server.py has https_only=True which will break Google OAuth
callbacks in local development over HTTP.

## Files You Will Touch
- backend/routes/auth_google.py         (MODIFY — improve error handling)
- backend/server.py                     (MODIFY — fix SessionMiddleware for dev, add startup check)
- backend/config.py                     (MODIFY — add GoogleConfig dataclass)

## Files You Must Read First (do not modify)
- backend/routes/auth_google.py        (read fully — understand the full OAuth flow)
- backend/server.py                    (find SessionMiddleware and lifespan startup section)
- backend/config.py                    (understand existing config dataclass pattern)
- backend/.env.example                 (GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, BACKEND_URL)

## Step 1: Add GoogleConfig to config.py
```python
@dataclass
class GoogleConfig:
    client_id: Optional[str] = field(default_factory=lambda: os.environ.get('GOOGLE_CLIENT_ID'))
    client_secret: Optional[str] = field(default_factory=lambda: os.environ.get('GOOGLE_CLIENT_SECRET'))
    backend_url: str = field(default_factory=lambda: os.environ.get('BACKEND_URL', 'http://localhost:8001'))
    
    def is_configured(self) -> bool:
        return bool(self.client_id and self.client_secret)
    
    @property
    def redirect_uri(self) -> str:
        return f"{self.backend_url}/api/auth/google/callback"
```
Add `google: GoogleConfig = field(default_factory=GoogleConfig)` to Settings.

## Step 2: Add startup check in server.py
In the lifespan startup section:
```python
if not settings.google.is_configured():
    logger.warning(
        "Google OAuth not configured — GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET missing. "
        "Google sign-in will return 503."
    )
else:
    logger.info(f"✓ Google OAuth configured (redirect: {settings.google.redirect_uri})")
```

## Step 3: Fix SessionMiddleware for development
Find this line in server.py:
```python
app.add_middleware(SessionMiddleware, secret_key=_session_secret, same_site="none", https_only=True)
```
Replace with:
```python
app.add_middleware(
    SessionMiddleware,
    secret_key=_session_secret,
    same_site="none" if settings.app.is_production else "lax",
    https_only=settings.app.is_production  # False in dev to allow HTTP
)
```
Without this fix, Google OAuth callbacks fail silently in local development
because the session cookie cannot be set over HTTP.

## Step 4: Add graceful guard to auth_google.py
At the start of both the `/auth/google` and `/auth/google/callback` endpoints, add:
```python
if not settings.google.is_configured():
    raise HTTPException(
        status_code=503,
        detail={
            "error": "google_auth_unavailable",
            "message": "Google sign-in is not configured on this server."
        }
    )
```
This prevents a cryptic Authlib crash when credentials are missing.

## Step 5: Add Google auth status to health endpoint
```python
health_status["checks"]["google_auth"] = "configured" if settings.google.is_configured() else "not_configured"
```

## Definition of Done
- `ENVIRONMENT=development` + HTTP → Google OAuth callback works (no https_only block)
- Missing Google credentials → clean HTTP 503 response, not a crash
- Startup logs clearly state Google auth status
- PR created to dev: "fix: Google OAuth config validation + fix dev SessionMiddleware"