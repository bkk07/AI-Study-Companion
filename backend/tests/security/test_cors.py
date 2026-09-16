"""Phase 49 — CORS is restricted to documented frontend origins (no wildcard)."""

from app.core.config import get_settings

from .helpers import setup, teardown


def test_configured_origins_never_wildcard():
    client, engine = setup()
    try:
        origins = [o.strip() for o in get_settings().cors_origins.split(",") if o.strip()]
        assert origins, "CORS allow-list must not be empty (empty would invite a permissive fallback)"
        assert "*" not in origins
        assert all(o.startswith("http://") or o.startswith("https://") for o in origins)
    finally:
        teardown(engine)


def test_allowed_origin_echoed_disallowed_omitted():
    client, engine = setup()
    try:
        preflight = {
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        }
        resp = client.options("/api/v1/spaces", headers=preflight)
        assert resp.headers.get("access-control-allow-origin") == "http://localhost:5173"

        # Loopback twin: browsers treat 127.0.0.1 as a different origin than
        # localhost, so it must be allow-listed explicitly (regression: real
        # browsers got 400 "Disallowed CORS origin" here).
        resp = client.options(
            "/api/v1/spaces",
            headers={"Origin": "http://127.0.0.1:5173", "Access-Control-Request-Method": "GET"},
        )
        assert resp.headers.get("access-control-allow-origin") == "http://127.0.0.1:5173"

        resp = client.options(
            "/api/v1/spaces",
            headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "GET"},
        )
        assert "access-control-allow-origin" not in resp.headers

        # A real request from an unknown origin gets no ACAO header either
        # (middleware restricts; it does not redirect or error).
        resp = client.get("/api/v1/spaces", headers={"Origin": "https://evil.example"})
        assert "access-control-allow-origin" not in resp.headers
    finally:
        teardown(engine)
