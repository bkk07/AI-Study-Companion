# Architecture Diagram Specifications — AI Study Companion
> Source of truth: actual repository implementation (inspected file-by-file) + authoritative spec `Project_Requirements (1).pdf` (PRD v3.0).
> Rule: every node path below was verified to exist. No invented components. README was NOT used as source of truth.
> How to use: recreate each diagram manually in draw.io / diagrams.net using the Nodes + Connections + Visual Design Specification. Every important component carries an explicit text label + repository path label for machine-readability.

**Conventions used in all 15 diagrams**
- Labels: every important box shows `Component Name` on line 1 and `repository/path` on line 2 (monospace, 8–9pt).
- Numbered flows: edges that form the primary path are labeled `1.`, `2.`, … in flow order.
- Failure edges: dashed red arrows labeled `F1`, `F2`, … pointing to an explicit failure/exit node (never a dead end).
- Security boundaries: dashed orange container. AI-calling boundary: dashed purple container. External network boundary: grey container.
- Legend (put on every diagram): rectangle = process/service; cylinder = database/storage; stick figure = human actor; dashed container = trust/boundary; solid arrow = sync request; dashed arrow = async/fire-and-forget; red dashed = failure path.

---

## Diagram 1 — System Context / High-Level Architecture

### A. Diagram Purpose
Shows the whole running system in one view: who uses it, the two deployable frontends (which one is actually deployed), the single FastAPI backend, data/knowledge stores, background worker, and external AI providers. Answers "what talks to what, and where does AI cross the network boundary."

### B. Nodes
| Node | Type | Technology | Responsibility | Repository path | Class / function |
|---|---|---|---|---|---|
| Learner (Browser) | Actor | Browser + React SPA | Creates spaces/projects, uploads PDFs, chats with tutor, takes quizzes, views mastery/growth/analytics | `frontend/src/features/...` (e.g. `frontend/src/features/tutor/TutorChat.tsx`) | — |
| Admin (Browser) | Actor | Browser + React SPA (admin route) | Inspects users, activity, AI usage, evaluation aggregates, job health | `frontend/src/features/admin/AdminPage.tsx` | — |
| Deployed Frontend (Nginx SPA) | Application | React 19 + Vite + nginx:alpine | Serves the actually-deployed UI; all API calls via axios to `/api/v1` | `frontend/src/App.tsx`, `frontend/src/main.tsx`, `frontend/Dockerfile` | `AppRoutes`, `AuthProvider` |
| Figma-Make Prototype Frontend (NOT deployed) | Application (design prototype) | React + Vite + Tailwind (root scaffold) | Early UI prototype only; NOT served by `frontend/Dockerfile`, `docker-compose.yml`, or `railway.toml` | `src/App.tsx`, `src/main.tsx`, `vite.config.ts` | `ActivePage` |
| FastAPI Backend | Application | FastAPI + Uvicorn (`app.main:app`) | Versioned REST API (`/api/v1`), auth, validation, authorization, error envelope, thin routes → services | `backend/app/main.py` | `app`, `root()` |
| Business-logic Services | Process group | Python service modules | Tutor/RAG, quiz, assessment, mastery, recommendations, analytics, storage, chunking, extraction | `backend/app/services/` (e.g. `tutor_service.py`, `retrieval_service.py`) | see Diagrams 6–10 |
| Celery Worker | Process | Celery 5 + Redis broker/backend | Runs `process_pdf`, `generate_embeddings`, `build_structure`, `generate_recommendation` without blocking HTTP | `backend/app/worker/celery_app.py`, `backend/app/worker/tasks/` | `process_pdf`, `generate_embeddings`, `build_structure`, `generate_recommendation` |
| PostgreSQL + pgvector | Database | `pgvector/pgvector:pg16`, SQLAlchemy 2, Alembic | All domain tables; `embeddings.embedding Vector(384)` for retrieval | `backend/app/models/`, `backend/app/db/session.py`, `docker/postgres/init-pgvector.sql` | `Base`, `UUIDTimestampMixin` |
| File Storage (uploads) | Storage | Local filesystem volume | Stores validated PDFs at `UPLOAD_DIR/{project}/{uuid}.pdf` | `backend/app/services/storage_service.py` | `save_pdf()` |
| Redis (broker + result backend ONLY) | Infrastructure | `redis:7-alpine` | Celery broker + result backend. NOT an application cache (no response/LLM/retrieval cache exists) | `docker-compose.yml`, `backend/app/core/config.py` | `celery_broker_url`, `celery_result_backend` |
| Groq API (external) | External AI | HTTPS `https://api.groq.com/openai/v1/chat/completions`, default model `openai/gpt-oss-20b` | Chat-completion JSON-mode generation for tutor/quiz/assessment/structure/title | `backend/app/services/ai/groq_client.py` | `chat_json()` |
| Inception API (external, optional) | External AI | HTTPS `https://api.inceptionlabs.ai/v1/chat/completions`, default `mercury-2.5` | Alternate provider selected by `LLM_PROVIDER=inception` | `backend/app/services/ai/groq_client.py`, `backend/app/core/config.py` | `chat_json()`, `Settings.llm_provider` |
| Local Embeddings (in-process) | Library | `fastembed TextEmbedding('BAAI/bge-small-en-v1.5')`, 384-dim, no network after download | Embeds queries and chunks locally | `backend/app/services/ai/embedding_client.py` | `embed()`, `embed_one()` |

### C. Connections
| # | Source → Destination | Dir | Protocol | Data | Sync/Async | Why | Repository evidence |
|---|---|---|---|---|---|---|---|
| 1 | Browser → Nginx SPA | → | HTTPS/HTTP | HTML/JS/CSS | sync | Serve UI | `frontend/Dockerfile` (nginx `try_files … /index.html`), `frontend/dist/` |
| 2 | Nginx SPA → FastAPI (`/api/v1`) | → | HTTPS/HTTP + JSON, `Authorization: Bearer <JWT>` | REST requests/responses | sync | All product operations | `frontend/src/lib/axios.ts` (`baseURL = VITE_API_BASE_URL + VITE_API_V1_PREFIX`, 15s timeout, Bearer interceptor) |
| 3 | FastAPI → PostgreSQL | ↔ | TCP, SQLAlchemy/psycopg | SQL rows | sync | Persist/read domain state | `backend/app/db/session.py` (`get_db`, `SessionLocal`) |
| 4 | FastAPI → File Storage | → | filesystem write | Validated `%PDF` bytes | sync (upload request; only `async def` route `upload_material`) | Durable PDF bytes | `backend/app/api/v1/materials.py`, `backend/app/services/storage_service.py` |
| 5 | FastAPI → Celery/Redis | → | Redis protocol (`.delay()`) | `job_id, material_id` task messages | async fire-and-forget | Don't block upload on extraction | `backend/app/api/v1/materials.py` (`process_pdf.delay`), `backend/app/worker/tasks/extraction.py` |
| 6 | Celery Worker → PostgreSQL | ↔ | SQLAlchemy (fresh `get_task_session()`) | chunks, embeddings, topics/concepts, job rows | async (worker) | Background persistence | `backend/app/worker/tasks/__init__.py`, `extraction.py`, `embeddings.py`, `structure.py` |
| 7 | Celery Worker → File Storage | → | filesystem read | PDF bytes re-read for page extraction | async | Extraction input | `backend/app/worker/tasks/extraction.py`, `structure.py:_load_pages` |
| 8 | Backend (API + Worker) → Groq/Inception | → | HTTPS POST JSON (`response_format json_object`, 60s timeout) | prompts (with `<<<DATA>>>` wrapping), JSON outlines back | sync (blocking call inside request or task) | All LLM generation | `backend/app/services/ai/groq_client.py` (`httpx.post timeout=60.0`) |
| 9 | Backend → Local embedding model | ↔ | in-process call | texts ↔ 384-float vectors | sync | Retrieval vectors, no network | `backend/app/services/ai/embedding_client.py` (`lru_cache _local_model`) |
| 10 | Redis ↔ FastAPI/Worker | ↔ | Redis | Celery broker + result backend messages | async | Task transport only | `docker-compose.yml`, `backend/app/worker/celery_app.py` |

### D. Data Flow
1. Learner/admin loads Nginx SPA (`frontend/dist` via `frontend/Dockerfile`).
2. SPA calls `http(s)://<API>/api/v1/...` with Bearer JWT (`frontend/src/lib/axios.ts`).
3. `backend/app/main.py` applies CORS, error-envelope handlers, routes to one of 18 `backend/app/api/v1/*` routers.
4. Route enforces `get_current_user` → ownership dep → optional `require_llm_budget`, then calls a service in `backend/app/services/`.
5. Service reads/writes PostgreSQL (`backend/app/db/session.py`) and, for uploads, writes the volume (`storage_service.save_pdf`); upload route enqueues `process_pdf.delay` and returns `201 {status: pending}` immediately.
6. Worker processes PDF → chunks → embeddings → knowledge map, updating `materials.status` and `background_jobs.status` polled by the UI.
7. Any LLM step calls `groq_client.chat_json` (Groq or Inception by settings) and records metering via `ai_usage_service.track_llm_call`; embeddings are always local.

### E. Failure Paths
- F1 Validation (422): `RequestValidationError` → `validation_error` envelope (`backend/app/core/exceptions.py:83-91`).
- F2 Auth (401/403): missing/expired/bad JWT → `authentication_required`; non-admin on `/admin/*` → `forbidden` (`dependencies/auth.py`, `dependencies/admin.py`).
- F3 Ownership (404): cross-user IDs hidden as `Space/Project not found` (`dependencies/authorization.py`).
- F4 Upload rejected (400/413): extension/content-type/magic/size checks (`services/storage_service.py`).
- F5 AI provider down/invalid JSON: `httpx.HTTPError` → 502 `upstream_unavailable`; malformed outline → `TutorProviderError` → 502 (`api/v1/tutor.py:47-54`); quiz `QuizGenerationError` → 422.
- F6 Retrieval empty: short-circuit `[]` before spending embedding call; tutor returns `supported=false` WITHOUT calling LLM (`services/tutor_service.py:217-220`, `services/retrieval_service.py:55-66`).
- F7 Background failure: `BackgroundJob.status=failed + error`, `Material.status=failed + error_message`; transient retries with backoff (extraction/structure `max_retries=3`, recommendations `max_retries=2`).
- F8 Metering/event failure never breaks requests: `ai_usage_service._persist` catches all; `activity_service` savepoint-based; covered by `tests/test_tracking_resilience.py`.

### F. Security Boundaries
- Authentication boundary: `OAuth2PasswordBearer(/api/v1/auth/login)` + `get_current_user` on every route except `register/login/health` (`dependencies/auth.py`).
- Authorization boundary: `get_authorized_space/project/project_in_space` (404-hiding joins) + `get_current_admin` (`dependencies/authorization.py`, `dependencies/admin.py`).
- External API boundary: only `groq_client.py` touches the public internet (Groq/Inception HTTPS); embeddings are local.
- Database boundary: `get_db` session per request with rollback+close (`db/session.py`).
- File boundary: `storage_service.save_pdf` (extension, content-type allow-list, `%PDF` magic, 10 MB cap, basename sanitize, project-scoped dir).

### G. AI Boundaries
- AI used during development: coding assistants / agents / design tools that produced this repo (document in AI-usage docs; NOT in this runtime diagram — show as an off-diagram note "Dev-time AI: no runtime path").
- AI used by final product: Groq/Inception LLM via `chat_json` (tutor, quiz, open-ended grading, structure extraction, title) + local `bge-small-en-v1.5` embeddings. Draw the latter INSIDE the runtime boundary, the former OUTSIDE as a note.

### H. Requirement Traceability
- PRD §17 conceptual architecture (Frontend → API → Business Logic → Data & Knowledge → Background → AI/External → Observability) → this diagram → `backend/app/main.py`, `docker-compose.yml`, `backend/app/worker/celery_app.py`, `backend/app/services/ai/groq_client.py`.
- PRD §15 auth/data-isolation/secure APIs → Auth/AuthZ nodes → `dependencies/auth.py`, `dependencies/authorization.py`, `core/jwt.py`, `core/security.py`.
- PRD §13 async-by-design → Worker + Redis nodes → `worker/tasks/*.py`, `api/v1/materials.py`.
- PRD §5 PDF + async pipeline → Storage + Worker + pgvector nodes → `services/storage_service.py`, `worker/tasks/extraction.py`, `models/embedding.py`.

### Visual Design Specification
- Orientation: landscape A4/Letter. Layout: left-to-right swimlanes: Actors | Frontend | Backend API | Data & Storage | Background | External AI.
- Containers: `Client trust zone` (browsers), `Deployment: API+Worker+DB+Redis` (docker-compose), `External network (Groq/Inception)` grey, `Dev-time AI (off-runtime)` note box.
- Shapes: actors = stick figures; SPA/API/Worker = rectangles; PostgreSQL = cylinder labeled `PostgreSQL + pgvector (pg16)` + path `backend/app/models/`; uploads = cylinder/file shape; Redis = rectangle labeled `Redis — Celery broker/backend ONLY (no app cache)`; Groq/Inception = rectangles with `HTTPS` label.
- Arrows: solid = sync HTTP/SQL; dashed = `.delay()` async; red dashed = F-paths to `Error envelope {"error":{code,message}}` note (`backend/app/core/exceptions.py`).
- Labels: number primary path 1–7; every box line-2 shows repo path; legend bottom-right; font ≥9pt; no icons without text.

---

## Diagram 2 — Frontend Architecture

### A. Diagram Purpose
Shows the ACTUALLY DEPLOYED frontend (`frontend/`, not the root Figma prototype): router, auth plumbing, shell, feature modules, API client behavior (token, 401 handling, 30s GET cache, materials polling), and which backend endpoints each screen calls.

