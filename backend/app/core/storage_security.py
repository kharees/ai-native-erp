"""
app/core/storage_security.py
===============================
Startup verification that the order-capture photo bucket
(settings.ORDER_CAPTURE_STORAGE_BUCKET) is NOT publicly readable.

Order-capture photos (app/services/order_capture.py) are real customer
order chits -- handwriting that may include names, phone numbers,
addresses. Supabase Storage buckets are private by default when created
correctly via the dashboard (Storage -> New bucket -> "Public bucket"
toggle left OFF -- see SECURITY_NOTES.md), but nothing in code enforces
that on its own. A bucket accidentally flipped to public in the
dashboard (or recreated later by someone unaware of this requirement)
would silently make every uploaded photo fetchable by anyone who guesses
or leaks an object path, no auth required -- this check catches that at
startup instead of relying on nobody ever making that mistake.
"""

import structlog

from app.core.config import settings
from app.core.database import get_supabase

log = structlog.get_logger(__name__)


async def verify_order_capture_bucket_is_private() -> None:
    """Call once during application startup, after init_db() (needs the
    Supabase client to already be initialised -- see main.py's lifespan).

    - Bucket is public: logs CRITICAL always; additionally *raises*
      (refusing to start) when settings.ENVIRONMENT == "production" --
      a public bucket of real customer data is a production incident, not
      a warning. Non-production environments only log, so a misconfigured
      local/staging bucket doesn't block day-to-day development, but is
      never silent either.
    - Bucket doesn't exist yet: logs a WARNING, not a CRITICAL, and
      returns -- a fresh environment before anyone has created the bucket
      in the Supabase dashboard is a setup gap, not a security incident.
      (upload_and_parse will itself fail loudly the moment something
      actually tries to upload to a nonexistent bucket.)
    - Bucket is private: logs an INFO confirming the check ran and passed.
    """
    bucket_name = settings.ORDER_CAPTURE_STORAGE_BUCKET
    try:
        bucket = await get_supabase().storage.get_bucket(bucket_name)
    except Exception as exc:
        log.warning(
            "order_capture_bucket_check_skipped",
            bucket=bucket_name,
            detail=f"Could not verify the bucket (it may not exist yet): {exc}",
        )
        return

    if bucket.public:
        log.critical(
            "order_capture_bucket_is_public",
            bucket=bucket_name,
            detail=(
                f"Storage bucket '{bucket_name}' is PUBLIC -- uploaded customer "
                "order photos are readable by anyone who has (or guesses) the "
                "object path, no authentication required. Fix in the Supabase "
                f"dashboard: Storage -> {bucket_name} -> Edit bucket -> turn "
                "'Public bucket' OFF. See SECURITY_NOTES.md."
            ),
        )
        if settings.ENVIRONMENT == "production":
            raise RuntimeError(
                f"Refusing to start in production: Storage bucket '{bucket_name}' "
                "is public. See SECURITY_NOTES.md."
            )
    else:
        log.info("order_capture_bucket_verified_private", bucket=bucket_name)
