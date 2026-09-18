# Project Architecture Analysis — AI Study Companion (Current Implementation)

> Generated 2026-09-18 by code inspection only. Code is the source of truth.
> Evidence paths are repo-relative unless prefixed with `C:\...`.
> Status labels: **Implemented** | **Partially implemented** | **Planned/TODO** | **Configuration-dependent** | **Unclear from code**.

---

## 1. Project Overview

**Project name:** AI Study Companion (`package.json` root: `figma-make-app`; `frontend/package.json`: `frontend-scaffold`; `backend/app/main.py`: `FastAPI(title="AI Study Companion API")`).

**Purpose:** Project-scoped learning partner. User creates Spaces → Projects (with a learning `goal`), uploads PDFs, gets a structured `Topic → Subtopic → Concept` knowledge map where `concept_id` is the unit of mastery, then studies via RAG-grounded tutor, adaptive MCQ quiz/exam, practice, open-ended grading, explain-it-back, and SM-2 flashcards. All learning signals append to `mastery_evidence`; deterministic services compute two-dimensional mastery (`mcq_mastery`/`applied_mastery`), mismatches, and a single Recommended Next Action. Evidence: `README.md:1-5`, `backend/app/services/mastery_service.py:1-60`, `backend/app/services/recommendation_service.py`, `backend/app/services/mismatch_service.py`.

**Main users:**

- Students (Spaces/Projects owners) — upload, chat, quiz, practice, review flashcards — `frontend/src/features/*`.
- Admins (`users.is_admin`) — read-only usage/health/evaluation dashboards — `backend/app/api/v1/admin.py`, `frontend/src/features/admin/*`.

**Main problems solved:**

- Unstructured PDFs → navigable knowledge map with page-grounded citations.
- Hallucinated tutoring → RAG with `WHERE project_id` isolation + cosine-distance support gate (`SUPPORTED_MAX_DISTANCE=0.5`, `backend/app/services/tutor_service.py:30`).
- Shallow MCQ-only mastery → two-stream mastery (MCQ vs applied) + mismatch detection (e.g. `mcq_high_applied_low`) + deterministic recommendations.

**Major features (implemented):**

- Auth (register/login/me, JWT + Argon2id) — `backend/app/api/v1/auth.py`.
- Spaces/Projects CRUD with ownership isolation — `backend/app/api/v1/spaces.py`, `projects.py`.
- PDF upload → hybrid extraction (PyMuPDF text + Tesseract OCR + tables + vision figures) → chunking → local embeddings → 2-pass LLM structure extraction — `backend/app/worker/tasks/{extraction,embeddings,structure}.py`.
- Tutor ask + multi-turn conversations + quiz-plan — `backend/app/api/v1/tutor.py`, `backend/app/services/tutor_service.py`, `tutor_conversation_service.py`.
- Quiz generate/attempt/answer/complete + adaptive selection + confidence 1–5 — `backend/app/api/v1/quizzes.py`, `quiz_generation_service.py`, `adaptive_quiz_service.py`, `quiz_attempt_service.py`.
- Open-ended generate/grade + explain-it-back — `backend/app/api/v1/assessment.py`, `open_ended_assessment_service.py`, `explain_it_back_service.py`.
- Flashcards deck-build/list/review (SM-2) — `backend/app/api/v1/flashcards.py`, `flashcard_service.py`.
- Dashboard (mastery + mismatches + recommendation accept/dismiss/refresh), growth replay, analytics/overview, knowledge tree/search/graph/concept-detail, practice recommendations, figures list/image, me streak/home, jobs polling, admin reads — `backend/app/api/v1/{dashboard,growth,analytics,knowledge,practice,figures,me,jobs,admin}.py`.
- AI usage metering + learning-events audit + per-minute LLM budgets — `backend/app/services/ai_usage_service.py`, `activity_service.py`, `backend/app/core/rate_limit.py`.

**Overall architecture style:** Monorepo with two independently runnable apps sharing only HTTP contracts (`README.md:63`). Thin FastAPI routers → service layer → SQLAlchemy/Postgres (+pgvector) + Celery/Redis workers; stateless API + stateful workers; React SPA (react-router) calling versioned REST (`/api/v1`). No microservices, no LangChain, no separate vector DB, no Kafka (explicitly out of scope per `README.md:145`, `docs/architecture-decisions.md` ADR-001/008).

---

## 2. Repository Structure

Simplified tree (meaningful entries only):

```text
AI Study Companion/
├── src/                          # Figma-Make prototype SPA (state-switch, mock data, NOT served in prod)
│   ├── App.tsx                   # view-switch router (login|spaces|projects|overview|...|admin)
│   ├── main.tsx, index.css, types.ts
│   ├── components/{Layout,CommandPalette,ui}.tsx
│   └── pages/{SpacesPage,ProjectsPage,AdminPage,auth/AuthPages,project/*.tsx}
├── frontend/                     # PRODUCT frontend (React 19 + Router 7 + Axios + Tailwind v3)
│   ├── Dockerfile                # node build → nginx SPA fallback
│   ├── vite.config.ts            # port 5175, @ → ./src
│   ├── tailwind.config.js, postcss.config.js
│   └── src/
│       ├── App.tsx               # BrowserRouter + AuthProvider + ProtectedRoute + AppShell outlet
│       ├── main.tsx, index.css
│       ├── context/AuthContext.tsx
│       ├── lib/{axios,api-error,auth-events,utils,estimate}.ts
│       ├── components/{AppShell,ProtectedRoute,KnowledgeGraph,ui,knowledge/*}.tsx
│       └── features/{landing,auth,spaces,projects,home,overview,tutor,quiz,practice,
│                      openended,flashcards,structure,progress,dashboard,analytics,admin}/
├── frontend-figmadesigned/       # Duplicate scaffold copy (has own .figma/, dist/, node_modules/)
├── backend/                      # PRODUCT backend (FastAPI + Celery + Alembic)
│   ├── Dockerfile                # python:3.11-slim + tesseract + redis + supervisor, bakes fastembed
│   ├── supervisord.conf          # demo single-container: redis + api + worker
│   ├── requirements.txt / pyproject.toml
│   ├── alembic.ini + alembic/versions/ (28 migrations)
│   ├── .env.example (95 lines, placeholders only)
│   ├── scripts/backfill_learning_events.py
│   ├── tests/ (67 test files) + tests/security/ + tests/integration/
│   └── app/
│       ├── main.py               # FastAPI app + CORS + 19 routers under /api/v1 + GET /
│       ├── core/{config,security,jwt,rate_limit,exceptions}.py
│       ├── db/{base,session}.py
│       ├── dependencies/{auth,authorization,admin}.py
│       ├── api/v1/{health,auth,spaces,projects,materials,me,jobs,structure,tutor,
│       │            quizzes,assessment,dashboard,growth,analytics,admin,practice,
│       │            knowledge,flashcards,figures}.py
│       ├── models/{user,space,project,material,background_job,chunk,embedding,topic,
│       │           subtopic,concept,concept_relationship,material_figure,quiz,quiz_attempt,
│       │           flashcard,mastery_evidence,learning_event,tutor_conversation,
│       │           recommendation,ai_usage,mismatch}.py
│       ├── schemas/{user,auth,token,space,project,material,background_job,structure,
│       │            structure_api,rag,quiz,tutor,assessment,flashcard,knowledge,dashboard,
│       │            practice,growth,analytics,home,figure,admin,errors}.py
│       ├── services/{activity,adaptive_quiz,analytics,chunking,confidence,dashboard,
│       │             document_extraction,explain_it_back,figure_persistence,flashcard,
│       │             growth,home,job,mastery,mastery_levels,mismatch,ocr,
│       │             open_ended_assessment,project,quiz_attempt,quiz_generation,rag,
│       │             recommendation,relationship,retrieval,rollup,space,storage,
│       │             structure_extraction,structure_persistence,tutor,tutor_conversation,
│       │             vision,ai_usage,ai/{groq_client,embedding_client,pricing}}.py
│       └── worker/{celery_app.py,tasks/{__init__,extraction,embeddings,structure,recommendations}.py}
├── docker-compose.yml            # 5 services: postgres, redis, api, worker, web
├── docker/postgres/init-pgvector.sql  # CREATE EXTENSION vector
├── docker/                       # (postgres init only observed)
├── docs/                         # blueprint, ADRs, status, storage, usage-tracking, architecture/
├── index.html                    # Figma shell (#root + /src/main.tsx)
├── vite.config.ts                # Root Figma dev server ($PORT||8443) + Figma plugins
├── package.json                  # Root Figma deps (react, recharts, tailwind v4)
├── railway.toml                  # forces DOCKERFILE backend/Dockerfile, healthcheck /api/v1/health
├── .mise.toml                    # node 22 + pnpm 10.34.3
├── opencode.json                 # model inception/mercury-2.5 (contains hardcoded apiKey — rotate)
├── ai-study-companion-blueprint.md / ai-study-companion-detailed-opencode-roadmap.md
├── Project_Requirements (1).pdf / DAA_Sort.pdf
└── README.md / CLAUDE.md / AGENTS.md
```

| Directory | Purpose | Important files | Responsibilities | Depends on |
|---|---|---|---|---|
| `src/` | Figma-Make UI prototype | `App.tsx`, `pages/project/*.tsx`, `components/Layout.tsx` | Mock-data screens for all views; no API calls | Nothing (broken imports: `context/AppContext`, `data/mockData` do not exist on disk) |
| `frontend/src/` | Product SPA | `App.tsx`, `context/AuthContext.tsx`, `lib/axios.ts`, `features/*` | Routing, auth state, API calls, study UX | `backend` HTTP `/api/v1` |
| `frontend-figmadesigned/` | Stale duplicate scaffold | own `src/`, `dist/`, `vite.config.ts` | Unclear — appears to be an exported copy; not referenced by compose/README | None observed |
| `backend/app/api/` | Thin HTTP layer | `v1/*.py` (19 routers) | Auth/project scoping, schema validation, error mapping | `services/*`, `dependencies/*` |
| `backend/app/services/` | Domain logic | `tutor_service.py`, `rag_service.py`, `mastery_service.py`, etc. | LLM, RAG, extraction, mastery math (all tested) | `models/*`, `ai/*`, `db/session` |
| `backend/app/models/` | SQLAlchemy tables | 21 files → 23 tables | Schema truth (Alembic mirrors) | `db/base.py` |
| `backend/app/worker/` | Async pipeline | `celery_app.py`, `tasks/*.py` | PDF → chunks → embeddings → structure → recommendation | Redis, Postgres, LLM/vision APIs |
| `backend/alembic/` | Migrations | 28 versions | Owns schema evolution | `DATABASE_URL` |
| `backend/tests/` | Tests | 67 files | Auth, isolation, pipeline, AI, mastery, admin | Test DB, mocks |
| `docker-compose.yml` + `docker/` | Local runtime | `docker-compose.yml`, `docker/postgres/init-pgvector.sql` | 5-service dev/prod-like stack | `backend/Dockerfile`, `frontend/Dockerfile` |
| `docs/` | Contracts/decisions | `architecture-decisions.md`, `implementation-status.md`, `usage-tracking.md`, `storage.md`, `architecture/` | Frozen stack, ADRs, phase log | Code (sometimes stale — see §24) |

---

## 3. Technology Stack

