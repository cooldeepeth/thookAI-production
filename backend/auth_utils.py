from fastapi import HTTPException, Request
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timezone
import os

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'thook-dev-secret')
ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


async def get_current_user(request: Request):
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
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id:
            user = await db.users.find_one({"user_id": user_id}, {"_id": 0})
            if user:
                return user
    except JWTError:
        pass

    # Try Google OAuth session token - only if token looks like a session token (not JWT)
    # JWT tokens are much longer and have dots, session tokens are shorter
    if '.' not in token or len(token) < 100:  # Session tokens are typically shorter than JWT tokens
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

    # If we get here, neither JWT nor session token validation worked
    raise HTTPException(status_code=401, detail="Invalid or expired token")