### B. Nodes
| Node | Type | Technology | Responsibility | Repository path | Class / function |
|---|---|---|---|---|---|
| `main.tsx` bootstrap | Entry | React 19 `createRoot` | Mounts `<App/>`, imports CSS | `frontend/src/main.tsx` | — |
| `App.tsx` router | Router | `react-router-dom BrowserRouter` | Public routes `/`, `/login`, `/register`; protected shell routes `/spaces`, `/spaces/:spaceId`, `/spaces/:spaceId/projects/:projectId`, `/admin`; tab sub-routing via `?tab=` | `frontend/src/App.tsx` | `AppRoutes`, `Home`, `NotFound` |
| `AuthContext` | State | React context + localStorage | Holds `token/user/loading`; `login/register/logout`; hydrates `GET /auth/me`; subscribes to 401 → logout+navigate | `frontend/src/context/AuthContext.tsx` | `AuthProvider`, `useAuth` |
| `axios client` | HTTP client | axios + interceptors + in-memory GET cache | `baseURL = VITE_API_BASE_URL + VITE_API_V1_PREFIX`, 15s timeout, Bearer injection, 401 → `notifyUnauthorized`, 30s GET cache, `noCache` opt-out, non-GET clears cache | `frontend/src/lib/axios.ts` | `apiClient` |
| `auth-events` bus | Utility | pub/sub set | Decouples 401 handling from navigation | `frontend/src/lib/auth-events.ts` | `subscribeUnauthorized`, `notifyUnauthorized` |
| `ProtectedRoute` | Guard | React Router wrapper | Spinner while loading; `Navigate /login` if no token | `frontend/src/components/ProtectedRoute.tsx` | `ProtectedRoute` |
| `AppShell` | Layout | React layout + sidebar | Dual public/authed shell; `PROJECT_NAV` 10 tabs via `?tab=`; `StreakFlame GET /me/streak`; space-name `GET /spaces/:spaceId` | `frontend/src/components/AppShell.tsx` | `AppShell`, `goTab` |
| Feature: auth/landing/home | Pages | React | `Login` (`POST /auth/login` + `GET /auth/me`), `Register` (`POST /auth/register` + login chain), `LandingPage` (static), `HomeDashboard` (`GET /me/home`) | `frontend/src/features/auth/Login.tsx`, `Register.tsx`, `frontend/src/features/landing/LandingPage.tsx`, `frontend/src/features/home/HomeDashboard.tsx` | — |
| Feature: spaces/projects | Pages | React | `SpacesPage` (`GET /spaces`, per-space `GET …/projects`, `POST /spaces`); `SpaceProjectsPage` (`GET /spaces/:id` + `GET …/projects`, `POST …/projects`); `ProjectDetailPage` (ownership `GET /projects/:id`, tab switch, cross-tab state) | `frontend/src/features/spaces/SpacesPage.tsx`, `frontend/src/features/projects/SpaceProjectsPage.tsx`, `ProjectDetailPage.tsx` | — |
| Feature: materials | Panel | React + polling | `GET …/materials` (`noCache:true`), `POST multipart/form-data` (120s timeout), `setInterval 5000ms` ONLY while `pending|processing` | `frontend/src/features/projects/MaterialsPanel.tsx` | — |
| Feature: tutor | Chat | React | Conversations CRUD + `POST …/messages`, `POST …/quiz-plan`, quiz handoff (`POST …/quizzes/generate` + `POST …/attempts`), flashcard deck build; cosmetic 1400ms thinking-step timer only | `frontend/src/features/tutor/TutorChat.tsx` | — |
| Feature: quiz/practice/open-ended | Pages | React | `QuizTaker` (generate → start → answer loop with confidence 1/3/5 → complete); `PracticePage/Session/Results`; `OpenEndedAnswersPage`; `QuizSetup/Modes/ConceptDetail` | `frontend/src/features/quiz/QuizTaker.tsx`, `QuizSetup.tsx`, `QuizModes.tsx`, `ConceptDetail.tsx`, `frontend/src/features/practice/*`, `frontend/src/features/openended/OpenEndedAnswersPage.tsx` | — |
| Feature: dashboard/analytics/growth | Pages | React | `Dashboard` (`GET …/dashboard`, `POST …/refresh|accept|dismiss`); `AnalyticsPage/View` (`GET …/analytics`, `GET …/analytics/overview?time_range=`); `GrowthView` (`GET …/growth[?concept_id=]`); `OverviewView`, `ProgressMap`, `StructureView`, `Flashcards` | `frontend/src/features/dashboard/Dashboard.tsx`, `frontend/src/features/analytics/*`, `frontend/src/features/overview/OverviewView.tsx`, `frontend/src/features/progress/ProgressMap.tsx`, `frontend/src/features/structure/StructureView.tsx`, `frontend/src/features/flashcards/Flashcards.tsx` | — |
| Feature: admin | Pages | React | `AdminPage` (`GET /admin/overview` + `GET /admin/health?limit=1`, `GET /admin/users`); `ActivityPanel`, `AIUsagePanel`, `EvaluationPanel`, `HealthPanel`, `JourneyPanel` | `frontend/src/features/admin/AdminPage.tsx`, `ActivityPanel.tsx`, `AIUsagePanel.tsx`, `EvaluationPanel.tsx`, `HealthPanel.tsx`, `JourneyPanel.tsx` | — |
| Root prototype (NOT deployed) | Prototype | Figma-Make scaffold | State-driven `ActivePage` switch; exists at repo root but NOT referenced by `frontend/Dockerfile`, compose `web`, or Railway | `src/App.tsx`, `src/main.tsx`, `src/pages/**`, `src/components/**` | `ActivePage`, `AppProvider` |

### C. Connections
| Source → Destination | Dir | Protocol | Data | Sync/Async | Why | Evidence |
|---|---|---|---|---|---|---|
| `main.tsx` → `App.tsx` | → | import/render | — | sync | Bootstrap | `frontend/src/main.tsx` |
| `App.tsx` → `AuthContext` | ↔ | React context | token/user | sync | Auth state | `frontend/src/App.tsx` (`AuthProvider`) |
| Any page → `axios client` | → | function call | `GET/POST /api/v1/...` | async `await apiClient` | Sole HTTP path (never raw `fetch`) | every `features/*` file |
| `axios` → Backend `/api/v1` | → | HTTP+JSON, Bearer | REST | sync req/resp | Data | `lib/axios.ts` baseURL/timeout |
| Backend 401 → `auth-events` → `AuthContext` | → | pub/sub + navigate | logout | async | Central session expiry | `lib/axios.ts` interceptor, `lib/auth-events.ts`, `context/AuthContext.tsx` |
| `ProjectDetailPage` → tab pages | → | props + `?tab=` | `quizFocus, quizDirect, practiceDirect, flashcardsDirect` | sync | Cross-tab handoff (tutor→quiz, practice→session) | `features/projects/ProjectDetailPage.tsx` |
| `MaterialsPanel` → Backend (poll) | → | HTTP GET `noCache` every 5s (gated) | material list with status overlay | async poll | Reflect background job progress | `features/projects/MaterialsPanel.tsx:77` |
| No WebSocket/SSE anywhere | — | — | — | — | Prototype uses polling only | grep: no `EventSource/WebSocket/StreamingResponse` in `frontend/src` or `backend/app` |

### D. Data Flow
1. `main.tsx` renders `App.tsx` → `AuthProvider` hydrates `GET /auth/me` if token exists.
2. `/` shows `LandingPage` (anonymous), redirects admins to `/admin`, else `HomeDashboard` (`GET /me/home`).
3. Protected shell (`ProtectedRoute` + `AppShell`) gates `/spaces…`, `/admin`.
4. Project page gates ownership (`GET /projects/:id`) then renders the `?tab=` child; tabs call their endpoints via `apiClient` with `useEffect` + `cancelled` flag + `ErrorBox/LoadingState`.
5. Mutations clear the 30s GET cache (client behavior); only materials polling bypasses it (`noCache:true`).

### E. Failure Paths
- 401 (except login/register): token removed + `notifyUnauthorized` → logout → `/login` (`lib/axios.ts`, `context/AuthContext.tsx`).
- API error shape: parsed by `lib/api-error.ts` from `{error:{message}}` or `detail`; pages show `ErrorBox`, keep prior state.
- Materials upload: 400 (bad PDF), 413 (over limit), polling continues while `pending|processing`, shows `failed + error_message` terminally.
- Ownership failure: `GET /projects/:id → 404` blocks the whole detail page (backend hides existence).
- No streaming fallback needed (no streaming implemented); long uploads use 120s timeout.

### F. Security Boundaries
- Token storage: `localStorage access_token`, injected as Bearer; cleared on 401.
- Route guard: `ProtectedRoute` (frontend UX only — real enforcement is backend `get_current_user` + ownership deps).
- Admin UX gate: `user?.is_admin → /admin`; real gate is `get_current_admin` (403).

### G. AI Boundaries
- Dev-time AI: Figma-Make scaffold + coding assistants produced UI code (off-diagram note).
- Product AI: frontend contains NO model calls; every AI behavior is a backend endpoint (`/tutor/*`, `/quizzes/generate`, `/assessment/*`, `/dashboard/*`). Label the frontend "no direct AI provider calls."

### H. Requirement Traceability
- PRD §16 (Home: continue/recent/progress/attention/next-action; Admin: users/activity/AI/health) → `HomeDashboard.tsx` (`GET /me/home`), `AdminPage.tsx` + panels → backend `home_service.py`, `api/v1/admin.py`.
- PRD §4 (dashboard flow Materials→Tutor→Quiz→Growth→Analytics) → `AppShell PROJECT_NAV` + `ProjectDetailPage ?tab=` routing.
- PRD §15 performance (pagination, async, avoid unnecessary calls) → 30s GET cache, gated 5s materials polling, `Promise.allSettled` counts.

### Visual Design Specification
- Orientation: portrait A4. Layout: top-down: Bootstrap → Router → Guards/Shell → Feature grid → HTTP client → Backend edge.
- Containers: `Deployed: frontend/` vs `Prototype (NOT deployed): src/` (greyed, dashed, labeled "do not draw runtime arrows from here").
- Shapes: all UI = rectangles; `axios client` = hexagon/cylinder-optional but label path; 401 path = red dashed to `auth-events → logout`.
- Labels: each feature box lists 1–3 endpoint strings it calls; table of `?tab=` values on `ProjectDetailPage`; legend; ≥9pt.

---

## Diagram 3 — Backend Architecture

### A. Diagram Purpose
Shows the FastAPI request pipeline in execution order: middleware → versioned routers (all 18) → dependencies (auth/authz/rate-limit) → services → DB, and how errors/AI-metering plug in. Proves "thin routes, service-owned logic."

### B. Nodes
| Node | Type | Technology | Responsibility | Repository path | Class / function |
|---|---|---|---|---|---|
| `app` + CORS + error handlers | Entry | FastAPI + `CORSMiddleware` | Title/version, `register_error_handlers`, origin allow-list from settings | `backend/app/main.py` | `app`, `register_error_handlers` |
| `Settings` | Config | `pydantic-settings BaseSettings` + `lru_cache` | DB/Redis/JWT/LLM/OCR/upload/CORS/rate-limit env | `backend/app/core/config.py` | `Settings`, `get_settings` |
| `get_db` session | DB plumbing | SQLAlchemy `sessionmaker`, `pool_pre_ping` | Per-request session, rollback-on-exception, close; `SELECT 1` health | `backend/app/db/session.py` | `get_db`, `SessionLocal`, `check_db_connection` |
| `Base` + mixins | ORM base | `DeclarativeBase` | UUID PK + `created_at/updated_at` for all tables | `backend/app/db/base.py` | `Base`, `UUIDTimestampMixin` |
| Auth deps | Guard | `OAuth2PasswordBearer`, PyJWT HS256 | `get_current_user` (401 expired/invalid), `get_current_admin` (403) | `backend/app/dependencies/auth.py`, `backend/app/dependencies/admin.py` | `get_current_user`, `get_current_admin` |
| Ownership deps | Guard | SQLAlchemy joins | `get_authorized_space/project/project_in_space` (404-hiding) | `backend/app/dependencies/authorization.py` | `get_authorized_*` |
| Rate-limit dep | Guard | in-memory sliding window (`threading.Lock`) | `require_llm_budget(scope)` for `tutor/quiz-generate/assessment/explain-back`; 429 on exhaustion | `backend/app/core/rate_limit.py` | `require_llm_budget`, `check_llm_budget` |
| 18 routers (`/api/v1/*`) | Controller | FastAPI `APIRouter` | Auth, spaces, projects (+direct), materials, me, jobs, structure, tutor, quizzes, assessment, dashboard, growth, analytics, admin, practice, knowledge, flashcards, health | `backend/app/api/v1/*.py` | per-file `router` |
| Service layer | Logic | Python modules | All domain + AI logic (see Diagrams 5–10) | `backend/app/services/*.py`, `backend/app/services/ai/*.py` | — |
| Error envelope | Middleware | Starlette handlers | `{error:{code,message,details}}`, 422 details `[{loc,msg,type}]`, 500 never leaks | `backend/app/core/exceptions.py`, `backend/app/schemas/errors.py` | `register_error_handlers`, `build_envelope` |
| Schemas | DTO | Pydantic v2 | Request/response validation per domain | `backend/app/schemas/*.py` | e.g. `tutor.py`, `quiz.py`, `assessment.py` |

Router inventory (draw as a stacked strip, not 18 separate swimlanes): `auth(/auth)`, `spaces(/spaces)`, `projects(/spaces/{space_id}/projects + /projects)`, `materials(/projects/{project_id}/materials)`, `tutor(/projects/{project_id}/tutor)`, `quizzes(/projects/{project_id}/quizzes)`, `assessment(/projects/{project_id}/assessment)`, `practice(/projects/{project_id}/practice)`, `growth`, `analytics`, `dashboard`, `knowledge`, `structure`, `flashcards` (all `/projects/{project_id}/…`), `jobs(/jobs)`, `me(/me)`, `admin(/admin)`, `health(/health)`.

### C. Connections
| Source → Destination | Dir | Protocol | Data | Sync/Async | Why | Evidence |
|---|---|---|---|---|---|---|
| Client → `app` (CORS) | → | HTTP | any `/api/v1/*` | sync | Origin gate | `main.py:36-46` (`cors_origins` split, allow_credentials) |
| `app` → router | → | ASGI dispatch | path → handler | sync | Versioned routing | `main.py:49-67` (18 `include_router(prefix="/api/v1")`) |
| Router → `get_current_user` | → | `Depends` | JWT `sub` → `User` | sync | Authentication | all routers except register/login/health |
| Router → ownership dep | → | `Depends` | space/project join check | sync | Isolation (404-hiding) | `authorization.py`; e.g. `tutor.py:32-38` |
| Router → `require_llm_budget` | → | `Depends` (AFTER ownership) | user+project sliding-window consume | sync | Abuse guard; ordering guarantees 404 before 429 | `core/rate_limit.py:77-89` docstring |
| Router → service | → | function call | DTOs → domain result | sync (except `upload_material` `async`) | Thin-route discipline | e.g. `materials.py` → `storage_service/job_service/worker`, `tutor.py` → `tutor_service` |
| Service → `get_db` session | ↔ | SQLAlchemy | ORM rows | sync | Persistence | `db/session.py` |
| Service → `groq_client` / `embedding_client` | → | HTTPS / in-process | prompts/vectors | sync | AI steps | `services/ai/*` |
| Any raise → error handlers | → | exception | `HTTPException/ValidationError/Exception` | sync | Uniform envelope | `core/exceptions.py:102-105` |

### D. Data Flow
1. Request hits `app` → CORS → router match (`/api/v1` prefix).
2. `Depends` chain runs: `get_db` → `get_current_user` (or public for register/login/health) → ownership (`get_authorized_*`) → `require_llm_budget` (LLM routes only).
3. Handler validates Pydantic schemas (`schemas/*`), calls exactly one domain service, maps domain errors (`ValueError→400`, `LookupError→404`, `QuizGenerationError/OpenEndedAssessmentError→422`, `TutorProviderError/httpx→502`, `RuntimeError→500`).
4. Unhandled cases fall to `register_error_handlers` envelope; 500 messages are scrubbed.

### E. Failure Paths
- 422 request validation with `details[]` (`exceptions.py:83-91`); domain `ValueError→400`, `LookupError→404`.
- 401 expired/invalid token (with `WWW-Authenticate: Bearer`); 403 non-admin.
- 404 ownership-hiding (never 403 for foreign IDs).
- 429 `LLM request budget exhausted — retry shortly` (only tutor/quiz-generate/assessment/explain-back scopes).
- 413/415/400 upload rejections; 502 upstream AI; 500 scrubbed `Internal server error`.
- Only `async def` is `upload_material` (awaits `save_pdf`); everything else sync `def` — no hidden async paths.

### F. Security Boundaries
- Draw three nested guards around every protected router box: Auth (JWT) → Ownership (space/project join) → Budget (LLM scopes). Admin routers add `get_current_admin` instead of ownership.

### G. AI Boundaries
- Dev-time AI: none in this diagram (code-generation only).
- Product AI: `groq_client.chat_json` + `embedding_client` are the ONLY AI-touching nodes; all other backend boxes are deterministic. Outline them in purple.

### H. Requirement Traceability
- PRD §17 (clean interfaces, validation, authz, error handling, separation) → this pipeline → `main.py`, `api/v1/*`, `dependencies/*`, `core/exceptions.py`, `schemas/*`.
- PRD §15 (auth, input validation, secure APIs) → guards → `core/jwt.py`, `core/security.py` (Argon2id), `core/rate_limit.py`.
- PRD §18 testing areas (auth/authz/validation) → `tests/test_auth.py`, `test_authorization.py`, `tests/security/*`.