| Layer | Technology | Purpose | Evidence |
|---|---|---|---|
| Frontend (product) | React 19.2 + React Router 7.18 + Vite 8.3 + TypeScript ~6.0 + Tailwind v3.4 + Axios 1.20 | SPA, routing, API client | `frontend/package.json`, `frontend/src/App.tsx:1,46-68`, `frontend/src/lib/axios.ts`, `frontend/vite.config.ts`, `frontend/tailwind.config.js` |
| Frontend (prototype) | React 19 + Vite 8 + Tailwind v4 + recharts 3.10 | Figma-Make mock screens | `package.json:12-27`, `src/App.tsx`, `src/index.css`, `vite.config.ts` |
| UI kit | shadcn-style `ui.tsx` + lucide-react + framer-motion + KaTeX + react-markdown + recharts | Components, math, charts | `frontend/src/components/ui.tsx`, `frontend/src/features/tutor/TutorChat.tsx`, `frontend/src/features/analytics/*` |
| Backend | FastAPI + Uvicorn[standard] + Pydantic v2 + pydantic-settings | HTTP API, validation, settings | `backend/requirements.txt:1-4`, `backend/app/main.py`, `backend/app/core/config.py` |
| ORM/Migrations | SQLAlchemy 2.0 + Alembic 1.13 + psycopg[binary] | Models, sessions, schema evolution | `backend/app/db/base.py`, `backend/app/db/session.py`, `backend/alembic/versions/` (28 files), `backend/alembic.ini` |
| Database | PostgreSQL 16 + pgvector (`VECTOR(384)`) | Relational + vector search | `docker-compose.yml:2-19`, `docker/postgres/init-pgvector.sql`, `backend/app/models/embedding.py:12,39` |
| Authentication | Argon2id (argon2-cffi) + PyJWT HS256 | Password hashing + bearer tokens | `backend/app/core/security.py`, `backend/app/core/jwt.py`, `backend/requirements.txt:8-9` |
| AI/LLM | Groq (`openai/gpt-oss-20b`) or Inception (`mercury-2.5`) via OpenAI-compatible `chat/completions` JSON mode; NaraRouter (`stepfun-3.7-flash`) for vision | Tutor answers, quiz gen, open-ended grade, structure extraction, figure captioning | `backend/app/services/ai/groq_client.py:25-38,99-139`, `backend/app/services/vision_service.py`, `backend/app/core/config.py:30-64` |
| Embeddings | Local fastembed `BAAI/bge-small-en-v1.5`, 384 dims (no key, baked in image) | Chunk vectors | `backend/app/services/ai/embedding_client.py`, `backend/app/models/embedding.py:12`, `backend/Dockerfile:26` |
| Vector Search | pgvector `cosine_distance` with `WHERE project_id` (+ optional `concept_id`) | Retrieval | `backend/app/services/retrieval_service.py:38-82` |
| Document Processing | PyMuPDF (text/tables/figures) + pytesseract + Pillow (worker only) | Hybrid PDF extraction | `backend/app/services/document_extraction_service.py`, `backend/app/services/ocr_service.py`, `backend/requirements.txt:12-14`, `backend/Dockerfile:12-18` |
| Background Processing | Celery 5.4 + Redis 7 (+ supervisord demo bundle) | `process_pdf` → `generate_embeddings` → `build_structure` → `generate_recommendation` | `backend/app/worker/celery_app.py`, `backend/app/worker/tasks/*.py`, `backend/supervisord.conf`, `docker-compose.yml:21-119` |
| Storage | Filesystem shared volume `uploads:/data/uploads` (`UPLOAD_DIR`), PNG figure crops + thumbs | PDFs + figure images | `backend/app/services/storage_service.py`, `backend/app/services/figure_persistence_service.py`, `docker-compose.yml:71,113` |
| Deployment | Docker Compose (5 services); Railway single-container backend; nginx SPA for web | Dev/prod runtime | `docker-compose.yml`, `railway.toml`, `backend/Dockerfile`, `frontend/Dockerfile` |
| Testing | pytest + pytest-asyncio + anyio | 67 test files incl. `tests/security/` (6) + `tests/integration/` (1) | `backend/tests/`, `backend/pyproject.toml` (`testpaths=["tests"]`, `asyncio_mode=auto`) |
| Config/Toolchain | mise (node 22, pnpm 10.34.3), oxlint/oxfmt, tsc | Toolchain, lint, format | `.mise.toml`, `frontend/package.json:9`, `package.json:10` |

---

## 4. High-Level System Architecture

```text
User (browser)
  ↓ HTTPS / HTTP
Product SPA (frontend/: React Router, AuthContext, apiClient w/ JWT + 30s GET cache)
  ↓ REST JSON + Bearer JWT → http://localhost:8000/api/v1 (VITE_API_BASE_URL+VITE_API_V1_PREFIX)
FastAPI (backend/app/main.py: 19 routers, CORS allow-list, unified error envelope)
  ↓ Depends(get_current_user) → Depends(get_authorized_space/project) → require_llm_budget(scope)
Services (backend/app/services/*)
  ├── Postgres+pgvector (SQLAlchemy): app data + VECTOR(384) similarity
  ├── Celery+Redis: process_pdf / generate_embeddings / build_structure / generate_recommendation
  ├── LLM (Groq or Inception, JSON mode, Pydantic-validated) + pricing/metering
  ├── Local fastembed embeddings (no network)
  ├── NaraRouter vision (figure captioning) + Tesseract OCR fallback
  └── Filesystem volume /data/uploads (PDFs + figure PNGs)
```

Component communication:

- **SPA → API:** `frontend/src/lib/axios.ts:12-24` builds `baseURL`; request interceptor attaches `Authorization: Bearer <localStorage access_token>`; 401 (non-auth URLs) clears token + `notifyUnauthorized()` → `AuthContext` logout + SPA navigate to `/login` (no hard reload). 30 s in-memory GET cache, cleared on any mutation.
- **API → DB:** `backend/app/db/session.py`: singleton engine (`pool_pre_ping`), `SessionLocal`, `get_db()` yield/rollback/close. Workers use fresh `create_engine(DATABASE_URL)` per task (`backend/app/worker/tasks/__init__.py`).
- **API → Workers:** API creates `background_jobs` row (`job_service.py`) + `process_pdf.delay()` best-effort; extraction task chains `generate_embeddings` + `build_structure` jobs + `.delay()` best-effort (`backend/app/worker/tasks/extraction.py`). Broker-down leaves job `pending` but upload still succeeds (resilience).
- **Workers → LLM/vision/embeddings:** `chat_json` (Groq/Inception), `embedding_client.embed` (local), `vision_service` (NaraRouter, never raises — returns `None`).
- **API → storage:** `storage_service.save_pdf` validates (10 MB, `.pdf`, `%PDF` magic, content-type) → `UPLOAD_DIR/{project}/{uuid}.pdf`; figures via `FileResponse image/png` with path-containment check (`backend/app/api/v1/figures.py`).
- **Deployment:** Compose `postgres (5433:5432) + redis (6379) + api (:8000 uvicorn) + worker (celery) + web (:5173→:80 nginx)`; Railway runs `backend/Dockerfile` (supervisord: loopback redis + api + worker) with healthcheck `/api/v1/health`.

---

## 5. Frontend Architecture

### 5.1 Two frontends (do not confuse)

| | `src/` (root) | `frontend/src/` (product) |
|---|---|---|
| Router | State-switch `useApp().state.view` (`src/App.tsx:20-39`), union in `src/types.ts` | `react-router-dom@7` routes + `?tab=` project tabs (`frontend/src/App.tsx:46-68`, `ProjectDetailPage.tsx:21,41-43`) |
| Auth | Fake `setTimeout(1200)`, `password==='wrong'` error; no token | `AuthContext` (`token` in `localStorage:access_token`, hydrate `GET /auth/me`, auto-login after register) |
| API | None — `../data/mockData` (file missing on disk; imports broken) | `lib/axios.ts` centralized client, JWT interceptor, GET cache |
| Status | **Broken on disk** (missing `context/AppContext`, `data/mockData`, `types.ts` referenced but `src/types.ts` listing shows only root `types.ts`? — `SpacesPage.tsx:3`, `Layout.tsx:8` fail) | **Implemented**, served by `frontend/Dockerfile` nginx |

### 5.2 Product frontend (`frontend/`) detail

**Applications/routes** (`frontend/src/App.tsx`):

- `/` → `Home()`: no token → `LandingPage`; admin → `/admin`; else `AppShell+HomeDashboard`.
- `/login`, `/register` → `features/auth/{Login,Register}.tsx` (+ `AuthSidePanel`).
- Protected layout `<ProtectedRoute><AppShell/></ProtectedRoute>` (single-mounted shell to avoid refetch on nav) with outlet routes: `/spaces` (`SpacesPage`), `/spaces/:spaceId` (`SpaceProjectsPage`), `/spaces/:spaceId/projects/:projectId` (`ProjectDetailPage`), `/admin` (`AdminPage`). `*` → `NotFound`.

**Project tabs (not routes):** `ProjectDetailPage` `TabId = overview|tutor|quiz|flashcards|materials|structure|progress|practice|open-ended|analytics` via `useSearchParams ?tab=`; `AppShell` mirrors `PROJECT_NAV` + `goTab()->setSearchParams({tab})`. Cross-tab handoffs (`quizDirect`, `practiceDirect`, `flashcardsDirect`) passed as props.

**Layouts:** `components/AppShell.tsx` — dual shell (public header/footer vs authed sidebar/breadcrumb/`StreakFlame GET /me/streak`/space name; admin minimal no-nav).

**Components (selected):**

- `components/ui.tsx`: Button/Card/Badge/Input/Select/Spinner/LoadingState/ErrorBox/EmptyState/PageHeader/Logo/Avatar/ProgressBar/MasteryBadge/Dot/Bar + `masteryLevelFor/levelForStatus` (85/66/34 bands mirroring backend `mastery_levels.py`).
- `components/knowledge/`: `KnowledgeTreeSelector` (+ `minimalCover`, `selectionCounts`, `checkedConceptIds`, skeletons), `EvaluationCard` (+ `GroundedChip`, `OEGrade`), `QuestionCountStepper`.
- `features/tutor/TutorChat.tsx`: markdown + KaTeX (`react-markdown`, `remark-gfm/math`, `rehype-katex`), citations, history/pin/search, `POST .../tutor/ask`, callbacks `onQuizReady/onPracticeReady/onFlashcardsReady`.
- `features/quiz/`: `QuizTaker` (stages `setup|busy|answering|done|failure`, 429/502/422 handling), `QuizSetup` (`{scope, topicIds, subtopicIds, conceptIds, numQuestions}` + tree selector), `QuizModes`, `ConceptDetail`.
- `features/practice/`: `PracticePage` (stages `select|generating|session|results`), `PracticeSession`, `PracticeResults`, `types.ts`.
- `features/{flashcards/Flashcards, openended/OpenEndedAnswersPage, structure/StructureView, progress/ProgressMap, dashboard/Dashboard, overview/OverviewView, analytics/{AnalyticsPage,AnalyticsView,GrowthView}, projects/MaterialsPanel, home/HomeDashboard, admin/*}` — see subagent report for props/stages.

**State management:** No Redux/Zustand. `AuthContext` (user/token/loading/login/register/logout) + local `useState` per feature + URL `?tab=` for project nav. GET cache in axios layer (30 s).

**API client:** `lib/axios.ts` only — never hard-code URLs. `apiError(e)` (`lib/api-error.ts`) reads `{error:{message}}` envelope + `detail` fallback; `authErrorMessage()` for offline distinction.

**Auth handling:** Login `POST /auth/login → store token → GET /auth/me`; register `POST /auth/register → login()`; `ProtectedRoute.tsx:5-18` spinner while `loading`, else `Navigate /login` if `!token`.

**Data fetching / loading / error:** Per-view `useEffect` fetch on mount (cache-backed); `LoadingState`/`Spinner`, `ErrorBox` with Retry, `EmptyState`; quiz/tutor surface 429 (budget), 502 (LLM upstream), 422 (validation/generation) distinctly.

**Major user-facing flows (frontend slice):**

- Auth → `/login` → token → `/` → spaces → space → projects → project `?tab=overview`.
- Upload (`MaterialsPanel`) → poll `GET .../materials` (API downgrades `ready→processing` while downstream jobs pending) + `GET /jobs/{id}` → structure/chunks ready → `structure`/`materials` tabs refresh.
- Tutor → `TutorChat` → ask → citations/figures → quiz/practice/flashcard handoffs.
- Quiz → `QuizSetup` (tree scope) → generate → answering (confidence stepper) → results.
- Practice/open-ended/flashcards/analytics/admin analogous; `Dashboard` shows mismatches + recommendation accept/dismiss.

---

## 6. Backend Architecture

**Entry point:** `backend/app/main.py` — `FastAPI(title, version 0.1.0)`, `register_error_handlers` (Phase 48 unified `{"error":{code,message,details}}`), CORS from `Settings.cors_origins` (fallback `http://localhost:5173`, `allow_credentials=True`), 19 routers under `/api/v1`, `GET /` → `{message, docs:/docs, health:/api/v1/health}`.

**API structure:** 19 routers, 55 decorators (verified by grep; includes `projects_router` + `projects_direct_router` both mounted). Prefixes: `/health`, `/auth`, `/spaces`, `/spaces/{space_id}/projects` + `/projects/{project_id}` (direct get), `/projects/{project_id}/materials`, `/jobs`, `/projects/{project_id}/structure`, `/projects/{project_id}/tutor`, `/projects/{project_id}/quizzes`, `/projects/{project_id}/assessment`, `/projects/{project_id}/dashboard`, `/projects/{project_id}/growth`, `/projects/{project_id}/analytics`, `/admin`, `/projects/{project_id}/practice`, `/projects/{project_id}/knowledge`, `/projects/{project_id}/flashcards`, figures (no prefix, full paths inline), `/me`. Full table in §14.

