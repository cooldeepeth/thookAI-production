"""
Media Routes for ThookAI

Handles file upload URLs and media asset management.
Uses Cloudflare R2 for storage with presigned URLs for direct uploads.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Optional

from auth_utils import get_current_user
from services.media_storage import (
    generate_upload_url,
    confirm_upload,
    get_user_assets,
    delete_asset,
    VALID_FILE_TYPES
)

router = APIRouter(prefix="/media", tags=["media"])


class UploadUrlRequest(BaseModel):
    file_type: str
    filename: str
    content_type: str


class ConfirmUploadRequest(BaseModel):
    storage_key: str
    file_type: str
    filename: str
    content_type: str
    file_size_bytes: int
    job_id: Optional[str] = None


@router.post("/upload-url")
async def get_upload_url(
    data: UploadUrlRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Get a presigned URL for direct file upload to R2.
    
    The client should:
    1. Call this endpoint to get the presigned URL
    2. PUT the file directly to the returned upload_url
    3. Call /media/confirm after successful upload
    
    No credits are deducted for uploads - only for processing.
    """
    result = generate_upload_url(
        user_id=current_user["user_id"],
        file_type=data.file_type,
        filename=data.filename,
        content_type=data.content_type
    )
    
    return {
        "success": True,
        **result
    }


@router.post("/confirm")
async def confirm_upload_endpoint(
    data: ConfirmUploadRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Confirm a completed upload and save the asset record.
    
    Call this after successfully uploading to the presigned URL.
    """
    asset = await confirm_upload(
        user_id=current_user["user_id"],
        storage_key=data.storage_key,
        file_type=data.file_type,
        filename=data.filename,
        content_type=data.content_type,
        file_size_bytes=data.file_size_bytes,
        job_id=data.job_id
    )
    
    return {
        "success": True,
        "media_id": asset["media_id"],
        "public_url": asset["public_url"],
        "asset": asset
    }


@router.get("/assets")
async def list_assets(
    file_type: Optional[str] = Query(None, description=f"Filter by type: {', '.join(VALID_FILE_TYPES)}"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user)
):
    """
    List the current user's media assets.
    """
    result = await get_user_assets(
        user_id=current_user["user_id"],
        file_type=file_type,
        limit=limit,
        offset=offset
    )
    
    return {
        "success": True,
        **result
    }


@router.delete("/assets/{media_id}")
async def delete_asset_endpoint(
    media_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a media asset.
    
    Only the owner can delete their assets.
    """
    await delete_asset(
        user_id=current_user["user_id"],
        media_id=media_id
    )
    
    return {
        "success": True,
        "message": "Asset deleted"
    }
