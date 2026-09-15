"""Phase 30 — retrieval isolation on real Postgres+pgvector (host 5433).

Deterministic one-hot 1536-dim vectors stand in for OpenAI embeddings
(`embed_one` is patched — no network). The cross-project test deliberately
stores the IDENTICAL vector in both projects: any fetch-all-then-filter
implementation would mix them, so passing proves the scope lives in SQL.
"""

import os
import uuid
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.db.session import get_db
from app.main import app
from app.models.chunk import DocumentChunk
from app.models.concept import Concept
from app.models.embedding import EMBEDDING_DIMS, Embedding
from app.models.material import Material
from app.models.subtopic import Subtopic
from app.models.topic import Topic
from app.services import retrieval_service

DIMS = EMBEDDING_DIMS


def _vec(hot: int) -> list[float]:
    v = [0.0] * DIMS
    v[hot] = 1.0
    return v


def _host_url() -> str:
    return os.getenv("DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5433/ai_study_companion")


def _setup():
    os.environ["DATABASE_URL"] = _host_url()
    get_settings.cache_clear()
    from app.core.config import get_settings as gs

    engine = create_engine(gs().database_url, pool_pre_ping=True, future=True)
    HostSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override():
        db = HostSessionLocal()
        try:
            yield db
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    app.dependency_overrides[get_db] = override
    return TestClient(app), engine


def _teardown(engine):
    app.dependency_overrides.clear()
    engine.dispose()
    get_settings.cache_clear()


def _register_login(client: TestClient, email: str) -> tuple[str, dict]:
    client.post("/api/v1/auth/register", json={"email": email, "password": "supersecret123"})
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": "supersecret123"})
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return token, {"Authorization": f"Bearer {token}"}


def _make_project(client: TestClient, headers: dict) -> uuid.UUID:
    resp = client.post("/api/v1/spaces", json={"name": "S"}, headers=headers)
    assert resp.status_code == 201, resp.text
    resp = client.post(f"/api/v1/spaces/{resp.json()['id']}/projects", json={"name": "P"}, headers=headers)
    assert resp.status_code == 201, resp.text
    return uuid.UUID(resp.json()["id"])


def _make_concept(engine, pid: uuid.UUID, title: str) -> uuid.UUID:
    Sess = sessionmaker(bind=engine)
    db = Sess()
    try:
        t = Topic(project_id=pid, title=f"t-{title}")
        db.add(t)
        db.flush()
        s = Subtopic(project_id=pid, topic_id=t.id, title=f"s-{title}")
        db.add(s)
        db.flush()
        c = Concept(project_id=pid, subtopic_id=s.id, title=title, summary=f"summary {title}")
        db.add(c)
        db.commit()
        db.refresh(c)
        return c.id
    finally:
        db.close()


def _seed_chunks(engine, pid: uuid.UUID, items: list[tuple[str, list[float], uuid.UUID | None]]) -> list[uuid.UUID]:
    """items: (text, vector, concept_id|None). Returns chunk ids in order."""
    Sess = sessionmaker(bind=engine)
    db = Sess()
    try:
        mat = Material(project_id=pid, filename="doc.pdf", storage_path="/tmp/doc.pdf", status="ready")
        db.add(mat)
        db.flush()
        ids = []
        for i, (text, vector, cid) in enumerate(items):
            chunk = DocumentChunk(
                project_id=pid,
                material_id=mat.id,
                concept_id=cid,
                chunk_index=i,
                content=text,
                page_number=i + 1,
                source_name="doc.pdf",
            )
            db.add(chunk)
            db.flush()
            db.add(Embedding(project_id=pid, material_id=mat.id, chunk_id=chunk.id, embedding=vector))
            ids.append(chunk.id)
        db.commit()
        return ids
    finally:
        db.close()


def _retrieve(engine, **kwargs):
    Sess = sessionmaker(bind=engine)
    db = Sess()
    try:
        return retrieval_service.retrieve(db, **kwargs)
    finally:
        db.close()


def _fresh_users():
    client, engine = _setup()
    suffix = uuid.uuid4().hex[:8]
    _, ha = _register_login(client, f"ret-a-{suffix}@example.com")
    _, hb = _register_login(client, f"ret-b-{suffix}@example.com")
    pa = _make_project(client, ha)
    pb = _make_project(client, hb)
    return client, engine, pa, pb


