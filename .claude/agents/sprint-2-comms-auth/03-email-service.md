# Agent: Email Service — Resend Integration
Sprint: 2 | Branch: feat/email-service | PR target: dev
Depends on: Sprint 1 fully merged to dev

## Context
There is zero email delivery anywhere in the platform. The `resend` Python package
is already in requirements.txt and RESEND_API_KEY + FROM_EMAIL are already declared
in config.py and .env.example — but nobody ever wired them up. This breaks:
1. Password reset — token is generated and saved but NEVER emailed to the user
2. Agency workspace invitations — "invite sent" message is a lie

## Files You Will Touch
- backend/services/email_service.py       (CREATE — does not exist)
- backend/routes/password_reset.py        (MODIFY — call email service)
- backend/routes/agency.py               (MODIFY — call email service on invite)
- backend/config.py                       (MODIFY — add email config dataclass)

## Files You Must Read First (do not modify)
- backend/.env.example                    (RESEND_API_KEY, FROM_EMAIL already defined)
- backend/routes/password_reset.py        (read fully — understand the token flow)
- backend/routes/agency.py               (read fully — find the invite endpoint)

## Step 1: Add EmailConfig to backend/config.py
Add a new dataclass EmailConfig alongside the existing ones:
```python
@dataclass
class EmailConfig:
    resend_api_key: Optional[str] = field(default_factory=lambda: os.environ.get('RESEND_API_KEY'))
    from_email: str = field(default_factory=lambda: os.environ.get('FROM_EMAIL', 'noreply@thookai.com'))
    frontend_url: str = field(default_factory=lambda: os.environ.get('FRONTEND_URL', 'http://localhost:3000'))
    
    def is_configured(self) -> bool:
        return bool(self.resend_api_key)
```
Add `email: EmailConfig = field(default_factory=EmailConfig)` to the Settings dataclass.

## Step 2: Create backend/services/email_service.py
Implement using the `resend` package. The service must:

1. `send_password_reset_email(to_email: str, reset_token: str) -> bool`
   - Constructs reset link: `{settings.email.frontend_url}/reset-password?token={reset_token}`
   - Sends HTML email with a clean button linking to the reset URL
   - Subject: "Reset your ThookAI password"
   - Returns True on success, False on failure (never raise — log errors)

2. `send_workspace_invite_email(to_email: str, workspace_name: str, invite_token: str, inviter_name: str) -> bool`
   - Constructs invite link: `{settings.email.frontend_url}/invite?token={invite_token}`
   - Sends HTML email explaining they were invited by inviter_name to workspace_name
   - Subject: f"You've been invited to {workspace_name} on ThookAI"
   - Returns True on success, False on failure

3. `send_content_published_email(to_email: str, platform: str, content_preview: str) -> bool`
   - Notifies user their scheduled post was published
   - Subject: f"Your {platform} post was published"

Implement a graceful fallback: if `settings.email.is_configured()` is False, 
log a WARNING and return False without crashing. This allows dev environments
without Resend to still work.

## Step 3: Wire into password_reset.py
Find the `POST /reset-password/request` endpoint. After saving the token to MongoDB,
add:
```python
from services.email_service import send_password_reset_email
email_sent = send_password_reset_email(email, reset_token)
if not email_sent:
    logger.warning(f"Password reset email failed to send for {email}")
```
The endpoint should still return 200 regardless of email success (security — don't
reveal if email exists). But log a warning if sending fails.

## Step 4: Wire into agency.py
Find the workspace invite endpoint (POST /agency/workspaces/{id}/invite or similar).
After creating the invite record in MongoDB, add:
```python
from services.email_service import send_workspace_invite_email
send_workspace_invite_email(
    to_email=invite_email,
    workspace_name=workspace["name"],
    invite_token=invite_token,
    inviter_name=current_user["name"]
)
```

## Definition of Done
- `backend/services/email_service.py` exists with all 3 functions
- `grep -n "send_password_reset_email" backend/routes/password_reset.py` returns a result
- `grep -n "send_workspace_invite_email" backend/routes/agency.py` returns a result
- If RESEND_API_KEY is empty, service logs WARNING and returns False (does not crash)
- PR created to dev with title: "feat: add Resend email service for reset and invites"