**Routers/controllers:** Thin; logic in `services/*`. Pattern: `Depends(get_current_user)` + `Depends(get_authorized_project)` (or space variant) + `Depends(get_db)`; LLM routes add `Depends(require_llm_budget(scope))` **after** auth so 404 precedes 429. Error mapping in-route: `LookupError→404`, `ValueError→400`, `QuizGenerationError/OpenEndedAssessmentError/StructureExtractionError→422`, `TutorProviderError/httpx.HTTPError→502`, `RuntimeError→500`.

**Services:** ~30 modules (`backend/app/services/`). Key: `ai/groq_client`, `ai/embedding_client`, `ai/pricing`, `document_extraction_service`, `ocr_service`, `vision_service`, `chunking_service`, `retrieval_service`, `rag_service`, `tutor_service`, `tutor_conversation_service`, `quiz_generation_service`, `quiz_attempt_service`, `adaptive_quiz_service`, `open_ended_assessment_service`, `explain_it_back_service`, `flashcard_service`, `mastery_service`, `mastery_levels`, `mismatch_service`, `recommendation_service`, `confidence_service`, `rollup_service`, `relationship_service`, `structure_extraction_service`, `structure_persistence_service`, `dashboard_service`, `growth_service`, `analytics_service`, `home_service`, `activity_service`, `ai_usage_service`, `job_service`, `storage_service`, `figure_persistence_service`, `space_service`, `project_service`.

**Schemas:** Pydantic v2, `from_attributes=True` on reads. ~23 files (`backend/app/schemas/`). Notable: `structure.py` (v1 outline + v2 topic-map/LO outlines with 1–10/1–20/size constraints), `quiz.py` (`MCQOutline`, `QuizGenerateRequest` with scope validator, answer-free `QuestionRead`), `tutor.py` (citations with figure support, `QuizPlanRequest` 1–5), `assessment.py` (grade thresholds pass≥80/partial≥50), `flashcard.py` (SM-2 review grades), `knowledge.py`/`dashboard.py` (mastery projections).

**Models:** SQLAlchemy `Base(DeclarativeBase)` + `UUIDTimestampMixin` (`backend/app/db/base.py`). 23 tables (§7). Repositories: none — services query directly (no repository layer).

**AuthN/Z:** `dependencies/auth.py` (`OAuth2PasswordBearer(tokenUrl=/api/v1/auth/login)`), `dependencies/authorization.py` (`get_authorized_space/project/project_in_space`, 404-hides-existence via joins), `dependencies/admin.py` (`is_admin` else 403). Middleware: CORS only; no session middleware (stateless JWT).

**Exception handling:** `backend/app/core/exceptions.py` — `STATUS_CODES` map, `_safe_message` (4xx/502 pass through, else generic), handlers for `StarletteHTTPException`, `RequestValidationError` (422 + loc/msg/type), bare `Exception` (500).

**Background:** Celery (`backend/app/worker/celery_app.py`, JSON ser, UTC, `task_track_started`, `broker_connection_retry_on_startup`) + 4 task modules. Also `recommendations.refresh_best_effort()` fire-and-forget `.delay()` skipped under pytest.

**Request path (actual):**

```text
HTTP Request → CORS → Router (prefix /api/v1)
  → get_current_user (JWT decode, UUID check, db.get(User)) → 401 expired vs invalid
  → get_authorized_space/project (join Space/Project, 404 hides existence)
  → require_llm_budget(scope) (in-memory sliding window per user+project) → 429
  → Pydantic validation → 422 envelope
  → Service (DB reads/writes + retrieval + chat_json/embed + metering via separate Session)
  → activity_service.record_event (ON CONFLICT DO NOTHING, never breaks caller)
  → Response schema (from_attributes) → JSON
  → (async side path) job_service.create_job + .delay() → Celery worker → DB status update
```

---

## 7. Database Architecture

DB: PostgreSQL 16 + pgvector (`docker-compose.yml:3`, `docker/postgres/init-pgvector.sql`). All PKs `UUID default uuid4` + `created_at/updated_at timestamptz server_default now()` (`backend/app/db/base.py`).

| Table | Key fields / constraints | File |
|---|---|---|
| `users` | `email String(255) unique indexed`, `hashed_password String(255)`, `is_admin bool default false` | `models/user.py` |
| `spaces` | `user_id FK users.id CASCADE indexed`, `name String(255)`, `description Text null` | `models/space.py` |
| `projects` | `space_id FK spaces.id CASCADE indexed`, `name`, `description Text null`, `goal Text null` | `models/project.py` |
| `materials` | `project_id FK CASCADE indexed`, `filename`, `storage_path`, `status default pending` (`pending→processing→ready/failed`), `extracted_text Text null`, `page_count Int null`, `error_message Text null` | `models/material.py` |
| `background_jobs` | `job_type String(64)`, `status default pending`, `material_id FK CASCADE nullable indexed`, `error Text null`, `celery_task_id String(255) null` | `models/background_job.py` |
| `document_chunks` | `project_id,material_id FK CASCADE indexed`, `concept/topic/subtopic_id FK CASCADE nullable indexed`, `page_number Int null`, `extraction_method String(8) null` (`TEXT`/`OCR`), `source_name`, `chunk_index Int`, `content Text`; `UQ(material_id,chunk_index)` | `models/chunk.py` |
| `embeddings` | `project_id,material_id indexed`, `chunk_id FK CASCADE unique indexed`, `embedding Vector(384)`, `model String(64) default BAAI/bge-small-en-v1.5` | `models/embedding.py:12,39-40` |
| `topics` | `project_id FK CASCADE indexed`, `title String(200)`; `UQ(project_id,title)` | `models/topic.py` |
| `subtopics` | `project_id FK CASCADE indexed`, `topic_id FK CASCADE indexed`, `title`; `UQ(topic_id,title)` | `models/subtopic.py` |
| `concepts` | `project_id,subtopic_id FK CASCADE indexed`, `title`, `summary Text`, `type Text default CONCEPT`, `importance Text default CORE indexed`, `page_start/end Int null`, `material_id FK SET NULL nullable indexed`, `meta JSONB "metadata" default '{}'`; `UQ(subtopic_id,title)`; `CK type IN (CONCEPT,DEFINITION,TERM,FORMULA,PROCESS,SKILL,OTHER)`; `CK importance IN (CORE,SUPPORTING,REFERENCE)` | `models/concept.py` |
| `concept_relationships` | `from/to_concept_id FK CASCADE`, `relation Text`, `evidence_span Text null`, `created_by Text`; `UQ triple`; `CK relation IN (PREREQUISITE_OF,RELATED_TO,EXAMPLE_OF,USES,DERIVED_FROM)`; `CK created_by IN (structure,llm)`; `CK from<>to`; `CK llm→evidence_span NOT NULL` | `models/concept_relationship.py` |
| `material_figures` | `project_id,material_id FK CASCADE indexed`, `page_number,fig_index Int`, `figure_type default DIAGRAM` (`CHART,TABLE_SCAN,DIAGRAM,PHOTO,DECORATIVE,UNKNOWN`), `storage_path`, `thumb_path null`, `image_hash`, `summary/markdown_table/latex_table/ocr_text Text null`, `vision_model`; `UQ(material_id,page_number,fig_index)` | `models/material_figure.py` |
| `quizzes` | `project_id indexed`, `mode String(16)` `CK practice/exam`, `question_count Int`, `time_limit_seconds null` | `models/quiz.py` |
| `quiz_questions` | `quiz_id FK CASCADE indexed`, `concept_id FK CASCADE indexed`, `question_text Text`, `options JSONB`, `correct_index Int`, `difficulty CK easy/medium/hard`, `source_chunk_id FK null` | `models/quiz.py` |
| `quiz_attempts` | `quiz_id FK CASCADE indexed`, `user_id FK CASCADE indexed`, `started/completed_at null`, `score Numeric(5,2) null` | `models/quiz_attempt.py` |
| `quiz_answers` | `attempt_id FK CASCADE indexed`, `question_id FK CASCADE`, `selected_index Int`, `is_correct bool`, `confidence Int null CK 1..5`, `answered_at default now()`; `UQ(attempt_id,question_id)` | `models/quiz_attempt.py` |
| `flashcards` | `project_id indexed`, `concept_id FK CASCADE indexed`, `front/back Text`, `source default auto CK auto/manual`, `efactor Numeric(4,2) default 2.50 CK ≥1.30`, `interval_days default 0 CK ≥0`, `repetitions/lapses/total/correct Int default 0`, `next_review_at null`; `UQ(concept_id,front)` + index `next_review_at` | `models/flashcard.py` |
| `mastery_evidence` | Append-only: `user/project/concept_id FK CASCADE indexed`, `evidence_type CK mcq,open_ended,explain_back,flashcard,tutor`, `source null indexed CK tutor,practice,quiz,open_ended,flashcard`, `raw_score Numeric(5,2) CK 0..100`, `difficulty CK easy/medium/hard null`, `feedback Text null` | `models/mastery_evidence.py` |
| `learning_events` | `user/project/space_id FK SET NULL nullable`, `event_type String(64)` CK 11 types, `entity_type null`, `entity_id UUID null`, `payload JSONB default {}`, `idempotency_key String(128) unique` | `models/learning_event.py` |
| `tutor_conversations` | `project/user_id FK CASCADE indexed`, `title default New chat` | `models/tutor_conversation.py` |
| `tutor_messages` | `conversation_id FK CASCADE indexed`, `role CK user/assistant`, `content Text`, `seq Int default nextval('tutor_messages_seq') indexed`, `supported bool null`, `citations JSONB default []`, `follow_ups JSONB default []` | `models/tutor_conversation.py` |
| `recommendations` | `user/project/concept_id FK CASCADE indexed`, `action_type CK ask_tutor,targeted_quiz,explain_back,review_material,exam_mode`, `score Numeric(6,2)`, `reasoning Text`, `status default active CK active,accepted,dismissed,expired` | `models/recommendation.py` |
| `ai_usage` | `user/project_id FK SET NULL nullable indexed`, `feature String(64) indexed`, `provider`, `model`, `prompt/completion_tokens null`, `tokens_estimated bool default false`, `latency_ms null`, `success default true`, `error_type`, `http_status`, `cost_usd Numeric(10,6) null`, `meta JSONB default {}` | `models/ai_usage.py` |

Non-table: `models/mismatch.py` — frozen `@dataclass Mismatch` (no table).

**Enums/CKs:** Concept `type` (7) / `importance` (3) / relationship `relation` (5) / `created_by` (2); quiz `mode`/`difficulty`; answers `confidence 1–5`; evidence `evidence_type`/`source`/`difficulty`; flashcards `source`; figures `figure_type`; events `event_type` (11); tutor `role`; recommendations `action_type`/`status`.

**Indexes:** FKs indexed throughout; `users.email unique`; UQs on `(material_id,chunk_index)`, `(project_id,title)`, `(topic/subtopic,title)`, `(concept triple)`, `(attempt,question)`, `(concept,front)`, `(material,page,fig)`; `embeddings.chunk_id unique`; `next_review_at`, `tutor_messages.seq`, mastery `source`.

**ASCII ERD (only real FKs):**

```text
users
 ├──< spaces (user_id CASCADE)
 │     └──< projects (space_id CASCADE)
 │           ├──< materials (project_id CASCADE)
 │           │     ├──< document_chunks (material_id CASCADE)
 │           │     │     └──1:1 embeddings (chunk_id CASCADE unique)
 │           │     ├──< material_figures (material_id CASCADE)
 │           │     └── concepts.material_id (SET NULL, nullable)
 │           ├──< topics (project_id CASCADE)
 │           │     └──< subtopics (topic_id CASCADE)
 │           │           └──< concepts (subtopic_id CASCADE)
 │           │                 ├──< concept_relationships (from/to CASCADE, self-ref)
 │           │                 ├──< document_chunks (concept/topic/subtopic nullable)
 │           │                 ├──< quiz_questions (concept_id CASCADE)
 │           │                 ├──< flashcards (concept_id CASCADE)
 │           │                 ├──< mastery_evidence (concept_id CASCADE)
 │           │                 └──< recommendations (concept_id CASCADE)
 │           ├──< quizzes (project_id) ──< quiz_questions ──< quiz_answers
 │           │        └──< quiz_attempts (quiz_id+user_id) ──< quiz_answers (attempt_id)
 │           ├──< tutor_conversations (project_id+user_id) ──< tutor_messages
 │           ├──< background_jobs (material_id nullable CASCADE)
 │           └── mastery_evidence / recommendations / ai_usage / learning_events (project_id denormalized)
users ──< quiz_attempts / mastery_evidence / recommendations / ai_usage / tutor_conversations
spaces ──< learning_events (space_id SET NULL, nullable)
```

---

## 8. Authentication & Authorization

