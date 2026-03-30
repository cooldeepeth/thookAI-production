import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends
from pydantic import BaseModel, EmailStr

from auth_utils import get_current_user
from database import db
from services.email_service import send_workspace_invite_email

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agency", tags=["agency"])

# Tiers that can create/manage workspaces
AGENCY_TIERS = ["studio", "agency", "custom"]


class CreateWorkspaceRequest(BaseModel):
    name: str
    description: Optional[str] = None


class InviteCreatorRequest(BaseModel):
    email: EmailStr
    role: str = "creator"  # creator, manager, admin


class UpdateCreatorRoleRequest(BaseModel):
    role: str  # creator, manager, admin


class WorkspaceMember(BaseModel):
    user_id: str
    email: str
    name: Optional[str] = None
    role: str
    joined_at: datetime
    status: str  # pending, active, inactive


async def check_agency_tier(user: dict):
    """Verify user has Studio+ tier for agency features."""
    tier = user.get("subscription_tier", "starter")
    # Custom plan users need team_members > 1 in their plan config
    if tier == "custom":
        plan_config = user.get("plan_config", {})
        features = plan_config.get("features", {})
        if features.get("team_members", 1) <= 1:
            raise HTTPException(
                status_code=403,
                detail="Your current plan doesn't include team features. Upgrade your plan to add team members."
            )
    elif tier not in AGENCY_TIERS:
        raise HTTPException(
            status_code=403,
            detail=f"Team features require a paid plan with team access. Current tier: {tier}"
        )
    return tier


async def check_workspace_access(workspace_id: str, user_id: str, required_roles: List[str] = None):
    """Check if user has access to workspace with optional role requirements."""
    workspace = await db.workspaces.find_one({"workspace_id": workspace_id})
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    
    # Check if user is owner
    if workspace["owner_id"] == user_id:
        return workspace, "owner"
    
    # Check if user is a member
    member = await db.workspace_members.find_one({
        "workspace_id": workspace_id,
        "user_id": user_id,
        "status": "active"
    })
    
    if not member:
        raise HTTPException(status_code=403, detail="Access denied to this workspace")
    
    if required_roles and member["role"] not in required_roles:
        raise HTTPException(status_code=403, detail=f"Requires role: {', '.join(required_roles)}")
    
    return workspace, member["role"]


# ============ WORKSPACE CRUD ============

@router.post("/workspace")
async def create_workspace(data: CreateWorkspaceRequest, current_user: dict = Depends(get_current_user)):
    """Create a new agency workspace. Requires Studio+ tier."""
    await check_agency_tier(current_user)
    
    # Check workspace limit based on tier
    tier = current_user.get("subscription_tier", "starter")
    existing_count = await db.workspaces.count_documents({"owner_id": current_user["user_id"]})

    if tier == "custom":
        plan_features = current_user.get("plan_config", {}).get("features", {})
        max_workspaces = min(plan_features.get("team_members", 1), 10)
    else:
        limits = {"studio": 3, "agency": 10}
        max_workspaces = limits.get(tier, 1)
    
    if existing_count >= max_workspaces:
        raise HTTPException(
            status_code=400,
            detail=f"Workspace limit reached ({max_workspaces} for {tier} tier)"
        )
    
    workspace_id = str(uuid.uuid4())
    workspace = {
        "workspace_id": workspace_id,
        "owner_id": current_user["user_id"],
        "name": data.name,
        "description": data.description,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "member_count": 1,
        "content_count": 0,
        "settings": {
            "allow_member_publish": False,
            "require_approval": True,
            "default_platforms": ["linkedin"]
        }
    }
    
    await db.workspaces.insert_one(workspace)
    
    return {
        "success": True,
        "workspace_id": workspace_id,
        "name": data.name,
        "message": "Workspace created successfully"
    }


@router.get("/workspaces")
async def list_my_workspaces(current_user: dict = Depends(get_current_user)):
    """List all workspaces the user owns or is a member of."""
    # Get owned workspaces
    owned = await db.workspaces.find(
        {"owner_id": current_user["user_id"]},
        {"_id": 0}
    ).to_list(100)
    
    # Get member workspaces
    memberships = await db.workspace_members.find(
        {"user_id": current_user["user_id"], "status": "active"},
        {"workspace_id": 1, "role": 1}
    ).to_list(100)
    
    member_workspace_ids = [m["workspace_id"] for m in memberships]
    member_workspaces = []
    
    if member_workspace_ids:
        member_workspaces = await db.workspaces.find(
            {"workspace_id": {"$in": member_workspace_ids}},
            {"_id": 0}
        ).to_list(100)
    
    # Add role info
    for ws in owned:
        ws["role"] = "owner"
    
    role_map = {m["workspace_id"]: m["role"] for m in memberships}
    for ws in member_workspaces:
        ws["role"] = role_map.get(ws["workspace_id"], "member")
    
    return {
        "success": True,
        "owned": owned,
        "member_of": member_workspaces,
        "total": len(owned) + len(member_workspaces)
    }


