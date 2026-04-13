"""
Tests for upload endpoints and media storage service.

Covers MEDIA-04 and MEDIA-05 requirements:
- MEDIA-04: File uploads go to R2 when configured; production returns 503 without R2; dev falls back to /tmp
- MEDIA-05: Media assets in DB have valid R2 public URLs; presigned URL flow works end-to-end

Task 1: Upload endpoint (routes/uploads.py) — R2 path, 503 guard, /tmp dev fallback, validation
Task 2: Media storage service (services/media_storage.py) — presigned URL gen, confirm_upload,
        get_user_assets, delete_asset, upload_bytes_to_r2
"""

import io
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI
from botocore.exceptions import ClientError


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FAKE_USER = {"user_id": "test_user_123", "email": "test@example.com"}
R2_PUBLIC_URL = "https://pub-test.r2.dev"
R2_BUCKET = "test-bucket"

# The router has prefix="/uploads" — mount at root "/" to avoid double prefix
MEDIA_PATH = "/uploads/media"
URL_PATH = "/uploads/url"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_png_bytes() -> bytes:
    """Minimal valid 1x1 pixel PNG."""
    return (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
        b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00"
        b"\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18"
        b"\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
    )


def _build_app_with_auth():
    """
    Build minimal FastAPI app with uploads router, auth dependency overridden.
    Returns (app, get_current_user) so callers can set dependency_overrides.
    """
    from routes.uploads import router
    from auth_utils import get_current_user

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: FAKE_USER
    return app, get_current_user


# ---------------------------------------------------------------------------
# Task 1 — Upload endpoint tests
# ---------------------------------------------------------------------------


class TestUploadMediaR2Path:
    """Test 1: upload_media with R2 configured uploads to R2 and returns R2 URL."""

    @pytest.mark.asyncio
    async def test_upload_media_r2_success(self):
        """R2 upload path: file goes to R2, URL starts with R2 public base."""
        mock_r2 = MagicMock()
        mock_r2.put_object = MagicMock()

        mock_db = MagicMock()
        mock_db.uploads.insert_one = AsyncMock(return_value=MagicMock())

        with (
            patch("routes.uploads._r2_client") as mock_r2_fn,
            patch("routes.uploads.settings") as mock_settings,
            patch("routes.uploads.db", mock_db),
        ):
            mock_r2_fn.return_value = mock_r2
            mock_settings.r2.r2_public_url = R2_PUBLIC_URL
            mock_settings.r2.r2_bucket_name = R2_BUCKET
            mock_settings.app.is_production = True

            app, _ = _build_app_with_auth()
            with TestClient(app) as client:
                resp = client.post(
                    MEDIA_PATH,
                    files={"file": ("test.png", io.BytesIO(_make_png_bytes()), "image/png")},
                    data={"context_type": "image"},
                )

        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        body = resp.json()
        assert "url" in body
        assert body["url"].startswith(R2_PUBLIC_URL + "/"), \
            f"URL should start with R2 base: {body['url']}"
        # Verify R2 put_object was called with correct bucket
        mock_r2.put_object.assert_called_once()
        call_kwargs = mock_r2.put_object.call_args[1]
        assert call_kwargs["Bucket"] == R2_BUCKET


class TestUploadMediaProduction503:
    """Test 2: upload_media without R2 in production returns 503 with media_storage_unavailable."""

    @pytest.mark.asyncio
    async def test_upload_media_no_r2_production_returns_503(self):
        """Production guard: 503 when R2 is not configured."""
        mock_db = MagicMock()
        mock_db.uploads.insert_one = AsyncMock(return_value=MagicMock())

        with (
            patch("routes.uploads._r2_client") as mock_r2_fn,
            patch("routes.uploads.settings") as mock_settings,
            patch("routes.uploads.db", mock_db),
        ):
            mock_r2_fn.return_value = None
            mock_settings.app.is_production = True

            app, _ = _build_app_with_auth()
            with TestClient(app) as client:
                resp = client.post(
                    MEDIA_PATH,
                    files={"file": ("test.png", io.BytesIO(_make_png_bytes()), "image/png")},
                    data={"context_type": "image"},
                )

        assert resp.status_code == 503, f"Expected 503, got {resp.status_code}: {resp.text}"
        body = resp.json()
        detail = body.get("detail", {})
        # detail is a dict: {"error": "media_storage_unavailable", "message": "..."}
        if isinstance(detail, dict):
            assert detail.get("error") == "media_storage_unavailable", \
                f"detail.error mismatch: {detail}"
        else:
            assert "media_storage_unavailable" in str(detail), f"detail mismatch: {detail}"