**Registration — Implemented** (`backend/app/api/v1/auth.py:17`): `email.strip().lower()`, 400 if exists, `User(email, hashed_password=hash_password(pw), is_admin=False)`, commit. `UserCreate`: email regex `^[^@\s]+@[^@\s]+\.[^@\s]+$`, password 8–128.

**Login — Implemented** (`auth.py:34`): lookup lowered email, `verify_password` else 401 `Invalid email or password`; `create_access_token(subject=str(user.id))` → `{access_token, token_type: bearer}`.

**Password hashing — Implemented** (`backend/app/core/security.py`): single Argon2id `PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4, hash_len=32, salt_len=16)` (OWASP comment); `verify_password` swallows `VerifyMismatchError|Exception → False`; `needs_rehash` utility.

**JWT creation — Implemented** (`backend/app/core/jwt.py`): HS256 `jwt.encode({sub=str(user_id), exp=now+JWT_EXPIRE_MINUTES (default 2880 = 48 h), iat})` via PyJWT.

**Token validation — Implemented** (`backend/app/dependencies/auth.py`): `OAuth2PasswordBearer(tokenUrl=/api/v1/auth/login)` → `Authorization: Bearer`; `decode_access_token`; distinct 401 `Token has expired` vs `Could not validate credentials`; UUID parse; `db.get(User, uid)`.

**Refresh — Not implemented.** No refresh tokens; frontend re-logins after expiry (token lives 48 h by default).

**Identity extraction:** `get_current_user → User ORM`; `get_token_subject` helper returns `None` on expiry/invalid.

**Protected routes:** All except `POST /auth/register`, `POST /auth/login`, `GET /health`, `GET /` require `get_current_user`. Project/space/job/figure/quiz/etc. additionally require `get_authorized_space/project/project_in_space/job` (joins, 404-hides-existence). Admin routes require `get_current_admin` (401 upstream, 403 `Admin access required` if `not is_admin`).

**Roles:** Boolean `users.is_admin` only; no RBAC beyond admin-vs-owner. Ownership = `Space.user_id`; projects inherit via join.

**Frontend auth state — Implemented** (`frontend/src/context/AuthContext.tsx`, `lib/axios.ts`, `components/ProtectedRoute.tsx`): token in `localStorage:access_token`; hydrate `GET /auth/me` on mount; `login: POST /auth/login → store → GET /auth/me`; `register → login()`; `logout` clears; 401 interceptor (except login/register) → `notifyUnauthorized()` pub/sub → logout + `navigate(/login)` SPA-safe; `ProtectedRoute` spinner/`Navigate`.

```text
Register: POST /auth/register {email,password} → 201 UserRead
Login: POST /auth/login {email,password} → {access_token} → store → GET /auth/me → User
Authed: apiClient adds Bearer → get_current_user → get_authorized_* → handler
Expiry: 401 Token has expired → interceptor clears → /login
```

---

## 9. Document Processing Pipeline

**Actual pipeline (implemented, worker-only heavy lifting):**

```text
Upload (POST /projects/{id}/materials, multipart)
 ↓ storage_service.save_pdf: 10MB, .pdf ext, %PDF magic, content-type → UPLOAD_DIR/{project}/{uuid}.pdf
Material(status=pending) + background_jobs(process_pdf=pending) committed
 ↓ process_pdf.delay() best-effort (broker-down → job stays pending, upload still 201)
Celery process_pdf(job_id,material_id) [bind, max_retries=3] — backend/app/worker/tasks/extraction.py
 ↓ idempotency guard (processing+running + celery_task_id mismatch → skipped)
 ↓ pending→running/processing
 ↓ document_extraction_service.extract_document_pages (PyMuPDF per page):
 │    TEXT branch (meaningful chars≥20 & words≥3) vs OCR branch (render Matrix DPI300 → Pillow → pytesseract, lang eng)
 │    tables: find_tables→GFM (MAX 3/page, 30 rows, 10 cols, 300 chars/cell) if TABLES_ENABLED
 │    figures: candidates (MAX 4/page, ≥40×40) → NaraRouter vision caption (VISION_MAX_IMAGES_PER_DOC=12, timeout 20s)
 │      → {figure_type, summary, markdown/latex_table} else cropped-OCR/placeholder (never fails doc)
 ↓ material.ready + extracted_text/page_count OR failed + error_message (+ material.failed event)
 ↓ inline chunking: chunk_pages (never spans pages, carries extraction_method) + persist_chunks (delete-then-insert, single commit)
 ↓ figure_persistence.save_figures (PNG+thumb, upsert, best-effort)
 ↓ create generate_embeddings + build_structure jobs + .delay() best-effort
 ↓ returns {status,page_count,chars,ocr_pages,tables,figures,chunks,embed_job,structure_job}
Embeddings task: read chunks ordered → embedding_client.embed (batched, dims N×384 check) → upsert per chunk_id (retry-safe)
Structure task: re-read PDF (vision_enabled=False) + attach stored figures → Pass1 extract_topic_map → Pass2 per-topic
  extract_learning_objects → persist_knowledge_map (case-insensitive upsert, obsolete handling) → completed/failed
Frontend: list_materials downgrades DB ready→API processing while downstream jobs pending/running;
  polls GET .../materials + GET /jobs/{job_id}
```

**Libraries:** `pymupdf`, `pytesseract`, `Pillow`, `httpx` (vision async), `fastembed` — `backend/requirements.txt:12-14,18`.

**Failure/retry:** `ValueError/FileNotFound → failed` no retry; transient → `retry(countdown=2^retries*2)` max 3 → failed; structure 429 backoff `60*(retries+1)`; vision/OCR failures degrade (placeholder/skip), never fail doc; vision disabled under `PYTEST_CURRENT_TEST`.

**Metadata:** `document_chunks.{page_number, extraction_method TEXT/OCR/NULL-legacy, source_name, chunk_index}` + `UQ(material_id,chunk_index)`; `materials.{page_count, extracted_text, error_message, status}`; `material_figures.{page_number, fig_index, figure_type, storage/thumb_path, image_hash, summary, markdown/latex_table, ocr_text, vision_model}`.

---

## 10. AI / LLM Architecture

| Workflow | Provider/Model | Prompt/output | Metering | Errors |
|---|---|---|---|---|
| Tutor answer (`tutor_service.ask_question`) | `LLM_PROVIDER` groq (`openai/gpt-oss-20b`) or inception (`mercury-2.5`); temp 0.0 clamped to provider min (0.5 Mercury); timeout 60 s; JSON mode | System: tutor-only-excerpts + `<<<DATA` quarantine + goal-as-DATA; user: excerpts + question; `TutorOutline(answer 1–20000, follow_ups 0–4)` Pydantic | `track_llm_call(feature=tutor_answer, meta chunks/min_distance)` | No chunks or `min(distance)>0.5` → unsupported, **no LLM call**; `TutorProviderError/httpx.HTTPError→502` |
| Conversational + quiz-plan | Same client; canned greetings/thanks/farewell/help bypass LLM; `plan_quiz` (CORE catalog, 2 tries, ≤8 concepts, 1–5 Qs) | `QuizPlanResponse(label,concept_ids)` | Same | Same |
| Quiz generation (`quiz_generation_service`, 713 lines) | Same | Context: concept chunks → fallback project chunks, `MAX_SOURCE_CHARS=6000`, enriched `CONTEXT=1500` + 8 supporting + related; adaptive difficulty; `MCQOutline(1–20 Qs)`; 1 retry then persist `Quiz+QuizQuestion` | `feature=quiz_generation` | `QuizGenerationError→422` |
| Open-ended generate/grade + explain-back | Same | `OpenEndedGenerateResponse(question,concept,scope,difficulty)`; grade thresholds pass≥80/partial≥50 → `OpenEndedGradeResponse(score,verdict,feedback,strengths,missing,suggestions)`; explain-back similar | Respective features | `OpenEndedAssessmentError→422` |
| Structure extraction (2-pass) | Same | Pass1 `extract_topic_map` (≤200 k chars) → `TopicMapOutline`; Pass2 per-topic `extract_learning_objects` (name/subtopic/type/importance/summary/pages/section/relationships ≤5); 1 retry; per-topic failures → `failed_topics` but map persists | `structure_topic_map`, `structure_learning_objects` | `StructureExtractionError→422`; 429 backoff in worker |
| Figure captioning | NaraRouter OpenAI-compat (`NARAROUTER_BASE_URL/chat/completions`, `stepfun-3.7-flash`, 20 s) async + sync wrapper | `_ANALYZE_SYSTEM` → `FigureAnalysis(figure_type, summary, markdown/latex_table)` | Best-effort (no strict metering observed) | Never raises → `None` → OCR/placeholder fallback |
| Embeddings | Local fastembed `BAAI/bge-small-en-v1.5` 384-d, `lru_cache`, no network | `embed(texts)` validates non-empty + dims; `embed_one` for queries | Not LLM-metered (local) | `ValueError` on bad dims |
| Cost | `ai/pricing.py`: `USD_PER_MTOK` (mercury 0.04/0.15, gpt-oss-20b 0.075/0.30, qwen3-32b, gpt-oss-120b) → `estimate_cost_usd` Decimal or `None` | — | `ai_usage` rows via dedicated `SessionLocal` (survives rollback); `tokens_estimated=len//4` fallback; never logs key/text | — |

**Actual tutor flow:**

```text
User Question → conversational_reply? (canned, no LLM)
 → assemble_context (retrieve top chunks + figures, max 5/6000 chars, word-snapped …)
 → no chunks OR min(distance)>0.5 → unsupported (no LLM call) + empty citations
 → else _build_user_prompt (excerpts as DATA) → track_llm_call(tutor_answer)
 → chat_json(system,user,temp 0.0,timeout 60) → TutorOutline parse
 → citations (280-char excerpts) + figure attach → {answer,supported,citations,follow_ups}
 → persist TutorMessage(user+assistant) via tutor_conversation_service (+ AI title after 3 exchanges)
 → sources/citations in response
```

Streaming: **not implemented** (sync JSON responses, 15 s axios timeout). Citations: chunk (`chunk/material/page/source/index/excerpt`) + figure (`figure_id/index/type/image_url`). AI tracking: `ai_usage` per call (provider/model/tokens/latency/success/error/cost/meta).

---

## 11. RAG Architecture

**Implemented.** Code locations: `backend/app/services/retrieval_service.py`, `rag_service.py`, `tutor_service.py`, `quiz_generation_service.py`.

- **Ingestion:** PDF → `extract_document_pages` → `chunk_pages` → `persist_chunks` (delete-then-insert idempotent) → `generate_embeddings` task (`backend/app/worker/tasks/embeddings.py`).
- **Chunking:** `CHUNK_SIZE_CHARS=2000 (~500 tok)`, `OVERLAP_CHARS=200 (~50 tok)` (`chunking_service.py:19-20`); word-boundary back-off + overlap snap-forward; never spans pages; carries `extraction_method`; returns `{text,start,end}`.
- **Embeddings:** Local `fastembed` 384-d, batched, dims-checked, upsert per `chunk_id` (`EMBEDDING_DIMS=384`, `models/embedding.py:12`).
- **Vector storage:** `embeddings.embedding Vector(384)`, one row per chunk (`chunk_id unique`), `model` label.
- **Similarity search:** `retrieve(db,project_id,query,top_k=5 clamp 1–20,concept_id?)`: short-circuits (no LLM/embed cost) if no `Embedding` rows; `embed_one(query)`; `cosine_distance` SQL ordered, `WHERE project_id` (+ `concept_id`) **before** ranking; returns `RetrievedChunk(chunk/material/content/page/source/index/score=distance)`.
- **Metadata filtering:** `project_id` always; optional `concept_id`; `figures_for_pages` (max 4 pages, 6 figures).
- **Retrieval count:** Default 5, max 10 (`rag_service.py:19-20`); tutor uses defaults; quiz uses `MAX_SOURCE_CHARS=6000` + enriched context.
- **Ranking:** Pure cosine distance ascending; no reranker observed.
- **Context assembly:** `assemble_context(max_chunks 5, max_chars 6000 clamp 500–20000)`: loop until chunks/chars budget, word-snapped truncation (`…`), returns `RagContext(query,scope,chunks,figures,total_chars,truncated)` (`schemas/rag.py`).
- **Answer/citation:** Tutor builds prompt from `RagContext` + validates `TutorOutline`; citations from retrieved chunks (excerpt 280 chars) + figures with `figure_image_url`.

---

## 12. Learning / Mastery / Assessment Architecture

### Tutor — Implemented

```text
UI TutorChat → POST .../tutor/ask {question,concept_id?} | .../conversations/{id}/messages
 → get_authorized_project + require_llm_budget → tutor_service.ask_question / tutor_conversation_service.send_message
 → RAG (see §11) → LLM → TutorOutline → citations/figures
 → persist TutorConversation/TutorMessage (+title) → mastery? NO (plain chat never writes evidence)
 → {answer,supported,citations,follow_ups}
```

