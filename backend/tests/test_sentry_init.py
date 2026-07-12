"""
tests/test_sentry_init.py
============================
Sentry SDK was installed and configured (settings.SENTRY_DSN) but
sentry_sdk.init() was never called anywhere in the app (audit #14) — no
error was ever actually reported despite the app believing it had
tracking. app/core/sentry.py:init_sentry() (called from main.py) fixes
that; this tests init_sentry() in isolation rather than reloading the
entire main module (which also registers every router and all
middleware — reloading it mid test-session risks duplicate registration
against the app instance every other test already imported).

No live Sentry DSN is configured in this dev environment (.env has none),
so this can't be verified end-to-end against a real Sentry project — this
test uses a syntactically valid but fake DSN (Sentry's SDK validates DSN
format and constructs a real client without making any network call until
an event is actually captured).
"""

import sentry_sdk

from app.core.sentry import init_sentry


def test_init_sentry_returns_false_and_noops_without_dsn(monkeypatch):
    monkeypatch.setattr("app.core.sentry.settings.SENTRY_DSN", "")
    sentry_sdk.Hub.current.bind_client(None)

    result = init_sentry()

    assert result is False
    assert sentry_sdk.Hub.current.client is None


def test_init_sentry_initializes_client_when_dsn_set(monkeypatch):
    monkeypatch.setattr("app.core.sentry.settings.SENTRY_DSN", "https://fakekey@o0.ingest.sentry.io/0")
    sentry_sdk.Hub.current.bind_client(None)

    try:
        result = init_sentry()

        assert result is True
        client = sentry_sdk.Hub.current.client
        assert client is not None
        assert client.dsn == "https://fakekey@o0.ingest.sentry.io/0"
    finally:
        # Don't leak an initialized Sentry client into later tests.
        sentry_sdk.Hub.current.bind_client(None)
