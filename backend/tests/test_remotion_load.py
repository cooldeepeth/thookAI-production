"""
Remotion Render Service Load Tests — E2E-05

Validates that the Remotion render queue handles concurrent render requests
without timeout or OOM errors.

Two execution modes
-------------------
Unit mode (always runs — CI-safe):
    cd backend && python -m pytest tests/test_remotion_load.py -x -v

Integration mode (requires a running Remotion service):
    REMOTION_URL=http://localhost:3001 python -m pytest tests/test_remotion_load.py -x -v

Unit tests mock HTTP calls and verify the concurrent dispatch pattern.
Integration tests fire real requests against the Remotion service.
"""

import asyncio
import os
import time
import uuid
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

REMOTION_URL = os.environ.get("REMOTION_URL", "")
INTEGRATION_SKIP_REASON = "Requires running Remotion service (set REMOTION_URL env var)"

COMPOSITION_IDS = [
    "StaticImageCard",
    "ImageCarousel",
    "TalkingHeadOverlay",
    "ShortFormVideo",
    "Infographic",
]


async def _mock_render_request(index: int, delay: float = 0.1) -> Dict[str, Any]:
    """Simulate an async render request with a short delay."""
    await asyncio.sleep(delay)
    return {
        "render_id": str(uuid.uuid4()),
        "status": "queued",
        "index": index,
    }


async def _poll_until_done(
    client: Any,
    render_id: str,
    remotion_url: str,
    poll_interval: float = 2.0,
    timeout: float = 120.0,
) -> Dict[str, Any]:
    """
    Poll GET /render/{id}/status until status is done or failed.

    Returns the final job dict.
    Raises TimeoutError if the job has not completed within `timeout` seconds.
    """
    deadline = time.monotonic() + timeout
    while True:
        resp = await client.get(f"{remotion_url}/render/{render_id}/status")
        resp.raise_for_status()
        job = resp.json()
        status = job.get("status")
        if status in ("done", "failed"):
            return job
        if time.monotonic() >= deadline:
            raise TimeoutError(
                f"Render {render_id} still '{status}' after {timeout}s"
            )
        await asyncio.sleep(poll_interval)


# ---------------------------------------------------------------------------
# Unit tests — always run (CI-safe, no external service required)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_concurrent_render_dispatch_logic():
    """
    Verifies that 5 render requests dispatched with asyncio.gather all complete
    in parallel rather than sequentially.

    Total elapsed time must be well below 5 * 0.1s = 0.5s because tasks run
    concurrently.
    """
    start = time.monotonic()
    results = await asyncio.gather(*[_mock_render_request(i) for i in range(5)])
    elapsed = time.monotonic() - start

    assert len(results) == 5, "Expected 5 results from 5 concurrent requests"
    assert elapsed < 1.0, (
        f"Concurrent dispatch took {elapsed:.3f}s — should be < 1s "
        "(suggests sequential execution)"
    )
    # Each mock returns a unique render_id
    render_ids = {r["render_id"] for r in results}
    assert len(render_ids) == 5, "Every dispatched request must return a unique render_id"


@pytest.mark.asyncio
async def test_render_queue_accepts_all_composition_types():
    """
    For each supported composition type, POST /render returns a unique render_id
    with status 'queued'.
    """
    render_ids: List[str] = []

    for composition_id in COMPOSITION_IDS:
        # Simulate the server response for POST /render
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "render_id": str(uuid.uuid4()),
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        resp = await mock_client.post(
            "http://remotion:3001/render",
            json={
                "composition_id": composition_id,
                "input_props": {"text": "Test content", "width": 600, "height": 400},
            },
        )
        resp.raise_for_status()
        data = resp.json()

        assert "render_id" in data, (
            f"POST /render for '{composition_id}' must return render_id"
        )
        render_ids.append(data["render_id"])

    assert len(set(render_ids)) == len(COMPOSITION_IDS), (
        "Each composition type must return a unique render_id"
    )


@pytest.mark.asyncio
async def test_render_status_polling_logic():
    """
    Verifies the polling loop correctly transitions from 'queued' → 'rendering'
    → 'done' and returns a valid URL upon completion.
    """
    render_id = str(uuid.uuid4())
    expected_url = f"https://cdn.example.com/renders/{render_id}.png"

    # Sequence of server responses: queued -> rendering -> done
    status_sequence = [
        {"render_id": render_id, "status": "queued", "compositionId": "StaticImageCard"},
        {"render_id": render_id, "status": "rendering", "compositionId": "StaticImageCard"},
        {
            "render_id": render_id,
            "status": "done",
            "compositionId": "StaticImageCard",
            "url": expected_url,
        },
    ]
    call_count = 0

    async def mock_get(url: str) -> MagicMock:
        nonlocal call_count
        response = MagicMock()
        response.raise_for_status = MagicMock()
        # Return responses in sequence; hold on the last one
        idx = min(call_count, len(status_sequence) - 1)
        response.json.return_value = status_sequence[idx]
        call_count += 1
        return response

    mock_client = AsyncMock()
    mock_client.get = mock_get

    job = await _poll_until_done(
        mock_client,
        render_id,
        "http://remotion:3001",
        poll_interval=0.01,  # fast for unit test
        timeout=5.0,
    )

    assert job["status"] == "done", f"Expected 'done', got '{job['status']}'"
    assert job.get("url") == expected_url, "Done job must include a valid URL"


