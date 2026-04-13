"""
User uploads for content creation context (files + URLs).
"""

import asyncio
import logging
import mimetypes
import os
import re
import uuid
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from urllib.parse import urlparse

import boto3
import httpx
from botocore.config import Config
from botocore.exceptions import ClientError
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from auth_utils import get_current_user
from config import settings
from database import db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/uploads", tags=["uploads"])

MAX_BYTES = 100 * 1024 * 1024

CONTEXT_TO_MIMES = {
    "image": {"image/jpeg", "image/png", "image/gif", "image/webp"},
    "video": {"video/mp4", "video/quicktime", "video/webm"},
    "document": {"application/pdf", "text/plain"},
}

EXT_ALLOWED = {
    "image": {".jpg", ".jpeg", ".png", ".gif", ".webp"},
    "video": {".mp4", ".mov", ".webm"},
    "document": {".pdf", ".txt"},
}


def _r2_client():
    if not settings.r2.r2_access_key_id:
        return None
    if not all(
        [
            settings.r2.r2_account_id,
            settings.r2.r2_secret_access_key,
            settings.r2.r2_bucket_name,
            settings.r2.r2_public_url,
        ]
    ):
        return None
    try:
        endpoint_url = f"https://{settings.r2.r2_account_id}.r2.cloudflarestorage.com"
        return boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=settings.r2.r2_access_key_id,
            aws_secret_access_key=settings.r2.r2_secret_access_key,
            config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
            region_name="auto",
        )
    except Exception as e:
        logger.error("R2 client error: %s", e)
        return None


def _validate_context_mime(context_type: str, content_type: str, filename: str) -> None:
    ct = (content_type or "").split(";")[0].strip().lower()
    allowed = CONTEXT_TO_MIMES.get(context_type)
    if not allowed:
        raise HTTPException(status_code=400, detail="Invalid context_type")
    ext = Path(filename or "").suffix.lower()
    if ext in EXT_ALLOWED.get(context_type, set()):
        return
    if ct in allowed:
        return
    guessed, _ = mimetypes.guess_type(filename or "")
    if guessed and guessed.lower() in allowed:
        return
    raise HTTPException(status_code=400, detail=f"Invalid file type for context '{context_type}'")


class UrlUploadRequest(BaseModel):
    url: str = Field(min_length=10, max_length=2048, description="URL to upload content from")
    context_type: str = "link"


def _extract_title_and_text(html: str) -> tuple[str, str]:
    m = re.search(
        r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']*)["\']',
        html,
        re.I,
    )
    if m:
        title = unescape(m.group(1).strip())
    else:
        m2 = re.search(r"<title[^>]*>([^<]+)</title>", html, re.I)
        title = unescape(m2.group(1).strip()) if m2 else ""
    text = re.sub(r"(?is)<script[^>]*>.*?</script>", " ", html)
    text = re.sub(r"(?is)<style[^>]*>.*?</style>", " ", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()[:500]
    return title, text


@router.post("/media")
async def upload_media(
    file: UploadFile = File(...),
    context_type: str = Form(...),
    current_user: dict = Depends(get_current_user),
):
    if context_type not in CONTEXT_TO_MIMES:
        raise HTTPException(status_code=400, detail="context_type must be image, video, or document")

    filename = file.filename or "upload"
    raw_ct = file.content_type or ""
    _validate_context_mime(context_type, raw_ct, filename)

    upload_id = f"upl_{uuid.uuid4().hex[:16]}"
    user_id = current_user["user_id"]
    size = 0
    chunks = []
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        size += len(chunk)
        if size > MAX_BYTES:
            raise HTTPException(status_code=400, detail="File too large (max 100MB)")
        chunks.append(chunk)
    data = b"".join(chunks)
    content_type = raw_ct.split(";")[0].strip() if raw_ct else (mimetypes.guess_type(filename)[0] or "application/octet-stream")

    client = _r2_client()
    if client:
        safe_name = "".join(c for c in filename if c.isalnum() or c in "._-")[:120] or "file"
        key = f"context/{user_id}/{upload_id}/{safe_name}"
        try:
            client.put_object(
                Bucket=settings.r2.r2_bucket_name,
                Key=key,
                Body=data,
                ContentType=content_type,
            )
            public_base = settings.r2.r2_public_url.rstrip("/")
            url = f"{public_base}/{key}"
        except ClientError as e:
            logger.error("R2 put_object failed: %s", e)
            raise HTTPException(status_code=500, detail="Upload failed")
    else:
        # R2 not configured — block uploads in production to prevent data loss
        if settings.app.is_production:
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "media_storage_unavailable",
                    "message": "Media storage is not configured. Contact support."
                }
            )
        # Dev mode: allow /tmp fallback with warning
        logger.warning(
            "R2 not configured — using /tmp fallback. Files will be lost on restart."
        )
        base = Path("/tmp/thookai_uploads") / user_id
        base.mkdir(parents=True, exist_ok=True)
        safe_name = "".join(c for c in filename if c.isalnum() or c in "._-")[:120] or "file"
        dest = base / f"{upload_id}_{safe_name}"
        dest.write_bytes(data)
        url = str(dest)

    now = datetime.now(timezone.utc)
    doc = {
        "upload_id": upload_id,
        "user_id": user_id,
        "filename": filename,
        "content_type": content_type,
        "context_type": context_type,
        "url": url,
        "size_bytes": len(data),
        "created_at": now,
    }
    await db.uploads.insert_one(doc)
    return {"upload_id": upload_id, "url": url, "content_type": content_type}