### Visual Design Specification
- Orientation: landscape. Layout: left-to-right pipeline with guard rail above and error/metering rail below.
- Containers: `HTTP boundary (CORS)` outer; `Auth → Ownership → Budget` guard strip (orange dashed); `AI-calling services` (purple dashed); `DB` cylinder right.
- Shapes: middleware/handlers = rounded rectangles; 18 routers = single stacked list box (avoid 18 lanes); deps = diamonds (decision) or small rectangles on the guard rail.
- Arrows: solid black = happy path numbered 1–4; red dashed = error mapping to envelope box; legend required.

---

## Diagram 4 — Database / Data Architecture

### A. Diagram Purpose
Documents the actual relational model: all 19 tables, keys, the single `pgvector Vector(384)` column, check constraints, Alembic history, and how Spaces→Projects→everything enforces isolation at the data layer.

### B. Nodes
All models inherit `UUID PK (uuid4)` + `created_at/updated_at (now())` from `backend/app/db/base.py` (`Base`, `UUIDTimestampMixin`). No active SQLAlchemy `relationship()` definitions (only a commented line in `models/space.py:27`) — associations are FK columns.

| Table (`__tablename__`) | File | Key columns / FKs / constraints |
|---|---|---|
| `users` | `backend/app/models/user.py` | `email unique indexed`, `hashed_password` (Argon2id), `is_admin default false` |
| `spaces` | `backend/app/models/space.py` | `user_id → users.id CASCADE indexed`, `name`, `description` |
| `projects` | `backend/app/models/project.py` | `space_id → spaces.id CASCADE indexed`, `name`, `description`, `goal` |
| `materials` | `backend/app/models/material.py` | `project_id → projects.id CASCADE indexed`, `filename`, `storage_path`, `status default pending`, `extracted_text`, `page_count`, `error_message` |
| `document_chunks` (+`uq_chunks_material_index(material_id,chunk_index)`) | `backend/app/models/chunk.py` | `project_id/material_id → CASCADE indexed`, `concept_id/topic_id/subtopic_id → CASCADE nullable indexed`, `page_number`, `extraction_method`, `source_name`, `chunk_index`, `content` (no vector here) |
| `embeddings` | `backend/app/models/embedding.py` | `project_id/material_id → CASCADE indexed`, `chunk_id → document_chunks.id CASCADE unique indexed`, **`embedding Vector(384)` (ONLY pgvector column)**, `model default BAAI/bge-small-en-v1.5`; `EMBEDDING_DIMS=384` |
| `topics` (+`uq_topics_project_title`) | `backend/app/models/topic.py` | `project_id → projects.id CASCADE indexed`, `title(200)` |
| `subtopics` (+`uq_subtopics_topic_title`) | `backend/app/models/subtopic.py` | `project_id/topic_id → CASCADE indexed`, `title` |
| `concepts` (+`uq_concepts_subtopic_title`, `ck type/importance`) | `backend/app/models/concept.py` | `project_id/subtopic_id → CASCADE indexed`, `title`, `summary`, `type CONCEPT/DEFINITION/TERM/FORMULA/PROCESS/SKILL/OTHER`, `importance CORE/SUPPORTING/REFERENCE indexed`, `page_start/page_end`, `material_id → materials.id SET NULL`, `metadata JSONB default {}` |
| `concept_relationships` (+triple-unique, 4 checks) | `backend/app/models/concept_relationship.py` | `from/to → concepts.id CASCADE`, `relation PREREQUISITE_OF/RELATED_TO/EXAMPLE_OF/USES/DERIVED_FROM`, `evidence_span` (required when `created_by=llm`), `created_by structure/llm`, self-edge forbidden |
| `quizzes` (`ck mode`), `quiz_questions` (`ck difficulty`) | `backend/app/models/quiz.py` | `Quiz.project_id → CASCADE`, `mode practice/exam`, `question_count`, `time_limit_seconds`; `Question.quiz_id/concept_id → CASCADE`, `question_text`, `options JSONB`, `correct_index`, `difficulty`, `source_chunk_id → document_chunks.id CASCADE nullable` |
| `quiz_attempts`, `quiz_answers` (+`uq attempt+question`, `ck confidence 1–5`) | `backend/app/models/quiz_attempt.py` | `Attempt.quiz_id/user_id → CASCADE`, `started_at/completed_at/score`; `Answer.attempt_id/question_id → CASCADE`, `selected_index`, `is_correct` (server-computed), `confidence`, `answered_at` |
| `mastery_evidence` (+4 checks, append-only) | `backend/app/models/mastery_evidence.py` | `user/project/concept_id → CASCADE indexed`, `evidence_type mcq/open_ended/explain_back/flashcard/tutor`, `source tutor/practice/quiz/open_ended/flashcard`, `raw_score 0–100`, `difficulty`, `feedback` |
| `recommendations` (+action/status checks) | `backend/app/models/recommendation.py` | `user/project/concept_id → CASCADE indexed`, `action_type ask_tutor/targeted_quiz/explain_back/review_material/exam_mode`, `score`, `reasoning`, `status active/accepted/dismissed/expired` |
| `learning_events` (+type check, `idempotency_key unique`) | `backend/app/models/learning_event.py` | `user/project/space_id → SET NULL nullable`, `event_type` (11 values e.g. `project.created/material.ready/quiz.completed/mastery.updated`), `entity_type/entity_id` (no FK), `payload JSONB`, `idempotency_key unique` (ON CONFLICT DO NOTHING) |
| `tutor_conversations`, `tutor_messages` (+role check, `tutor_messages_seq`) | `backend/app/models/tutor_conversation.py` | `Conversation.project_id/user_id → CASCADE`; `Message.conversation_id → CASCADE indexed`, `role user/assistant`, `content`, `seq (sequence)`, `supported`, `citations JSONB`, `follow_ups JSONB` |
| `flashcards` (+front-unique, SM-2 checks, `ix next_review`) | `backend/app/models/flashcard.py` | `project/concept_id → CASCADE`, `front/back`, `source auto/manual`, `efactor≥1.30`, `interval_days`, `repetitions`, `lapses`, `next_review_at`, `total/correct_reviews` |
| `background_jobs` | `backend/app/models/background_job.py` | `job_type`, `status default pending`, `material_id → materials.id CASCADE nullable indexed`, `error`, `celery_task_id` |
| `ai_usage` | `backend/app/models/ai_usage.py` | `user/project_id → SET NULL indexed`, `feature`, `provider`, `model`, `prompt/completion_tokens`, `tokens_estimated`, `latency_ms`, `success`, `error_type`, `http_status`, `cost_usd`, `meta JSONB`. NEVER prompt/response text |
| `Mismatch` (NO table, frozen dataclass) | `backend/app/models/mismatch.py` | Derived type `concept_id/mismatch_type/mcq_mastery/applied_mastery/gap/reason` |
| Migrations + extension | `backend/alembic.ini`, `backend/alembic/env.py`, `backend/alembic/versions/` (27 files), `docker/postgres/init-pgvector.sql` | Baseline → materials/spaces/projects/jobs/chunks/topics/embeddings(`VECTOR(1536)`→384)/tutor/quizzes/mastery/recommendations/events/ai_usage/flashcards/LO fields; `CREATE EXTENSION vector` |

### C. Connections
- Ownership chain (all `CASCADE`, draw as solid FK arrows): `users → spaces → projects → {materials, topics→subtopics→concepts, chunks, embeddings, quizzes, mastery_evidence, recommendations, tutor_*, flashcards}`; `materials → chunks → embeddings (1:1 unique on chunk_id)`; `concepts → {chunks.concept_id, questions.concept_id, mastery_evidence.concept_id, recommendations.concept_id, flashcards.concept_id, relationships from/to}`.
- Nullable/weak links (dashed): `learning_events/ai_usage → user/project (SET NULL, survive deletes)`; `concepts.material_id → materials (SET NULL)`; `events.entity_id` (no FK by design).
- Isolation invariant: every project-scoped row carries `project_id`; retrieval and all reads filter `project_id` (see Diagram 11).

### D. Data Flow
Create order: `user → space → project → material → chunks → embeddings → topics → subtopics → concepts → relationships → quizzes → attempts/answers → mastery_evidence → recommendations`; cross-cutting `learning_events` + `ai_usage` appended at each step; `background_jobs` tracks async steps per material.

### E. Failure Paths
- Duplicate insert: unique constraints (`uq_*`, `idempotency_key`, `attempt+question`) → 400/409 or `ON CONFLICT DO NOTHING` (events) / `IntegrityError` race guard (answers).
- Check violation: `type/importance/mode/difficulty/evidence_type/confidence/action/status` → 422/400, never silent.
- Embedding dim mismatch (`!=384`) → `ValueError`, job `failed`.
- Migration drift: Alembic versions are the schema authority; `env.py` registers all models.

### F. Security Boundaries
- Row-ownership boundary: `Space.user_id` is the ONLY user link; project access always joins `Project→Space→user` (`dependencies/authorization.py`).
- PII boundary: `hashed_password` never returned (admin users endpoint excludes it); `ai_usage` stores no prompt/response; `learning_events.payload` holds counts/ids only.

### G. AI Boundaries
- Dev-time AI: migration/model code may be assistant-generated (off-diagram).
- Product AI artifacts IN the DB: `embeddings.embedding` (local model), `concepts/summaries/relationships` (LLM-extracted), `tutor_messages.citations/follow_ups`, `quiz_questions`, `open-ended grades/feedback`, `recommendations.reasoning`. Label these columns with a purple dot + "AI-generated".

### H. Requirement Traceability
- PRD §17 (users↔spaces↔projects↔materials↔conversations↔concepts↔assessments↔mastery↔recommendations↔activity↔AI usage) → all tables above → `models/__init__.py` registry.
- PRD §5 (chunks/concepts/metadata/relationships/page-refs/embeddings) → `chunk.py`, `concept.py`, `concept_relationship.py`, `embedding.py`.
- PRD §12 (events support activity/analytics/reco/admin + idempotency) → `learning_event.py` + `services/activity_service.py`.
- PRD §14 (model/feature/latency/tokens/cost/success) → `ai_usage.py` + `services/ai/pricing.py`.

### Visual Design Specification
- Orientation: landscape (wide ERD). Layout: ownership spine top-to-bottom left (`users→spaces→projects`), project children fanning right in grouped containers: `Knowledge`, `Assessment`, `Mastery & Reco`, `Conversations`, `Ops (jobs/events/ai_usage)`.
- Shapes: tables = rectangles with `tablename` bold + 4–8 key columns; PK `PK`, FK `FK→table`, unique `UQ`, check `CK`; `embeddings.embedding Vector(384)` highlighted; cylinders not needed (all one DB cylinder behind).
- Arrows: solid = CASCADE FK with `CASCADE` label where true; dashed = SET NULL / no-FK; red dashed = constraint-violation exits.
- Labels: every table box line-2 shows `backend/app/models/<file>`; legend explains PK/FK/UQ/CK/CASCADE/SET NULL; ≥8pt monospace for column names.

---

## Diagram 5 — Document Processing Pipeline

### A. Diagram Purpose
Traces one PDF from upload HTTP to `Ready`, through validation, Celery chaining (`process_pdf → generate_embeddings + build_structure`), hybrid text/OCR extraction, chunking, and status polling. Shows exactly what runs inline vs async.

### B. Nodes
| Node | Type | Technology | Responsibility | Repository path | Function |
|---|---|---|---|---|---|
| Upload route | Controller | FastAPI `async def` (only one in codebase) | Auth+ownership, delegates to storage+jobs+Celery, returns 201 pending | `backend/app/api/v1/materials.py` | `upload_material` |
| `save_pdf` | Service | Python filesystem | `.pdf` ext, content-type `{pdf,x-pdf,octet-stream}`, non-empty, ≤10 MB (413), `%PDF` magic (400), `UPLOAD_DIR/{project}/{uuid}.pdf`, traversal-safe | `backend/app/services/storage_service.py` | `save_pdf()` |
| `job_service` | Service | SQLAlchemy | `create_job/get_job/mark_running/completed/failed` with `pending→running→completed/failed` (+`pending→failed`), idempotent same-status | `backend/app/services/job_service.py` | `create_job`, `mark_*` |
| `process_pdf` task | Worker | Celery `bind,max_retries=3` | Idempotency skip, `pending→running`, one extraction pass, `ValueError/FileNotFound→failed` no-retry, transient→retry `2^retries*2`, chains downstream | `backend/app/worker/tasks/extraction.py` | `process_pdf(job_id, material_id)` |
| `extract_document_pages` | Service | PyMuPDF + pytesseract/Pillow | Per-page hybrid: meaningful text (≥20ch & ≥3 words)→`TEXT`; else images+`ocr_enabled`→OCR→`OCR`/`EMPTY`; else `EMPTY`; single bad page never fails doc | `backend/app/services/document_extraction_service.py` | `extract_document_pages`, `combine_page_texts` |
| `ocr_fitz_page` | Service | `fitz.Matrix(dpi/72)` + Pillow + tesseract (`eng`, dpi 300) | Render→CMYK→RGB→PNG→`image_to_string`; ALL failures → `OcrError` (caller degrades to `EMPTY`) | `backend/app/services/ocr_service.py` | `ocr_fitz_page` |
| `chunk_pages` + `persist_chunks` | Service | Deterministic word-boundary chunker | `CHUNK_SIZE 2000ch / OVERLAP 200ch`, exact offsets, never spans pages, `page_number` 1-indexed + `extraction_method`; idempotent delete+insert | `backend/app/services/chunking_service.py` | `chunk_text`, `chunk_pages`, `persist_chunks` |
| `generate_embeddings` task | Worker | Celery + fastembed | Batched `embed(contents)`, validate count+dims==384, upsert 1:1 `Embedding/chunk_id`, `No chunks/ValueError→failed` fast | `backend/app/worker/tasks/embeddings.py` | `generate_embeddings` |
| `build_structure` task | Worker | Celery `bind,max_retries=3` + LLM | Pass1 topic map → Pass2 learning objects per topic → `persist_knowledge_map`; provider/validation fails per policy below | `backend/app/worker/tasks/structure.py` | `build_structure` |
| `Material.status` / `BackgroundJob.status` | State | PostgreSQL rows | `pending→processing→ready/failed` (material); `pending→running→completed/failed` (jobs); list endpoint overlays running jobs as `processing` | `backend/app/models/material.py`, `background_job.py`, `backend/app/api/v1/materials.py` | `list_materials` overlay |
| Polling UI | Client | React `setInterval 5000ms` gated | `GET …/materials` (`noCache:true`) while `pending|processing` | `frontend/src/features/projects/MaterialsPanel.tsx` | — |
| Config | Config | pydantic-settings | `UPLOAD_DIR /data/uploads`, `OCR_ENABLED True/LANGUAGE eng/DPI 300`, `REDIS/CELERY`, `DATABASE_URL` | `backend/app/core/config.py` | `Settings` |

