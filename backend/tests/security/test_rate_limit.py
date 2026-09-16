"""Phase 49 — per-user / per-project LLM budgets (429 envelope, auth-first)."""

import uuid
from unittest.mock import patch

from app.core.config import get_settings
from app.core.rate_limit import reset_budgets
from app.schemas.rag import RagChunk, RagContext

from .helpers import login, make_project, setup, tag, teardown


def _shrink(user=None, project=None):
    s = get_settings()
    old = (s.rate_limit_llm_per_minute_user, s.rate_limit_llm_per_minute_project)
    if user is not None:
        s.rate_limit_llm_per_minute_user = user
    if project is not None:
        s.rate_limit_llm_per_minute_project = project
    return old


def _restore(old):
    s = get_settings()
    s.rate_limit_llm_per_minute_user, s.rate_limit_llm_per_minute_project = old
    reset_budgets()


def _ctx(pid):
    chunk = RagChunk(
        chunk_id=uuid.uuid4(), material_id=uuid.uuid4(), content="Slope content.",
        page_number=1, source_name="doc.pdf", chunk_index=0, score=0.05,
    )
    return RagContext(query="Q?", scope_project_id=uuid.UUID(pid),
                      chunks=[chunk], total_chars=14, truncated=False)


def _ask(client, pid, headers):
    with (
        patch("app.services.tutor_service.rag_service") as rag,
        patch("app.services.tutor_service.groq_client") as groq,
    ):
        rag.assemble_context.return_value = _ctx(pid)
        groq.chat_json.return_value = {"answer": "Slope is rise over run [1]."}
        return client.post(f"/api/v1/projects/{pid}/tutor/ask", json={"question": "Q?"}, headers=headers)


def test_user_budget_exhausts_to_429_envelope():
    client, engine = setup()
    old = _shrink(user=2)
    try:
        h = login(client, tag("sec-rl"))
        _, pid = make_project(client, h)
        assert _ask(client, pid, h).status_code == 200
        assert _ask(client, pid, h).status_code == 200
        resp = _ask(client, pid, h)
        assert resp.status_code == 429, resp.text
        err = resp.json()["error"]
        assert err["code"] == "rate_limited"
        assert "budget" in err["message"].lower()
    finally:
        _restore(old)
        teardown(engine)


def test_budgets_isolate_users_and_projects():
    client, engine = setup()
    old = _shrink(user=1, project=100)
    try:
        ha = login(client, tag("sec-rlA"))
        hb = login(client, tag("sec-rlB"))
        _, pid_a = make_project(client, ha, suffix="A")
        assert _ask(client, pid_a, ha).status_code == 200
        assert _ask(client, pid_a, ha).status_code == 429  # A's user bucket spent
        assert _ask(client, pid_a, hb).status_code in (401, 403, 404)  # B not owner: no leak, no consume
        _, pid_b = make_project(client, hb, suffix="B")
        assert _ask(client, pid_b, hb).status_code == 200  # B's own budget untouched
    finally:
        _restore(old)
        teardown(engine)


def test_project_budget_and_scope_independence():
    client, engine = setup()
    old = _shrink(user=100, project=1)
    try:
        h = login(client, tag("sec-rlP"))
        _, pid = make_project(client, h)
        assert _ask(client, pid, h).status_code == 200
        assert _ask(client, pid, h).status_code == 429  # project bucket spent
        # Other scopes are unaffected: quiz-generate passes the limiter,
        # then fails on the bogus concept (404) — proving per-scope buckets.
        resp = client.post(
            f"/api/v1/projects/{pid}/quizzes/generate",
            json={"concept_id": str(uuid.uuid4()), "num_questions": 5, "mode": "practice"},
            headers=h,
        )
        assert resp.status_code == 404, resp.text
    finally:
        _restore(old)
        teardown(engine)