Only graded explain-back/follow-up via `record_tutor_evidence` writes `tutor` stream (max 1/day/concept).

### Flashcards — Implemented (SM-2)

```text
UI Flashcards (dashboard|study|library|generate) → POST .../flashcards/decks {topic/subtopic/concept_ids}
 → flashcard_service.build_deck: deterministic front/back by LO type, practicable CORE+SUPPORTING only,
   idempotent on (concept_id,front) → {created,total}
Study → GET .../flashcards (due-first) → POST .../{card_id}/review {grade again|hard|good|easy}
 → SM-2 (quality 0/3/4/5, efactor floor 1.30, intervals 1/6/efactor, lapse reset)
 → mastery_evidence(flashcard, score=quality*20) → {card,quality,score}
```

### Quiz (incl. adaptive + confidence) — Implemented

```text
UI QuizSetup (tree scope) → POST .../quizzes/generate {concept_id?,scope,topic/subtopic/concept_ids,num 1–20,mode practice|exam,difficulty?}
 → quiz_generation_service: _load_source (concept chunks→fallback project), page-range, related enrichment,
   adaptive difficulty (adaptive_quiz_service: weakest-first, bands, exposure-balanced), MAX_SOURCE 6000
 → LLM MCQOutline (1 retry) → persist Quiz+QuizQuestion → {quiz_id,question_count}
Attempt: POST .../{quiz_id}/attempts → AttemptStartResponse
Answer: POST .../attempts/{id}/answers {question_id,selected_index,confidence 1–5?} → server-side is_correct,
  UQ race→ValueError, emits question.answered event → AnswerSubmitResponse
Complete: POST .../attempts/{id}/complete → locks, score → AttemptCompleteResponse
Evidence: quiz_attempt_service writes mcq evidence (difficulty-aware) on completion/answers
```

### Practice — Implemented

```text
UI PracticePage → GET .../practice/recommendations → recommendation_service.recommend_many (CORE top-N, no persist)
 → generate/answer via quiz/assessment paths with source=practice → mastery practice stream (weight .20)
```

### Open-ended + Explain-back — Implemented

```text
UI OpenEndedAnswersPage → POST .../assessment/open-ended/generate {scope,difficulty?} → LLM question
 → answer → POST .../assessment/open-ended {concept_id,answer 1–5000,question_text?} → LLM grade
 → OpenEndedGradeResponse(score 0–100, verdict pass≥80|partial≥50|fail, feedback,strengths,missing,suggestions)
 → mastery_evidence(open_ended, source=open_ended)
Explain-back: POST .../assessment/explain-back → grade + explain_back evidence
```

### Concept mastery — Implemented (EMA, deterministic, never LLM)

Weights: `quiz .35, open_ended .25, practice .20, flashcard .15, tutor .05` (`mastery_service.py:13-17`); per-point `weight = difficulty base (easy .2/medium .3/hard .4) + gap boost (.1 if >7 d, cap .5)`; tutor fixed `.15`, ≤1/day/concept; `mastery += w*(score-mastery)`; `final` renormalized; caps: tutor-only 40, formative-only 70, 1-row 60, 2-row 75; `evidence_confidence none/low(<3)/ok`. Dual projection: `mcq` (quiz+practice) vs `applied` (open_ended+flashcard+tutor). Statuses: `Not Started (None), <34 Needs Practice, ≤66 Developing, <85 Strong, ≥85 Mastered` (`mastery_levels.py`). Only CORE non-obsolete are mastery targets; CORE+SUPPORTING are practicable.

### Mastery evidence — Implemented (append-only `mastery_evidence`, CKs on type/source/score/difficulty).

### Adaptive selection — Implemented (`adaptive_quiz_service.py`, 111 lines): weakest-first, difficulty bands aligned to mastery bands, exposure balancing.

### Recommendations — Implemented (deterministic Decision Engine, `recommendation_service.py` 539 lines):

```text
build_dashboard → score = weakness(100-min mastery) + uncertainty(+25 overconf) + recency(+15 if >5d)
 + goal(+10 keyword) + base(ask10/quiz15/explain20/review5/exam8) − repetition(25×last7d same)
 + mismatch(+40 explain/review, −20 quiz), floor 0 → recommend() expires prior active (single-current)
 → persist recommendations{action_type,score,reasoning,status} → Dashboard accept/dismiss/refresh
```

### Growth — Implemented (`growth_service.py` 206 lines): EMA replay per prefix → `GET .../growth?concept_id=` → `GrowthView` trends; `analytics_service` reuses for overview.

---

## 13. Important Data Flows

Only flows that exist in code (all **Implemented** unless noted):

### 13.1 User Authentication

1. Trigger: `POST /auth/register` or `/auth/login` from `Login/Register`.
2. Components: SPA → `auth.py` → `security.py`/`jwt.py` → `users`.
3. Endpoints: `POST /auth/register → 201 UserRead`; `POST /auth/login → Token`; `GET /auth/me → UserRead`.
4. Tables: `users`.
5. External: none.
6. Transforms: `email.lower().strip()`, Argon2id hash, HS256 `{sub,exp,iat}`.
7. Result: `access_token` in localStorage + `User` hydrated.

### 13.2 Project Creation (Spaces/Projects)

1. Trigger: SpacesPage/SpaceProjectsPage create forms.
2. Components: SPA → `spaces.py`/`projects.py` → `space_service`/`project_service`.
3. Endpoints: `POST /spaces`, `GET /spaces`, `GET /spaces/{id}`, `POST /spaces/{id}/projects`, `GET /spaces/{id}/projects`, `GET /spaces/{id}/projects/{pid}`, `GET /projects/{pid}`.
4. Tables: `spaces`, `projects`.
5. Result: `SpaceRead/ProjectRead` (goal feeds recommender+tutor).

### 13.3 Document Upload

Covered in §9. Trigger: `MaterialsPanel` multipart. Endpoint: `POST /projects/{id}/materials → 201 MaterialRead`. Tables: `materials`, `background_jobs`, `learning_events(material.uploaded)`. Result: pending material + job id; frontend polls.

### 13.4 Document Processing

See §9. Endpoints polled: `GET .../materials`, `GET /jobs/{id}`. Tables: `materials`, `document_chunks`, `embeddings`, `topics/subtopics/concepts`, `concept_relationships`, `material_figures`, `background_jobs`, `learning_events(material.ready/failed)`.

### 13.5 Knowledge/RAG Query

Trigger: tutor ask / quiz-plan / quiz-gen context. Components: `retrieval_service` → `rag_service`. No dedicated HTTP endpoint (internal). Tables: `document_chunks`, `embeddings`, `material_figures`. Result: `RagContext`.

### 13.6 AI Tutor

See §10/12. Endpoints: `POST .../tutor/ask`, CRUD `.../tutor/conversations*`, `POST .../tutor/quiz-plan`. Tables: `tutor_conversations/messages`, `ai_usage`, `learning_events(tutor.message)`. No mastery write (except graded tutor evidence path).

### 13.7 Quiz Generation/Submission

See §12. Endpoints: `POST .../quizzes/generate`, `POST .../{qid}/attempts`, `POST .../attempts/{aid}/answers`, `POST .../attempts/{aid}/complete`. Tables: `quizzes`, `quiz_questions`, `quiz_attempts`, `quiz_answers`, `mastery_evidence(mcq)`, `ai_usage`, `learning_events(quiz.started/completed, question.answered, mastery.updated)`.

### 13.8 Practice — Implemented

Endpoint: `GET .../practice/recommendations` (+ quiz/assessment endpoints with `source=practice`). Tables: `recommendations` (not persisted for many), `mastery_evidence(practice)`.

### 13.9 Open-ended Assessment — Implemented

Endpoints: `POST .../assessment/open-ended/generate`, `POST .../assessment/open-ended`, `POST .../assessment/explain-back`. Tables: `mastery_evidence(open_ended/explain_back)`, `ai_usage`.

### 13.10 Flashcards — Implemented

Endpoints: `POST .../flashcards/decks`, `GET .../flashcards`, `POST .../flashcards/{id}/review`. Tables: `flashcards`, `mastery_evidence(flashcard)`.

### 13.11 Mastery Calculation — Implemented

Trigger: any evidence write → `mastery_service` EMA → read via `dashboard/knowledge/growth/analytics`. Tables: `mastery_evidence` → computed (no mastery table). Result: `{mcq,applied,final,status,confidence,streams}`.

### 13.12 Recommendations — Implemented

Trigger: dashboard load/refresh or `generate_recommendation` task. Endpoints: `GET .../dashboard`, `POST .../dashboard/refresh|accept|dismiss`, `GET .../practice/recommendations`. Tables: `recommendations`, `mastery_evidence`, `learning_events(recommendation.generated, mastery.updated)`.

---

## 14. API Inventory

Base: `/api/v1`. Auth: `PUB` or `USER` (+ `ADMIN`); all `USER` also project-scoped except where noted. Implementation = `backend/app/api/v1/*.py`.

**Health/Root:**

| Method | Endpoint | Purpose | Auth | Request | Response | Implementation |
|---|---|---|---|---|---|---|
| GET | `/health` | Liveness (Railway + Docker HEALTHCHECK) | PUB | — | `{status: ok}` | `health.py:7` |
| GET | `/` (unversioned) | Shell pointer | PUB | — | `{message,docs,health}` | `main.py:72` |

**Auth:**

| POST | `/auth/register` | Register | PUB | `{email,password 8–128}` | `201 UserRead{id,email,is_admin,created_at}` | `auth.py:17` |
| POST | `/auth/login` | Login | PUB | `{email,password}` | `Token{access_token,token_type}` | `auth.py:34` |
| GET | `/auth/me` | Current user | USER | Bearer | `UserRead` | `auth.py:44` |

**Spaces/Projects:**

| POST | `/spaces` | Create space | USER | `{name,description?}` | `201 SpaceRead` | `spaces.py:16` |
| GET | `/spaces` | List my spaces | USER | — | `SpaceRead[]` | `spaces.py:29` |
| GET | `/spaces/{space_id}` | Get space | USER (owner, 404 else) | — | `SpaceRead` | `spaces.py:38` |
| POST | `/spaces/{space_id}/projects` | Create project | USER | `{name≤80,description?,goal?}` | `201 ProjectRead` | `projects.py:19` |
| GET | `/spaces/{space_id}/projects` | List projects | USER | — | `ProjectRead[]` | `projects.py:32` |
| GET | `/spaces/{space_id}/projects/{project_id}` | Get in space | USER | — | `ProjectRead` | `projects.py:42` |
| GET | `/projects/{project_id}` | Direct get (ownership gate) | USER | — | `ProjectRead` | `projects.py:49 direct_router` |

**Materials/Jobs:**

| POST | `/projects/{project_id}/materials` | Upload PDF | USER | `multipart file` | `201 MaterialRead{status,page_count,error}` | `materials.py:31` |
| GET | `/projects/{project_id}/materials` | List (ready→processing downgrade) | USER | — | `MaterialRead[]` | `materials.py:81` |
| GET | `/jobs/{job_id}` | Poll job (material-scoped, else 404) | USER | — | `BackgroundJobRead` | `jobs.py:47` |

**Structure/Knowledge:**

| GET | `/projects/{project_id}/structure` | Full Topic→Sub→Concept tree | USER | — | `StructureRead` | `structure.py:16` |
| GET | `/projects/{project_id}/knowledge/tree` | Browse tree w/ mastery | USER | — | `KnowledgeTreeRead` | `knowledge.py:111` |
| GET | `/projects/{project_id}/knowledge/search?q=` | Concept search | USER | `q` | `SearchResultsRead` | `knowledge.py:192` |
| GET | `/projects/{project_id}/knowledge/graph` | Nodes/edges | USER | — | `KnowledgeGraphRead` | `knowledge.py:218` |
| GET | `/projects/{project_id}/knowledge/concepts/{concept_id}` | Concept detail + mastery/streams/relations/source | USER | — | `ConceptDetailRead` | `knowledge.py:268` |

**Tutor:**