### C. Connections
| Source → Destination | Dir | Protocol | Data | Sync/Async | Why | Evidence |
|---|---|---|---|---|---|---|
| Browser → Upload route | → | `multipart/form-data`, Bearer | PDF bytes | sync (120s client timeout) | Ingest | `MaterialsPanel.tsx`, `materials.py` |
| Upload route → `save_pdf` | → | `await` call | `(storage_path, filename)` | sync | Validate+persist bytes | `materials.py`, `storage_service.py` |
| Upload route → `job_service.create_job` + `process_pdf.delay` | → | SQL + Redis `.delay()` | `job_id, material_id` | async | Return 201 fast | `materials.py` |
| `process_pdf` → PDF file | → | fs read | bytes | worker | Extract | `tasks/extraction.py` |
| `process_pdf` → `extract_document_pages/ocr` | → | call | `[{page_number,text,extraction_method,has_images}]` | worker | Hybrid pages | `document_extraction_service.py` |
| `process_pdf` → `chunk_pages/persist_chunks` (inline) | → | call | drafts → `document_chunks` | worker | Chunk before embeddings; failure returns `chain_error` and STOPS | `tasks/extraction.py:_chain_downstream` |
| `process_pdf` → `generate_embeddings.delay` + `build_structure.delay` | → | Redis `.delay()` best-effort | job ids | async | Parallel downstream; dispatch failure logged, extraction stays `completed` | `tasks/extraction.py` |
| `generate_embeddings` → `embedding_client.embed` → `embeddings` table | ↔ | in-process + SQL upsert | 384-vectors | worker | Searchable representation | `tasks/embeddings.py` |
| `build_structure` → `extract_topic_map/extract_learning_objects` → `persist_knowledge_map` | ↔ | `chat_json` + SQL | topics/subtopics/concepts/relationships | worker | Knowledge map | `tasks/structure.py`, `services/structure_*` |
| UI → List materials | → | HTTP GET poll | statuses | async poll | Progress UX | `MaterialsPanel.tsx:77` |

### D. Data Flow
1. `POST /projects/{id}/materials` (Bearer + ownership) → `save_pdf` → `Material(pending)` + `BackgroundJob(pending)` + `record_event(material.uploaded)` → `process_pdf.delay` → `201`.
2. `process_pdf`: UUID validate → idempotency skip → `pending→running` → `extract_document_pages` (hybrid TEXT/OCR/EMPTY per page) → `combine_page_texts` → `Material(extracted_text,page_count,ready)` + `material.ready` event (or `failed` + `material.failed` on corrupt/empty/no-content).
3. Inline: `chunk_pages` + `persist_chunks` (idempotent replace).
4. Enqueue `generate_embeddings` (batch embed → 1:1 upserts) and `build_structure` (Pass1→Pass2→atomic persist) as separate jobs; UI polls list endpoint until `ready/failed`.

### E. Failure Paths
- F1 Upload validation: bad ext/type/magic→400 `bad_request`; >10 MB→413 `payload_too_large`; traversal name sanitized (`evil.pdf`); stranger→404, anon→401 (`storage_service.py`, `tests/security/test_upload_hardening.py`, `tests/test_upload.py`).
- F2 Corrupt/zero-pages/no-usable-content → `failed` NO retry (`ValueError/FileNotFoundError` branch).
- F3 Transient extraction error → retry 3× `countdown 2^retries*2` then `failed`.
- F4 Chunk failure inline → `chain_error`, downstream never enqueued.
- F5 Embeddings: `No chunks`/`ValueError` (count/dim) → `failed` fast.
- F6 Structure Pass1 `Structure/Value/Runtime→failed`, `httpx.HTTPError→retry` (429: `60*(retries+1)` else `2^retries*2`, 3×); Pass2 per-topic failure → skip to `failed_topics`, rest commits.
- F7 Dispatch failure of downstream `.delay()` → logged in extraction result, extraction stays `completed` (provider failure never rolls back chunks/embeddings).

### F. Security Boundaries
- Auth/ownership: `get_authorized_project` before any disk/DB write.
- File boundary: `save_pdf` allow-list + magic + size + basename-sanitize + project dir.
- Job ownership: `GET /jobs/{id}` re-chains `Job→Material→Project→Space(user)` (`api/v1/jobs.py:get_authorized_job`).

### G. AI Boundaries
- Dev-time AI: extraction/chunking code may be assistant-written (note only).
- Product AI in this pipeline: `build_structure` LLM (topic map + learning objects) + local embeddings. `extract_document_pages`/`ocr/chunking` are deterministic (NOT AI) — label them "no LLM".

### H. Requirement Traceability
- PRD §5 (Upload→Queued→Processing/OCR→Content&Structure→Knowledge→Retrieval→Ready + status visibility + retry/duplicate handling) → this pipeline → `materials.py`, `tasks/extraction|embeddings|structure.py`, `document_extraction_service.py`, `ocr_service.py`, `chunking_service.py`, `embedding_client.py`.
- PRD §13 material workflow → same chain.
- PRD §18 (PDF materials, background processing, deployment) → `storage_service.py`, `supervisord.conf`, `docker-compose.yml`.

### Visual Design Specification
- Orientation: landscape. Layout: left-to-right pipeline with async lane below (`process_pdf` → fork `embeddings` / `structure`).
- Containers: `HTTP request (sync)` vs `Celery worker (async)` vs `External/LLM` (only `build_structure` touches it).
- Shapes: routes/services = rectangles; Celery tasks = double-border rectangles; DB rows = cylinders; file = file shape; decision diamonds for `TEXT vs OCR vs EMPTY` and `failed vs retry vs completed`.
- Arrows: solid = call; dashed = `.delay()`; red dashed = F1–F7 to `failed` state box; number happy path 1–7; legend required.

---

## Diagram 6 — RAG / Tutor Architecture

### A. Diagram Purpose
Shows grounded Q&A end-to-end: small-talk bypass, project-scoped pgvector retrieval, char-budgeted context assembly, single `chat_json` call with `<<<DATA>>>` prompt discipline, citations, `supported` flag, conversation persistence, metering, and quiz-plan handoff.

### B. Nodes
| Node | Type | Technology | Responsibility | Repository path | Function |
|---|---|---|---|---|---|
| `TutorChat` UI | Client | React | Conversations CRUD, message send, quiz-plan → quiz handoff, deck build | `frontend/src/features/tutor/TutorChat.tsx` | — |
| Tutor routers | Controller | FastAPI | `POST …/tutor/ask`, `…/conversations*`, `POST …/tutor/quiz-plan` (all ownership + `require_llm_budget("tutor")` on ask/send/quiz-plan) | `backend/app/api/v1/tutor.py` | `ask`, `send_message`, `quiz_plan` |
| `tutor_conversation_service` | Service | SQLAlchemy | `create/list/get_owned/get_messages/delete`; `send_message` stores user → `ask_question` → stores assistant (+citations/follow_ups), first-exchange retitle, post-3rd-msg AI retitle (≤8 words/60ch, never overwrite custom, fail→None) | `backend/app/services/tutor_conversation_service.py` | `send_message`, `citation_models` |
| `retrieval_service.retrieve` | Service | pgvector in-SQL `cosine_distance` | `top_k 1–20 (default 5)`, dual `project_id` filter, optional `concept_id`, zero-embedding short-circuit BEFORE `embed_one`, dim check | `backend/app/services/retrieval_service.py` | `retrieve()`, `RetrievedChunk(score=distance)` |
| `rag_service.assemble_context` | Service | Pure budgeting | Drop blanks, word-snapped char budget (`max_chars` default 6000, min 500/max 20000, max 10 chunks), preserve ids/page/source/score, `truncated` flag; NO unsupported decision | `backend/app/services/rag_service.py` | `assemble_context()` |
| `tutor_service.ask_question` | Service | `groq_client.chat_json` + rules | Greeting/thanks/farewell/help bypass (canned, no retrieval/LLM); else context → `SUPPORTED_MAX_DISTANCE=0.5` gate → single LLM call → `TutorOutline{answer,follow_ups}`; goal ≤1000ch as `<<<DATA>` | `backend/app/services/tutor_service.py` | `ask_question`, `conversational_reply`, `plan_quiz` |
| `groq_client.chat_json` | AI gateway | httpx 60s, `response_format json_object`, temp 0.0 | Provider switch groq/inception, `sanitize_for_llm` (NFKC), token fallback `len/4`, `LLMCallRecord` metering scope | `backend/app/services/ai/groq_client.py` | `chat_json()` |
| `embedding_client` | AI local | fastembed `bge-small-en-v1.5` 384 | `embed_one(query)` for retrieval; `lru_cache` model | `backend/app/services/ai/embedding_client.py` | `embed_one` |
| `track_llm_call` | Observability | Dedicated `SessionLocal` | Drains metering scope → 1 `ai_usage` row/call (incl. failures), cost via pricing if success, never raises, never stores prompt/response | `backend/app/services/ai_usage_service.py` | `track_llm_call(feature=tutor_answer/tutor_title/tutor_quiz_plan)` |
| `record_tutor_evidence` (downstream) | Learning | SQLAlchemy | Optional tutor evidence write (score 0–100, 1/day dedup, `mastery.updated` event) — caller-side, not inside `ask_question` | `backend/app/services/mastery_service.py` | `record_tutor_evidence` |
| `plan_quiz` | Service | LLM + catalog filter | `QUIZ_PLAN_SYSTEM`, initial+1 retry, drop unknown/dup ids, cap 8, only `is_mastery_target` concepts, empty catalog → empty plan no LLM | `backend/app/services/tutor_service.py` | `plan_quiz()` |

### C. Connections
| Source → Destination | Dir | Protocol | Data | Sync/Async | Why | Evidence |
|---|---|---|---|---|---|---|
| UI → `POST …/conversations/:id/messages {question}` | → | HTTP+JSON Bearer | question text | sync | Persistent chat path | `TutorChat.tsx`, `api/v1/tutor.py` |
| Route → `tutor_conversation_service.send_message` | → | call | convo + question | sync | Persist + answer | `tutor.py`, `tutor_conversation_service.py` |
| Service → `tutor_service.ask_question` | → | call | `project_id, question, concept_id?` | sync | Grounded answer | `tutor_conversation_service.py` |
| `ask_question` → small-talk check | → | string match (lower/punct-strip, filler-strip) | canned reply `supported=true` | sync (no retrieval/LLM) | Don't waste AI on greetings | `tutor_service.py` (`_GREETINGS/_THANKS/...`) |
| `ask_question` → `assemble_context` → `retrieve` → `embed_one` | → | call → pgvector SQL | `RetrievedChunk[chunk_id,material_id,page,source,score]` | sync | Project-isolated evidence | `rag_service.py`, `retrieval_service.py` |
| Gate: 0 chunks OR `min(score)>0.5` → `supported=false` | → | return | `UNSUPPORTED_MESSAGE`, empty citations, **Groq never called** | sync | Evidence-over-guessing | `tutor_service.py:217-220`, `SUPPORTED_MAX_DISTANCE=0.5` |
| Else → `chat_json(_SYSTEM_PROMPT, <<<DATA excerpts + goal)` | → | HTTPS | `{answer markdown, follow_ups[2–4 ≤120ch]}` | sync | Grounded generation | `tutor_service.py` system prompt + `FEATURE_TUTOR_ANSWER` |
| Answer → 1 `TutorCitation`/chunk (`excerpt` 280ch word-snapped) | → | build | citations[] | sync | Trace-to-source | `tutor_service.py:EXCERPT_CHARS=280` |
| Conversation service → `tutor_messages` row | → | SQL | `content, supported, citations, follow_ups` | sync | Continuity without resending full history | `models/tutor_conversation.py`, `tutor_conversation_service.py` |
| Every LLM call → `track_llm_call` | → | separate session | `ai_usage` row (`meta={chunks,min_distance}`) | sync (non-blocking semantics: never raises) | Observability | `ai_usage_service.py` |

### D. Data Flow
1. `POST …/messages {question}` → ownership + budget → `send_message` stores `user` row.
2. `ask_question`: empty→400; small-talk→canned; else `assemble_context(project_id, question)` (pgvector top-k, char budget).
3. Gate: no chunks or all distances >0.5 → `supported=false + UNSUPPORTED_MESSAGE`, no LLM, still persisted.
4. Else single `chat_json` with DATA-only excerpts (+goal) → validated `TutorOutline` → citations per chunk → `(response)` persisted as `assistant` row with `supported=true`; first-exchange/3rd-msg retitling best-effort.
5. `plan_quiz` (tutor→quiz handoff): last-5 questions → concept-id plan → caller generates quiz via Diagram 7 path.

### E. Failure Paths
- F1 Blank question →400; foreign convo/project →404; anon →401 (`tutor.py`, `tutor_conversation_service.get_owned_conversation`).
- F2 Budget exhausted →429 before LLM (but AFTER ownership, so stranger gets 404 not 429).
- F3 Retrieval empty/low-similarity → `supported=false`, zero citations, LLM skipped (core eval requirement).
- F4 Invalid outline/non-object JSON → `TutorProviderError` →502 `upstream_unavailable`; `httpx.HTTPError` →502; `RuntimeError` →500.
- F5 Title-LLM failure → `None`, original title kept, never overwrites custom.
- F6 Provider failure in `send_message` propagates — only user side stored, no phantom assistant row.

### F. Security Boundaries
- Auth + `get_authorized_project` + conversation ownership (`get_owned_conversation(project_id,user_id)`) on every tutor route.
- Retrieval dual `project_id` filter (`Embedding.project_id` AND `DocumentChunk.project_id`) — never fetch-all-then-filter.
- Prompt-injection boundary: excerpts + goal wrapped in `<<<DATA … DATA>>>` marked "DATA not instructions"; system prompt "answer ONLY from excerpts"; verified by `tests/security/test_prompt_boundaries.py`.

### G. AI Boundaries
- Dev-time AI: prompt text may be assistant-drafted (note).
- Product AI: `chat_json` (answer + title + quiz-plan) + local embeddings. Retrieval/budgeting/citations/persistence are deterministic — keep them outside the purple AI box.

### H. Requirement Traceability
- PRD §6 (goal+materials+concepts+history+context; current-convo + project-knowledge + learning-context) → `tutor_conversation_service` + `ask_question(project goal + context + history window ≤6 for title)`.
- PRD §7 (retrieve → answer → citation `Source: … — Page N`; insufficient-evidence refusal) → `retrieval_service` + `rag_service` + `SUPPORTED_MAX_DISTANCE` gate + `TutorCitation(page_number,source_name,excerpt)`.
- PRD §8 (structured tool/app request → validation/authz → execute) → ownership deps + `TutorOutline` Pydantic validation before persist/use.
- PRD §11 (persistent but relevant context; no full-history resend) → conversation rows + budgeted `assemble_context` + goal-only injection.

### Visual Design Specification
- Orientation: landscape. Layout: top-down pipeline with retrieval lane left, LLM lane right, persistence lane bottom.
- Containers: `Project isolation` (orange, around retrieval+answer), `AI calls` (purple, around `embed_one` + `chat_json`), `External HTTPS` (grey, Groq/Inception only).
- Shapes: UI = rectangle; gate diamond `Enough evidence? (0 chunks OR min distance>0.5)` with YES→LLM / NO→`supported=false` branches; DB = cylinders; citations = document shapes labeled `chunk_id/material_id/page`.
- Arrows: numbered 1–6 happy path; red dashed F1–F6; edge labels show `top_k`, `0.5`, `280ch`, `<<<DATA>>>`; legend required.

---

## Diagram 7 — Adaptive Quiz Architecture

### A. Diagram Purpose
Shows evidence-driven (NOT naive wrong→easy) MCQ generation: mastery-ordered concept allocation, deterministic DB sourcing (no embeddings), single validated LLM call, persistence, then attempt lifecycle (start → answer with server-graded correctness + confidence → complete → evidence + events).