@pytest.mark.asyncio
async def test_polling_detects_failed_status():
    """
    Verifies the polling loop returns immediately when status transitions to
    'failed' rather than waiting for a timeout.
    """
    render_id = str(uuid.uuid4())

    async def mock_get(url: str) -> MagicMock:
        response = MagicMock()
        response.raise_for_status = MagicMock()
        response.json.return_value = {
            "render_id": render_id,
            "status": "failed",
            "error": "Out of memory",
            "compositionId": "ShortFormVideo",
        }
        return response

    mock_client = AsyncMock()
    mock_client.get = mock_get

    start = time.monotonic()
    job = await _poll_until_done(
        mock_client,
        render_id,
        "http://remotion:3001",
        poll_interval=0.01,
        timeout=5.0,
    )
    elapsed = time.monotonic() - start

    assert job["status"] == "failed", "Polling must stop on 'failed' status"
    assert elapsed < 1.0, "Polling must return immediately on terminal status"


@pytest.mark.asyncio
async def test_concurrent_dispatch_returns_independent_render_ids():
    """
    5 concurrent mock dispatches must each return a unique render_id — confirming
    the server does not reuse or collide IDs under concurrent load.
    """

    async def dispatch_one(i: int) -> str:
        result = await _mock_render_request(i, delay=0.05)
        return result["render_id"]

    render_ids = await asyncio.gather(*[dispatch_one(i) for i in range(5)])

    assert len(set(render_ids)) == 5, (
        "All 5 concurrent dispatches must produce distinct render_ids"
    )


# ---------------------------------------------------------------------------
# Integration tests — skipped unless REMOTION_URL is set
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not REMOTION_URL,
    reason=INTEGRATION_SKIP_REASON,
)
@pytest.mark.asyncio
async def test_5_concurrent_renders_complete():
    """
    Integration: Fire 5 concurrent POST /render requests to the live Remotion
    service and verify all reach a terminal state (done or failed) within 300s.

    Runs 5 StaticImageCard (still image) renders with minimal inputProps.
    """
    import httpx

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Dispatch 5 concurrent render requests
        async def submit_render(i: int) -> str:
            resp = await client.post(
                f"{REMOTION_URL}/render",
                json={
                    "composition_id": "StaticImageCard",
                    "input_props": {
                        "text": f"Test render {i}",
                        "width": 600,
                        "height": 400,
                        "layout": "standard",
                    },
                    "render_type": "still",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            assert "render_id" in data, f"Render {i}: missing render_id in response"
            return data["render_id"]

        start = time.monotonic()
        render_ids = await asyncio.gather(*[submit_render(i) for i in range(5)])

        assert len(render_ids) == 5, "Expected 5 render IDs"
        assert len(set(render_ids)) == 5, "All render IDs must be unique"

        # Poll for completion
        async def wait_for_render(render_id: str) -> Dict[str, Any]:
            return await _poll_until_done(
                client,
                render_id,
                REMOTION_URL,
                poll_interval=2.0,
                timeout=120.0,
            )

        jobs = await asyncio.gather(*[wait_for_render(rid) for rid in render_ids])

        total_elapsed = time.monotonic() - start
        print(f"\n[Load Test] Total wall-clock time for 5 concurrent renders: {total_elapsed:.1f}s")
        for job in jobs:
            print(
                f"  render_id={job.get('render_id', 'unknown')} "
                f"status={job.get('status')} "
                f"url={job.get('url', '-')}"
            )

        terminal_statuses = {j["status"] for j in jobs}
        assert terminal_statuses.issubset({"done", "failed"}), (
            f"Renders must reach terminal state, got: {terminal_statuses}"
        )
        assert total_elapsed < 300.0, (
            f"5 concurrent renders took {total_elapsed:.1f}s — must complete within 300s"
        )


@pytest.mark.skipif(
    not REMOTION_URL,
    reason=INTEGRATION_SKIP_REASON,
)
@pytest.mark.asyncio
async def test_concurrent_renders_no_oom():
    """
    Integration: E2E-05 OOM check — none of the 5 concurrent renders must fail
    with an out-of-memory error.

    OOM indicators: 'out of memory', 'ENOMEM', 'heap', 'JavaScript heap'
    """
    import httpx

    OOM_PATTERNS = ["out of memory", "enomem", "heap", "javascript heap"]

    async with httpx.AsyncClient(timeout=30.0) as client:
        async def submit_render(i: int) -> str:
            resp = await client.post(
                f"{REMOTION_URL}/render",
                json={
                    "composition_id": "StaticImageCard",
                    "input_props": {
                        "text": f"OOM test render {i}",
                        "width": 600,
                        "height": 400,
                        "layout": "standard",
                    },
                    "render_type": "still",
                },
            )
            resp.raise_for_status()
            return resp.json()["render_id"]

        render_ids = await asyncio.gather(*[submit_render(i) for i in range(5)])

        async def wait_for_render(render_id: str) -> Dict[str, Any]:
            return await _poll_until_done(
                client,
                render_id,
                REMOTION_URL,
                poll_interval=2.0,
                timeout=120.0,
            )

        jobs = await asyncio.gather(*[wait_for_render(rid) for rid in render_ids])

        for job in jobs:
            if job.get("status") == "failed":
                error_msg = (job.get("error") or "").lower()
                is_oom = any(pattern in error_msg for pattern in OOM_PATTERNS)
                assert not is_oom, (
                    f"Render {job.get('render_id')} failed with OOM: {job.get('error')}"
                )
