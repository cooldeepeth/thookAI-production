"""
ThookAI Email Service

Transactional emails via Resend for password resets, workspace invites,
and content-published notifications.

Usage:
    from services.email_service import send_password_reset_email
    success = send_password_reset_email("user@example.com", reset_token)
"""

import html as html_lib
import logging
from urllib.parse import quote as url_quote

import resend

from config import settings

logger = logging.getLogger(__name__)


def _send_email(to_email: str, subject: str, html: str) -> bool:
    """
    Low-level email send via Resend.
    Returns True on success, False on failure. Never raises.
    """
    if not settings.email.is_configured():
        logger.warning(
            "Email not configured (RESEND_API_KEY missing). "
            "Skipping email to %s — subject: %s",
            to_email,
            subject,
        )
        return False

    try:
        resend.api_key = settings.email.resend_api_key
        resend.Emails.send(
            {
                "from": settings.email.from_email,
                "to": [to_email],
                "subject": subject,
                "html": html,
            }
        )
        logger.info("Email sent to %s — subject: %s", to_email, subject)
        return True
    except Exception as exc:
        logger.exception("Failed to send email to %s", to_email)  # FIXED: use logger.exception for traceback
        return False


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def send_password_reset_email(to_email: str, reset_token: str) -> bool:
    """
    Send a password-reset email with a link containing the token.

    Args:
        to_email: Recipient address.
        reset_token: The raw (unhashed) token the user will submit to reset.

    Returns:
        True if the email was accepted by Resend, False otherwise.
    """
    frontend_url = settings.email.frontend_url.rstrip("/")
    reset_link = f"{frontend_url}/reset-password?token={url_quote(reset_token, safe='')}"  # FIXED: URL-encode token

    html = f"""\
<div style="font-family: Arial, sans-serif; max-width: 480px; margin: 0 auto;">
  <h2 style="color: #111;">Reset your ThookAI password</h2>
  <p>We received a request to reset the password for your ThookAI account.</p>
  <p>Click the button below to choose a new password. This link is valid for
  <strong>1 hour</strong>.</p>
  <p style="text-align: center; margin: 32px 0;">
    <a href="{reset_link}"
       style="background-color: #6366f1; color: #fff; padding: 12px 32px;
              border-radius: 6px; text-decoration: none; font-weight: 600;">
      Reset Password
    </a>
  </p>
  <p style="color: #666; font-size: 13px;">
    If you did not request this, you can safely ignore this email.
  </p>
  <hr style="border: none; border-top: 1px solid #eee; margin: 24px 0;" />
  <p style="color: #999; font-size: 12px;">ThookAI &mdash; AI-powered content creation</p>
</div>
"""

    return _send_email(to_email, "Reset your ThookAI password", html)


def send_workspace_invite_email(
    to_email: str,
    workspace_name: str,
    invite_token: str,
    inviter_name: str,
) -> bool:
    """
    Notify a user that they have been invited to a workspace.

    Args:
        to_email: Invitee email address.
        workspace_name: Human-readable workspace name.
        invite_token: The invite_id used to accept the invitation.
        inviter_name: Display name of the person who sent the invite.

    Returns:
        True if the email was accepted by Resend, False otherwise.
    """
    frontend_url = settings.email.frontend_url.rstrip("/")
    invite_link = f"{frontend_url}/invite?token={url_quote(invite_token, safe='')}"  # FIXED: URL-encode token
    safe_workspace = html_lib.escape(workspace_name)  # FIXED: escape user-controlled HTML
    safe_inviter = html_lib.escape(inviter_name)  # FIXED: escape user-controlled HTML
    html = f"""\
<div style="font-family: Arial, sans-serif; max-width: 480px; margin: 0 auto;">
  <h2 style="color: #111;">You're invited to {safe_workspace}</h2>
  <p><strong>{safe_inviter}</strong> has invited you to join the
  <strong>{safe_workspace}</strong> workspace on ThookAI.</p>
  <p>Click the button below to accept the invitation and start collaborating.</p>
  <p style="text-align: center; margin: 32px 0;">
    <a href="{invite_link}"
       style="background-color: #6366f1; color: #fff; padding: 12px 32px;
              border-radius: 6px; text-decoration: none; font-weight: 600;">
      Accept Invitation
    </a>
  </p>
  <p style="color: #666; font-size: 13px;">
    If you don't have a ThookAI account yet, you can create one after clicking
    the link above.
  </p>
  <hr style="border: none; border-top: 1px solid #eee; margin: 24px 0;" />
  <p style="color: #999; font-size: 12px;">ThookAI &mdash; AI-powered content creation</p>
</div>
"""

    subject = f"You've been invited to {safe_workspace} on ThookAI"
    return _send_email(to_email, subject, html)


def send_content_published_email(
    to_email: str,
    platform: str,
    content_preview: str,
) -> bool:
    """
    Notify a user that their scheduled post was published.

    Args:
        to_email: Author email address.
        platform: Social platform name (e.g. "linkedin", "x", "instagram").
        content_preview: First ~200 chars of the published content.

    Returns:
        True if the email was accepted by Resend, False otherwise.
    """
    # Truncate preview for safety
    preview = html_lib.escape((content_preview[:200] + "...") if len(content_preview) > 200 else content_preview)  # FIXED: escape user content
    platform_display = html_lib.escape(platform.capitalize())  # FIXED: escape platform name

    html = f"""\
<div style="font-family: Arial, sans-serif; max-width: 480px; margin: 0 auto;">
  <h2 style="color: #111;">Your {platform_display} post was published</h2>
  <p>Great news! Your scheduled post has been successfully published
  to <strong>{platform_display}</strong>.</p>
  <div style="background: #f9fafb; border-left: 4px solid #6366f1;
              padding: 12px 16px; margin: 16px 0; border-radius: 4px;">
    <p style="margin: 0; color: #333; font-size: 14px;">{preview}</p>
  </div>
  <p>Head over to your dashboard to track its performance.</p>
  <hr style="border: none; border-top: 1px solid #eee; margin: 24px 0;" />
  <p style="color: #999; font-size: 12px;">ThookAI &mdash; AI-powered content creation</p>
</div>
"""

    subject = f"Your {platform_display} post was published"
    return _send_email(to_email, subject, html)
