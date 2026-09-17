"""Phase 1 — AI usage tracking: metering, cost, never-break, no-PII (real PG)."""

import os
import uuid
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.models.ai_usage import AIUsage
from app.services import ai_usage_service
from app.services.ai import groq_client
from app.services.ai.pricing import estimate_cost_usd


def _engine():
    os.environ["DATABASE_URL"] = os.getenv(
        "DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5433/ai_study_companion"
    )
    get_settings.cache_clear()
    engine = create_engine(get_settings().database_url, pool_pre_ping=True, future=True)
    get_settings.cache_clear()
    return engine


def _provider_settings(model="mercury-2.5"):
    """Patch groq_client settings to a deterministic fake provider."""
    settings_patch = patch("app.services.ai.groq_client.get_settings")
    mock_settings = settings_patch.start()
    mock_settings.return_value.llm_provider = "groq"
    mock_settings.return_value.groq_api_key = "test-key"
    mock_settings.return_value.groq_model = model
    return settings_patch


class _FakeResp:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def _clean(engine, feature):
    Sess = sessionmaker(bind=engine)
    db = Sess()
    try:
        db.query(AIUsage).filter(AIUsage.feature == feature).delete()
        db.commit()
    finally:
        db.close()


def test_pricing_known_and_unknown_models():
    assert estimate_cost_usd("mercury-2.5", 1_000_000, 0) is not None
    assert estimate_cost_usd("openai/gpt-oss-20b", 1000, 500) is not None
    assert estimate_cost_usd("unknown-model-xyz", 1000, 500) is None
    assert estimate_cost_usd("mercury-2.5", None, 5) is None


def test_no_prompt_response_columns_by_design():
    cols = {c.name for c in AIUsage.__table__.columns}
    for forbidden in ("prompt", "response", "prompt_text", "response_text", "messages", "content"):
        assert forbidden not in cols, forbidden
    # Error detail is capped at type + http status — no free-text message column.
    assert "error_message" not in cols


def test_token_fallback_when_provider_omits_usage():
    patcher = _provider_settings()
    try:
        payload = {"choices": [{"message": {"content": '{"ok": true}'}}]}  # no usage block
        with patch("app.services.ai.groq_client.httpx.post", return_value=_FakeResp(payload)):
            with ai_usage_service.track_llm_call(
                user_id=None, project_id=None, feature="test_fallback_probe"
            ) as _:
                # Drain records manually: capture what chat_json recorded.
                captured = []
                token = groq_client._calls_in_scope.get()
                assert token is not None
                parsed = groq_client.chat_json("system text here", "user text here")
                assert parsed == {"ok": True}
                captured.extend(groq_client._calls_in_scope.get())
        assert len(captured) == 1
        rec = captured[0]
        assert rec.success is True
        assert rec.tokens_estimated is True
        assert rec.prompt_tokens and rec.prompt_tokens > 0
        assert rec.completion_tokens and rec.completion_tokens > 0
    finally:
        patcher.stop()


def test_track_writes_success_row_with_cost():
    engine = _engine()
    feature = f"test_success_{uuid.uuid4().hex[:8]}"
    Sess = sessionmaker(bind=engine)
    patcher = _provider_settings(model="mercury-2.5")
    try:
        payload = {
            "choices": [{"message": {"content": '{"ok": true}'}}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 50},
        }
        with (
            patch("app.services.ai.groq_client.httpx.post", return_value=_FakeResp(payload)),
            patch.object(ai_usage_service, "SessionLocal", Sess),
        ):
            with ai_usage_service.track_llm_call(
                user_id=None, project_id=None, feature=feature, meta={"unit": True}
            ):
                assert groq_client.chat_json("s", "u") == {"ok": True}
        db = Sess()
        try:
            row = db.query(AIUsage).filter(AIUsage.feature == feature).one()
            assert row.success is True
            assert row.provider == "groq"
            assert row.model == "mercury-2.5"
            assert row.prompt_tokens == 100
            assert row.completion_tokens == 50
            assert row.tokens_estimated is False
            assert row.cost_usd is not None and float(row.cost_usd) > 0
            assert row.meta == {"unit": True}
            assert row.error_type is None
        finally:
            db.close()
    finally:
        patcher.stop()
        _clean(engine, feature)
        engine.dispose()
        get_settings.cache_clear()


