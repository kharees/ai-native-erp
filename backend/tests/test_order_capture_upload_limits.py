"""
tests/test_order_capture_upload_limits.py
=============================================
HTTP-level tests for the upload-hardening added to
app/api/v1/endpoints/order_capture.py's upload_order_photo:
  - oversized uploads rejected with 413 (Content-Length pre-check)
  - wrong/spoofed content type rejected with 415 (both the declared
    Content-Type header AND real magic-byte sniffing)
  - the 10/minute per-user rate limit returning 429 after the 10th request

Unlike tests/test_order_capture.py (which calls app.services.order_capture
directly), these go through the real HTTP endpoint via async_client, since
the validations under test live in the endpoint layer, not the service.
get_ai_provider/get_supabase are mocked exactly like test_order_capture.py
-- no live AI/Storage calls.
"""
import json
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.core.config import settings
from app.core.rate_limit import limiter

pytestmark = pytest.mark.asyncio

_UPLOAD_URL = "/api/v1/omnichannel-billing/order-capture/upload"

# Minimal-but-valid JPEG magic bytes (SOI + JFIF-ish marker), padded so it
# isn't a suspiciously tiny "empty file" -- the endpoint's own emptiness
# check is a separate, already-existing 400 case, not what these tests
# are about.
_VALID_JPEG_BYTES = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01" + b"\x00" * 200


def _mock_vision_provider():
    provider = AsyncMock()
    provider.complete = AsyncMock(return_value=json.dumps({"line_items": []}))
    return provider


async def test_oversized_upload_rejected_with_413(async_client: AsyncClient, auth_headers: dict, monkeypatch):
    monkeypatch.setattr(settings, "MAX_UPLOAD_BYTES", 50)  # smaller than _VALID_JPEG_BYTES
    limiter.reset()
    try:
        resp = await async_client.post(
            _UPLOAD_URL,
            headers=auth_headers,
            files={"file": ("photo.jpg", _VALID_JPEG_BYTES, "image/jpeg")},
        )
        assert resp.status_code == 413, resp.text
        body = resp.json()
        assert body["detail"]["error"] is True
        assert body["detail"]["type"] == "file_too_large"
    finally:
        limiter.reset()


async def test_wrong_declared_content_type_rejected_with_415(async_client: AsyncClient, auth_headers: dict):
    limiter.reset()
    try:
        resp = await async_client.post(
            _UPLOAD_URL,
            headers=auth_headers,
            files={"file": ("document.pdf", b"%PDF-1.4 not an image", "application/pdf")},
        )
        assert resp.status_code == 415, resp.text
        body = resp.json()
        assert body["detail"]["error"] is True
        assert body["detail"]["type"] == "unsupported_media_type"
    finally:
        limiter.reset()


async def test_spoofed_content_type_with_non_image_bytes_rejected_with_415(async_client: AsyncClient, auth_headers: dict):
    """The declared Content-Type header claims image/jpeg, but the actual
    bytes are plain text -- magic-byte sniffing must catch this even
    though the header alone would have passed."""
    limiter.reset()
    try:
        resp = await async_client.post(
            _UPLOAD_URL,
            headers=auth_headers,
            files={"file": ("photo.jpg", b"this is not actually a jpeg file at all", "image/jpeg")},
        )
        assert resp.status_code == 415, resp.text
        assert resp.json()["detail"]["type"] == "unsupported_media_type"
    finally:
        limiter.reset()


async def test_valid_jpeg_is_accepted(async_client: AsyncClient, auth_headers: dict):
    limiter.reset()
    try:
        with patch("app.services.order_capture.get_ai_provider", return_value=_mock_vision_provider()), \
             patch("app.services.order_capture.get_supabase") as mock_supabase:
            mock_supabase.return_value.storage.from_.return_value.upload = AsyncMock()
            resp = await async_client.post(
                _UPLOAD_URL,
                headers=auth_headers,
                files={"file": ("photo.jpg", _VALID_JPEG_BYTES, "image/jpeg")},
            )
        assert resp.status_code == 201, resp.text
    finally:
        limiter.reset()


async def test_11th_upload_within_a_minute_returns_429(async_client: AsyncClient, auth_headers: dict):
    limiter.reset()
    try:
        with patch("app.services.order_capture.get_ai_provider", return_value=_mock_vision_provider()), \
             patch("app.services.order_capture.get_supabase") as mock_supabase:
            mock_supabase.return_value.storage.from_.return_value.upload = AsyncMock()

            responses = [
                await async_client.post(
                    _UPLOAD_URL, headers=auth_headers,
                    files={"file": (f"photo-{i}.jpg", _VALID_JPEG_BYTES, "image/jpeg")},
                )
                for i in range(11)
            ]

        for resp in responses[:10]:
            assert resp.status_code == 201, resp.text

        assert responses[10].status_code == 429, responses[10].text
        body = responses[10].json()
        assert body["detail"]["type"] == "rate_limit_exceeded"
    finally:
        limiter.reset()
