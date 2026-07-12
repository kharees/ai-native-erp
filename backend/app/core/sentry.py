"""
app/core/sentry.py
====================
Sentry SDK was installed and configured (settings.SENTRY_DSN existed as a
setting) but sentry_sdk.init() was never called anywhere in the app (audit
#14) — no error was ever actually reported to Sentry despite the app
believing it had error tracking.

Split into its own function (rather than inline in main.py) specifically so
it's unit-testable without reloading the entire main module (which also
registers every router and all middleware — reloading it mid test-session
risks duplicate registration against the app instance every other test
already imported).
"""

import structlog

from app.core.config import settings

log = structlog.get_logger(__name__)


def init_sentry() -> bool:
    """
    Initializes the Sentry SDK if settings.SENTRY_DSN is configured.
    No-ops (and logs why) if it isn't — this dev environment's .env has no
    SENTRY_DSN set, so this path is exercised by unit test with a fake DSN
    (see tests/test_sentry_init.py), not verified against a live Sentry
    project.

    Returns True if Sentry was initialized, False otherwise.
    """
    if not settings.SENTRY_DSN:
        log.info("sentry_not_configured", detail="SENTRY_DSN unset — error tracking disabled")
        return False

    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.starlette import StarletteIntegration

    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
        release=settings.APP_VERSION,
        integrations=[StarletteIntegration(), FastApiIntegration()],
        # Sentry's default behavior auto-detects and enables an integration
        # for every installed package it recognizes — including a Langchain
        # integration, since langchain/langchain-openai are declared
        # dependencies here (for the AI provider work). Importing that
        # integration transitively imports `langsmith`, which is broken
        # under the Python version this is installed against (a stdlib
        # ForwardRef._evaluate() signature change breaks langsmith's
        # pydantic v1 compat shim — a real, pre-existing, unrelated
        # dependency incompatibility this surfaced). Only the two
        # integrations explicitly listed above are needed; disabling
        # auto-detection avoids importing anything else.
        auto_enabling_integrations=False,
        # Errors are always captured; traces are sampled to control volume/cost.
        traces_sample_rate=0.1 if settings.ENVIRONMENT == "production" else 1.0,
        send_default_pii=False,
    )
    log.info("sentry_initialized", environment=settings.ENVIRONMENT)
    return True