| POST | `/projects/{project_id}/tutor/ask` | One-shot grounded answer | USER + LLM budget | `{question 1–2000,concept_id?}` | `TutorAskResponse{answer,supported,citations,follow_ups}` | `tutor.py:33` |
| GET | `/projects/{project_id}/tutor/conversations` | List chats | USER | — | `ConversationRead[]` | `tutor.py:67` |
| POST | `/projects/{project_id}/tutor/conversations` | Create chat | USER | `{title?}` | `201 ConversationRead` | `tutor.py:85` |
| GET | `/projects/{project_id}/tutor/conversations/{conversation_id}` | Get thread | USER | — | `ConversationDetail` | `tutor.py:100` |
| POST | `/projects/{project_id}/tutor/conversations/{conversation_id}/messages` | Send message (persists both sides) | USER + budget | `{question,concept_id?}` | `ChatSendResponse` | `tutor.py:123` |
| DELETE | `/projects/{project_id}/tutor/conversations/{conversation_id}` | Delete | USER | — | `204` | `tutor.py:157` |
| POST | `/projects/{project_id}/tutor/quiz-plan` | Quiz-me plan (≤5 Qs, CORE) | USER + budget | `{questions 1–5}` | `QuizPlanResponse{label,concept_ids}` | `tutor.py:170` |

**Quizzes:**

| POST | `/projects/{project_id}/quizzes/generate` | Generate MCQ (scoped) | USER + budget | `QuizGenerateRequest{scope,ids,num 1–20,mode,difficulty?}` | `201 {quiz_id,question_count}` | `quizzes.py:29` |
| POST | `/projects/{project_id}/quizzes/{quiz_id}/attempts` | Start attempt | USER | — | `AttemptStartResponse` | `quizzes.py:81` |
| POST | `/projects/{project_id}/quizzes/attempts/{attempt_id}/answers` | Submit answer (+confidence) | USER | `{question_id,selected_index,confidence 1–5?}` | `AnswerSubmitResponse{is_correct}` | `quizzes.py:107` |
| POST | `/projects/{project_id}/quizzes/attempts/{attempt_id}/complete` | Complete + score | USER | — | `AttemptCompleteResponse{score}` | `quizzes.py:135` |

**Assessment:**

| POST | `/projects/{project_id}/assessment/open-ended/generate` | Generate OE question | USER + budget | `{scope,difficulty?}` | `201 {question_text,concept_id,scope_label}` | `assessment.py:26` |
| POST | `/projects/{project_id}/assessment/open-ended` | Grade answer | USER + budget | `{concept_id,answer 1–5000,question_text?}` | `{score 0–100,verdict,feedback,strengths,missing,suggestions}` | `assessment.py:65` |
| POST | `/projects/{project_id}/assessment/explain-back` | Grade explanation | USER + budget | `{concept_id,answer,...}` | `ExplainBackResponse + evidence_id` | `assessment.py:102` |

**Dashboard/Growth/Analytics/Practice:**

| GET | `/projects/{project_id}/dashboard` | Mastery + mismatches + recommendation | USER | — | `DashboardResponse` | `dashboard.py:129` |
| POST | `/projects/{project_id}/dashboard/refresh` | Regenerate recommendation | USER | — | `201 RecommendationRead` | `dashboard.py:141` |
| POST | `/projects/{project_id}/dashboard/accept` | Accept | USER | `{recommendation_id}` | `RecommendationRead(status=accepted)` | `dashboard.py:191` |
| POST | `/projects/{project_id}/dashboard/dismiss` | Dismiss | USER | `{id}` | `RecommendationRead(dismissed)` | `dashboard.py:201` |
| GET | `/projects/{project_id}/growth?concept_id=` | EMA replay trend | USER | `concept_id?` | `ProjectGrowthRead\|ConceptGrowthRead` | `growth.py:23` |
| GET | `/projects/{project_id}/analytics` | Counts + reuse growth | USER | — | `ProjectAnalyticsRead` | `analytics.py:23` |
| GET | `/projects/{project_id}/analytics/overview?time_range=2w\|1m\|all` | Topic mastery, confidence scatter, timeline | USER | `time_range` | `AnalyticsOverviewRead` | `analytics.py:50` |
| GET | `/projects/{project_id}/practice/recommendations` | Top-N practice (no persist) | USER | — | `PracticeRecommendationsRead` | `practice.py:18` |

**Flashcards/Figures/Me/Admin:**

| POST | `/projects/{project_id}/flashcards/decks` | Build deck | USER | `{topic/subtopic/concept_ids}` | `201 {created,total}` | `flashcards.py:44` |
| GET | `/projects/{project_id}/flashcards` | List due-first | USER | — | `FlashcardListRead` | `flashcards.py:66` |
| POST | `/projects/{project_id}/flashcards/{card_id}/review` | SM-2 review | USER | `{grade again\|hard\|good\|easy}` | `ReviewResponse{card,quality,score}` | `flashcards.py:95` |
| GET | `/projects/{project_id}/materials/{material_id}/figures` | List figures | USER | — | `FigureRead[]` | `figures.py:47` |
| GET | `/projects/{project_id}/materials/{material_id}/figures/{figure_id}/image` | PNG bytes | USER | — | `FileResponse image/png` | `figures.py:89` |
| GET | `/me/streak` | UTC-day evidence streak | USER | — | `StreakRead` | `me.py:27` |
| GET | `/me/home` | Continue/recent/stats/actions/week | USER | — | `HomeRead` | `me.py:36` |
| GET | `/admin/users` | Paginated users | ADMIN | — | `UsersPage` | `admin.py:56` |
| GET | `/admin/overview` | Usage overview | ADMIN | — | `AdminOverview` | `admin.py:110` |
| GET | `/admin/activity` | Events | ADMIN | — | `ActivityPage` | `admin.py:139` |
| GET | `/admin/ai-usage` | Spend by feature/model | ADMIN | — | `AIUsageSummary` | `admin.py:181` |
| GET | `/admin/users/{user_id}/journey` | Per-user journey | ADMIN | — | `UserJourney` | `admin.py:282` |
| GET | `/admin/health` | System health | ADMIN | — | `HealthRead` | `admin.py:365` |
| GET | `/admin/ai-evaluation` | Heuristic eval | ADMIN | — | `AIEvaluation` | `admin.py:413` |

Total: **55 decorators across 19 routers** (grep-verified). No versioning beyond `/api/v1`; no GraphQL/websocket observed.

---

## 15. External Services

| Service | Purpose | Used By | Configuration (no secrets) |
|---|---|---|---|
| Groq API | LLM generation/eval/quiz/structure/tutor (OpenAI-compat `chat/completions`, JSON mode) | `services/ai/groq_client.py` (`provider=groq`) | `LLM_PROVIDER=groq`, `GROQ_API_KEY`, `GROQ_MODEL=openai/gpt-oss-20b` (`core/config.py:30-32`, `backend/.env.example:30-32`, `docker-compose.yml:53-54`) |
| Inception Labs API | Alternate LLM (`mercury-2.5`, temp clamp 0.5) | Same client (`provider=inception`) | `INCEPTION_API_KEY`, `INCEPTION_MODEL=mercury-2.5` |
| NaraRouter | Vision figure captioning (`{base}/chat/completions`, `stepfun-3.7-flash`) | `services/vision_service.py` | `NARAROUTER_API_KEY`, `NARAROUTER_BASE_URL=https://router.bynara.id/v1`, `NARAROUTER_MODEL`, `VISION_*` (`core/config.py:52-64`) |
| OpenAI API | Documented embedding option (`text-embedding-3-small`) — **currently inactive/broken** (dims 1536 vs local 384) | `backend/.env.example:35-40` only; code defaults `EMBEDDING_PROVIDER=local` | `OPENAI_API_KEY`, `EMBEDDING_MODEL` |
| PostgreSQL + pgvector | App + vector store | SQLAlchemy + `retrieval_service` | `DATABASE_URL` (`postgres:5432` in compose, `localhost:5433` host, Neon `sslmode=require` commented) |
| Redis | Celery broker + result backend | `worker/celery_app.py` | `REDIS_URL/CELERY_BROKER_URL/CELERY_RESULT_BACKEND` (compose `redis://redis:6379/0`, demo `127.0.0.1`, host `localhost`) |
| Local Tesseract OCR | Scanned-page OCR (worker) | `services/ocr_service.py` | `OCR_ENABLED/LANGUAGE/DPI`, `Dockerfile` apt `tesseract-ocr(+eng)` |
| Hosting — Railway | Single-container backend deploy | `backend/Dockerfile` + `supervisord.conf` | `railway.toml` (builder DOCKERFILE, healthcheck `/api/v1/health`) |
| Hosting — Docker Compose | 5-service local stack | `docker-compose.yml` | `api/worker/web/postgres/redis`, `uploads` volume, `VITE_API_BASE_URL` build-arg |
| Hosting — nginx | Serve `frontend/dist` SPA fallback | `frontend/Dockerfile:22-35` | `try_files $uri /index.html`, `:80` |

No OAuth, maps, email, payment, analytics-vendor, or separate vector-DB service observed. `opencode.json` references `https://api.inceptionlabs.ai/v1` for the dev agent (with committed key — rotate, not app runtime).

---

## 16. Background Jobs & Async Processing

**Implemented:** Celery + Redis. `backend/app/worker/celery_app.py`: `Celery("ai_study_companion", broker, backend, include=[tasks, extraction, embeddings, structure, recommendations])`, JSON ser, UTC, `task_track_started`, `broker_connection_retry_on_startup`.

| Task | Trigger | Work | DB update | Frontend status |
|---|---|---|---|---|
| `process_pdf(job_id,material_id)` (`tasks/extraction.py`, bind, max 3) | `POST .../materials` → `job_service.create_job(process_pdf)` + `.delay()` best-effort | UUID parse, idempotency guard, `extract_document_pages`, inline chunk+figures, chain downstream | `materials pending→processing→ready/failed`, `background_jobs pending→running→completed/failed`, `learning_events` | Poll `GET .../materials` + `GET /jobs/{id}`; `list_materials` masks `ready→processing` while downstream pending |
| `generate_embeddings` (`tasks/embeddings.py`) | Chained by extraction (own job row + `.delay()` best-effort) | Ordered chunks → `embed()` batched → dims check → upsert per `chunk_id` | `background_jobs`, `embeddings` | Same polling |
| `build_structure` (`tasks/structure.py`, bind, max 3) | Same chain | Re-read PDF (no vision) + stored figures → Pass1 topic map (metered) → Pass2 LOs per topic (metered, per-topic fail → `failed_topics`) → `persist_knowledge_map` | `topics/subtopics/concepts/relationships`, job row | `GET .../structure`, `.../knowledge/*` |
| `generate_recommendation(user,project)` (`tasks/recommendations.py`, max 2) | `refresh_best_effort().delay()` (fire-and-forget, swallowed, skipped under pytest) | `build_dashboard → recommend()` | `recommendations` (single-current: prior `active→expired`) | `GET .../dashboard` |
| `ping/add` (`tasks/__init__.py`) | Tests/health | Trivial | None | None |

Retry: transient `retry(countdown=2^retries*2)`; 429 in structure `60*(retries+1)`; `ValueError/FileNotFound/LookupError` → terminal `failed/None` no retry. `DOWNSTREAM_JOB_TYPES=("generate_embeddings","build_structure")` (`materials.py`) drives the ready-mask.

```text
Trigger (upload/chain) → job_service.create_job(pending) → .delay() best-effort
 → Worker (fresh engine/session) → processing/running → extract/chunk/embed/structure
 → completed/failed + material status + learning_events → Frontend poll (materials/jobs/structure)
```

Scheduled/periodic (beat): **not observed**. Queues: single default Celery queue; no priority/routing observed.

---

## 17. Deployment Architecture