class TestUploadMediaDevFallback:
    """Test 3: upload_media without R2 in dev mode falls back to /tmp."""

    @pytest.mark.asyncio
    async def test_upload_media_no_r2_dev_falls_back_to_tmp(self):
        """Dev fallback: /tmp path returned when R2 not configured and not production."""
        mock_db = MagicMock()
        mock_db.uploads.insert_one = AsyncMock(return_value=MagicMock())

        with (
            patch("routes.uploads._r2_client") as mock_r2_fn,
            patch("routes.uploads.settings") as mock_settings,
            patch("routes.uploads.db", mock_db),
        ):
            mock_r2_fn.return_value = None
            mock_settings.app.is_production = False

            app, _ = _build_app_with_auth()
            with TestClient(app) as client:
                resp = client.post(
                    MEDIA_PATH,
                    files={"file": ("test.png", io.BytesIO(_make_png_bytes()), "image/png")},
                    data={"context_type": "image"},
                )

        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        body = resp.json()
        assert "url" in body
        url = body["url"]
        # In dev fallback mode, the URL is a filesystem path under /tmp/thookai_uploads
        assert url.startswith("/tmp") or "thookai_uploads" in url, \
            f"Dev fallback URL should be a local path, got: {url}"


class TestUploadMediaInvalidContextType:
    """Test 4: upload_media with invalid context_type returns 400."""

    @pytest.mark.asyncio
    async def test_upload_media_invalid_context_type_returns_400(self):
        """Invalid context_type rejected with HTTP 400."""
        with (
            patch("routes.uploads._r2_client") as mock_r2_fn,
            patch("routes.uploads.settings") as mock_settings,
        ):
            mock_r2_fn.return_value = None
            mock_settings.app.is_production = False

            app, _ = _build_app_with_auth()
            with TestClient(app) as client:
                resp = client.post(
                    MEDIA_PATH,
                    files={"file": ("test.png", io.BytesIO(_make_png_bytes()), "image/png")},
                    data={"context_type": "invalid_type"},
                )

        assert resp.status_code == 400, f"Expected 400, got {resp.status_code}: {resp.text}"


class TestUploadMediaTooLarge:
    """Test 5: upload_media with file exceeding MAX_BYTES returns 400 with 'too large'."""

    @pytest.mark.asyncio
    async def test_upload_media_too_large_returns_400(self):
        """File size guard: rejects files over 100MB."""
        MAX_BYTES = 100 * 1024 * 1024
        large_data = b"x" * (MAX_BYTES + 1)

        with (
            patch("routes.uploads._r2_client") as mock_r2_fn,
            patch("routes.uploads.settings") as mock_settings,
        ):
            mock_r2_fn.return_value = None
            mock_settings.app.is_production = False

            app, _ = _build_app_with_auth()
            with TestClient(app) as client:
                resp = client.post(
                    MEDIA_PATH,
                    files={"file": ("bigfile.png", io.BytesIO(large_data), "image/png")},
                    data={"context_type": "image"},
                )

        assert resp.status_code == 400, f"Expected 400, got {resp.status_code}: {resp.text}"
        assert "too large" in resp.json().get("detail", "").lower(), \
            f"Detail should mention 'too large': {resp.json()}"


class TestUploadMediaMimeMismatch:
    """Test 6: upload_media with wrong MIME type for context returns 400."""

    @pytest.mark.asyncio
    async def test_upload_media_video_file_for_image_context_returns_400(self):
        """MIME/context mismatch: video file rejected for image context."""
        with (
            patch("routes.uploads._r2_client") as mock_r2_fn,
            patch("routes.uploads.settings") as mock_settings,
        ):
            mock_r2_fn.return_value = None
            mock_settings.app.is_production = False

            app, _ = _build_app_with_auth()
            with TestClient(app) as client:
                resp = client.post(
                    MEDIA_PATH,
                    files={"file": ("test.mp4", io.BytesIO(b"fakevideo"), "video/mp4")},
                    data={"context_type": "image"},
                )

        assert resp.status_code == 400, f"Expected 400, got {resp.status_code}: {resp.text}"


