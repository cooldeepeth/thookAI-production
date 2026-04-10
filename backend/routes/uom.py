from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from auth_utils import get_current_user

router = APIRouter(prefix="/uom", tags=["uom"])


class UomUpdateRequest(BaseModel):
    risk_tolerance: Optional[str] = None  # conservative | balanced | bold
    focus_preference: Optional[str] = None  # single-platform | multi-platform
    content_velocity: Optional[str] = None  # low | medium | high
    preferred_content_depth: Optional[str] = None  # shallow | balanced | deep


@router.get("/")
async def get_user_uom(user=Depends(get_current_user)):
    """Get the current user's UOM profile. Frontend uses this to adapt UI."""
    from services.uom_service import get_uom
    uom = await get_uom(user["user_id"])
    return {"success": True, "uom": uom}


@router.get("/directives/{agent_name}")
async def get_directives(agent_name: str, user=Depends(get_current_user)):
    """Get UOM directives for a specific agent. Debug/transparency endpoint."""
    from services.uom_service import get_agent_directives
    valid_agents = ["thinker", "writer", "qc", "commander", "analyst", "planner", "consigliere"]
    if agent_name not in valid_agents:
        raise HTTPException(status_code=400, detail=f"Invalid agent. Must be one of: {valid_agents}")
    directives = await get_agent_directives(user["user_id"], agent_name)
    return {"success": True, "agent": agent_name, "directives": directives}


@router.post("/refresh")
async def refresh_uom(user=Depends(get_current_user)):
    """Trigger a full UOM refresh from behavioral data."""
    from services.uom_service import run_periodic_uom_update
    updated_uom = await run_periodic_uom_update(user["user_id"])
    return {"success": True, "uom": updated_uom, "message": "UOM refreshed from behavioral data"}


@router.patch("/")
async def update_uom_fields(body: UomUpdateRequest, user=Depends(get_current_user)):
    """
    Manually override specific UOM fields.
    Only certain fields are user-adjustable: risk_tolerance, focus_preference, content_velocity.
    Other fields are inferred and cannot be manually set.
    """
    from services.uom_service import update_uom

    VALID_VALUES = {
        "risk_tolerance": {"conservative", "balanced", "bold"},
        "focus_preference": {"single-platform", "multi-platform"},
        "content_velocity": {"low", "medium", "high"},
        "preferred_content_depth": {"shallow", "balanced", "deep"},
    }

    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    for field, value in updates.items():
        if field in VALID_VALUES and value not in VALID_VALUES[field]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid value for {field}: '{value}'. Must be one of: {', '.join(VALID_VALUES[field])}"
            )

    updated = await update_uom(user["user_id"], updates)
    return {"success": True, "uom": updated}