def test_cross_project_identical_vector_never_leaks():
    client, engine, pa, pb = _fresh_users()
    try:
        same = _vec(0)
        (ca,) = _seed_chunks(engine, pa, [("project A alpha content", same, None)])
        (cb,) = _seed_chunks(engine, pb, [("project B alpha content", same, None)])
        with patch("app.services.retrieval_service.embedding_client") as mc:
            mc.embed_one.return_value = _vec(0)
            ra = _retrieve(engine, project_id=pa, query="alpha")
            rb = _retrieve(engine, project_id=pb, query="alpha")
        assert [r.chunk_id for r in ra] == [ca]
        assert [r.chunk_id for r in rb] == [cb]
        assert all(r.score == 0.0 for r in ra + rb)
    finally:
        _teardown(engine)


def test_ranking_returns_nearest_first_with_citation_metadata():
    client, engine, pa, _ = _fresh_users()
    try:
        # Strictly ordered similarities vs the hot-1 query: 0.0 < ~0.006 < 1.0,
        # so the full ranking is deterministic (no distance ties).
        mid = [0.0, 0.9, 0.1] + [0.0] * (DIMS - 3)
        ids = _seed_chunks(
            engine,
            pa,
            [
                ("far content zero", _vec(0), None),
                ("near content one", _vec(1), None),
                ("mid content blended", mid, None),
            ],
        )
        with patch("app.services.retrieval_service.embedding_client") as mc:
            mc.embed_one.return_value = _vec(1)
            hits = _retrieve(engine, project_id=pa, query="one")
        assert [h.chunk_id for h in hits] == [ids[1], ids[2], ids[0]]
        assert hits[0].score == 0.0
        assert hits[0].content == "near content one"
        assert hits[0].page_number == 2
        assert hits[0].source_name == "doc.pdf"
        assert hits[0].chunk_index == 1
        assert isinstance(hits[0].material_id, uuid.UUID)
    finally:
        _teardown(engine)


def test_concept_scope_respected_and_foreign_concept_empty():
    client, engine, pa, pb = _fresh_users()
    try:
        c1 = _make_concept(engine, pa, "Slope")
        c2 = _make_concept(engine, pa, "Intercept")
        other = _make_concept(engine, pb, "Foreign")
        ids = _seed_chunks(
            engine,
            pa,
            [
                ("slope rise over run", _vec(0), c1),
                ("intercept crosses axis", _vec(1), c2),
                ("slope steepness grade", _vec(2), c1),
            ],
        )
        with patch("app.services.retrieval_service.embedding_client") as mc:
            # Query vector exactly matches the c2 chunk, but scope is c1:
            # nearest-in-scope must win over globally nearest.
            mc.embed_one.return_value = _vec(1)
            scoped = _retrieve(engine, project_id=pa, query="intercept", concept_id=c1)
            exact = _retrieve(engine, project_id=pa, query="intercept", concept_id=c2)
            foreign = _retrieve(engine, project_id=pa, query="intercept", concept_id=other)
            unscoped = _retrieve(engine, project_id=pa, query="intercept")
        assert {h.chunk_id for h in scoped} == {ids[0], ids[2]}
        assert [h.chunk_id for h in exact] == [ids[1]]
        assert foreign == []
        assert unscoped[0].chunk_id == ids[1]
    finally:
        _teardown(engine)


def test_top_k_honored_and_empty_project_returns_empty():
    client, engine, pa, _ = _fresh_users()
    try:
        _seed_chunks(
            engine,
            pa,
            [
                ("chunk zero words", _vec(0), None),
                ("chunk one words", _vec(1), None),
                ("chunk two words", _vec(2), None),
                ("chunk three words", _vec(3), None),
            ],
        )
        other_client_suffix = uuid.uuid4().hex[:8]
        _, hc = _register_login(client, f"ret-c-{other_client_suffix}@example.com")
        pc = _make_project(client, hc)
        with patch("app.services.retrieval_service.embedding_client") as mc:
            mc.embed_one.return_value = _vec(0)
            hits = _retrieve(engine, project_id=pa, query="words", top_k=2)
            empty = _retrieve(engine, project_id=pc, query="words")
        assert len(hits) == 2
        assert hits[0].score == 0.0
        assert empty == []
    finally:
        _teardown(engine)


def test_empty_scope_returns_empty_without_embedding_call():
    _, engine = _setup()
    try:
        with patch("app.services.retrieval_service.embedding_client") as mc:
            mc.embed_one.return_value = _vec(0)
            assert _retrieve(engine, project_id=uuid.uuid4(), query="anything") == []
            mc.embed_one.assert_not_called()
    finally:
        _teardown(engine)


def test_empty_query_raises_without_embedding_call():
    _, engine = _setup()
    try:
        with patch("app.services.retrieval_service.embedding_client") as mc:
            try:
                _retrieve(engine, project_id=uuid.uuid4(), query="   ")
            except ValueError:
                pass
            else:
                raise AssertionError("expected ValueError")
            mc.embed_one.assert_not_called()
    finally:
        _teardown(engine)