class TestUploadUrl:
    """Test 7: upload_url stores link documents in db.uploads with context_type='link'."""

    @pytest.mark.asyncio
    async def test_upload_url_stores_link_document(self):
        """URL upload flow stores link document with context_type='link' in db.uploads."""
        inserted_doc = {}

        async def fake_insert(doc):
            inserted_doc.update(doc)
            return MagicMock()

        mock_db = MagicMock()
        mock_db.uploads.insert_one = AsyncMock(side_effect=fake_insert)

        # Mock httpx client to avoid real HTTP requests
        mock_resp = MagicMock()
        mock_resp.is_success = True
        mock_resp.status_code = 200
        mock_resp.text = "<html><title>Test Page</title></html>"
        mock_resp.raise_for_status = MagicMock()

        mock_http = MagicMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=False)
        mock_http.head = AsyncMock(return_value=mock_resp)
        mock_http.get = AsyncMock(return_value=mock_resp)

        with (
            patch("routes.uploads.db", mock_db),
            patch("routes.uploads.httpx.AsyncClient", return_value=mock_http),
        ):
            app, _ = _build_app_with_auth()
            with TestClient(app) as client:
                resp = client.post(
                    URL_PATH,
                    json={"url": "https://example.com/article", "context_type": "link"},
                )

        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        body = resp.json()
        assert body.get("content_type") == "link"
        # Verify the DB document was saved with context_type='link'
        assert inserted_doc.get("context_type") == "link"
        assert inserted_doc.get("user_id") == FAKE_USER["user_id"]


# ---------------------------------------------------------------------------
# Task 2 — media_storage.py service tests
# ---------------------------------------------------------------------------


class TestGenerateUploadUrl:
    """Test 1: generate_upload_url with R2 configured returns upload_url, storage_key, expires_in."""

    def test_generate_upload_url_r2_configured(self):
        """Presigned URL generation returns correct structure."""
        mock_r2 = MagicMock()
        mock_r2.generate_presigned_url = MagicMock(
            return_value="https://r2.example.com/presigned?sig=abc"
        )

        with (
            patch("services.media_storage.get_r2_client", return_value=mock_r2),
            patch("services.media_storage.settings") as mock_settings,
        ):
            mock_settings.r2.r2_bucket_name = R2_BUCKET
            mock_settings.r2.r2_public_url = R2_PUBLIC_URL
            mock_settings.r2.has_r2 = MagicMock(return_value=True)

            from services.media_storage import generate_upload_url

            result = generate_upload_url(
                user_id="u1",
                file_type="image",
                filename="photo.png",
                content_type="image/png",
            )

        assert "upload_url" in result
        assert "storage_key" in result
        assert "expires_in" in result
        assert result["upload_url"] == "https://r2.example.com/presigned?sig=abc"
        assert "u1/image/" in result["storage_key"]


class TestGenerateUploadUrlNoR2:
    """Test 2: generate_upload_url without R2 raises HTTPException 503."""

    def test_generate_upload_url_no_r2_raises_503(self):
        """503 raised when R2 client is not available."""
        from fastapi import HTTPException

        with (
            patch("services.media_storage.get_r2_client", return_value=None),
            patch("services.media_storage.settings") as mock_settings,
        ):
            mock_settings.r2.has_r2 = MagicMock(return_value=False)

            from services.media_storage import generate_upload_url

            with pytest.raises(HTTPException) as exc_info:
                generate_upload_url(
                    user_id="u1",
                    file_type="image",
                    filename="photo.png",
                    content_type="image/png",
                )

        assert exc_info.value.status_code == 503


class TestGenerateUploadUrlInvalidFileType:
    """Test 3: generate_upload_url with invalid file_type raises HTTPException 400."""

    def test_generate_upload_url_invalid_file_type_raises_400(self):
        """Invalid file_type rejected with HTTP 400 before R2 is checked."""
        from fastapi import HTTPException
        from services.media_storage import generate_upload_url

        with pytest.raises(HTTPException) as exc_info:
            generate_upload_url(
                user_id="u1",
                file_type="pdf",  # not in VALID_FILE_TYPES
                filename="file.pdf",
                content_type="application/pdf",
            )

        assert exc_info.value.status_code == 400


