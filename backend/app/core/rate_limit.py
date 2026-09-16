"""Per-user / per-project budgets for LLM-calling endpoints (Phase 49).

AI-cost protection: every request that can trigger a Groq call must first
pass `require_llm_budget(scope)`. Sliding-window counters live in memory —
honest for this architecture because compose runs a single uvicorn `api`
process (no `--workers`); horizontal scaling would need a shared store
(Redis) and is explicitly deferred.

Exhaustion raises 429, which Phase 48's handlers render as the standard
`{"error": {"code": "rate_limited", ...}}` envelope. Budgets are consumed on
entry (before validation/LLM), so malformed requests cannot be used to probe
the provider for free.
"""

import threading
import time
from collections import defaultdict, deque
from typing import Deque, Dict

from fastapi import Depends, HTTPException, Path, status

from app.core.config import get_settings
from app.dependencies.auth import get_current_user
from app.models.user import User

_BUDGET_EXHAUSTED_MESSAGE = "LLM request budget exhausted — retry shortly."

_lock = threading.Lock()
_BUCKETS: Dict[str, Deque[float]] = defaultdict(deque)


def reset_budgets() -> None:
    """Clear all counters. Tests only — never wired into a route."""
    with _lock:
        _BUCKETS.clear()


def _allow(key: str, limit: int, window_seconds: float, now: float) -> bool:
    bucket = _BUCKETS[key]
    while bucket and now - bucket[0] >= window_seconds:
        bucket.popleft()
    if len(bucket) >= limit:
        return False
    bucket.append(now)
    return True


def check_llm_budget(user_id: str, project_id: str, scope: str) -> None:
    """Consume one unit from the user's and the project's bucket for `scope`.

    Raises:
        HTTPException: 429 when either bucket is exhausted.
    """
    settings = get_settings()
    window = float(settings.rate_limit_window_seconds)
    now = time.monotonic()
    with _lock:
        user_ok = _allow(
            f"llm:{scope}:user:{user_id}",
            settings.rate_limit_llm_per_minute_user,
            window,
            now,
        )
        project_ok = _allow(
            f"llm:{scope}:project:{project_id}",
            settings.rate_limit_llm_per_minute_project,
            window,
            now,
        )
    if not (user_ok and project_ok):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=_BUDGET_EXHAUSTED_MESSAGE,
        )


def require_llm_budget(scope: str):
    """FastAPI dependency factory enforcing the budget for one LLM endpoint.

    Declare AFTER the ownership dependency so auth/isolation (404) is
    evaluated before any budget is consumed or disclosed.
    """

    def guard(
        user: User = Depends(get_current_user),
        project_id: str = Path(...),
    ) -> None:
        check_llm_budget(str(user.id), project_id, scope)

    return guard