- **Compose (canonical, `docker-compose.yml` 137 lines):** `postgres (pgvector/pgvector:pg16, 5433:5432, volumes postgres_data + init-pgvector.sql, healthcheck pg_isready)`, `redis (7-alpine, 6379, healthcheck ping)`, `api (build ./backend, uvicorn :8000, env DATABASE/REDIS/JWT/LLM/OCR/VISION/UPLOAD/CORS, volume uploads:/data/uploads, depends healthy pg+redis)`, `worker (same image, celery worker, same env + OCR_DPI/TIMEOUT, same volume)`, `web (build ./frontend ARG VITE_API_BASE_URL=http://localhost:8000, :5173→:80 nginx)`. Browser `localhost:8000/5173`; containers `postgres`/`redis` names; `UPLOAD_DIR=/data/uploads` identical in api+worker.
- **Backend image (`backend/Dockerfile` 47 lines, `python:3.11-slim`):** apt `tesseract-ocr(+eng) redis-server supervisor build-essential`; `pip -r requirements.txt`; bake `TextEmbedding(BAAI/bge-small-en-v1.5)` (`FASTEMBED_CACHE_PATH=/app/.fastembed-cache`); `mkdir /data/uploads`; demo defaults `REDIS 127.0.0.1`; `EXPOSE 8000`; `HEALTHCHECK /api/v1/health` via `$PORT`; default `CMD supervisord`.
- **Demo single-container (`backend/supervisord.conf` 51 lines):** `redis-server (127.0.0.1, no persist)`, `uvicorn app.main:app ${PORT:-8000}`, `celery worker --concurrency=2`, all `autorestart`.
- **Web image (`frontend/Dockerfile` 35 lines):** `node:20-alpine npm ci → build (ARG VITE_*)` + `nginx:alpine` serve `dist` with SPA fallback.
- **Railway (`railway.toml`):** `builder=DOCKERFILE dockerfilePath=backend/Dockerfile`, `healthcheckPath=/api/v1/health`, `ON_FAILURE ×10`.
- **Env:** `backend/.env.example` (95) + `frontend/.env.example` (`VITE_API_BASE_URL`, `VITE_API_V1_PREFIX=/api/v1`). Compose `environment:` overrides `.env` (must export keys in shell — documented header). Real `.env` gitignored.
- **Build/start:** `api: uvicorn app.main:app --host 0.0.0.0 --port 8000`; `worker: celery -A app.worker.celery_app worker`; `web: npm run build (tsc -b && vite build)` → nginx. Root Figma `npm run dev/build/preview` is prototype-only.
- **CORS:** `backend/app/main.py:36-47` from `CORS_ORIGINS` (default `5173+5175` + loopbacks), `allow_credentials=True`, `allow_methods/headers *`. Production must list real origins (comment in `.env.example:85-86`).
- **DB config:** `DATABASE_URL` single truth; `pool_pre_ping`; Alembic `env.py` reads it; init script enables `vector`.
- **Production arch (determinable):** Railway backend (supervisord all-in-one) + separate static web (nginx/compose `web` or Vercel-future per `docs/storage.md` — **Planned**, not built) + managed Postgres (Neon `sslmode=require` commented) + managed Redis (`rediss://` commented). **Partially implemented** — compose + Railway files exist; Vercel/S3 future only in docs.

---

## 18. Testing Architecture

- **Runner:** `pytest`, `pytest-asyncio`, `anyio` (`backend/requirements.txt:20-22`); `pyproject.toml: testpaths=["tests"]`, `asyncio_mode=auto`.
- **Counts (verified):** **67 `test_*.py`** — 60 in `tests/`, 6 in `tests/security/` (+`helpers.py`), 1 in `tests/integration/` (+inits). No frontend test runner observed (`frontend/package.json` has no `test` script; no Playwright/Cypress config found).
- **Categories observed (by filename):** `auth, authorization, security, cors, cross_project, material_access, prompt_boundaries, rate_limit, upload_hardening, user, spaces, projects, materials, upload, jobs, celery, db_session, routes, error_handling, home, health, extraction, extraction_robustness, hybrid_pdf_routing, chunking, embeddings_task, embedding_client, structure_*, knowledge*, rag_service, retrieval_isolation, tutor*, practice*, quiz_*, adaptive_quiz, confidence, open_ended_assessment, explain_back, flashcards, mastery*, mismatch, recommendation, dashboard, growth, analytics, streak, learning_events, learning_objects, ai_usage, tracking_resilience, admin*, figures, pipeline_chain`.
- **What is tested (sampled from names + services):** ownership isolation (404-not-403, cross-project RAG), upload hardening (size/magic), prompt quarantine (`<<<DATA`), LLM budget 429, chunking boundaries, embedding dims, extraction TEXT/OCR routing, structure persist idempotency, RAG retrieval scoping, tutor support-gate + citations, quiz gen/attempt/UQ race/confidence CK, SM-2 transitions, EMA mastery + caps + dual streams, mismatch gaps, recommendation scoring/expiry, dashboard/growth/analytics projections, jobs retry/idempotency, pipeline chain, admin reads, error envelope, tracking resilience (metering survives rollback, events never break caller).
- **Fixtures/mocks:** `conftest`-style helpers + `tests/security/helpers.py` (not fully read); vision disabled under `PYTEST_CURRENT_TEST`; `rate_limit.reset_budgets()` tests-only; `get_task_session` fresh engine respects test DB URL. **Partially verified** — full fixture inventory requires reading `conftest.py` (not enumerated here).
- **AI eval:** `GET /admin/ai-evaluation` heuristic endpoint + `tests/test_admin_eval.py`, `test_groq_client.py`, `test_embedding_client.py`; no LLM-judge harness observed (docs flag as gap — `docs/evaluation-report.md`).
- **E2E:** **Not implemented** (Phase 56 pending per `docs/implementation-status.md`).

---

## 19. Security Architecture

Implemented mechanisms only:

- **Password hashing:** Argon2id OWASP params (`core/security.py:6-12`); never plaintext; `UserRead` never exposes hash.
- **JWT:** HS256, `sub=user UUID`, 48 h expiry default, `iat`; `PyJWT`; distinct expired/invalid 401s; `OAuth2PasswordBearer`.
- **Authorization:** Owner joins (`authorization.py`), 404-hides-existence; generic `job.material_id=None → 404`; figures path-containment; `is_admin` gate (403).
- **Input validation:** Pydantic v2 everywhere (length/range/enum/CK-mirroring validators; e.g. quiz `num 1–20`, tutor `question 1–2000`, answers `confidence 1–5`, OE `answer 1–5000`).
- **SQL injection:** SQLAlchemy ORM + parameterized `cosine_distance`; no raw string SQL observed.
- **CORS:** Allow-list from env, never `*` in code; credentials true.
- **File validation:** `save_pdf`: 10 MB cap, `.pdf` ext, `%PDF` magic, content-type check; `UPLOAD_DIR` outside web root; shared volume api+worker only.
- **Secrets:** `.env` gitignored, `.example` placeholders; compose warns override; image bakes no secrets (demo Redis loopback). **Gap:** `opencode.json` commits a hardcoded `apiKey` (rotate — see §24).
- **Rate limiting:** In-memory sliding-window per-user (30/min) + per-project (120/min) per LLM scope (`core/rate_limit.py`); honest single-`uvicorn` comment (needs Redis for multi-worker). Auth-endpoint throttling: **not observed** beyond LLM scopes.
- **AI controls:** `WHERE project_id` before ranking; `<<<DATA>>>` quarantine + `sanitize_for_llm` (NFKC, U+FFFD, controls); JSON-mode + Pydantic parse + 1 retry; support-gate avoids ungrounded answers; metering never logs key/text; vision never raises.
- **Not observed:** refresh rotation, account lockout, email verification, 2FA, per-IP throttling, CSP headers, upload antivirus, PII redaction beyond no-log rule.

---

## 20. Observability

- **Logging:** Uvicorn/supervisor stdout/stderr (no structured logger observed in `main.py`; service-level `logger` usage **Unclear — not inventoried**).
- **Error handling:** Unified envelope `{"error":{code,message,details}}` (`core/exceptions.py` + `schemas/errors.py`); `RequestValidationError → 422` with loc/msg/type; `_safe_message` hides 5xx internals; frontend `apiError()` surfaces `error.message`/`detail`.
- **AI usage tracking — Implemented** (`services/ai_usage_service.py` 116 lines, `models/ai_usage.py`): `track_llm_call(feature, meta)` contextmanager, **separate `SessionLocal`** so metering survives caller rollback; records provider/model/prompt+completion tokens (+`tokens_estimated` fallback), latency, success/error_type/http_status, `cost_usd` via `pricing.py`, `meta`; surfaced in `GET /admin/ai-usage`, `.../ai-evaluation`, `AnalyticsPage/AIUsagePanel`.
- **Learning audit — Implemented** (`services/activity_service.py` 122 lines, `models/learning_event.py`): `record_event[_committed]` with `pg_insert ON CONFLICT DO NOTHING` on `idempotency_key`, caller-txn, never breaks caller; 11 `event_type`s; surfaced `GET /admin/activity`, `ActivityPage`, `HomeDashboard`.
- **Metrics/tracing/monitoring:** No Prometheus/Grafana/APM/Sentry observed. **Not implemented.**
- **Health checks:** `GET /api/v1/health` (DB `SELECT 1` via `check_db_connection` — verify in `db/session.py` + `api/v1/health.py`); Docker `HEALTHCHECK`, compose `pg_isready`/`redis-cli ping`, Railway `healthcheckPath`. Admin `GET /admin/health` aggregates.

---

## 21. Architecture Decisions

- **Decision:** Frozen stack + thin routers → services; sync tutor/quiz-gen (<3 s) vs Celery else. **Implementation:** `main.py` 19 thin routers; `services/*` own logic; `worker/tasks/*` for PDF/embeddings/structure/reco. **Reason:** Blueprint contract, prototype speed. **Evidence:** `docs/architecture-decisions.md:ADR-001/002`, `README.md:9-20`.
- **Decision:** Single Postgres truth, denormalized `project_id` everywhere, `require_project_access` 404-not-403, vector `WHERE project_id` before ranking. **Implementation:** `project_id` on chunks/embeddings/concepts/etc.; `authorization.py` joins; `retrieval_service.py:53-82`. **Evidence:** `docs/architecture-decisions.md:ADR-003`.
- **Decision:** Argon2id + locked CORS + LLM budgets + upload sniffing + AI-no-DB + `<<<DATA>>>` quarantine + PyMuPDF worker-only. **Implementation:** `core/security.py`, `main.py:36-47`, `core/rate_limit.py`, `storage_service.py`, `groq_client.sanitize_for_llm`, tutor `DATA` prompt, `document_extraction_service` imported only in worker path. **Evidence:** ADR-004.
- **Decision:** Celery jobs `process_pdf/generate_embeddings/build_structure/...` with `pending→running→completed/failed`, idempotency (skip-if-topics, delete-chunks-before-insert). **Implementation:** `background_jobs` table, `tasks/extraction.py` guards, `chunking.persist_chunks`, `structure_persistence` upserts. **Evidence:** ADR-005 (job names drifted slightly — `evaluate_assessment/update_mastery` inline now, not separate jobs).
- **Decision:** Thin `GroqClient/EmbeddingClient`, Pydantic JSON, 1 re-prompt then `failed`, `detected_concept_id` nullable, confidence≠mastery. **Implementation:** `ai/groq_client.chat_json`, `MCQOutline/TutorOutline` parses, `confidence` CK separate from mastery. **Evidence:** ADR-006.
- **Decision:** `Base+SessionLocal+get_db`, Alembic owns schema. **Implementation:** `db/base.py`, `db/session.py`, 28 migrations. **Evidence:** ADR-007.
- **Decision:** Local 384-d embeddings (not OpenAI 1536). **Implementation:** `fastembed BAAI/bge-small-en-v1.5`, `Vector(384)`, baked in `Dockerfile:26`. **Reason if documented:** No key/network after download; prototype cost. **Evidence:** `services/ai/embedding_client.py:1-12`, `models/embedding.py:12`; contradicts `README.md:15-17` (1536) — reason for switch not explicitly documented in code. `Reason not explicitly documented.`
- **Decision:** 2-pass structure extraction + CORE/SUPPORTING/REFERENCE + 5 relation types + rollup = mean of practiced CORE. **Implementation:** `structure_extraction_service` (topic map → LOs), `concept_relationship.py` CKs, `rollup_service.py`, `mastery_levels.py`. **Evidence:** `docs/learning-model-design.md` (Phases A–D, implemented 2026-09-16 per status doc).
- **Decision:** Separate `learning_events` (caller txn, idempotent) vs `ai_usage` (dedicated session, per-attempt cost), choke-point `chat_json`, no PII/prompts. **Implementation:** `activity_service.py`, `ai_usage_service.py`. **Evidence:** `docs/usage-tracking.md`.
- **Decision:** Single-container demo (supervisord redis+api+worker) + compose 5-service dev + Railway backend pin. **Implementation:** `supervisord.conf`, `docker-compose.yml`, `railway.toml`. **Reason if documented:** Demo portability. **Evidence:** `Dockerfile:33-47` comments.

---

## 22. Current Architecture Diagram Specification

### Components (only what exists)

1. `Browser User (student/admin)`
2. `Product SPA (frontend/: React Router + AuthContext + apiClient)` — port 5173 (nginx :80 in container)
3. `Figma Prototype SPA (src/)` — dev-only, mock data, port 8443 (`$PORT`) — include as dashed/legacy
4. `FastAPI (backend/app/main.py, 19 routers, /api/v1)` — :8000
5. `PostgreSQL 16 + pgvector (VECTOR 384)` — 5433 host / 5432 container
6. `Redis 7` — 6379 (broker + backend)
7. `Celery Worker (extraction/embeddings/structure/recommendations)` — same image as API
8. `Filesystem Volume (/data/uploads: PDFs + figure PNGs)` — shared api+worker
9. `LLM Provider (Groq openai/gpt-oss-20b | Inception mercury-2.5)` — HTTPS JSON
10. `Local Embeddings (fastembed BAAI/bge-small-en-v1.5, in-worker)` — in-process
11. `Vision Provider (NaraRouter stepfun-3.7-flash)` — HTTPS (worker only)
12. `OCR (Tesseract eng, in-worker)` — in-process
13. `nginx (frontend/Dockerfile SPA fallback)` — :80→:5173
14. `supervisord bundle (demo: redis+api+worker)` — Railway/single-container only