### B. Nodes
| Node | Type | Technology | Responsibility | Repository path | Function |
|---|---|---|---|---|---|
| Quiz UI | Client | React | `QuizSetup/Modes` (tree/search/recommendations) → `QuizTaker` (generate→attempt→answer→complete) | `frontend/src/features/quiz/QuizSetup.tsx`, `QuizModes.tsx`, `QuizTaker.tsx`, `ConceptDetail.tsx` | — |
| Quizzes router | Controller | FastAPI | `POST …/quizzes/generate` (+`require_llm_budget("quiz-generate")`), `POST …/{quiz_id}/attempts`, `POST …/attempts/{id}/answers`, `POST …/attempts/{id}/complete` | `backend/app/api/v1/quizzes.py` | — |
| `adaptive_quiz_service` | Logic (pure, no LLM/DB) | Python | `select_questions`: weakest-mastery first, `_target_level` (<34 easy, 34–66 medium, >66 hard), exposure unseen→least-asked→least-recent, curriculum+ID tiebreak, round-robin; `order_concepts_by_mastery` | `backend/app/services/adaptive_quiz_service.py` | `select_questions`, `order_concepts_by_mastery`, `UNKNOWN_MASTERY=50.0` |
| `quiz_generation_service` | Service | `chat_json` + SQL reads | `_scoped_source` (page-range→concept-tagged→selection→project), `_supporting_context` (≤8 siblings ≤200ch + related names), `_order_concepts_adaptive` + `_allocate_concepts` (weight `(100-mastery)+10`, one-per-concept then weakest-first), `_adaptive_difficulty_hint` (fresh→easy), single LLM +1 retry, `_validate_outline`, persist `Quiz+QuizQuestion(source_chunk_id=None)` | `backend/app/services/quiz_generation_service.py` | `generate_quiz`, `generate_scoped_quiz`, `MAX_SOURCE_CHARS=6000` |
| `quiz_attempt_service` | Service (no AI) | SQLAlchemy | `start_attempt` (+`quiz.started`), `attempt_questions`, `submit_answer` (server `is_correct`, 1-answer/question + `IntegrityError` guard, `question.answered`), `attempt_score`, `write_mcq_evidence` (100/0, `source=quiz\|practice`), `complete_attempt` (lock, score%, `quiz.completed+mastery.updated`) | `backend/app/services/quiz_attempt_service.py` | `start_attempt`, `submit_answer`, `complete_attempt` |
| `groq_client.chat_json` | AI | JSON mode | `SYSTEM_PROMPT` (SOURCE TEXT untrusted, return ONLY `{questions:[{question_text,options[2–6],correct_index,difficulty}]}`), `FEATURE_QUIZ_GENERATION` | `backend/app/services/ai/groq_client.py` | `chat_json` |
| Quiz tables | Data | PostgreSQL | `quizzes`, `quiz_questions`, `quiz_attempts`, `quiz_answers` | `backend/app/models/quiz.py`, `quiz_attempt.py` | — |
| Downstream | Learning | Services | `write_mcq_evidence` rows → mastery (D9) → `refresh_best_effort` recommendation | `backend/app/services/mastery_service.py`, `backend/app/worker/tasks/recommendations.py` | `refresh_best_effort` |

### C. Connections
| Source → Destination | Dir | Protocol | Data | Sync/Async | Why | Evidence |
|---|---|---|---|---|---|---|
| UI → `POST …/quizzes/generate {scope,topic/subtopic/concept_ids,num 1–20,mode,difficulty?}` | → | HTTP Bearer | spec | sync | Evidence-driven generation request | `QuizTaker.tsx`, `quizzes.py` |
| Route → `generate_scoped_quiz` | → | call | `project_id, scope, mastery snapshot, user_id` | sync | Adaptive allocation | `quizzes.py`, `quiz_generation_service.py` |
| Generation → DB reads (no embeddings) | ↔ | SQL | concept titles/summaries + supporting snippets | sync | Deterministic sourcing | `_build_enriched_source`, `_scoped_source` |
| Generation → `chat_json` (+1 retry) | → | HTTPS | outline `{questions[]}` | sync | Question authoring | `SYSTEM_PROMPT`, `FEATURE_QUIZ_GENERATION` |
| Generation → `quizzes/quiz_questions` | → | SQL commit/rollback | persisted quiz | sync | Attemptable artifact | `quiz_generation_service.py` |
| UI → `POST …/{quiz}/attempts` → `POST …/attempts/{id}/answers {question_id,selected_index,confidence 1\|3\|5}` (loop) → `POST …/complete` | → | HTTP | answers + confidence | sync | Attempt lifecycle | `QuizTaker.tsx`, `quiz_attempt_service.py` |
| `complete_attempt` → `write_mcq_evidence` + events | → | SQL + `record_event` | `mcq` rows 100/0, `quiz.started/completed`, `question.answered`, `mastery.updated` | sync | Feed mastery/growth | `quiz_attempt_service.py` |

### D. Data Flow
1. UI collects scope (browse tree / search / recommendation) → `generate` with `difficulty=null` for adaptive hint.
2. Service orders concepts weakest-first (`order_concepts_by_mastery` + curriculum key), allocates counts proportionally, resolves deterministic source text per concept.
3. One `chat_json` per batch (+1 retry) → `_validate_outline` (MCQ shape, `correct_index` range, count) → single commit of quiz+questions.
4. `start_attempt` → per-question `submit_answer` (server grades, confidence stored 1–5, one-answer enforced) → `complete_attempt` locks, scores %, banks `mcq` evidence, emits events, best-effort recommendation refresh.

### E. Failure Paths
- F1 Bad spec (`num/mode/difficulty/scope`) →400/422; out-of-scope ids →`LookupError`→404.
- F2 Non-practicable target (non-CORE/SUPPORTING or obsolete) or zero source → `QuizGenerationError` →422 (no empty quiz persisted).
- F3 Invalid LLM outline after retry → `QuizGenerationError` →422; `httpx` →502.
- F4 Double-answer same question →400/`IntegrityError` guard; unknown quiz/attempt ids →404 (scope-checked by `project_id+user_id`).
- F5 `complete` on locked/empty attempt handled by service (lock + score logic).

### F. Security Boundaries
- Ownership: `get_authorized_project`; `quiz_id/attempt_id: str→UUID` then service verifies `project_id+user_id` (404 on mismatch).
- Budget: `require_llm_budget("quiz-generate")` on generate only (answering is free/deterministic).
- Correctness trust: `is_correct` server-computed from `correct_index`; client `selected_index` never trusted for grading.

### G. AI Boundaries
- Dev-time AI: generation prompt authoring (note).
- Product AI: exactly one LLM call (question authoring). Selection/allocation/grading/evidence are deterministic — draw outside purple.

### H. Requirement Traceability
- PRD §9 (MCQ + adaptive on concepts/mastery/mistakes/recency/difficulty/history/activity; NOT wrong→easy; Start→Mastery→Select→Generate→Answer→Evaluate→Mastery→Next) → `adaptive_quiz_service` + `quiz_generation_service._order/_allocate/_hint` → mastery/growth inputs.
- PRD §8 (validate structured AI before persist/use) → `_validate_outline` + single commit/rollback.
- PRD §10/12 (assessment feeds mastery/growth/events) → `write_mcq_evidence` + `quiz.*`/`mastery.updated` events.

### Visual Design Specification
- Orientation: landscape. Layout: two lanes — `Generation (LLM)` top, `Attempt lifecycle (deterministic)` bottom — sharing the quiz tables cylinder.
- Containers: `Adaptive policy (pure)` box listing bands `<34 easy / 34–66 medium / >66 hard` + exposure rule; `AI` purple around `chat_json` only.
- Shapes: allocation = stacked-bar/trapezoid labeled with weight formula; attempt = 4 numbered circles (start→answer→score→complete); DB = cylinder.
- Arrows: solid happy path 1–6; red dashed F1–F5; legend required.

---

## Diagram 8 — Open-Ended Assessment Architecture

### A. Diagram Purpose
Shows generation + AI grading of open-ended questions (including Explain-It-Back reuse of the same grader), deterministic verdict bands, evidence writes, and feedback (strengths/missing/suggestions) — proving "feedback, not just a score."

### B. Nodes
| Node | Type | Technology | Responsibility | Repository path | Function |
|---|---|---|---|---|---|
| Open-ended UI | Client | React | `OpenEndedAnswersPage` (tree → generate loop → answer → grade); `PracticeSession` (mixed MCQ+OE with 850ms eval-step cosmetic timer) | `frontend/src/features/openended/OpenEndedAnswersPage.tsx`, `frontend/src/features/practice/PracticeSession.tsx` | `EVAL_STEPS` |
| Assessment router | Controller | FastAPI | `POST …/assessment/open-ended/generate`, `POST …/assessment/open-ended`, `POST …/assessment/explain-back` (budgets `assessment`/`assessment`/`explain-back`) | `backend/app/api/v1/assessment.py` | — |
| `open_ended_assessment_service` | Service | `chat_json` + SQL reads | `generate_open_ended_question` (scope resolve + `QUESTION_SYSTEM_PROMPT` + `FEATURE_OPEN_ENDED_GENERATE`); `grade_open_ended` (concept-tagged→project-wide 6000ch source, `SYSTEM_PROMPT` JSON-only, +1 retry, `FEATURE_OPEN_ENDED_GRADE`); `verdict_for` ≥80 pass / ≥50 partial / else fail | `backend/app/services/open_ended_assessment_service.py` | `generate_open_ended_question`, `grade_open_ended`, `GradeOutline`, `verdict_for` |
| `explain_it_back_service` | Service | Reuses grader | `submit_explanation` → shared `grade_open_ended` → persists `MasteryEvidence(explain_back/source=open_ended/raw_score/feedback)` in one commit; grading failure persists nothing; emits `assessment.completed+mastery.updated` + `refresh_best_effort` | `backend/app/services/explain_it_back_service.py` | `submit_explanation` |
| `groq_client.chat_json` | AI | JSON mode | Grading + question prompts (untrusted-data discipline) | `backend/app/services/ai/groq_client.py` | `chat_json` |
| Evidence/events | Data | PostgreSQL | `mastery_evidence(open_ended/explain_back)`, `learning_events(assessment.completed, mastery.updated)` | `backend/app/models/mastery_evidence.py`, `learning_event.py` | `EVENT_*` |

### C. Connections
| Source → Destination | Dir | Protocol | Data | Sync/Async | Why | Evidence |
|---|---|---|---|---|---|---|
| UI → `POST …/generate {scope,topic/subtopic/concept_ids}` (loop per oeCount) | → | HTTP Bearer | spec | sync | One question per call | `PracticePage.tsx`, `OpenEndedAnswersPage.tsx` |
| UI → `POST …/open-ended {concept_id,answer_text ≤5000ch,question_text?}` | → | HTTP | answer | sync | Grade request | `PracticeSession.tsx`, `assessment.py` |
| Route → `generate/grade` service | → | call | source resolve (concept-tagged else project-wide) | sync | Grounded authoring/grading | `open_ended_assessment_service.py` |
| Service → `chat_json` (+1 retry) | → | HTTPS | `QuestionOutline{question_text,difficulty}` / `GradeOutline{score 0–100,feedback 1–2000,strengths/missing/suggestions ≤5×300ch}` | sync | AI authoring/grading | `QUESTION_SYSTEM_PROMPT`/`SYSTEM_PROMPT` |
| Grade → `Grade{score,verdict,feedback,…}` (deterministic band) | → | map | pass/partial/fail | sync | Stable verdicts | `verdict_for` |
| Explain-back → `mastery_evidence` commit | → | SQL single commit/rollback | evidence row | sync | Feed mastery | `explain_it_back_service.py` |
| All → `track_llm_call` | → | separate session | `ai_usage` rows | sync (never raises) | Metering | `ai_usage_service.py` |

### D. Data Flow
1. Generate: resolve scope concepts (`_resolve_scope/practice_concepts`) → scoped source → `chat_json` → `OpenEndedQuestion` (anchored `concept_id=concepts[0]`).
2. Answer: `grade_open_ended(project, concept, answer≤5000ch)` → source → `chat_json` → validated `GradeOutline` → `verdict_for` band → feedback object (score + what was understood + missing + suggestions).
3. Explain-back: same grader → persist `explain_back` evidence + events + recommendation refresh; pure open-ended grading path persists via caller evidence flow.

### E. Failure Paths
- F1 Empty/oversize answer, bad scope → `ValueError/LookupError` →400/404.
- F2 Zero source or invalid outline after retry → `OpenEndedAssessmentError` →422.
- F3 Provider `httpx` →502; `RuntimeError` →500.
- F4 Grading failure in explain-back → persists NOTHING (atomic rollback), no partial evidence.

### F. Security Boundaries
- Ownership (`get_authorized_project`) + per-scope budgets; answer length cap 5000ch (input validation); structured-output validation before any persist.

### G. AI Boundaries
- Dev-time AI: rubric/prompt drafting (note).
- Product AI: question + grade JSON calls. Verdict banding, persistence, events are deterministic.

### H. Requirement Traceability
- PRD §9 (open-ended: understanding/accuracy/relevance/coverage/missing/reasoning; explanatory feedback; feeds mastery/growth) → `GradeOutline` fields + `feedback` + `explain_back` evidence → `mastery_service` streams.
- PRD §8/§14 (structured reliability; grade/eval quality) → Pydantic outlines +1 retry; `tests/test_open_ended_assessment.py`, `test_practice_and_open_ended.py`.

### Visual Design Specification
- Orientation: portrait (two stacked pipelines sharing the grader box). Layout: Generate lane top, Grade lane middle, Explain-back lane bottom.
- Shapes: LLM boxes purple with `QUESTION_SYSTEM_PROMPT` / grading `SYSTEM_PROMPT` labels; verdict = 3-exit diamond (`≥80 pass / ≥50 partial / else fail`); feedback = document shape listing fields.
- Arrows: numbered per lane; red dashed F1–F4; legend required.

---

## Diagram 9 — Mastery / Learning Intelligence Architecture

### A. Diagram Purpose
Shows how append-only evidence becomes stream-weighted mastery, calibration, mismatch badges, and rollups — all deterministic (NO LLM) — plus the thresholds the UI renders.

### B. Nodes
| Node | Type | Technology | Responsibility | Repository path | Function |
|---|---|---|---|---|---|
| `mastery_evidence` table | Data | PostgreSQL append-only | `evidence_type mcq/open_ended/explain_back/flashcard/tutor`, `source`, `raw_score 0–100`, `difficulty`, `feedback`; no weight/resulting columns | `backend/app/models/mastery_evidence.py` | — |
| `mastery_service` | Logic (pure EMA, no LLM) | Python | Streams `quiz .35 / open_ended .25 / practice .20 / flashcard .15 / tutor .05`; `_weight` easy .2/medium .3/hard .4/default .3 +0.1 if gap>7d cap .5, tutor fixed .15 max 1/day; `compute_final` renormalized + caps (tutor-only 40, formative-only 70, 1-row 60, 2-row 75); `compute_mastery`, batch readers, `record_tutor_evidence` (ONLY tutor writer) | `backend/app/services/mastery_service.py` | `compute_mastery`, `mastery_for_concept(s)`, `record_tutor_evidence` |
| `mastery_levels` | Logic (no AI) | Python thresholds | `status_for`: None→Not Started, <34 Needs Practice, ≤66 Developing, <85 Strong, ≥85 Mastered; `is_mastery_target` (CORE + non-obsolete), `is_practicable` (CORE/SUPPORTING + non-obsolete) | `backend/app/services/mastery_levels.py` | `status_for`, `is_mastery_target`, `is_practicable` |
| `confidence_service` | Logic (pure) | Python | `summarize`: per-concept + overall `ConceptCalibration{answered,correct,accuracy,rated,avg_confidence,gap=(avg-1)*25-accuracy%,confidently_wrong[wrong&≥4],unsure_right[right&≤2]}` | `backend/app/services/confidence_service.py` | `summarize` |
| `mismatch_service` | Logic (pure) | Python | `detect_mismatches`: primary `mcq-applied≥25 (≥3 & ≥1)` or Plan-A `quiz-open_ended≥25`; else calibration over/under-confidence; 1 badge/concept priority `mcq_high>over>under`, rank `(priority,gap,id)` | `backend/app/services/mismatch_service.py` | `detect_mismatches`, `Mismatch` |
| `rollup_service` | Presentation (no LLM) | Python | `display_mastery=mean(known mcq/applied)`, `final_mastery=scores.final`; rollups mean of PRACTICED CORE only, unpracticed excluded (never zero), obsolete excluded | `backend/app/services/rollup_service.py` | `rollup_concepts/for_subtopic/for_topic/for_project` |
| `growth_service` | Reads (no LLM) | Python | `concept_growth`: replay `compute_mastery` per time-prefix → `GrowthPoint(at,evidence_type,raw,streams,final_after)` + trends; `project_growth`: current avgs + `evidenced_concepts/total_evidence/since/until` | `backend/app/services/growth_service.py` | `concept_growth`, `project_growth` |
| Evidence writers | Services | SQLAlchemy | MCQ (`quiz_attempt_service.write_mcq_evidence` 100/0), open-ended/explain-back, flashcard (`quality×20`), tutor (`record_tutor_evidence`) | `backend/app/services/quiz_attempt_service.py`, `explain_it_back_service.py`, `flashcard_service.py`, `mastery_service.py` | — |
| UI surfaces | Client | React | Concept bars (88/72/51/42 style), growth charts, calibration panels | `frontend/src/features/dashboard/Dashboard.tsx`, `features/analytics/*`, `features/quiz/ConceptDetail.tsx` | — |