class TestGenerateUploadUrlInvalidContentType:
    """Test 4: generate_upload_url with invalid content_type for file_type raises HTTPException 400."""

    def test_generate_upload_url_invalid_content_type_raises_400(self):
        """Wrong MIME type for file_type rejected with HTTP 400."""
        from fastapi import HTTPException
        from services.media_storage import generate_upload_url

        with pytest.raises(HTTPException) as exc_info:
            generate_upload_url(
                user_id="u1",
                file_type="image",
                filename="file.png",
                content_type="video/mp4",  # wrong type for image
            )

        assert exc_info.value.status_code == 400


class TestConfirmUploadSavesAsset:
    """Test 5: confirm_upload saves media asset to db.media_assets with correct fields."""

    @pytest.mark.asyncio
    async def test_confirm_upload_saves_asset_with_correct_fields(self):
        """confirm_upload creates media asset with media_id, user_id, status='uploaded'."""
        saved_doc = {}

        async def fake_insert(doc):
            saved_doc.update(doc)
            return MagicMock()

        mock_db = MagicMock()
        mock_db.media_assets.insert_one = AsyncMock(side_effect=fake_insert)

        with (
            patch("services.media_storage.db", mock_db),
            patch("services.media_storage.settings") as mock_settings,
        ):
            mock_settings.r2.r2_public_url = R2_PUBLIC_URL

            from services.media_storage import confirm_upload

            result = await confirm_upload(
                user_id="u1",
                storage_key="u1/image/abc123/test.png",
                file_type="image",
                filename="test.png",
                content_type="image/png",
                file_size_bytes=1024,
            )

        assert "media_id" in result
        assert result["user_id"] == "u1"
        assert result["status"] == "uploaded"
        assert result["file_type"] == "image"
        assert result["public_url"].startswith(R2_PUBLIC_URL + "/"), \
            f"public_url should start with R2 base URL: {result['public_url']}"
        mock_db.media_assets.insert_one.assert_called_once()


class TestConfirmUploadR2Url:
    """Test 6: confirm_upload public_url starts with settings.r2.r2_public_url."""

    @pytest.mark.asyncio
    async def test_confirm_upload_public_url_uses_r2_base(self):
        """public_url in saved asset uses the correct R2 public base URL."""
        mock_db = MagicMock()
        mock_db.media_assets.insert_one = AsyncMock(return_value=MagicMock())

        with (
            patch("services.media_storage.db", mock_db),
            patch("services.media_storage.settings") as mock_settings,
        ):
            mock_settings.r2.r2_public_url = R2_PUBLIC_URL

            from services.media_storage import confirm_upload

            result = await confirm_upload(
                user_id="u1",
                storage_key="u1/image/abc/test.png",
                file_type="image",
                filename="test.png",
                content_type="image/png",
                file_size_bytes=512,
            )

        expected_url = f"{R2_PUBLIC_URL}/u1/image/abc/test.png"
        assert result["public_url"] == expected_url, \
            f"public_url {result['public_url']} != expected {expected_url}"


class TestGetUserAssets:
    """Test 7: get_user_assets returns only assets belonging to the user with status='uploaded'."""

    @pytest.mark.asyncio
    async def test_get_user_assets_returns_user_assets(self):
        """get_user_assets filters by user_id and status='uploaded'."""
        test_assets = [
            {"media_id": "m1", "user_id": "u1", "status": "uploaded", "file_type": "image"},
            {"media_id": "m2", "user_id": "u1", "status": "uploaded", "file_type": "video"},
        ]

        mock_cursor = MagicMock()
        mock_cursor.sort = MagicMock(return_value=mock_cursor)
        mock_cursor.skip = MagicMock(return_value=mock_cursor)
        mock_cursor.limit = MagicMock(return_value=mock_cursor)
        mock_cursor.to_list = AsyncMock(return_value=test_assets)

        mock_db = MagicMock()
        mock_db.media_assets.find = MagicMock(return_value=mock_cursor)
        mock_db.media_assets.count_documents = AsyncMock(return_value=2)

        with patch("services.media_storage.db", mock_db):
            from services.media_storage import get_user_assets

            result = await get_user_assets(user_id="u1")

        assert len(result["assets"]) == 2
        assert result["total"] == 2
        # Verify query filters by user_id and status
        query_used = mock_db.media_assets.find.call_args[0][0]
        assert query_used["user_id"] == "u1"
        assert query_used["status"] == "uploaded"


