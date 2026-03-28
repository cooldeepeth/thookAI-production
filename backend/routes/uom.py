from fastapi import APIRouter, Depends
from auth_utils import get_current_user

router = APIRouter(prefix="/uom", tags=["uom"])

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
        from fastapi import HTTPException
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
async def update_uom_fields(body: dict, user=Depends(get_current_user)):
    """
    Manually override specific UOM fields.
    Only certain fields are user-adjustable: risk_tolerance, focus_preference, content_velocity.
    Other fields are inferred and cannot be manually set.
    """
    from services.uom_service import update_uom
    from fastapi import HTTPException

    user_adjustable = {"risk_tolerance", "focus_preference", "content_velocity", "preferred_content_depth"}
    invalid_fields = set(body.keys()) - user_adjustable
    if invalid_fields:
        raise HTTPException(status_code=400, detail=f"Cannot manually set: {invalid_fields}. Only {user_adjustable} are adjustable.")

    updated = await update_uom(user["user_id"], body)
    return {"success": True, "uom": updated}