def test_track_writes_failure_row_without_cost():
    import httpx

    engine = _engine()
    feature = f"test_fail_{uuid.uuid4().hex[:8]}"
    Sess = sessionmaker(bind=engine)
    patcher = _provider_settings()
    try:
        with (
            patch(
                "app.services.ai.groq_client.httpx.post",
                side_effect=httpx.ConnectError("provider down"),
            ),
            patch.object(ai_usage_service, "SessionLocal", Sess),
        ):
            with ai_usage_service.track_llm_call(
                user_id=None, project_id=None, feature=feature
            ):
                try:
                    groq_client.chat_json("s", "u")
                except httpx.ConnectError:
                    pass
                else:
                    raise AssertionError("expected ConnectError")
        db = Sess()
        try:
            row = db.query(AIUsage).filter(AIUsage.feature == feature).one()
            assert row.success is False
            assert row.error_type == "ConnectError"
            assert row.cost_usd is None
        finally:
            db.close()
    finally:
        patcher.stop()
        _clean(engine, feature)
        engine.dispose()
        get_settings.cache_clear()


def test_tracking_never_breaks_caller_when_db_down():
    patcher = _provider_settings()
    try:
        payload = {"choices": [{"message": {"content": '{"ok": true}'}}]}
        with patch("app.services.ai.groq_client.httpx.post", return_value=_FakeResp(payload)):
            with patch.object(
                ai_usage_service, "SessionLocal", side_effect=RuntimeError("db down")
            ):
                # Must not raise even though persistence explodes.
                with ai_usage_service.track_llm_call(
                    user_id=None, project_id=None, feature="test_never_break"
                ):
                    assert groq_client.chat_json("s", "u") == {"ok": True}
    finally:
        patcher.stop()


def test_open_ended_fake_client_writes_no_rows():
    """Injected test fakes bypass chat_json → tracker records nothing."""
    import uuid as uuid_mod

    from app.core.security import hash_password
    from app.models.chunk import DocumentChunk
    from app.models.concept import Concept
    from app.models.material import Material
    from app.models.project import Project
    from app.models.space import Space
    from app.models.subtopic import Subtopic
    from app.models.topic import Topic
    from app.models.user import User
    from app.services.open_ended_assessment_service import grade_open_ended

    engine = _engine()
    Sess = sessionmaker(bind=engine)
    db = Sess()
    try:
        suffix = uuid_mod.uuid4().hex[:8]
        user = User(email=f"aiu-{suffix}@example.com", hashed_password=hash_password("x" * 12))
        db.add(user)
        db.flush()
        space = Space(user_id=user.id, name="S")
        db.add(space)
        db.flush()
        project = Project(space_id=space.id, name="P")
        db.add(project)
        db.flush()
        topic = Topic(project_id=project.id, title="T")
        db.add(topic)
        db.flush()
        sub = Subtopic(project_id=project.id, topic_id=topic.id, title="ST")
        db.add(sub)
        db.flush()
        concept = Concept(project_id=project.id, subtopic_id=sub.id, title="C", summary="Sum.")
        db.add(concept)
        db.flush()
        mat = Material(project_id=project.id, filename="d.pdf", storage_path="/tmp/d.pdf", status="ready")
        db.add(mat)
        db.flush()
        db.add(
            DocumentChunk(
                project_id=project.id, material_id=mat.id, concept_id=concept.id,
                chunk_index=0, content="Content here.", page_number=1, source_name="d.pdf",
            )
        )
        db.commit()
        pid, cid, uid = project.id, concept.id, user.id
    finally:
        db.close()

    def fake_client(system, user_prompt):
        return {"score": 90, "feedback": "Good.", "strengths": [], "missing_points": [], "suggestions": []}

    db2 = Sess()
    try:
        before = db2.query(AIUsage).filter(AIUsage.feature == "open_ended_grade").count()
        grade_open_ended(db2, project_id=pid, concept_id=cid, answer_text="An answer.", client=fake_client)
        after = db2.query(AIUsage).filter(AIUsage.feature == "open_ended_grade").count()
        assert after == before  # fake client → no provider call → no row
    finally:
        db2.close()
        # Cleanup domain rows + engine.
        db3 = Sess()
        try:
            db3.query(DocumentChunk).filter(DocumentChunk.project_id == pid).delete()
            db3.query(Material).filter(Material.project_id == pid).delete()
            db3.query(Concept).filter(Concept.project_id == pid).delete()
            db3.query(Subtopic).filter(Subtopic.project_id == pid).delete()
            db3.query(Topic).filter(Topic.project_id == pid).delete()
            db3.query(Project).filter(Project.id == pid).delete()
            db3.query(Space).filter(Space.user_id == uid).delete()
            db3.query(User).filter(User.id == uid).delete()
            db3.commit()
        finally:
            db3.close()
        engine.dispose()
        get_settings.cache_clear()