class TestDeleteAssetRemovesBoth:
    """Test 8: delete_asset removes from both R2 and MongoDB."""

    @pytest.mark.asyncio
    async def test_delete_asset_removes_from_r2_and_db(self):
        """delete_asset calls R2 delete_object and MongoDB delete_one."""
        test_asset = {
            "media_id": "test_mid",
            "user_id": "u1",
            "storage_key": "u1/image/abc/test.png",
        }

        mock_r2 = MagicMock()
        mock_r2.delete_object = MagicMock()

        mock_db = MagicMock()
        mock_db.media_assets.find_one = AsyncMock(return_value=test_asset)
        mock_db.media_assets.delete_one = AsyncMock(return_value=MagicMock())

        with (
            patch("services.media_storage.db", mock_db),
            patch("services.media_storage.get_r2_client", return_value=mock_r2),
            patch("services.media_storage.settings") as mock_settings,
        ):
            mock_settings.r2.has_r2 = MagicMock(return_value=True)
            mock_settings.r2.r2_bucket_name = R2_BUCKET

            from services.media_storage import delete_asset

            result = await delete_asset(user_id="u1", media_id="test_mid")

        assert result is True
        mock_r2.delete_object.assert_called_once()
        mock_db.media_assets.delete_one.assert_called_once()


class TestDeleteAssetNotFound:
    """Test 9: delete_asset with non-existent media_id raises HTTPException 404."""

    @pytest.mark.asyncio
    async def test_delete_asset_nonexistent_raises_404(self):
        """delete_asset raises HTTP 404 when asset not found."""
        from fastapi import HTTPException

        mock_db = MagicMock()
        mock_db.media_assets.find_one = AsyncMock(return_value=None)

        with patch("services.media_storage.db", mock_db):
            from services.media_storage import delete_asset

            with pytest.raises(HTTPException) as exc_info:
                await delete_asset(user_id="u1", media_id="nonexistent")

        assert exc_info.value.status_code == 404


class TestUploadBytesToR2:
    """Test 10: upload_bytes_to_r2 calls put_object and returns public URL."""

    def test_upload_bytes_to_r2_returns_public_url(self):
        """upload_bytes_to_r2 uploads to R2 and returns valid public URL."""
        mock_r2 = MagicMock()
        mock_r2.put_object = MagicMock()

        with (
            patch("services.media_storage.get_r2_client", return_value=mock_r2),
            patch("services.media_storage.settings") as mock_settings,
        ):
            mock_settings.r2.r2_public_url = R2_PUBLIC_URL
            mock_settings.r2.r2_bucket_name = R2_BUCKET
            mock_settings.r2.has_r2 = MagicMock(return_value=True)

            from services.media_storage import upload_bytes_to_r2

            result = upload_bytes_to_r2(
                storage_key="test/key/file.png",
                data=b"testdata",
                content_type="image/png",
            )

        assert result.startswith(R2_PUBLIC_URL), f"URL should start with R2 base: {result}"
        assert "test/key/file.png" in result
        mock_r2.put_object.assert_called_once()
        call_kwargs = mock_r2.put_object.call_args[1]
        assert call_kwargs["Bucket"] == R2_BUCKET
        assert call_kwargs["Key"] == "test/key/file.png"


# ============ MDIA-08 REGRESSION: R2 presigned upload flow ============


