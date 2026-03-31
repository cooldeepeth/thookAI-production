from fastapi import APIRouter, HTTPException, Response, Request, Depends
from pydantic import BaseModel, EmailStr
from jose import jwt
from datetime import datetime, timezone, timedelta
from pymongo import WriteConcern
import uuid
from database import db
from auth_utils import hash_password, verify_password, get_current_user
from config import settings

router = APIRouter(prefix="/auth", tags=["auth"])

ALGORITHM = "HS256"


def _jwt_secret() -> str:
    """Return JWT secret, falling back to dev default when not configured."""
    return settings.security.jwt_secret_key or "thook-dev-secret"


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


def create_jwt_token(user_id: str, email: str) -> str:
    expire_days = settings.security.jwt_expire_days
    expire = datetime.now(timezone.utc) + timedelta(days=expire_days)
    return jwt.encode({"sub": user_id, "email": email, "exp": expire}, _jwt_secret(), algorithm=ALGORITHM)


def set_auth_cookie(response: Response, token: str):
    # Use secure=False and samesite=lax in development to allow cookies over HTTP
    is_dev = settings.app.is_development
    expire_days = settings.security.jwt_expire_days
    response.set_cookie(
        key="session_token", value=token,
        httponly=True,
        secure=not is_dev,
        samesite="lax" if is_dev else "none",
        max_age=expire_days * 24 * 3600, path="/"
    )


def safe_user(user: dict) -> dict:
    return {k: v for k, v in user.items() if k not in ("hashed_password", "_id")}


@router.post("/register")
async def register(data: RegisterRequest, response: Response):
    if await db.users.find_one({"email": data.email}, {"_id": 0}):
        raise HTTPException(status_code=400, detail="Email already registered")

    user_id = f"user_{uuid.uuid4().hex[:12]}"
    user = {
        "user_id": user_id, "email": data.email, "name": data.name,
        "picture": None, "auth_method": "email",
        "hashed_password": hash_password(data.password),
        "plan": "starter", "subscription_tier": "starter",
        "credits": 200, "credit_allowance": 0,
        "credits_last_refresh": datetime.now(timezone.utc),
        "credits_refreshed_at": datetime.now(timezone.utc),
        "onboarding_completed": False, "platforms_connected": [],
        "created_at": datetime.now(timezone.utc)
    }
    users_wmajority = db.users.with_options(write_concern=WriteConcern("majority"))
    await users_wmajority.insert_one(user)
    token = create_jwt_token(user_id, data.email)
    set_auth_cookie(response, token)
    return {**safe_user(user), "token": token}


@router.post("/login")
async def login(data: LoginRequest, response: Response):
    user = await db.users.find_one({"email": data.email}, {"_id": 0})
    if not user or user.get("auth_method") == "google":
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not verify_password(data.password, user.get("hashed_password", "")):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_jwt_token(user["user_id"], data.email)
    set_auth_cookie(response, token)
    return {**safe_user(user), "token": token}


@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    return safe_user(current_user)


@router.post("/logout")
async def logout(response: Response, request: Request):
    token = request.cookies.get("session_token")
    if token:
        await db.user_sessions.delete_one({"session_token": token})
    response.delete_cookie(key="session_token", path="/", samesite="none", secure=True)
    return {"message": "Logged out"}