class PresignedUploadRequest(BaseModel):
    filename: str = Field(..., min_length=1, max_length=255)
    content_type: str = Field(..., min_length=1, max_length=100)
    context_type: str = Field(default="reference_image", min_length=1, max_length=50)


class ConfirmUploadRequest(BaseModel):
    upload_id: str = Field(..., min_length=1, max_length=64)


def generate_presigned_upload_url(user_id: str, filename: str, content_type: str) -> dict:
    """Generate a presigned PUT URL for direct browser upload to R2 (MDIA-08).

    Returns dict with upload_url, storage_key, public_url.
    Patchable by tests via routes.uploads.generate_presigned_upload_url.
    """
    client = _r2_client()
    if not client:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "media_storage_unavailable",
                "message": "R2 storage is not configured.",
            },
        )

    safe_name = "".join(c for c in filename if c.isalnum() or c in "._-")[:120] or "file"
    storage_key = f"{user_id}/uploads/{uuid.uuid4().hex[:16]}_{safe_name}"

    upload_url = client.generate_presigned_url(
        ClientMethod="put_object",
        Params={
            "Bucket": settings.r2.r2_bucket_name,
            "Key": storage_key,
            "ContentType": content_type,
        },
        ExpiresIn=3600,
    )

    public_base = settings.r2.r2_public_url.rstrip("/")
    public_url = f"{public_base}/{storage_key}"

    return {
        "upload_url": upload_url,
        "storage_key": storage_key,
        "public_url": public_url,
    }


@router.post("/upload-url")
async def request_upload_url(
    data: PresignedUploadRequest,
    current_user: dict = Depends(get_current_user),
):
    """MDIA-08: Generate a presigned R2 PUT URL for direct browser upload.

    The browser will PUT the file directly to the returned upload_url.
    After the browser PUT succeeds, client calls POST /uploads/confirm to
    finalize the upload record.
    """
    user_id = current_user["user_id"]

    presigned = generate_presigned_upload_url(
        user_id=user_id,
        filename=data.filename,
        content_type=data.content_type,
    )

    upload_id = f"upl_{uuid.uuid4().hex[:16]}"
    now = datetime.now(timezone.utc)

    doc = {
        "upload_id": upload_id,
        "user_id": user_id,
        "filename": data.filename,
        "content_type": data.content_type,
        "context_type": data.context_type,
        "storage_key": presigned["storage_key"],
        "url": presigned["public_url"],
        "status": "pending",
        "created_at": now,
    }
    await db.uploads.insert_one(doc)

    return {
        "upload_id": upload_id,
        "upload_url": presigned["upload_url"],
        "storage_key": presigned["storage_key"],
        "public_url": presigned["public_url"],
    }


@router.post("/confirm")
async def confirm_upload(
    data: ConfirmUploadRequest,
    current_user: dict = Depends(get_current_user),
):
    """MDIA-08: Confirm a presigned upload after the browser PUT completes.

    Marks the upload record as confirmed and returns its public URL.
    """
    upload = await db.uploads.find_one({
        "upload_id": data.upload_id,
        "user_id": current_user["user_id"],
    })
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")

    await db.uploads.update_one(
        {"upload_id": data.upload_id},
        {"$set": {"status": "confirmed", "confirmed_at": datetime.now(timezone.utc)}},
    )

    return {
        "upload_id": data.upload_id,
        "url": upload["url"],
        "status": "confirmed",
    }


@router.post("/url")
async def upload_url(data: UrlUploadRequest, current_user: dict = Depends(get_current_user)):
    if data.context_type != "link":
        raise HTTPException(status_code=400, detail="context_type must be 'link' for URL uploads")
    url_str = str(data.url)
    parsed = urlparse(url_str)
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(status_code=400, detail="Invalid URL")

    async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
        head_ok = False
        try:
            head = await client.head(url_str)
            head_ok = head.is_success
        except httpx.HTTPError:
            head_ok = False

        try:
            if head_ok:
                get_r = await client.get(url_str)
                get_r.raise_for_status()
            else:
                get_r = await client.get(url_str)
                if get_r.status_code >= 400:
                    raise HTTPException(status_code=400, detail="URL not reachable")
        except HTTPException:
            raise
        except httpx.HTTPError:
            raise HTTPException(status_code=400, detail="URL not reachable")

        html = get_r.text[:200_000]
    title, _ = _extract_title_and_text(html)
    upload_id = f"upl_{uuid.uuid4().hex[:16]}"
    now = datetime.now(timezone.utc)
    doc = {
        "upload_id": upload_id,
        "user_id": current_user["user_id"],
        "url": url_str,
        "title": title or url_str,
        "context_type": "link",
        "content_type": "link",
        "created_at": now,
    }
    await db.uploads.insert_one(doc)
    return {"upload_id": upload_id, "url": url_str, "title": doc["title"], "content_type": "link"}


@router.get("/{upload_id}")
async def get_upload(upload_id: str, current_user: dict = Depends(get_current_user)):
    doc = await db.uploads.find_one({"upload_id": upload_id}, {"_id": 0})
    if not doc or doc.get("user_id") != current_user["user_id"]:
        raise HTTPException(status_code=404, detail="Upload not found")
    return doc