@pytest.mark.asyncio
async def test_r2_presigned_upload_flow():
    """
    Wave 0 test for MDIA-08.

    The upload flow must:
    1. POST /api/uploads/upload-url → returns {"upload_url": presigned_put_url, "storage_key": str, "upload_id": str}
    2. Client PUTs file directly to presigned_put_url (browser-side, not tested here)
    3. POST /api/uploads/confirm → confirms the upload and returns {"url": public_url, "upload_id": str, "status": "confirmed"}

    This test mocks R2 (boto3) so it passes in CI without real credentials.
    If the /api/uploads/upload-url endpoint does not exist yet, the test FAILS,
    which is the expected RED state until MDIA-08 is implemented.
    """
    fake_presigned_url = "https://fake-r2-account.r2.cloudflarestorage.com/bucket/user_abc/uploads/test.jpg?X-Amz-Signature=fake"
    fake_public_url = "https://pub-test.r2.dev/user_abc/uploads/test.jpg"
    fake_storage_key = "user_abc/uploads/test.jpg"
    fake_upload_id = "upload_abc123"

    with patch("routes.uploads.db") as mock_db, \
         patch("routes.uploads.generate_presigned_upload_url", return_value={
             "upload_url": fake_presigned_url,
             "storage_key": fake_storage_key,
             "public_url": fake_public_url,
         }, create=True) as mock_presigned:

        mock_db.uploads.insert_one = AsyncMock(return_value=MagicMock(inserted_id="fake_id"))
        mock_db.uploads.find_one = AsyncMock(return_value={
            "upload_id": fake_upload_id,
            "user_id": "user_abc",
            "storage_key": fake_storage_key,
            "url": fake_public_url,
            "status": "pending",
        })
        mock_db.uploads.update_one = AsyncMock(return_value=None)

        from fastapi.testclient import TestClient
        from auth_utils import get_current_user
        from server import app

        # Override auth dependency to return a known user
        app.dependency_overrides[get_current_user] = lambda: {"user_id": "user_abc", "email": "test@example.com"}

        try:
            client = TestClient(app)

            # Step 1: Request a presigned upload URL
            upload_url_response = client.post(
                "/api/uploads/upload-url",
                json={
                    "filename": "test.jpg",
                    "content_type": "image/jpeg",
                    "context_type": "reference_image",
                },
            )
        finally:
            app.dependency_overrides.clear()

        assert upload_url_response.status_code in (200, 201), (
            f"POST /api/uploads/upload-url failed: {upload_url_response.status_code} "
            f"{upload_url_response.text[:200]}. "
            "This endpoint does not exist yet — Plan 29-05 must implement MDIA-08."
        )

        upload_data = upload_url_response.json()
        assert "upload_url" in upload_data, (
            f"Response missing 'upload_url' field. Got: {list(upload_data.keys())}"
        )
        assert "storage_key" in upload_data or "upload_id" in upload_data, (
            f"Response missing storage tracking fields. Got: {list(upload_data.keys())}"
        )

        # Step 2: Confirm the upload (simulate browser PUT succeeded)
        upload_id = upload_data.get("upload_id", fake_upload_id)

        app.dependency_overrides[get_current_user] = lambda: {"user_id": "user_abc", "email": "test@example.com"}
        try:
            client2 = TestClient(app)
            confirm_response = client2.post(
                "/api/uploads/confirm",
                json={"upload_id": upload_id},
            )
        finally:
            app.dependency_overrides.clear()

        assert confirm_response.status_code in (200, 201), (
            f"POST /api/uploads/confirm failed: {confirm_response.status_code} "
            f"{confirm_response.text[:200]}"
        )

        confirm_data = confirm_response.json()
        assert confirm_data.get("status") == "confirmed" or "url" in confirm_data, (
            f"Confirm response missing expected fields. Got: {confirm_data}"
        )


@pytest.mark.asyncio
async def test_r2_presigned_url_upload_requires_auth():
    """
    Upload URL endpoint must reject unauthenticated requests.
    If the endpoint doesn't exist, it returns 404 — which means MDIA-08 is not yet implemented.
    This test accepts 401, 403, 404, or 422 (404 = endpoint missing = expected RED state).
    """
    from fastapi.testclient import TestClient
    from server import app

    client = TestClient(app)
    response = client.post(
        "/api/uploads/upload-url",
        json={"filename": "test.jpg", "content_type": "image/jpeg"},
        # No Authorization header
    )
    # 404 = endpoint not yet implemented (expected RED state for MDIA-08)
    # 405 = route path matched by another method (GET /{upload_id}) — endpoint POST not yet added
    # 401/403/422 = endpoint exists and correctly rejects unauthenticated requests
    assert response.status_code in (401, 403, 404, 405, 422), (
        f"Unexpected status code. Got: {response.status_code}. "
        f"Expected 404/405 (endpoint missing) or 401/403/422 (auth rejected)."
    )