@router.get("/workspace/{workspace_id}")
async def get_workspace(workspace_id: str, current_user: dict = Depends(get_current_user)):
    """Get workspace details."""
    workspace, role = await check_workspace_access(workspace_id, current_user["user_id"])
    
    # Remove MongoDB _id
    workspace.pop("_id", None)
    workspace["user_role"] = role
    
    return {
        "success": True,
        "workspace": workspace
    }


@router.put("/workspace/{workspace_id}")
async def update_workspace(
    workspace_id: str,
    data: CreateWorkspaceRequest,
    current_user: dict = Depends(get_current_user)
):
    """Update workspace details. Owner or admin only."""
    await check_workspace_access(workspace_id, current_user["user_id"], ["owner", "admin"])
    
    await db.workspaces.update_one(
        {"workspace_id": workspace_id},
        {
            "$set": {
                "name": data.name,
                "description": data.description,
                "updated_at": datetime.now(timezone.utc)
            }
        }
    )
    
    return {"success": True, "message": "Workspace updated"}


@router.delete("/workspace/{workspace_id}")
async def delete_workspace(workspace_id: str, current_user: dict = Depends(get_current_user)):
    """Delete workspace. Owner only."""
    workspace = await db.workspaces.find_one({"workspace_id": workspace_id})
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    
    if workspace["owner_id"] != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="Only workspace owner can delete")
    
    # Delete workspace and all related data
    await db.workspaces.delete_one({"workspace_id": workspace_id})
    await db.workspace_members.delete_many({"workspace_id": workspace_id})
    await db.workspace_invites.delete_many({"workspace_id": workspace_id})
    
    return {"success": True, "message": "Workspace deleted"}


# ============ MEMBER MANAGEMENT ============