### C. Connections
| Source → Destination | Dir | Protocol | Data | Sync/Async | Why | Evidence |
|---|---|---|---|---|---|---|
| Attempt/grade/review/message → `mastery_evidence` INSERT | → | SQL | `(user,project,concept,type,source,score,difficulty,feedback)` | sync (inside request or `complete/review/submit`) | Append-only truth | `quiz_attempt_service.write_mcq_evidence`, `explain_it_back_service`, `flashcard_service.review_card`, `mastery_service.record_tutor_evidence` |
| Readers → `mastery_for_concept(s)` (batch 1 query) | ↔ | SQL | `EvidenceInput[]` | sync | Efficient recompute | `mastery_service.py` |
| `compute_mastery` → streams + final | → | pure | `MasteryScores{5 streams + mcq/applied compat + final,total_count,evidence_confidence none/low(<3)/ok}` | sync | Estimate, not claim | `mastery_service.py` |
| Scores → `status_for/is_*` → UI labels | → | map | Not Started/Needs/Developing/Strong/Mastered | sync | Render thresholds | `mastery_levels.py` |
| Scores + calibration → `detect_mismatches` → badges | → | pure | `Mismatch[]` | sync | Attention signals | `mismatch_service.py`, `dashboard_service.build_dashboard` |
| Scores → `rollup_*` → topic/project avgs | → | mean | `Rollup{mastery,practiced,total}` / None=Not started | sync | Hierarchy progress | `rollup_service.py` |
| Evidence order → `growth` replay | → | replay | `GrowthPoint[]` + trends | sync | Change over time | `growth_service.py` |

### D. Data Flow
1. Every learning action appends exactly one typed evidence row (never updates in place).
2. Any read replays rows through stream EMA with difficulty/recency weights + caps → `final` + per-stream values.
3. Thresholds map finals to statuses; rollups average practiced CORE; mismatches compare streams/calibration; growth replays prefixes over time.

### E. Failure Paths
- No-evidence concept → `None` (Not Started), excluded from rollups (never 0) — draw as explicit `None` exit, not an error.
- Single-source caps (tutor-only 40 etc.) prevent overconfidence — label as guardrail boxes.
- Bad confidence values → `ValueError`; unknown concept → `LookupError`→404.
- Legacy `source=NULL` rows routed by compat map (`mcq→quiz` etc.), never dropped.

### F. Security Boundaries
- All readers filter `project_id (+user_id)`; service scope-checks on tutor-evidence write; no cross-project averaging.

### G. AI Boundaries
- Dev-time AI: weight/threshold design assistance (note).
- Product AI: NONE in this diagram — the entire lane is deterministic. Label prominently "NO LLM in mastery path" to prevent misreading.

### H. Requirement Traceability
- PRD §10 (mastery estimate evolving with evidence; improving/stable/attention; e.g. 88/72/51/42 bars) → `mastery_service` + `mastery_levels` + `growth_service` + `rollup_service`.
- PRD §12 (mastery updates as events) → `mastery.updated` events (`activity_service`, `quiz_attempt_service.complete_attempt`).
- PRD §18 learning tests (mastery updates, adaptive selection) → `tests/test_mastery.py`, `test_mastery_plan_a.py`, `test_confidence.py`, `test_mismatch.py`.

### Visual Design Specification
- Orientation: landscape. Layout: left evidence writers → central `mastery_evidence` cylinder → parallel deterministic boxes (streams → finals → statuses / mismatches / rollups / growth) → UI right.
- Shapes: evidence = small document shapes per type with weight labels (`.35/.25/.20/.15/.05`); caps = guardrail octagons; thresholds = 5-step bar; mismatches = badge shapes.
- Arrows: solid black replay path; no purple (no AI); legend must state "No LLM in this diagram."

---

## Diagram 10 — Recommendation Architecture

### A. Diagram Purpose
Shows the deterministic next-action engine: signal assembly (`dashboard_service`), scoring (`recommendation_service`), persistence lifecycle, and UI accept/dismiss/refresh. Emphasizes NO LLM generation — reasoning strings are templated with numbers.

### B. Nodes
| Node | Type | Technology | Responsibility | Repository path | Function |
|---|---|---|---|---|---|
| `dashboard_service.build_dashboard` | Assembler (reads, no LLM) | Python | CORE-only, curriculum-ordered; batch evidence + rated-`QuizAnswer(confidence)` queries; calibration over rated quiz/practice only (OE excluded); `days_since` clamped; mismatches via `detect_mismatches` → `(progress[], signals[])` | `backend/app/services/dashboard_service.py` | `build_dashboard`, `current_recommendation` |
| `recommendation_service` | Scorer (deterministic, no LLM) | Python | Actions `ask_tutor 10 / targeted_quiz 15 / explain_back 20 / review_material 5 / exam_mode 8`; `score = (100-min(known mcq/applied)) +25 overconfident +15 stale>5d +10 goal-match +base +40 explain_back/review on mismatch /-20 quiz on mismatch -25×recent(7d)`, floor 0; `is_eligible` (exam needs ≥3 evidenced); `recommend` persists winner (expires prior active + event); `recommend_many` top-`limit(1–8,def 4)` + starters + stalest-mastered fallback | `backend/app/services/recommendation_service.py` | `recommend`, `recommend_many`, `goal_keywords_for_project` |
| `generate_recommendation` task | Worker | Celery `max_retries=2` | `goal_keywords + build_dashboard → recommend`; `LookupError/ValueError` (nothing scorable) → `None` no-retry | `backend/app/worker/tasks/recommendations.py` | `generate_recommendation`, `refresh_best_effort` (fire-and-forget, skipped under pytest) |
| Dashboard/practice routers | Controller | FastAPI | `GET …/dashboard`, `POST …/dashboard/refresh|accept|dismiss`, `GET …/practice/recommendations?limit=` | `backend/app/api/v1/dashboard.py`, `practice.py` | — |
| `recommendations` table | Data | PostgreSQL | `(user,project,concept,action_type,score,reasoning,status active/accepted/dismissed/expired)` | `backend/app/models/recommendation.py` | — |
| UI | Client | React | `Dashboard` + `OverviewView` + `PracticePage` + `HomeDashboard` next-actions; `POST accept/dismiss/refresh` | `frontend/src/features/dashboard/Dashboard.tsx`, `features/overview/OverviewView.tsx`, `features/practice/PracticePage.tsx`, `features/home/HomeDashboard.tsx` | — |

### C. Connections
| Source → Destination | Dir | Protocol | Data | Sync/Async | Why | Evidence |
|---|---|---|---|---|---|---|
| UI → `GET …/dashboard` / `GET …/practice/recommendations?limit=4` | → | HTTP Bearer | dashboard + rec list | sync | Next-step surfaces | `Dashboard.tsx`, `practice.py` |
| Route → `build_dashboard` → `recommend(_many)` | → | call | `ConceptSignal{mastery,counts,mismatch,calibration,recency,importance/lo_type,streams}` → scored actions | sync | Deterministic ranking | `dashboard.py`, `practice.py`, `recommendation_service.py` |
| `recommend` → `recommendations` INSERT (expire prior active) + `recommendation.generated` event | → | SQL | winner row | sync | Lifecycle | `recommendation_service.recommend` |
| Events (`quiz.completed`, `assessment.completed`, `mastery.updated`) → `refresh_best_effort().delay()` | → | Redis fire-and-forget, swallowed | `(user_id,project_id)` | async | Keep recs fresh without blocking | `quiz_attempt_service`, `explain_it_back_service`, `flashcard_service`, `tasks/recommendations.py` |
| UI → `POST …/accept\|dismiss\|refresh` | → | HTTP | status transitions | sync | Learner control | `dashboard.py`, `Dashboard.tsx` |

### D. Data Flow
1. Request (or background refresh) builds signals for every CORE concept (mastery + counts + mismatch + calibration + recency + goal keywords + times-recommended).
2. Each eligible action scored with the additive formula; winner persisted (prior active expired); reasoning string embeds the numbers (e.g. "mcq 42, applied 71, gap 29").
3. `recommend_many` returns ranked top-N for practice/home; mastered→quiz skipped; unscorable skipped; fresh starters and stalest-mastered review fill gaps.
4. Learner accepts/dismisses; completion events trigger background refresh.

### E. Failure Paths
- F1 Nothing scorable (no CORE or no evidence) → `LookupError/ValueError` → 404/400 or `None` (task, no retry) — UI shows empty state, not an error toast.
- F2 `exam_mode` ineligible (<3 evidenced) → excluded from ranking.
- F3 Refresh task failure → swallowed (best-effort); next read recomputes synchronously.
- F4 Stale rec: `current_recommendation` falls back active → latest accepted/dismissed → None.

### F. Security Boundaries
- Ownership on all dashboard/practice routes; scoring reads only own-project evidence; `accepted/dismissed` transitions scoped to own row.

### G. AI Boundaries
- Dev-time AI: scoring-weight design (note).
- Product AI: NONE — explicitly label "Rule-based recommender (no LLM)". Goal keywords are token/phrase matching, not generation.

### H. Requirement Traceability
- PRD §10 (weaknesses + mistakes + goals + recency + history + materials → "what should I do next", e.g. Concept C guidance) → scoring inputs + reasoning strings → `recommendation_service.py`, `dashboard_service.py`.
- PRD §12/13 (quiz-completed → weakness → insight → recommendation workflows; repeated-mistake workflow) → `refresh_best_effort` triggers + mismatch inputs.
- PRD §16 (dashboard next-step; home next-action) → `Dashboard.tsx`, `HomeDashboard.tsx` (`GET /me/home` next_actions).

### Visual Design Specification
- Orientation: landscape. Layout: signals (left stack) → scoring formula box (center, show formula text) → ranked list → persistence cylinder → UI.
- Shapes: signals = small parallelograms; formula = large rectangle with exact additive terms; actions = 5 lanes with base scores; lifecycle = state circles `active→accepted/dismissed/expired`.
- Arrows: solid ranking path numbered; dashed async refresh; no purple; legend states "No LLM".

---

## Diagram 11 — Authentication / Authorization / Data Isolation

### A. Diagram Purpose
Proves project-level isolation at four layers: JWT auth, ownership deps, query filters (including pgvector dual-filter), and job/storage guards — plus what's tested.

### B. Nodes
| Node | Type | Technology | Responsibility | Repository path | Function |
|---|---|---|---|---|---|
| `hash_password/verify_password` | Crypto | Argon2id (`time_cost=3,mem=65536,par=4`) | Salted hashing, `needs_rehash`, constant-time verify | `backend/app/core/security.py` | `hash_password`, `verify_password` |
| `create/decode_access_token` | Token | PyJWT HS256, `sub=user-UUID`, exp 48h (`2880min`), `iat` | Issue/validate Bearer tokens | `backend/app/core/jwt.py` | `create_access_token`, `decode_access_token` |
| `oauth2_scheme + get_current_user` | Guard | `OAuth2PasswordBearer(/api/v1/auth/login)` | Decode → UUID-validate → `db.get(User)`; 401 invalid/expired (+`WWW-Authenticate`) | `backend/app/dependencies/auth.py` | `get_current_user` |
| `get_authorized_space/project/project_in_space` | Guard | Join queries | 404-hiding ownership (`Space.user_id`, `Project→Space→user`, both checks for nested) | `backend/app/dependencies/authorization.py` | `get_authorized_*` |
| `get_current_admin` | Guard | Boolean flag | 403 unless `is_admin` (401 upstream) | `backend/app/dependencies/admin.py` | `get_current_admin` |
| `require_llm_budget` | Guard | In-memory sliding window | Per-user (30/min) + per-project (120/min) × scope (`tutor/quiz-generate/assessment/explain-back`); 429; declared AFTER ownership | `backend/app/core/rate_limit.py` | `require_llm_budget`, `check_llm_budget` |
| Retrieval filter | Guard | pgvector SQL | `Embedding.project_id==X AND DocumentChunk.project_id==X (+concept_id?)`; short-circuit before embedding | `backend/app/services/retrieval_service.py:55-82` | `retrieve` |
| Job guard | Guard | Chained lookup | `Job→Material→Project→Space(user)` else 404 (orphans hidden) | `backend/app/api/v1/jobs.py` | `get_authorized_job` |
| Storage guard | Guard | Validation | Ext/type/magic/size/traversal checks | `backend/app/services/storage_service.py` | `save_pdf` |
| Auth routes | Controller | FastAPI | `POST /auth/register` (lowercase email, 400 exists), `POST /auth/login` (`Token`), `GET /auth/me` | `backend/app/api/v1/auth.py` | — |
| Frontend auth | Client | React + axios | localStorage token, Bearer injection, 401→logout→`/login` | `frontend/src/context/AuthContext.tsx`, `lib/axios.ts`, `lib/auth-events.ts`, `components/ProtectedRoute.tsx` | `login/register/logout` |
| Security tests | Tests | pytest | Cross-project 404s, rate-limit buckets, prompt `<<<DATA>>>`, upload hardening, auth matrix | `backend/tests/security/*`, `backend/tests/test_authorization.py`, `test_auth.py` | — |

### C. Connections
| Source → Destination | Dir | Protocol | Data | Sync/Async | Why | Evidence |
|---|---|---|---|---|---|---|
| `POST /auth/register` → `users` | → | SQL | `email(lower), hashed_password` | sync | Create identity | `api/v1/auth.py`, `core/security.py` |
| `POST /auth/login` → JWT | → | verify + encode | `access_token` | sync | Session | `core/jwt.py`, `core/security.verify_password` |
| Every protected route → `get_current_user` → ownership → budget | → | `Depends` chain | 401→404→429 order | sync | Layered gate; 404 precedes 429 by declaration order | `rate_limit.py:80-81` docstring; e.g. `tutor.py:32-38` |
| Any domain read → `…WHERE project_id==authorized.id` | → | SQL | scoped rows | sync | Isolation at query, not just route | `knowledge.py`, `retrieval_service.py`, `dashboard_service.py`, etc. |
| Worker tasks → owner resolve (`project→space→user`) | → | SQL | `user_id` for `ai_usage`/events | async | Preserve ownership off-request | `ai_usage_service.resolve_owner_*`, `tasks/*` |
| AI caps → `<<<DATA>>>` wrapping | → | prompt construction | untrusted text quarantined | sync | Prompt-injection boundary | `tutor/quiz/structure prompts`, `tests/security/test_prompt_boundaries.py` |

### D. Data Flow
1. Register (hash) → login (verify + JWT 48h) → Bearer on every call → `get_current_user`.
2. Space/project routes add join-ownership (existence hidden as 404); admin routes add `is_admin` (403).
3. LLM routes add budget AFTER ownership (stranger sees 404, never consumes budget).
4. Services re-filter by `project_id` (retrieval dual-filter); jobs re-chain ownership; storage validates before writing.
5. Frontend mirrors with guards + 401 logout, but enforcement is backend-only.

