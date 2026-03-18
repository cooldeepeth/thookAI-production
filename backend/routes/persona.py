from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from database import db
from auth_utils import get_current_user

router = APIRouter(prefix="/persona", tags=["persona"])


class PersonaCardUpdate(BaseModel):
    card: Optional[Dict[str, Any]] = None


@router.get("/me")
async def get_my_persona(current_user: dict = Depends(get_current_user)):
    persona = await db.persona_engines.find_one({"user_id": current_user["user_id"]}, {"_id": 0})
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found. Complete onboarding first.")
    return persona


@router.put("/me")
async def update_my_persona(data: PersonaCardUpdate, current_user: dict = Depends(get_current_user)):
    update = {"updated_at": datetime.now(timezone.utc)}
    if data.card:
        update["card"] = data.card
    await db.persona_engines.update_one({"user_id": current_user["user_id"]}, {"$set": update})
    return {"message": "Persona updated successfully"}


@router.delete("/me")
async def reset_persona(current_user: dict = Depends(get_current_user)):
    await db.persona_engines.delete_one({"user_id": current_user["user_id"]})
    await db.users.update_one(
        {"user_id": current_user["user_id"]},
        {"$set": {"onboarding_completed": False}}
    )
    return {"message": "Persona reset. Complete onboarding to create a new one."}
