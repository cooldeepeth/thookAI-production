"""
ThookAI Authentication Utilities

Features:
- JWT token management
- Password hashing with bcrypt
- Session validation
- Password policy enforcement
"""

from fastapi import Depends, HTTPException, Request
from jose import JWTError, jwt
import bcrypt
from datetime import datetime, timezone
import re
import logging
from config import settings

logger = logging.getLogger(__name__)

# ==================== PASSWORD HASHING ====================


def hash_password(password: str) -> str:
    """Hash a password using bcrypt directly (no passlib dependency)"""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a password against its bcrypt hash"""
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


# ==================== PASSWORD POLICY ====================

class PasswordPolicy:
    """
    Password strength validation.
    Enforces security requirements for user passwords.
    """
    
    MIN_LENGTH = 8
    MAX_LENGTH = 128
    
    @classmethod
    def validate(cls, password: str) -> tuple[bool, list[str]]:
        """
        Validate password against policy.
        Returns (is_valid, list_of_errors)
        """
        errors = []
        
        # Length check
        if len(password) < cls.MIN_LENGTH:
            errors.append(f"Password must be at least {cls.MIN_LENGTH} characters")
        
        if len(password) > cls.MAX_LENGTH:
            errors.append(f"Password must be at most {cls.MAX_LENGTH} characters")
        
        # Complexity checks
        if not re.search(r'[A-Z]', password):
            errors.append("Password must contain at least one uppercase letter")
        
        if not re.search(r'[a-z]', password):
            errors.append("Password must contain at least one lowercase letter")
        
        if not re.search(r'\d', password):
            errors.append("Password must contain at least one number")
        
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors.append("Password must contain at least one special character")
        
        # Common password check (basic list, expand as needed)
        common_passwords = {
            'password', 'password123', '123456', '12345678', 'qwerty',
            'abc123', 'letmein', 'welcome', 'admin', 'login'
        }
        if password.lower() in common_passwords:
            errors.append("Password is too common. Please choose a stronger password")
        
        return len(errors) == 0, errors


def validate_password_strength(password: str) -> None:
    """
    Validate password and raise HTTPException if invalid.
    Use in registration endpoints.
    """
    is_valid, errors = PasswordPolicy.validate(password)
    if not is_valid:
        raise HTTPException(
            status_code=400,
            detail={"message": "Password does not meet requirements", "errors": errors}
        )


# ==================== JWT HANDLING ====================

def create_access_token(user_id: str, expires_days: int = None) -> str:
    """Create a JWT access token for a user"""
    from datetime import timedelta
    
    if expires_days is None:
        expires_days = settings.security.jwt_expire_days
    
    expire = datetime.now(timezone.utc) + timedelta(days=expires_days)
    
    to_encode = {
        "sub": user_id,
        "exp": expire,
        "iat": datetime.now(timezone.utc)
    }
    
    return jwt.encode(
        to_encode,
        settings.security.jwt_secret_key,
        algorithm=settings.security.jwt_algorithm
    )


def decode_token(token: str) -> dict:
    """
    Decode and validate a JWT token.
    Raises JWTError if invalid or if JWT_SECRET_KEY is not configured.

    SECURITY: Never falls back to a hardcoded secret. If JWT_SECRET_KEY is
    not configured, raises JWTError immediately — do not silently accept tokens
    signed with a default dev key in production (BILL-06).
    """
    secret = settings.security.jwt_secret_key
    if not secret:
        raise JWTError("JWT secret key not configured")
    return jwt.decode(
        token,
        secret,
        algorithms=[settings.security.jwt_algorithm]
    )


# ==================== USER AUTHENTICATION ====================

async def get_current_user(request: Request):
    """
    Get the current authenticated user from request.
    Supports both JWT tokens and session tokens (Google OAuth).
    
    Token can be provided via:
    - Cookie: session_token
    - Header: Authorization: Bearer <token>
    """
    from database import db

    token = request.cookies.get("session_token")
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]

    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Try JWT first (email/password auth)
    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        if user_id:
            user = await db.users.find_one({"user_id": user_id}, {"_id": 0})
            if user:
                return user
    except JWTError:
        pass

    # Try Google OAuth session token
    # JWT tokens are longer and have dots, session tokens are shorter
    if '.' not in token or len(token) < 100:
        session = await db.user_sessions.find_one({"session_token": token}, {"_id": 0})
        if session:
            expires_at = session["expires_at"]
            if isinstance(expires_at, str):
                expires_at = datetime.fromisoformat(expires_at)
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if expires_at < datetime.now(timezone.utc):
                raise HTTPException(status_code=401, detail="Session expired")

            user = await db.users.find_one({"user_id": session["user_id"]}, {"_id": 0})
            if user:
                return user

    # Neither JWT nor session token validation worked
    raise HTTPException(status_code=401, detail="Invalid or expired token")


# Set admin via MongoDB: db.users.updateOne({email: "..."}, {$set: {role: "admin"}})
async def require_admin(current_user: dict = Depends(get_current_user)):
    """Dependency that requires admin role."""
    from database import db
    user = await db.users.find_one({"user_id": current_user["user_id"]})
    if not user or user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


async def get_optional_user(request: Request):
    """
    Get current user if authenticated, otherwise return None.
    Use for endpoints that work both authenticated and anonymously.
    """
    try:
        return await get_current_user(request)
    except HTTPException:
        return None


# ==================== TOKEN ENCRYPTION (for OAuth tokens) ====================

_dev_fernet_key: str | None = None


def get_fernet():
    """Get Fernet instance for encrypting OAuth tokens"""
    global _dev_fernet_key
    from cryptography.fernet import Fernet

    key = settings.security.fernet_key
    if not key:
        if settings.app.is_production:
            logger.error("FERNET_KEY not configured in production!")
            raise ValueError("FERNET_KEY must be configured in production")
        # Cache generated key for process lifetime to prevent per-call regeneration
        if _dev_fernet_key is None:
            _dev_fernet_key = Fernet.generate_key().decode()
            logger.warning("Using auto-generated Fernet key — set FERNET_KEY for persistent token encryption")
        key = _dev_fernet_key

    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_token(token: str) -> str:
    """Encrypt a token (e.g., OAuth access token) for storage"""
    fernet = get_fernet()
    return fernet.encrypt(token.encode()).decode()


def decrypt_token(encrypted: str) -> str:
    """Decrypt a stored token"""
    fernet = get_fernet()
    return fernet.decrypt(encrypted.encode()).decode()