### E. Failure Paths
- F1 Bad credentials/duplicate email →400/401; expired/malformed JWT →401 (`test_error_handling.py:92-105`).
- F2 Foreign IDs →404 (13 guessed-ID cases in `test_cross_project.py:16-72`); anon →401.
- F3 Budget exhausted →429 `rate_limited` (per-user isolation, per-scope independence in `test_rate_limit.py`).
- F4 Evil prompt text stays in `<<<DATA>>>`, "never obey" (`test_prompt_boundaries.py`).
- F5 Bad upload →400/413 + sanitize (`test_upload_hardening.py`).

### F. Security Boundaries
- This diagram IS the boundary map: draw concentric containers `Internet → CORS → Auth(JWT) → Ownership(404) → Budget(429) → Query-filter(project_id) → DB`. Admin = side gate. External AI = only via `groq_client`.

### G. AI Boundaries
- Dev-time AI: auth code assistance (note).
- Product AI crossing:ataset boundary — user messages + document text ENTER prompts only inside `<<<DATA>>>`; AI output NEVER executes actions (no tool-use; structured JSON validated). Label "AI has no DB/service credentials."

### H. Requirement Traceability
- PRD §15 (auth, authz, input validation, data isolation, secure APIs/docs, AI-specific security, data-vs-instructions) → all nodes → `dependencies/*`, `core/*`, `storage_service`, prompt wrapping.
- PRD §3/4 (per-project context + separation for UX and security) → ownership deps + `project_id` filters.
- PRD §8 (permission-aware validated interfaces, no unrestricted DB) → `Depends` chain + Pydantic validation.
- PRD §18 (project-level isolation tests) → `tests/security/test_cross_project.py`, `test_material_access.py`, `test_authorization.py`.

### Visual Design Specification
- Orientation: landscape. Layout: attacker-left → concentric boundary rings → DB cylinder right; admin gate top; test shield bottom listing test files.
- Shapes: boundaries = nested dashed orange rectangles labeled with file + function; gates = diamonds (401/404/429/403); DB = cylinder.
- Arrows: green solid = allowed; red dashed = denied with code labels; legend maps codes→files.

---

## Diagram 12 — Async Processing Architecture

### A. Diagram Purpose
Shows everything that runs WITHOUT blocking HTTP: Celery topology, the four tasks, chaining/retry/idempotency semantics, job-state polling, and the single-container vs compose deployment of the worker.

### B. Nodes
| Node | Type | Technology | Responsibility | Repository path | Function |
|---|---|---|---|---|---|
| Celery app | Broker config | Celery 5, `redis://…/0` broker+backend, `json`, UTC, `track_started`, `broker_connection_retry_on_startup` | Task registry | `backend/app/worker/celery_app.py` | — |
| `get_task_session` | DB plumbing | Fresh engine from `DATABASE_URL` per task | Worker-side persistence (no request session) | `backend/app/worker/tasks/__init__.py` | `get_task_session` (+demo `ping/add`) |
| `process_pdf` | Task | `bind,max_retries=3` | Full §5 chain head (see D5) | `backend/app/worker/tasks/extraction.py` | `process_pdf` |
| `generate_embeddings` | Task | Celery (no bind retries; fast-fail) | Batch embed + 1:1 upsert | `backend/app/worker/tasks/embeddings.py` | `generate_embeddings` |
| `build_structure` | Task | `bind,max_retries=3` | Pass1→Pass2→persist (see D5) | `backend/app/worker/tasks/structure.py` | `build_structure` |
| `generate_recommendation` | Task | `bind,max_retries=2` | Score + persist winner (see D10) | `backend/app/worker/tasks/recommendations.py` | `generate_recommendation`, `refresh_best_effort` |
| `job_service` | State machine | SQLAlchemy | `pending→running→completed/failed` (+`pending→failed`), idempotent same-status else 400 | `backend/app/services/job_service.py` | `create_job`, `mark_*` |
| `background_jobs` table | State | PostgreSQL | `(job_type,status,material_id,error,celery_task_id)` | `backend/app/models/background_job.py` | — |
| Enqueue sites | Callers | `.delay()` | Upload → `process_pdf`; extraction → embeddings+structure; events → recommendation refresh | `backend/app/api/v1/materials.py`, `tasks/extraction.py`, `quiz_attempt/explain/flashcard services` | `.delay()` |
| Polling | Client | React | `GET /jobs/{id}` (ownership-chained) + materials list overlay + 5s gated poll | `backend/app/api/v1/jobs.py`, `frontend/src/features/projects/MaterialsPanel.tsx` | `get_authorized_job` |
| Runtime | Infra | supervisord (Railway single-container: redis-loopback + api + worker) vs compose (separate `api/worker/redis/postgres/web`) | Process topology | `backend/supervisord.conf`, `backend/Dockerfile`, `docker-compose.yml`, `railway.toml` | — |

### C. Connections
| Source → Destination | Dir | Protocol | Data | Sync/Async | Why | Evidence |
|---|---|---|---|---|---|---|
| Upload route → Redis (`process_pdf.delay`) | → | Celery message | `(job_id,material_id)` | async | Non-blocking ingest | `api/v1/materials.py` |
| `process_pdf` → Redis (`generate_embeddings.delay`, `build_structure.delay`) | → | Celery best-effort | job ids | async | Parallel fan-out; dispatch fail logged, extraction stays completed | `tasks/extraction.py:_chain_downstream` |
| Any completion → Redis (`generate_recommendation.delay` via `refresh_best_effort`) | → | Celery fire-and-forget swallowed, pytest-skipped | `(user_id,project_id)` | async | Fresh recs | `tasks/recommendations.py` |
| Tasks → PostgreSQL (`get_task_session`) | ↔ | SQL | all writes | async | Durable progress | `tasks/__init__.py` |
| Tasks → Groq (structure only) / local embed | → | HTTPS / in-process | outlines / vectors | sync-inside-async | AI steps off-request | `tasks/structure.py`, `tasks/embeddings.py` |
| UI → `GET /jobs/{id}` / `GET …/materials` | → | HTTP poll | statuses | async poll | No browser-hold needed | `api/v1/jobs.py`, `MaterialsPanel.tsx:77` |

### D. Data Flow
1. HTTP creates `pending` job + enqueues Celery id → returns immediately (browser may close).
2. Worker `pending→running`, does unit of work, `→completed/failed(+error)`; extraction fans out two more jobs; learning events fan out recommendation refresh.
3. UI polls job/material endpoints; retries/backoff happen broker-side per task policy.

### E. Failure Paths
- F1 Bad UUID → immediate fail, no retry. F2 Corrupt/empty/no-content → `failed` no-retry + `material.failed` event. F3 Transient → retry (extraction 3× `2^r*2`; structure Pass1 `httpx` 429:`60*(r+1)` else `2^r*2` 3×; reco 2×). F4 Per-topic structure failure → `failed_topics[]`, rest commits. F5 Same-status mark idempotent; illegal transition →400. F6 Dispatch failure → logged, upstream stays `completed`. F7 Duplicate delivery → idempotency skip (`processing+running` different celery id) / `ON CONFLICT DO NOTHING` events / 1:1 embedding upsert.
- Covered by `tests/test_celery.py`, `test_jobs.py`, `test_embeddings_task.py`, `test_pipeline_chain.py`.

### F. Security Boundaries
- Broker is NOT exposed publicly (compose internal network; supervisord loopback `127.0.0.1:6379`); tasks re-resolve ownership from IDs (no caller trust); job reads ownership-chained.

### G. AI Boundaries
- Dev-time AI: task code assistance (note).
- Product AI off-request: structure LLM + local embeddings run ONLY in worker tasks — label worker lane "AI runs here too (not only in HTTP)."

### H. Requirement Traceability
- PRD §5/13 (queued/processing/ready/failed visibility; retry/failure/duplicate handling; browser-close safe) → job states + policies + polling → `job_service.py`, `tasks/*.py`, `MaterialsPanel.tsx`.
- PRD §12 (retries, duplicate events, idempotency) → `activity_service ON CONFLICT`, task idempotency, `learning_event.idempotency_key`.
- PRD §15 (timeouts/retries/fallback, no duplicate state on retry) → backoff counts + upsert/ON CONFLICT + `IntegrityError` guard.

### Visual Design Specification
- Orientation: landscape. Layout: HTTP lane top (enqueue + return), broker middle (Redis queue icon as rectangle), worker pool bottom with 4 task boxes, DB cylinder right, UI poll loop left.
- Shapes: tasks = double-border rectangles with `max_retries` label; broker = queue shape (rectangle with lines); job states = 4-circle lifecycle.
- Arrows: dashed = `.delay()` with payload labels; solid = SQL; red dashed = retry/failed exits with countdown formulas; legend required.

---

## Diagram 13 — Deployment Architecture

### A. Diagram Purpose
Shows the two REAL deployment targets (compose for local/full-stack, Railway single-container for backend) and the Figma prototype that is NOT deployed — with ports, volumes, env, healthchecks, and build args.

### B. Nodes
| Node | Type | Technology | Responsibility | Repository path | Key config |
|---|---|---|---|---|---|
| `postgres` | Container | `pgvector/pgvector:pg16` | Data; init `CREATE EXTENSION vector`; `5433:5432`; `postgres_data` + init-sql mount; `pg_isready` healthcheck | `docker-compose.yml`, `docker/postgres/init-pgvector.sql` | `5433:5432`, `postgres_data:/var/lib/postgresql/data` |
| `redis` | Container | `redis:7-alpine` | Broker+backend; `6379:6379`; `redis_data`; `redis-cli ping` healthcheck | `docker-compose.yml` | `6379:6379` |
| `api` | Container | `backend/Dockerfile` + `uvicorn app.main:app 0.0.0.0:8000` | HTTP API; `8000:8000`; env DB/Redis/JWT/LLM/OCR/`UPLOAD_DIR /data/uploads`/`CORS_ORIGINS (+3000)`; `uploads:/data/uploads`; waits healthy pg+redis | `docker-compose.yml`, `backend/Dockerfile` | `8000:8000` |
| `worker` | Container | Same build, `celery -A app.worker.celery_app worker` | Background tasks; same env + `OCR_*`; `uploads` vol | `docker-compose.yml` | — |
| `web` | Container | `frontend/Dockerfile` (node:20 build → nginx runtime, SPA `try_files`) | Serves `frontend/dist`; build args `VITE_API_BASE_URL=http://localhost:8000`, `VITE_API_V1_PREFIX=/api/v1`; `5173:80`; depends `api` | `docker-compose.yml`, `frontend/Dockerfile` | `5173:80` |
| Railway (backend only) | PaaS | `DOCKERFILE backend/Dockerfile` + supervisord (redis-loopback:127.0.0.1 + api `$PORT` + worker conc=2) | Single-container API+worker+loopback-redis; healthcheck `/api/v1/health` 300s; `ON_FAILURE×10` | `railway.toml`, `backend/supervisord.conf`, `backend/Dockerfile` | `healthcheckPath=/api/v1/health` |
| `backend/Dockerfile` detail | Image | `python:3.11-slim` + `tesseract-ocr(+eng)` + `redis-server` + `supervisor` + bake `bge-small-en-v1.5` (`FASTEMBED_CACHE_PATH`) | Reproducible AI-ready image; `EXPOSE 8000`; `HEALTHCHECK /api/v1/health`; `CMD supervisord` (compose overrides) | `backend/Dockerfile` | `EXPOSE 8000` |
| Env/secrets | Config | `.env` (git-ignored) + compose env + Railway dashboard | `DATABASE_URL/JWT_SECRET/GROQ_API_KEY/INCEPTION_API_KEY/...`; image ships NO secrets; `extra=ignore` | `backend/app/core/config.py`, `.mise.toml` (toolchain) | `env_file=.env` |
| Non-deployed | Prototype | Root Vite + Figma plugins (`PORT||8443`), `src/` | Design scaffold only — NO container, NO compose service, NO Railway target | `vite.config.ts`, `src/*`, `package.json`, `index.html` | `8443` |

### C. Connections
| Source → Destination | Dir | Protocol | Data | Why | Evidence |
|---|---|---|---|---|---|
| `web:80` → `api:8000` | → | HTTP `/api/v1` | SPA REST | Compose full-stack | `frontend/Dockerfile` args, `docker-compose.yml` |
| `api/worker` → `postgres:5432` | ↔ | TCP SQL | rows + `Vector(384)` | Data | `DATABASE_URL …@postgres:5432/…` |
| `api/worker` → `redis:6379` | ↔ | Redis | Celery msgs | Async | `CELERY_* redis://redis:6379/0` |
| `api/worker` → Groq/Inception | → | egress HTTPS | LLM JSON | AI | `groq_client.py` |
| Railway ingress → `$PORT` → supervisord `api` | → | HTTP | same API | PaaS backend | `supervisord.conf`, `railway.toml` |
| Healthcheckers → `/api/v1/health` | → | HTTP `{"status":"ok"}` | liveness | Ops | `api/v1/health.py`, both Docker + Railway configs |

### D. Data Flow
Compose: `postgres+redis` (healthy) → `api` (8000) + `worker` → `web` (5173, baked API URL) → browser. Railway: single image boots loopback-redis + api (`$PORT`) + worker; platform probes `/api/v1/health`.

### E. Failure Paths
- F1 Unhealthy pg/redis → `api/worker` don't start (`depends_on healthy`).
- F2 Healthcheck fail → container restart (compose) / `ON_FAILURE×10` (Railway).
- F3 Missing `DATABASE_URL/JWT_SECRET/GROQ_KEY` → boot/call failure (no committed secrets; `.env` required).
- F4 Baked `VITE_API_*` mismatch → SPA points at wrong API (rebuild needed — args are build-time).

### F. Security Boundaries
- Secrets never in image/repo (` Voice: image ships no secrets`; `.gitignore` + `extra=ignore`); Redis loopback-only on Railway, private network in compose; CORS allow-list per env; JWT secret via env.

### G. AI Boundaries
- Dev-time AI: Dockerfiles/compose authored with assistance (note).
- Product AI at runtime: container egress to Groq/Inception + baked local embedding cache (`FASTEMBED_CACHE_PATH`) — label image layer "contains bge-small-en-v1.5 (~384-dim)".

### H. Requirement Traceability
- PRD §18 (public URL; working frontend+backend+DB+auth+AI+docs+background; secrets out of code) → compose (full-stack) + Railway (backend) + `.env` discipline.
- PRD §17 (choices justified: pgvector, Celery+Redis, local embeddings, Groq) → `docker-compose.yml`, `requirements.txt` (`pgvector/fastembed/celery/redis/httpx/pymupdf/tesseract`), `docs/architecture-decisions.md`, `docs/storage.md`.

### Visual Design Specification
- Orientation: landscape. Layout: two deployment boxes side-by-side: `docker-compose (local/full-stack)` with 5 service boxes + volumes + ports; `Railway (single-container)` with supervisord 3-process stack; `NOT deployed` greyed box for root prototype.
- Shapes: containers = rectangles with `image:tag` + `port:port`; volumes = cylinders; env = note shapes; healthcheck = green crosshair annotation.
- Arrows: solid = runtime TCP/HTTP with port labels; dashed = build-time args; red = failure/restart; legend required.

---

## Diagram 14 — Observability / Error Handling Architecture

### A. Diagram Purpose
Shows how EVERY request, LLM call, event, and job is observed: envelope errors, `ai_usage` metering, learning events, admin aggregates, health, and what evaluation exists vs what's only aggregates (honest gap).

