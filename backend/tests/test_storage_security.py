"""
tests/test_storage_security.py
=================================
Verifies app/core/storage_security.py's verify_order_capture_bucket_is_
private -- the startup check that catches an accidentally-public order-
capture photo bucket (see SECURITY_NOTES.md).

get_supabase is mocked at point of use (same convention as
tests/test_order_capture.py) -- no live Storage call.
"""
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.core.storage_security import verify_order_capture_bucket_is_private

pytestmark = pytest.mark.asyncio


def _mock_supabase_with_bucket(*, public: bool):
    supabase = AsyncMock()
    supabase.storage.get_bucket = AsyncMock(return_value=SimpleNamespace(public=public))
    return supabase


async def test_private_bucket_passes_silently():
    supabase = _mock_supabase_with_bucket(public=False)
    with patch("app.core.storage_security.get_supabase", return_value=supabase):
        await verify_order_capture_bucket_is_private()  # must not raise


async def test_public_bucket_in_non_production_logs_critical_but_does_not_raise():
    supabase = _mock_supabase_with_bucket(public=True)
    with patch("app.core.storage_security.get_supabase", return_value=supabase), \
         patch("app.core.storage_security.settings") as mock_settings, \
         patch("app.core.storage_security.log") as mock_log:
        mock_settings.ORDER_CAPTURE_STORAGE_BUCKET = "order-captures"
        mock_settings.ENVIRONMENT = "development"
        await verify_order_capture_bucket_is_private()  # must not raise
        assert mock_log.critical.called


async def test_public_bucket_in_production_raises_and_refuses_to_start():
    supabase = _mock_supabase_with_bucket(public=True)
    with patch("app.core.storage_security.get_supabase", return_value=supabase), \
         patch("app.core.storage_security.settings") as mock_settings, \
         patch("app.core.storage_security.log") as mock_log:
        mock_settings.ORDER_CAPTURE_STORAGE_BUCKET = "order-captures"
        mock_settings.ENVIRONMENT = "production"
        with pytest.raises(RuntimeError, match="public"):
            await verify_order_capture_bucket_is_private()
        assert mock_log.critical.called


async def test_missing_bucket_logs_warning_and_does_not_raise():
    """A fresh environment where nobody has created the bucket yet is a
    setup gap, not a security incident -- must not block startup."""
    supabase = AsyncMock()
    supabase.storage.get_bucket = AsyncMock(side_effect=Exception("bucket not found"))
    with patch("app.core.storage_security.get_supabase", return_value=supabase), \
         patch("app.core.storage_security.log") as mock_log:
        await verify_order_capture_bucket_is_private()  # must not raise
        assert mock_log.warning.called
        assert not mock_log.critical.called