@router.post("/workspace/{workspace_id}/invite")
async def invite_creator(
    workspace_id: str,
    data: InviteCreatorRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """Invite a creator to the workspace."""
    workspace, role = await check_workspace_access(
        workspace_id, current_user["user_id"], ["owner", "admin", "manager"]
    )
    
    # Check member limit based on tier
    owner = await db.users.find_one({"user_id": workspace["owner_id"]})
    tier = owner.get("subscription_tier", "starter") if owner else "starter"

    if tier == "custom" and owner:
        plan_features = owner.get("plan_config", {}).get("features", {})
        max_members = plan_features.get("team_members", 1)
    else:
        limits = {"studio": 10, "agency": 50}
        max_members = limits.get(tier, 5)
    
    current_members = await db.workspace_members.count_documents({
        "workspace_id": workspace_id,
        "status": {"$in": ["active", "pending"]}
    })
    
    if current_members >= max_members:
        raise HTTPException(
            status_code=400,
            detail=f"Member limit reached ({max_members} for {tier} tier)"
        )
    
    # Check if already invited/member
    existing = await db.workspace_members.find_one({
        "workspace_id": workspace_id,
        "email": data.email.lower()
    })
    
    if existing:
        raise HTTPException(status_code=400, detail="User already invited or is a member")
    
    # Check if invitee has an account
    invitee = await db.users.find_one({"email": data.email.lower()})
    
    invite_id = str(uuid.uuid4())
    member_doc = {
        "invite_id": invite_id,
        "workspace_id": workspace_id,
        "email": data.email.lower(),
        "user_id": invitee["user_id"] if invitee else None,
        "name": invitee.get("name") if invitee else None,
        "role": data.role,
        "status": "pending",
        "invited_by": current_user["user_id"],
        "invited_at": datetime.now(timezone.utc),
        "joined_at": None
    }
    
    await db.workspace_members.insert_one(member_doc)

    # FIXED: send invite email in background to avoid blocking event loop
    try:
        background_tasks.add_task(
            send_workspace_invite_email,
            to_email=data.email.lower(),
            workspace_name=workspace["name"],
            invite_token=invite_id,
            inviter_name=current_user.get("name", "A team member"),
        )
    except Exception as email_err:
        logger.warning("Failed to queue invite email for %s: %s", data.email, email_err)

    return {
        "success": True,
        "invite_id": invite_id,
        "email": data.email,
        "status": "pending",
        "message": f"Invitation sent to {data.email}"
    }


@router.get("/workspace/{workspace_id}/members")
async def list_workspace_members(workspace_id: str, current_user: dict = Depends(get_current_user)):
    """List all members of a workspace."""
    await check_workspace_access(workspace_id, current_user["user_id"])
    
    # Get workspace owner
    workspace = await db.workspaces.find_one({"workspace_id": workspace_id})
    owner = await db.users.find_one({"user_id": workspace["owner_id"]})
    
    members = [{
        "user_id": owner["user_id"],
        "email": owner.get("email"),
        "name": owner.get("name"),
        "role": "owner",
        "status": "active",
        "joined_at": workspace["created_at"]
    }]
    
    # Get other members
    member_docs = await db.workspace_members.find(
        {"workspace_id": workspace_id},
        {"_id": 0}
    ).to_list(100)
    
    # Enrich with user data
    for m in member_docs:
        if m.get("user_id"):
            user = await db.users.find_one({"user_id": m["user_id"]})
            if user:
                m["name"] = user.get("name")
                m["picture"] = user.get("picture")
        members.append(m)
    
    return {
        "success": True,
        "members": members,
        "total": len(members)
    }


@router.put("/workspace/{workspace_id}/members/{member_user_id}/role")
async def update_member_role(
    workspace_id: str,
    member_user_id: str,
    data: UpdateCreatorRoleRequest,
    current_user: dict = Depends(get_current_user)
):
    """Update a member's role. Owner or admin only."""
    await check_workspace_access(workspace_id, current_user["user_id"], ["owner", "admin"])
    
    if data.role not in ["creator", "manager", "admin"]:
        raise HTTPException(status_code=400, detail="Invalid role")
    
    result = await db.workspace_members.update_one(
        {"workspace_id": workspace_id, "user_id": member_user_id},
        {"$set": {"role": data.role}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Member not found")
    
    return {"success": True, "message": f"Role updated to {data.role}"}


@router.delete("/workspace/{workspace_id}/members/{member_user_id}")
async def remove_member(
    workspace_id: str,
    member_user_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Remove a member from workspace. Owner, admin, or self-remove."""
    workspace, role = await check_workspace_access(workspace_id, current_user["user_id"])
    
    # Allow self-removal or admin removal
    if member_user_id != current_user["user_id"] and role not in ["owner", "admin"]:
        raise HTTPException(status_code=403, detail="Cannot remove other members")
    
    # Cannot remove owner
    workspace = await db.workspaces.find_one({"workspace_id": workspace_id})
    if workspace["owner_id"] == member_user_id:
        raise HTTPException(status_code=400, detail="Cannot remove workspace owner")
    
    result = await db.workspace_members.delete_one({
        "workspace_id": workspace_id,
        "user_id": member_user_id
    })
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Member not found")
    
    # Update member count
    await db.workspaces.update_one(
        {"workspace_id": workspace_id},
        {"$inc": {"member_count": -1}}
    )
    
    return {"success": True, "message": "Member removed"}


# ============ CREATOR MANAGEMENT ============

@router.get("/workspace/{workspace_id}/creators")
async def list_managed_creators(workspace_id: str, current_user: dict = Depends(get_current_user)):
    """List all creators in the workspace with their stats."""
    await check_workspace_access(workspace_id, current_user["user_id"])
    
    # Get all active members with creator role
    members = await db.workspace_members.find({
        "workspace_id": workspace_id,
        "status": "active",
        "user_id": {"$ne": None}
    }).to_list(100)
    
    creators = []
    for member in members:
        user_id = member["user_id"]
        
        # Get user info
        user = await db.users.find_one({"user_id": user_id})
        if not user:
            continue
        
        # Get persona info (safe data only, NO UOM)
        persona = await db.persona_engines.find_one({"user_id": user_id})
        persona_card = persona.get("card", {}) if persona else {}
        
        # Get content stats
        content_count = await db.content_jobs.count_documents({"user_id": user_id})
        last_content = await db.content_jobs.find_one(
            {"user_id": user_id},
            sort=[("created_at", -1)]
        )
        
        creators.append({
            "user_id": user_id,
            "name": user.get("name"),
            "email": user.get("email"),
            "picture": user.get("picture"),
            "role": member["role"],
            "joined_at": member.get("joined_at"),
            "persona": {
                "archetype": persona_card.get("personality_archetype"),
                "niche": persona_card.get("content_niche_signature"),
                "platforms": persona_card.get("focus_platforms", []),
                "has_persona": persona is not None
            },
            "stats": {
                "total_content": content_count,
                "last_content_date": last_content.get("created_at") if last_content else None
            }
        })
    
    return {
        "success": True,
        "creators": creators,
        "total": len(creators)
    }


@router.get("/workspace/{workspace_id}/content")
async def get_workspace_content(
    workspace_id: str,
    status: Optional[str] = None,
    platform: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: dict = Depends(get_current_user)
):
    """Get aggregated content from all workspace creators."""
    await check_workspace_access(workspace_id, current_user["user_id"])
    
    # Get all member user IDs
    members = await db.workspace_members.find({
        "workspace_id": workspace_id,
        "status": "active",
        "user_id": {"$ne": None}
    }).to_list(100)
    
    user_ids = [m["user_id"] for m in members]
    
    # Also include workspace owner
    workspace = await db.workspaces.find_one({"workspace_id": workspace_id})
    if workspace["owner_id"] not in user_ids:
        user_ids.append(workspace["owner_id"])
    
    # Build query
    query = {"user_id": {"$in": user_ids}}
    if status:
        query["status"] = status
    if platform:
        query["platform"] = platform
    
    # Get content
    content = await db.content_jobs.find(
        query,
        {"_id": 0}
    ).sort("created_at", -1).skip(offset).limit(limit).to_list(limit)
    
    total = await db.content_jobs.count_documents(query)
    
    # Enrich with creator info
    user_cache = {}
    for item in content:
        uid = item.get("user_id")
        if uid not in user_cache:
            user = await db.users.find_one({"user_id": uid})
            user_cache[uid] = {
                "name": user.get("name") if user else "Unknown",
                "picture": user.get("picture") if user else None
            }
        item["creator"] = user_cache[uid]
    
    return {
        "success": True,
        "content": content,
        "total": total,
        "limit": limit,
        "offset": offset
    }


# ============ INVITATIONS ============

@router.get("/invitations")
async def get_my_invitations(current_user: dict = Depends(get_current_user)):
    """Get pending workspace invitations for current user."""
    invites = await db.workspace_members.find({
        "email": current_user.get("email", "").lower(),
        "status": "pending"
    }).to_list(50)
    
    # Enrich with workspace info
    result = []
    for inv in invites:
        workspace = await db.workspaces.find_one({"workspace_id": inv["workspace_id"]})
        if workspace:
            inviter = await db.users.find_one({"user_id": inv["invited_by"]})
            result.append({
                "invite_id": inv["invite_id"],
                "workspace_id": inv["workspace_id"],
                "workspace_name": workspace["name"],
                "role": inv["role"],
                "invited_by": inviter.get("name") if inviter else "Unknown",
                "invited_at": inv["invited_at"]
            })
    
    return {
        "success": True,
        "invitations": result,
        "total": len(result)
    }


@router.post("/invitations/{invite_id}/accept")
async def accept_invitation(invite_id: str, current_user: dict = Depends(get_current_user)):
    """Accept a workspace invitation."""
    invite = await db.workspace_members.find_one({
        "invite_id": invite_id,
        "email": current_user.get("email", "").lower(),
        "status": "pending"
    })
    
    if not invite:
        raise HTTPException(status_code=404, detail="Invitation not found")
    
    # Update invitation to active
    await db.workspace_members.update_one(
        {"invite_id": invite_id},
        {
            "$set": {
                "status": "active",
                "user_id": current_user["user_id"],
                "name": current_user.get("name"),
                "joined_at": datetime.now(timezone.utc)
            }
        }
    )
    
    # Update workspace member count
    await db.workspaces.update_one(
        {"workspace_id": invite["workspace_id"]},
        {"$inc": {"member_count": 1}}
    )
    
    return {"success": True, "message": "Invitation accepted"}


@router.post("/invitations/{invite_id}/decline")
async def decline_invitation(invite_id: str, current_user: dict = Depends(get_current_user)):
    """Decline a workspace invitation."""
    result = await db.workspace_members.delete_one({
        "invite_id": invite_id,
        "email": current_user.get("email", "").lower(),
        "status": "pending"
    })
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Invitation not found")
    
    return {"success": True, "message": "Invitation declined"}