### Connections

```text
Browser User → Product SPA — HTTP(S), page/app shell
Product SPA → FastAPI — HTTPS/REST JSON + Bearer JWT, all /api/v1 (VITE_API_BASE_URL+PREFIX)
Product SPA → nginx — static dist + SPA fallback (prod web container)
FastAPI → PostgreSQL — TCP SQLAlchemy+psycopg (DATABASE_URL), app data + pgvector queries
FastAPI → Redis — TCP enqueue (CELERY_BROKER_URL) best-effort .delay()
Celery Worker → Redis — TCP dequeue/results
Celery Worker → PostgreSQL — TCP fresh engine per task, status + vectors + structure
FastAPI + Worker → Filesystem Volume — POSIX read/write PDFs/PNGs (UPLOAD_DIR identical mount)
FastAPI/Worker → LLM Provider — HTTPS OpenAI-compat chat/completions JSON mode (GROQ/INCEPTION keys)
Worker → Local Embeddings — in-process fastembed (no network after bake)
Worker → Vision Provider — HTTPS OpenAI-compat image_url (NARAROUTER key, 20 s timeout, never-raises)
Worker → OCR — in-process Tesseract render (DPI 300)
FastAPI → Browser User — JSON envelope {data} or {error:{code,message,details}} + status codes
Railway → FastAPI — HTTPS healthcheck GET /api/v1/health
Figma Prototype SPA - - > FastAPI — NONE (no API calls; mock only, dashed)
```

### Diagram Layers

```text
Users (student, admin)
 ↓
Frontend (Product SPA [+ Prototype dashed legacy] + nginx)
 ↓ HTTPS/REST Bearer JWT
API (FastAPI 19 routers + CORS + budgets + envelope)
 ↓ SQLAlchemy / Celery delay
Application Services (tutor/quiz/mastery/reco/analytics + retrieval/RAG + extraction/chunking)
 ↓ TCP / POSIX / HTTPS
Data / AI / External (Postgres+pgvector, Redis, Volume, Groq/Inception, fastembed, NaraRouter, Tesseract)
 ↓
Deployment (Compose 5-svc | Railway supervisord single-container)
```

---

## 23. Diagram Requirements

1. **System Architecture** — Purpose: end-to-end request→response across SPA/API/DB/workers/AI. Components: user, SPA, FastAPI, Postgres+pgvector, Redis, worker, volume, Groq/Inception, fastembed, NaraRouter. Connections: REST, SQL, Celery, POSIX, HTTPS. Labels: `/api/v1`, `Bearer`, `VECTOR(384)`, `process_pdf→embeddings→structure`. Detail: component-level, no code.
2. **Deployment Architecture** — Purpose: how to run/ship. Components: compose 5 services + ports/volumes + Railway single-container + nginx. Connections: `5433:5432`, `6379`, `8000:8000`, `5173:80`, `uploads:/data/uploads`, healthchecks. Labels: build contexts, ARGs, `HEALTHCHECK`, `supervisord`. Detail: infra-level with env names (no values).
3. **Database ERD** — Purpose: table relationships. Components: all 23 tables (§7). Connections: FK CASCADE/SET NULL, UQs, CK enums. Labels: PK `UUID`, `Vector(384)`, `JSONB`, `Numeric`. Detail: column-level for PK/FK/UQ/CK.
4. **Document Processing Pipeline** — Purpose: upload→ready trace. Components: SPA, `materials.py`, `storage`, `background_jobs`, `process_pdf`, PyMuPDF/OCR/tables/vision, chunking, `save_figures`, embeddings/structure jobs. Connections: sync upload vs async chain, retry/backoff, ready-mask. Labels: `10MB/%PDF`, `TEXT/OCR`, `2000/200`, `N×384`, `pending→running→completed/failed`. Detail: swimlane with failure branches.
5. **RAG Pipeline** — Purpose: retrieval→answer grounding. Components: query, `embed_one`, pgvector `cosine_distance`, `assemble_context`, prompt `<<<DATA`, `chat_json`, `TutorOutline`, citations/figures. Connections: `WHERE project_id`, `top_k 5/6000 chars`, `distance>0.5 gate`. Labels: `SUPPORTED_MAX_DISTANCE=0.5`, `EXCERPT 280`, `word-snapped …`. Detail: step-level with gates.
6. **AI Tutor Flow** — Purpose: chat + conversations UX→DB. Components: `TutorChat`, `tutor.py`, `tutor_service`, `tutor_conversation_service`, `tutor_conversations/messages`, `ai_usage`. Connections: ask vs threaded messages, title-after-3, no-evidence rule. Labels: `supported bool`, `citations[]`, `follow_ups[]`, `seq`. Detail: sequence diagram.
7. **Authentication Flow** — Purpose: register→login→authed→expiry. Components: SPA `AuthContext`, `auth.py`, Argon2id, JWT, `get_current_user`, `ProtectedRoute`, axios 401 handler. Connections: `241 UserRead`, `Token`, `Bearer`, 401 expired vs invalid. Labels: `HS256`, `48 h`, `localStorage:access_token`. Detail: sequence with error branches.
8. **Mastery/Assessment Flow** — Purpose: evidence→mastery→mismatch→recommendation. Components: quiz/practice/OE/flashcard/tutor writers, `mastery_evidence`, `mastery_service` EMA + caps, `mismatch_service`, `recommendation_service`, dashboard/growth/analytics. Connections: weights `.35/.25/.20/.15/.05`, caps `40/70/60/75`, gap≥25. Labels: `mcq vs applied`, statuses `34/66/85`, action types. Detail: data-flow with formulas.
9. **Major User Journey** — Purpose: spaces→projects→upload→structure→tutor→quiz→dashboard. Components: `SpacesPage→SpaceProjectsPage→ProjectDetailPage(?tab=)`, materials/structure/tutor/quiz/dashboard features + backing endpoints. Connections: tab handoffs (`quizDirect` etc.), polling, accept/dismiss. Detail: UX-journey, no internals.

Omit: streaming diagram (not built), microservice mesh (monolith), separate vector-DB (pgvector in-DB), scheduler/beat (none), OAuth (none).

---

## 24. Architecture Risks / Gaps

- **Issue:** Root `src/` prototype imports missing (`context/AppContext`, `data/mockData`, `types.ts` mismatch) — `src/App.tsx:2`, `components/Layout.tsx:8`, `pages/SpacesPage.tsx:3` fail. **Evidence:** `Test-Path` false per exploration; `src/` listing has no `context/`/`data/`. **Impact:** Root `npm run dev/build` broken; confusion vs product `frontend/`. **Workaround:** Use `frontend/` only (per `AGENTS.md` product is `frontend/`? actually AGENTS describes Figma scaffold — discrepancy, see §25).
- **Issue:** `README.md` stale (claims `VECTOR(1536)`, JWT 60 min, Phase 02, no flashcards). **Evidence:** `README.md:15-17,25,139,145` vs `models/embedding.py:12 (384)`, `core/config.py:26 (2880)`, `implementation-status.md (Phase 49)`, `flashcards.py`. **Impact:** Onboarding/architecture drift. **Workaround:** Trust code + `docs/implementation-status.md`.
- **Issue:** OpenAI embedding path broken by dims (1536 vs `Vector(384)`; `.env.example:35-40` warns resize needed). **Evidence:** `models/embedding.py:39`, `services/ai/embedding_client.py` (local only). **Impact:** Setting `EMBEDDING_PROVIDER=openai` fails. **Workaround:** Stay `local` (default).
- **Issue:** `opencode.json` commits hardcoded `apiKey: sk_11c84...`. **Evidence:** `opencode.json` (per docs-task read). **Impact:** Secret leak; rotate key. **Workaround:** None — rotate + git-history purge.
- **Issue:** In-memory LLM budgets don't share across workers. **Evidence:** `core/rate_limit.py` comment (single `uvicorn`, needs Redis for scale). **Impact:** Multi-replica bypass. **Workaround:** Single api replica (compose default).
- **Issue:** `VITE_API_BASE_URL=http://localhost:8000` baked at build time. **Evidence:** `frontend/Dockerfile:14-17`, `docker-compose.yml:125`. **Impact:** Image not portable to other hosts. **Workaround:** Rebuild per env.
- **Issue:** Duplicate `frontend-figmadesigned/` + `dist/` + `node_modules/` committed. **Evidence:** Directory listing. **Impact:** Bloat/confusion. **Workaround:** Ignore; use `frontend/`.
- **Issue:** No refresh tokens, no E2E, no APM/Sentry, no beat scheduler, no frontend tests. **Evidence:** Absence in `dependencies/`, `package.json` scripts, `worker/celery_app.py` (no beat), `tests/` backend-only. **Impact:** Session UX (re-login 48 h), release risk, blind spots. **Workaround:** Manual QA + admin health/usage panels.
- **Issue:** Compose `environment:` overrides `.env` (dummy keys fail AI). **Evidence:** `backend/.env.example:5-12`, `docker-compose.yml:52-58` dummies. **Impact:** AI 502 until keys exported in shell. **Workaround:** Export `GROQ/INCEPTION_API_KEY` + `LLM_PROVIDER` before `compose up` (documented).

---

## 25. Unknowns / Requires Confirmation

## Unknowns / Requires Confirmation

- Whether `src/` (Figma Make) or `frontend/` is the intended going-forward UI — `AGENTS.md`/`vite.config.ts` describe `src/` on `$PORT` 8443, but `README.md`/`docker-compose.yml`/`railway` serve `frontend/` on 5173; both have overlapping pages. Requires product-owner confirmation.
- Purpose/ownership of `frontend-figmadesigned/` (export snapshot vs active fork?) — no README reference found.
- Production frontend host (Vercel future per `docs/storage.md` vs compose `web` vs Railway backend-only?) — `railway.toml` pins backend only.
- Real LLM spend/latency SLOs — `pricing.py` estimates exist but no budget alerts or per-tenant quotas observed.
- `ADMIN_EMAIL/PASSWORD` seeding — commented in `.env.example:93-95`; seeder implementation not verified.
- `scripts/backfill_learning_events.py` scope/idempotency — file listed but not read in full.
- `docs/architecture/diagrams/` currency (draw.io vs code) — not diffed.
- `Project_Requirements (1).pdf` / `DAA_Sort.pdf` normative status — not parsed (binary).
- Test-suite pass rate on this checkout — not executed (read-only analysis).
- Log aggregation/retention and PII handling beyond no-prompt-logging — no config found.

---

## Summary Counts

- **Major components discovered:** 14 (product SPA, prototype SPA (legacy), nginx, FastAPI 19 routers, Postgres+pgvector, Redis, Celery worker (4 task modules), shared volume, Groq/Inception LLM, local fastembed, NaraRouter vision, Tesseract OCR, supervisord demo bundle, Compose/Railway deploy targets).
- **API domains/endpoints:** 19 router domains, **55 route decorators** (health 1, auth 3, spaces 3, projects 4 incl. direct, materials 2, jobs 1, structure 1, tutor 7, quizzes 4, assessment 3, dashboard 4, growth 1, analytics 2, admin 7, practice 1, knowledge 4, flashcards 3, figures 2, me 2).
- **Database tables/models:** 21 model files → **23 tables** (users, spaces, projects, materials, background_jobs, document_chunks, embeddings, topics, subtopics, concepts, concept_relationships, material_figures, quizzes, quiz_questions, quiz_attempts, quiz_answers, flashcards, mastery_evidence, learning_events, tutor_conversations, tutor_messages, recommendations, ai_usage) + 1 non-table dataclass (`Mismatch`).
- **Major AI workflows:** 7 (tutor ask/chat + quiz-plan, quiz generation, open-ended generate, open-ended/explain-back grade, 2-pass structure extraction, vision figure captioning, local embedding ingestion) + deterministic (non-LLM) mastery/mismatch/recommendation math.
- **Major data flows:** 12 (auth, project creation, upload, processing, RAG query, tutor, quiz gen/submit, practice, open-ended, flashcards, mastery calc, recommendations).
- **Recommended diagrams:** 9 (system, deployment, ERD, document pipeline, RAG, tutor sequence, auth sequence, mastery/assessment data-flow, user journey).
- **Important unknowns:** 10 (UI going-forward, figmadesigned ownership, prod frontend host, SLOs, admin seeding, backfill script, diagram currency, PDFs normative status, test pass rate, log/PII policy).
