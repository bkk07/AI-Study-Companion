# Architecture Decisions — AI Study Companion

**Status:** Living log — updated per phase. Phase 01 baseline established 2026-09-15.
**Authority:** Blueprint v2 (`ai-study-companion-blueprint.md`) + Detailed Roadmap architecture freeze. No decision here may override either without an explicit ADR amendment.

---

## ADR-001 — Frozen Stack

**Decision:** Adopt the exact mandated stack from the architecture freeze.

- Frontend: React + Vite + TypeScript + Tailwind CSS + shadcn/ui + React Router + Axios
- Backend: Python + FastAPI + Pydantic + SQLAlchemy + Alembic
- DB: PostgreSQL + pgvector (`VECTOR(1536)` via `text-embedding-3-small`)
- Auth: JWT (HS256, 60 min) + Argon2id
- AI: Groq (generation/evaluation) + OpenAI Embeddings
- Documents: PyMuPDF (worker only)
- Background: Celery + Redis (broker + result backend)
- Runtime: Docker Compose with exactly 5 services — `api`, `worker`, `web`, `postgres`, `redis`

**Rationale:** Every later phase (migrations, RAG isolation, background jobs, frontend build) depends on these choices; substitution would break phase ordering.

**Consequences:** No LangChain/LangGraph/agent framework, no Kafka/RabbitMQ, no separate vector DB, no object storage in prototype, no microservices.

**Status:** Accepted (Phase 01).

---

## ADR-002 — Service Boundaries

**Decision:**
- Browser → FastAPI only (JWT bearer, `VITE_API_BASE_URL` → `localhost:8000` from host; containers use service names `postgres`/`redis` internally).
- FastAPI thin routes (Pydantic validation, `require_project_access`) → service layer (TutorService, RAGService, QuizService, MasteryService, ConfidenceService, MismatchService, RecommendationService, AssessmentService).
- Long-running work via Celery workers; Redis for broker + result state.
- Worker shares the same upload volume as API at `/data/uploads`.

**Rationale:** Keeps request handlers <3s (Tutor/quiz sync) while allowing 10s–2min PDF processing to survive browser close; preserves testable service layer.

**Status:** Accepted (Phase 01).

---

## ADR-003 — Data & Isolation Boundary

**Decision:**
- PostgreSQL is the single relational source of truth; pgvector lives inside it.
- `project_id` (via `user → space → project → material/concept/chunk/...` chain) is the isolation boundary for all study data. Every project-scoped table carries denormalized `project_id`; every query filters on it; `require_project_access` returns 404 (not 403) on ownership failure.
- `document_chunks.project_id` is denormalized so retrieval is one indexed `WHERE project_id = :authenticated` filter before ranking.
- `topics/subtopics/concepts` all carry `project_id` with the same dependency.

**Rationale:** Prevents cross-project leakage via IDs, list endpoints, background jobs, retrieval, and UI flows (tested per phase).

**Status:** Accepted (Phase 01).

---

## ADR-004 — Security Boundaries

**Decision:**
- Passwords: Argon2id only, centralized `hash_password`/`verify_password`.
- JWT: HS256, 60 min expiry, `JWT_SECRET` from env; no refresh rotation at prototype scope.
- File access: uploads in Docker volume outside web root, served only via authenticated, ownership-checked route; size-capped + content-sniffed MIME (not extension).
- RAG isolation: `project_id` filter inside pgvector query's `WHERE` before ranking.
- AI trust boundary: uploaded text and LLM output are untrusted; chunk text is delimited reference data, LLM output is validated via Pydantic before persistence; model never touches DB directly (no tool surface).
- Prompt-injection mitigation: Groq system prompt treats delimited chunk content as data, never instructions; PyMuPDF runs only in worker.
- CORS locked to frontend origin; rate-limit `auth/*` + `tutor/message`.

**Status:** Accepted (Phase 01).

---

## ADR-005 — Background Processing

**Decision:**
- Celery tasks: `process_pdf`, `extract_learning_structure` (full-document Groq structured output, one re-prompt on validation failure then `failed`), `generate_embeddings` (batch OpenAI), `evaluate_assessment` (open-ended + Explain-It-Back shared evaluator), `update_mastery` (runs mismatch check inline), `generate_recommendation`.
- Tutor messages + (usually) quiz generation are synchronous; everything else is Celery.
- `background_jobs` table is the user-facing status record (not Celery internals); `pending → running → succeeded|failed`; frontend polls `GET /projects/{id}/materials/{mid}/status` and `/jobs/{id}`.
- Idempotency: `process_pdf` guards `status != processing`; `generate_embeddings` deletes existing chunks per material before insert; `extract_learning_structure` skips if topics already exist for the material (stable concept IDs).

**Status:** Accepted (Phase 01). Deferred: concrete retry/backoff tuning validated in Celery phases.

---

## ADR-006 — AI Provider Wrappers

**Decision:** Thin `GroqClient` + `EmbeddingClient` wrappers, no orchestration layer. Typed Pydantic schemas (`ExplainBackEvaluation`, `TutorAnswer`, `LearningStructureExtraction` etc.) validate every LLM JSON response; one re-prompt on parse failure, then fallback to `failed`/`pending manual review` rather than guessing. Tutor `detected_concept_id` only when confident, else NULL; confidence never feeds mastery.

**Status:** Accepted (Phase 01).

---

## ADR-007 — Persistence & Migrations

**Decision:** SQLAlchemy declarative `Base` + `SessionLocal` + `get_db()` dependency; Base mixin `id (UUID) + created_at/updated_at`. Alembic owns all schema changes after Phase 09; `alembic upgrade head` must run cleanly on empty DB (no-op placeholder allowed before model phases).

**Status:** Accepted (Phase 01) — scaffolding deferred to Phases 08–09; this ADR records the commitment.

---

## ADR-008 — Excluded Technologies

**Decision:** Do not introduce: flashcards, concept dependency maps, study planner, spaced repetition, audio/video, collaboration, gamification, notifications, exam readiness score, live lecture features, LangChain/LangGraph, Kafka/RabbitMQ, microservices, separate vector DB, ad hoc Redis caching, S3 (volume→S3 swap is production note only).

**Status:** Accepted (Phase 01).

---

## ADR-009 — Decision Deferrals

**Decision:** Four behaviors remain intentionally open until their phases per the source roadmap:

1. Mastery formula (weights, recency, caps) — deferred to Mastery Engine phase(s).
2. Mismatch thresholds (`MISMATCH_GAP_THRESHOLD`, `MISMATCH_MIN_EVIDENCE`, confidence bands) — deferred to Mismatch phase.
3. Recommendation weights & scoring (`ACTION_BASE_VALUE`, bonuses/penalties) — deferred to Decision Engine phase.
4. Adaptive quiz selection (concept priority + difficulty policy, practice vs exam spread) — deferred to Adaptive Quiz phases.

Blueprint v2 provisional values are logged in `docs/00-blueprint-analysis.md §10` and are not considered finalized until the noted phase verifies them. No invention before then.

**Status:** Accepted (Phase 01).

---

## Log

| Date | Phase | Change |
|------|-------|--------|
| 2026-09-15 | 01 | Initial freeze: ADRs 001–009 accepted; no product code. |

---

*All subsequent ADRs must reference the phase and verification that introduced them, and must not silently override this freeze.*