### B. Nodes
| Node | Type | Technology | Responsibility | Repository path | Function |
|---|---|---|---|---|---|
| Error envelope | Middleware | Starlette handlers | `{error:{code,message,details}}`; `STATUS_CODES` incl. 413/415/422/429/502/503; `_safe_message` scrubs 500; 422 `details[{loc,msg,type}]` | `backend/app/core/exceptions.py`, `backend/app/schemas/errors.py` | `register_error_handlers`, `build_envelope` |
| `LLMCallRecord` scope | Metering | Context-local list in `groq_client` | Per-attempt `(provider,model,prompt/completion_tokens,tokens_estimated,latency_ms,success,error_type,http_status)`; token fallback `len/4`; 60s timeout | `backend/app/services/ai/groq_client.py` | `chat_json`, `LLMCallRecord` |
| `track_llm_call` + `pricing` | Persistence | Dedicated session + placeholder prices | 1 `ai_usage` row/attempt (incl. failures/retries), `cost_usd` if success else NULL, never raises, never stores prompt/response | `backend/app/services/ai_usage_service.py`, `services/ai/pricing.py` | `track_llm_call`, `estimate_cost_usd`, `FEATURE_*` |
| `ai_usage` table | Data | PostgreSQL | `(feature,provider,model,tokens(+estimated),latency,success,error,http,cost,meta{chunks,min_distance},user/project SET NULL)` | `backend/app/models/ai_usage.py` | — |
| `activity_service` + `learning_events` | Events | `pg_insert ON CONFLICT(idempotency_key) DO NOTHING`, savepoint flush, never raises | 11 types (`project.created/material.*/tutor.message/quiz.*/question.answered/assessment.completed/mastery.updated/recommendation.generated`); small payloads | `backend/app/services/activity_service.py`, `models/learning_event.py` | `record_event(_committed)` |
| Admin observability API | Controller | Direct aggregates (no service) | `GET /admin/overview` (counts + `cost_week_usd`), `/activity` (filtered events), `/ai-usage` (calls/tokens/cost/error_rate/p50/p95 via `percentile_cont`, top errors, day×feature×provider×model ≤500), `/health` (failed jobs + failed LLM, 24h counts, by-status), `/users/{id}/journey`, `/users` | `backend/app/api/v1/admin.py` | — |
| `/admin/ai-evaluation` (descriptive ONLY) | Controller | SQL aggregates, read-only | Tutor (supported rate, citation coverage/avg), retrieval (avg chunks/top-distance/zero-context rate, by model), assessment (MCQ avg/accuracy-by-difficulty, OE bands), reco (accept rate), 8-week trends; NULLs never fabricated; NO LLM-judge/curated-set/MRR/regression gate | `backend/app/api/v1/admin.py:412-671` | — |
| Health + rate-limit ops | Ops | `GET /api/v1/health {"status":"ok"}` (no auth/DB); in-memory budgets + `reset_budgets()` test-only | Liveness; abuse signal (429) | `backend/app/api/v1/health.py`, `core/rate_limit.py` | `health_check` |
| Admin UI | Client | React panels | Overview/Activity/AIUsage/Evaluation/Health/Journey | `frontend/src/features/admin/*` | — |
| Eval/test evidence | Docs+tests | Markdown + pytest | `docs/evaluation-report.md` (R19/R39 PARTIAL: observability PASS, eval WEAK), `docs/usage-tracking.md` (choke-point, PII, limits), tracking-resilience + error-handling tests | `docs/evaluation-report.md`, `docs/usage-tracking.md`, `backend/tests/test_tracking_resilience.py`, `test_error_handling.py`, `test_ai_usage.py` | — |

### C. Connections
| Source → Destination | Dir | Protocol | Data | Sync/Async | Why | Evidence |
|---|---|---|---|---|---|---|
| Any raise → envelope | → | exception | code+message | sync | Uniform debuggability | `core/exceptions.py` |
| Every `chat_json` → `LLMCallRecord` → `track_llm_call` → `ai_usage` | → | in-process → separate SQL session | metering row | sync (survives caller rollback) | Cost/latency/failure visibility | `groq_client.py:167-209`, `ai_usage_service.py:95-133` |
| Domain actions → `record_event(_committed)` | → | SQL (ON CONFLICT) | event rows | sync | Activity/analytics/reco/admin feed | `activity_service.py` |
| Jobs/tasks → `mark_*` + `error` | → | SQL | job states | async | Workflow visibility | `job_service.py` |
| Admin UI → `/admin/*` | → | HTTP (`get_current_admin`) | aggregates | sync | Lightweight ops (not infra monitoring) | `features/admin/*`, `api/v1/admin.py` |
| Docs/tests → gaps | — | — | PARTIAL verdicts | — | Honest limits | `evaluation-report.md:39,60,89-100` |

### D. Data Flow
1. Request path: validation/authz/domain errors → envelope codes (400/401/403/404/413/415/422/429/500/502).
2. AI path: each LLM attempt metered (model/feature/latency/tokens/cost/success + `meta`) into `ai_usage` via rollback-proof session — even when the request itself rolls back.
3. Event path: domain actions append idempotent events feeding user activity, analytics, recommendations, admin.
4. Admin path: aggregates (usage p50/p95, error rates, evaluation descriptives, health) rendered in dashboard; evaluation answers "slow/which model/poor retrieval/failed workflow/cost/why-doc-failed" from stored columns.

### E. Failure Paths
- F1 Metering DB down → request STILL 200 (`test_tracking_resilience.py:70-101`).
- F2 Event insert down → request STILL 200 (`:130-154`).
- F3 Malformed LLM JSON →502 `upstream_unavailable` (never 500 leak; `test_error_handling.py:163-194`).
- F4 500 internals scrubbed (`traceback/hashed_password` never leak; `:145-160`).
- F5 Timeout: 60s set but NO explicit timeout test (only `ConnectError` propagation) — label as gap.
- F6 No streaming-token counts (all calls non-streaming JSON) + embeddings unmetered (`usage-tracking.md:83`).

### F. Security Boundaries
- PII: no prompt/response in `ai_usage`; no free-text error column (could echo content); no hashes in admin users; event payloads minimal.
- Admin gate: ALL `/admin/*` require `get_current_admin` (401/403).

### G. AI Boundaries
- Dev-time AI: eval docs drafted with assistance (note).
- Product AI observed: every LLM call metered + aggregated; NO hidden model calls (choke-point `chat_json`); embeddings explicitly UNmetered (document as gap, not hidden).

### H. Requirement Traceability
- PRD §14 (abstract generation/structured/embeddings/eval/doc-understanding; track model/feature/latency/tokens/cost/success; debug slow/model/poor-retrieval/failed-workflow/cost/doc-fail; eval tutor/retrieval/assessment/reco; regression awareness) → `groq_client` + `embedding_client` + `ai_usage*` + `pricing` + `/admin/ai-usage|ai-evaluation|health` + `evaluation-report.md` (PARTIAL where aggregates-only).
- PRD §15 (timeouts/retries/logging/fallback/recovery; no duplicate state) → 60s timeout, retry policies, idempotency, envelope logging.
- PRD §16 (admin: users/activity/engagement/analytics/AI usage/eval/background/health + journey) → `admin.py` 7 endpoints + 6 panels.

### Visual Design Specification
- Orientation: landscape. Layout: three horizontal lanes (Errors top, AI metering middle, Events/Jobs bottom) converging on `Admin API + UI` right; docs/tests box as annotation.
- Shapes: envelope = hexagon; `ai_usage`/`learning_events` = cylinders with column lists; admin endpoints = stacked rectangles; gaps = yellow note shapes ("aggregates only — no LLM-judge").
- Arrows: solid = write paths; dashed = read/aggregate; red = failure-resilient (still-200) paths; legend required.

---

## Diagram 15 — End-to-End Learning Loop

### A. Diagram Purpose
Walks the PRD §1/§19 success path in executable order — Space → Project → Material → Knowledge → Tutor (+citation) → Unsupported handling → Adaptive Quiz → Assessment → Mastery → Growth → Analytics → Recommendation → Continue — binding each step to its real route/service/table/UI, with admin watching throughout.

### B. Nodes
Numbered loop stations (each: UI page + API route(s) + service(s) + table(s)):

| # | Station | UI | API | Service | Tables |
|---|---|---|---|---|---|
| 1 | Create Space | `SpacesPage.tsx` | `POST/GET /spaces`, `GET /spaces/{id}` (`api/v1/spaces.py`) | `space_service.py` | `spaces` |
| 2 | Create Project | `SpaceProjectsPage.tsx` | `POST/GET /spaces/{sid}/projects`, `GET /projects/{id}` (`projects.py`) | `project_service.py` | `projects` (+`project.created` event) |
| 3 | Add Material | `MaterialsPanel.tsx` | `POST/GET /projects/{id}/materials` (`materials.py`) | `storage_service.save_pdf`, `job_service` | `materials(pending)`, `background_jobs` |
| 4 | Process & Understand | gated 5s poll | `GET …/materials`, `GET /jobs/{id}` (`materials.py`, `jobs.py`) | `process_pdf` → chunks → `generate_embeddings` + `build_structure` | `document_chunks`, `embeddings`, `topics/subtopics/concepts`, `concept_relationships` |
| 5 | Learn with Tutor | `TutorChat.tsx` | `POST …/tutor/conversations*/messages`, `POST …/quiz-plan` (`tutor.py`) | `tutor_conversation_service` → `tutor_service.ask_question` → `retrieval+rag+chat_json` | `tutor_conversations/messages`, `ai_usage`, `learning_events(tutor.message)` |
| 6 | Grounded Answer + Citation | same | same | `TutorCitation(chunk_id,material_id,page,source,excerpt 280ch)` per chunk | `tutor_messages.citations` |
| 7 | Unsupported Handling | same | same (no new endpoint) | gate: 0 chunks OR min distance>0.5 → `supported=false`, LLM skipped | same (empty citations) |
| 8 | Adaptive Quiz | `QuizSetup/Modes/Taker` | `POST …/quizzes/generate|…/attempts|…/answers|…/complete` (`quizzes.py`) | `adaptive_quiz_service` + `quiz_generation_service` + `quiz_attempt_service` | `quizzes/questions/attempts/answers`, `mastery_evidence(mcq)` |
| 9 | Open-Ended Assessment | `OpenEndedAnswersPage/PracticeSession` | `POST …/assessment/open-ended/generate|…/open-ended|…/explain-back` (`assessment.py`) | `open_ended_assessment_service` + `explain_it_back_service` | `mastery_evidence(open_ended/explain_back)` |
| 10 | Mastery Update | `Dashboard/ConceptDetail` | read via `GET …/dashboard`, `GET …/knowledge/*` | `mastery_service` (+levels/confidence/mismatch/rollup) | `mastery_evidence` replay + `mastery.updated` events |
| 11 | Growth | `GrowthView` | `GET …/growth[?concept_id=]` (`growth.py`) | `growth_service` replay | same evidence |
| 12 | Analytics | `AnalyticsView/Page`, `OverviewView` | `GET …/analytics`, `GET …/analytics/overview?time_range=` (`analytics.py`) | `analytics_service` (+dashboard/home) | `learning_events`, `ai_usage`, evidence |
| 13 | Recommendation | `Dashboard/Overview/Practice/Home` | `GET …/dashboard`, `GET …/practice/recommendations`, `POST …/dashboard/accept\|dismiss\|refresh` | `dashboard_service` + `recommendation_service` (+bg refresh) | `recommendations`, `recommendation.generated` |
| 14 | Continue Learning | `HomeDashboard` (`GET /me/home`), `AppShell` tabs | `GET /me/home`, `GET /me/streak` (`me.py`) | `home_service` (continue tab, recent ≤6, stats, attention ≤5, next ≤5, week activity) | all of the above |
| ∞ | Admin watches | `AdminPage + 6 panels` | `GET /admin/*` (7 endpoints) | direct aggregates | `users/spaces/projects/activity/AI/eval/health` |

### C. Connections
Loop edges 1→2→…→14→(back to 5/8/3) are the UI→API→service→DB chains above (all sync except 3→4 async via Celery and 10→13 async refresh). Admin `∞` reads every station's tables via `/admin/*` (sidecar, never in the loop path).

### D. Data Flow
Execute stations in order with the Demo-Video script (PRD §20): Space → Project (+goal) → Upload → poll Ready → Ask Tutor → verify citation → ask out-of-scope → verify `supported=false` → Adaptive Quiz (mixed difficulties from weakest concepts) → Open-ended + Explain-back → check Mastery bars/statuses → check Growth deltas → check Analytics (activity/performance/mastery/AI) → accept Recommendation → Continue from Home. Admin simultaneously inspects journey/activity/AI/health.

### E. Failure Paths
Per-station exits (draw red spurs, not loop breaks): 401/404 at any gate; 400/413 upload; `failed` material (poll shows error); `supported=false` (by design, loop continues); 422 quiz/assessment generation; capped mastery (tutor-only etc.); empty reco (nothing scorable); metering/event outage (loop still 200). Background retries per Diagram 12.

### F. Security Boundaries
Single orange container around stations 1–14 labeled "One user's project scope — every edge re-checks `get_authorized_project`"; admin sidecar in its own `get_current_admin` container; external AI touched only at stations 4 (structure), 5–6 (tutor), 8–9 (quiz/assessment).

### G. AI Boundaries
- Dev-time AI: entire loop built with assistants (off-loop note).
- Product AI per station: 4 LLM (structure), 5 (tutor/title/quiz-plan), 8 (quiz questions), 9 (OE question+grade) + local embeddings (4–5); stations 1–3, 10–14 deterministic. Color ONLY the AI stations purple.

### H. Requirement Traceability
- PRD §1 loop + §19 success criterion (full chain without losing context + admin inspection) → stations 1–14+∞ → file chains in table B.
- PRD §20 demo script order → same station order (Space→…→Admin).
- PRD §2 Context-First / Evidence-over-guessing / Persistent-relevant / Async / Observable / Safe-AI → gates at 5–7 (isolation + unsupported + budgeted context), 3–4 (async), 12–∞ (observable), prompts (safe).

### Visual Design Specification
- Orientation: landscape (wide loop) or 2-page portrait loop. Layout: stations as numbered rounded rectangles in a clockwise loop (2 rows: 1–7 top, 14–8 bottom), admin sidecar box above with dashed read-arrows to each station's tables.
- Shapes: stations = numbered rectangles with 3-line labels (`Station` / `UI page` / `POST …`); async hop 3→4 = dashed; unsupported 7 = branch diamond; AI stations purple fill-light; DB tables = tiny cylinder icons WITH text labels under each station.
- Arrows: thick numbered loop 1–14; thin dashed admin reads; red failure spurs; legend + station table (B) reproduced as a figure key; ≥9pt; no icon-only steps.

---

## Appendix — Global Visual Rules (all diagrams)
- Page: A4/Letter, landscape except D2 (portrait) and D15 (landscape-wide or 2-page). Margins ≥15mm. Export PDF: embed fonts, ≥150dpi.
- Typography: titles 16–18pt bold; box titles 10–11pt bold; paths/Endpoints 8–9pt monospace (`Consolas/Menlo`); edge labels 8–9pt; legend 8pt. No text <8pt.
- Color (restrained): black edges; red `#C0392B` failures; orange `#E67E22` security; purple `#7D3C98` AI-calling; grey `#7F8C8D` external/dev-note; yellow `#F9E79F` gaps. No gradients/illustrations.
- Arrows: solid open-arrow = sync; dashed open-arrow = async/poll/read; red dashed = failure; line width 1–1.5pt; every arrow labeled (verb or code).
- Machine-readability: every service/table/route box carries its `backend/...` or `frontend/...` path; abbreviations (`RAG`, ` pgvector`, `SM-2`, `EMA`, `PII`) defined once in legend.
- Prohibited: invented components, README-only claims, icon-only nodes, crossing-arrow spaghetti (use lanes/containers), streaming/caching boxes (NOT implemented — if shown, label "NOT IMPLEMENTED" explicitly).
