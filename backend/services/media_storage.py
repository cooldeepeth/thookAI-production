"""
Media Storage Service for ThookAI

Handles file uploads and storage using Cloudflare R2 (S3-compatible).
Provides presigned URLs for direct client uploads.
"""

import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from uuid import uuid4
from fastapi import HTTPException
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from database import db
from config import settings

logger = logging.getLogger(__name__)

# Valid file types for upload
VALID_FILE_TYPES = {"video", "audio", "image", "document"}

# Max file size per type (bytes)
MAX_FILE_SIZE = {
    "video": 500 * 1024 * 1024,   # 500MB
    "audio": 25 * 1024 * 1024,    # 25MB
    "image": 20 * 1024 * 1024,    # 20MB
    "document": 50 * 1024 * 1024, # 50MB
}

# MIME type validation by file type
ALLOWED_MIME_TYPES = {
    "video": ["video/mp4", "video/webm", "video/quicktime", "video/x-msvideo", "video/mpeg"],
    "audio": ["audio/mpeg", "audio/wav", "audio/x-wav", "audio/mp4", "audio/ogg", "audio/aac", "audio/flac", "audio/mp3"],
    "image": ["image/jpeg", "image/png", "image/webp", "image/gif", "image/heic"],
    "document": ["application/pdf", "text/plain", "application/msword", 
                 "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]
}


def get_r2_client():
    """
    Get a boto3 S3 client configured for Cloudflare R2.

    Raises:
        ValueError: If R2 credentials are present but invalid / client fails to initialise.

    Returns:
        boto3 S3 client, or None if R2 is not configured at all.
    """
    if not settings.r2.has_r2():
        logger.warning("R2 storage not configured. Media storage features unavailable.")
        return None

    try:
        endpoint_url = f"https://{settings.r2.r2_account_id}.r2.cloudflarestorage.com"

        client = boto3.client(
            's3',
            endpoint_url=endpoint_url,
            aws_access_key_id=settings.r2.r2_access_key_id,
            aws_secret_access_key=settings.r2.r2_secret_access_key,
            config=Config(
                signature_version='s3v4',
                s3={'addressing_style': 'path'}
            ),
            region_name='auto'
        )

        return client
    except Exception as e:
        logger.error(f"Failed to create R2 client: {e}")
        raise ValueError(
            f"R2 storage configuration error (check credentials, endpoint, bucket name): {e}"  # FIXED: more accurate error message
        )


def generate_upload_url(
    user_id: str,
    file_type: str,
    filename: str,
    content_type: str
) -> Dict[str, Any]:
    """
    Generate a presigned PUT URL for direct client upload to R2.
    
    Args:
        user_id: The user's ID
        file_type: One of "video", "audio", "image", "document"
        filename: Original filename
        content_type: MIME type of the file
        
    Returns:
        dict with upload_url, storage_key, expires_in
        
    Raises:
        HTTPException if R2 not configured or validation fails
    """
    # Validate file type
    if file_type not in VALID_FILE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Must be one of: {', '.join(VALID_FILE_TYPES)}"
        )
    
    # Validate content type
    if content_type not in ALLOWED_MIME_TYPES.get(file_type, []):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid content type '{content_type}' for file type '{file_type}'"
        )
    
    try:
        client = get_r2_client()
    except ValueError as e:
        logger.error(f"R2 client initialisation error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Media storage credentials are invalid. Please contact support."
        )

    if not client:
        raise HTTPException(
            status_code=503,
            detail="Media storage not configured. Please contact support."
        )

    # Generate unique storage key
    unique_id = str(uuid4())
    # Sanitize filename (keep only alphanumeric, dots, underscores, hyphens)
    safe_filename = "".join(c for c in filename if c.isalnum() or c in "._-")[:100]
    storage_key = f"{user_id}/{file_type}/{unique_id}/{safe_filename}"

    expires_in = 600  # 10 minutes

    try:
        upload_url = client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': settings.r2.r2_bucket_name,
                'Key': storage_key,
                'ContentType': content_type
            },
            ExpiresIn=expires_in,
            HttpMethod='PUT'
        )

        return {
            "upload_url": upload_url,
            "storage_key": storage_key,
            "expires_in": expires_in
        }
    except ClientError as e:
        logger.error(f"Failed to generate presigned URL: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to generate upload URL"
        )


def get_public_url(storage_key: str) -> str:
    """
    Get the public URL for a stored file.
    
    Args:
        storage_key: The storage key of the file
        
    Returns:
        Full public URL to the file
    """
    return f"{settings.r2.r2_public_url}/{storage_key}"


