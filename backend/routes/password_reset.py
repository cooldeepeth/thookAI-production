"""
Password reset via email (Resend) and token stored in MongoDB.
"""

import hashlib
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone

import resend
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr

from auth_utils import hash_password
from database import db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

FORGOT_RESPONSE = {"message": "If that email exists, a reset link was sent."}
RESET_SUCCESS = {"message": "Password reset successfully."}


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@router.post("/forgot-password")
async def forgot_password(data: ForgotPasswordRequest):
    user = await db.users.find_one({"email": data.email}, {"_id": 0})
    if user and user.get("auth_method") == "email":
        token = secrets.token_urlsafe(32)
        th = _token_hash(token)
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=1)
        await db.password_resets.insert_one(
            {
                "token_hash": th,
                "user_id": user["user_id"],
                "expires_at": expires_at,
                "used": False,
                "created_at": now,
            }
        )
        api_key = os.environ.get("RESEND_API_KEY", "").strip()
        from_email = os.environ.get("FROM_EMAIL", "noreply@thookai.com").strip()
        frontend = os.environ.get("FRONTEND_URL", "http://localhost:3000").rstrip("/")
        link = f"{frontend}/reset-password?token={token}"
        body = (
            "Reset your ThookAI password by visiting this link (valid for 1 hour):\n\n"
            f"{link}\n\n"
            "If you did not request this, you can ignore this email."
        )
        if api_key:
            try:
                resend.api_key = api_key
                resend.Emails.send(
                    {
                        "from": from_email,
                        "to": [data.email],
                        "subject": "Reset your ThookAI password",
                        "text": body,
                    }
                )
            except Exception as e:
                logger.warning("Resend send failed: %s", e)
        else:
            logger.warning("RESEND_API_KEY not set; skip email send (dev)")

    return FORGOT_RESPONSE


@router.post("/reset-password")
async def reset_password(data: ResetPasswordRequest):
    if len(data.new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    th = _token_hash(data.token)
    doc = await db.password_resets.find_one({"token_hash": th})
    if not doc or doc.get("used"):
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    expires_at = doc["expires_at"]
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    user_id = doc["user_id"]
    new_hash = hash_password(data.new_password)
    await db.users.update_one({"user_id": user_id}, {"$set": {"hashed_password": new_hash}})
    await db.password_resets.update_one({"token_hash": th}, {"$set": {"used": True}})
    return RESET_SUCCESS
