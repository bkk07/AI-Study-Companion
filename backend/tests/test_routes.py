"""Route-table regression tests — no DB required.

Guards the public auth contract (POST /api/v1/auth/register) against
router-include/prefix regressions: if a router is dropped from app.main
or a prefix changes, these fail before anything reaches deployment.
"""

from app.main import app


def _routes() -> set[tuple[str, str]]:
    found: set[tuple[str, str]] = set()
    for r in app.routes:
        for method in getattr(r, "methods", []) or []:
            found.add((method, getattr(r, "path", "?")))
    return found


def test_auth_register_route_exists():
    assert ("POST", "/api/v1/auth/register") in _routes()


def test_auth_login_and_me_routes_exist():
    routes = _routes()
    assert ("POST", "/api/v1/auth/login") in routes
    assert ("GET", "/api/v1/auth/me") in routes


def test_health_route_exists():
    assert ("GET", "/api/v1/health") in _routes()