async def delete_media(storage_key: str) -> bool:
    """
    Delete a file from R2 storage.

    Args:
        storage_key: The storage key of the file to delete

    Returns:
        True if deleted successfully

    Raises:
        HTTPException: If R2 is not configured or the delete operation fails
        ValueError: If R2 credentials are invalid
    """
    try:
        client = get_r2_client()
    except ValueError as e:
        logger.error(f"R2 client initialisation error during delete: {e}")
        raise HTTPException(
            status_code=500,
            detail="Media storage credentials are invalid. Please contact support."
        )

    if not client:
        logger.warning("Cannot delete media - R2 not configured")
        raise HTTPException(
            status_code=503,
            detail="Media storage not configured. Cannot delete files."
        )

    try:
        client.delete_object(
            Bucket=settings.r2.r2_bucket_name,
            Key=storage_key
        )
        logger.info(f"Deleted media from R2: {storage_key}")
        return True
    except ClientError as e:
        logger.error(f"Failed to delete media from R2: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to delete media file from storage."
        )


async def confirm_upload(
    user_id: str,
    storage_key: str,
    file_type: str,
    filename: str,
    content_type: str,
    file_size_bytes: int,
    job_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Confirm a completed upload and save asset record to MongoDB.
    
    Args:
        user_id: The user's ID
        storage_key: The storage key returned from generate_upload_url
        file_type: Type of file
        filename: Original filename
        content_type: MIME type
        file_size_bytes: Size of uploaded file in bytes
        job_id: Optional content job ID to associate with this asset
        
    Returns:
        The saved media asset document (without _id)
    """
    # Validate storage_key ownership — prevent IDOR
    if not storage_key.startswith(f"{user_id}/"):
        raise ValueError(f"Storage key does not belong to user {user_id}")

    # Validate file_size_bytes against MAX_FILE_SIZE
    max_size = MAX_FILE_SIZE.get(file_type, MAX_FILE_SIZE.get("document", 10 * 1024 * 1024))
    if file_size_bytes > max_size:
        raise ValueError(f"File size {file_size_bytes} exceeds maximum {max_size} for {file_type}")

    media_id = str(uuid4())
    public_url = get_public_url(storage_key)

    asset = {
        "media_id": media_id,
        "user_id": user_id,
        "storage_key": storage_key,
        "public_url": public_url,
        "file_type": file_type,
        "filename": filename,
        "content_type": content_type,
        "file_size_bytes": file_size_bytes,
        "job_id": job_id,
        "created_at": datetime.now(timezone.utc),
        "status": "uploaded"
    }
    
    await db.media_assets.insert_one(asset)
    
    # Return without MongoDB _id
    asset.pop("_id", None)
    
    logger.info(f"Confirmed upload: media_id={media_id}, user={user_id}, file={filename}")
    
    return asset


def upload_bytes_to_r2(storage_key: str, data: bytes, content_type: str) -> str:
    """
    Upload raw bytes directly to R2 and return the public URL.

    Args:
        storage_key: The full key (path) in the bucket
        data: File bytes
        content_type: MIME type

    Returns:
        Public URL of the uploaded file

    Raises:
        HTTPException if R2 is not configured or upload fails
    """
    try:
        client = get_r2_client()
    except ValueError as e:
        logger.error(f"R2 client init error during direct upload: {e}")
        raise HTTPException(status_code=500, detail="Media storage credentials are invalid.")

    if not client:
        raise HTTPException(status_code=503, detail="Media storage not configured.")

    try:
        client.put_object(
            Bucket=settings.r2.r2_bucket_name,
            Key=storage_key,
            Body=data,
            ContentType=content_type,
        )
        return get_public_url(storage_key)
    except ClientError as e:
        logger.error(f"R2 put_object failed for {storage_key}: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload file to storage.")


async def get_user_assets(
    user_id: str,
    file_type: Optional[str] = None,
    limit: int = 20,
    offset: int = 0
) -> Dict[str, Any]:
    """
    Get a user's media assets.
    
    Args:
        user_id: The user's ID
        file_type: Optional filter by file type
        limit: Maximum number of results (max 100)
        offset: Number of results to skip
        
    Returns:
        dict with assets list and total count
    """
    query = {"user_id": user_id, "status": "uploaded"}
    
    if file_type and file_type in VALID_FILE_TYPES:
        query["file_type"] = file_type
    
    limit = min(limit, 100)
    
    assets = await db.media_assets.find(
        query,
        {"_id": 0}
    ).sort("created_at", -1).skip(offset).limit(limit).to_list(limit)
    
    total = await db.media_assets.count_documents(query)
    
    return {
        "assets": assets,
        "total": total,
        "limit": limit,
        "offset": offset
    }


async def delete_asset(user_id: str, media_id: str) -> bool:
    """
    Delete a media asset (both from R2 and MongoDB).
    
    Args:
        user_id: The user's ID (for ownership verification)
        media_id: The media asset ID
        
    Returns:
        True if deleted, raises HTTPException on error
    """
    # Find the asset
    asset = await db.media_assets.find_one({
        "media_id": media_id,
        "user_id": user_id
    })
    
    if not asset:
        raise HTTPException(status_code=404, detail="Media asset not found")
    
    # Delete from R2
    await delete_media(asset["storage_key"])
    
    # Delete from MongoDB
    await db.media_assets.delete_one({"media_id": media_id})
    
    logger.info(f"Deleted asset: media_id={media_id}, user={user_id}")
    
    return True
