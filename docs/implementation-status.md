# Implementation Status — AI Study Companion

**Last updated:** 2026-09-16 — Phase 34 complete, awaiting `CONTINUE`
**Roadmap:** `ai-study-companion-detailed-opencode-roadmap.md` (58 phases)
**Blueprint:** `ai-study-companion-blueprint.md` v2
**Protocol:** One phase at a time, runnable after every phase, no silent next-phase start.

---

## Phase Overview

| Phase | Name | Status | Completed | Verification | Notes |
|------:|------|--------|-----------|--------------|-------|
| 01 | Repository & Blueprint Analysis | ✅ Complete | 2026-09-15 | Pass (docs-only; see § Verification below) | Blueprint frozen as contract; no product code |
| 02 | Project Skeleton & Monorepo Layout | ✅ Complete | 2026-09-15 | Pass (skeleton, no product code) | `.gitignore` + `.env.example`×2 + `README` + `.gitkeep`; verified no secrets/service drift |
| 03 | Frontend Initialization | ✅ Complete | 2026-09-15 | Pass (`npm run build` ✓ 24 modules) | Vite+React+TS+Tailwind+shadcn+Router+Axios; `src/lib/axios.ts` + routing shell; `npm run build` 260kB gzip 82.85kB |
| 04 | Backend Initialization | ✅ Complete | 2026-09-15 | Pass (pytest 3/3, health 200) | FastAPI shell `app/main.py`+`api/v1/health`+`pyproject.toml`/`requirements.txt`+`tests/test_health.py`; `/api/v1/health` 200 |
| 05 | Docker Compose Foundation | ✅ Complete | 2026-09-15 | Pass (config --quiet + dry-run) | 5 services `api/worker/web/postgres/redis`; Dockerfiles + `uploads` shared; `VITE localhost` vs `postgres/redis` service names |
| 06 | PostgreSQL Setup | ✅ Complete | 2026-09-15 | Pass (SELECT 1 via host 5433 + container) | `core/config.py`+`db/session.py`+`psycopg`; `postgres:16-alpine` 5433:5432 `SELECT 1` true |
| 07 | pgvector Setup | ✅ Complete | 2026-09-15 | Pass (vector 0.8.6 + throwaway) | `pgvector/pgvector:pg16` + `CREATE EXTENSION` + `vector(3)` test; 1536 dims |
| 08 | SQLAlchemy & DB Session Management | ✅ Complete | 2026-09-15 | Pass (6 db +3 health, DI) | `Base` + `UUIDTimestampMixin` + `SessionLocal`/`get_db` (yield/rollback/close) |
| 09 | Alembic Migrations | ✅ Complete | 2026-09-15 | Pass (upgrade head idempotent) | `alembic.ini` + `env.py` (Base.metadata + get_settings url) + `5257ffa81b36` no-op |
| 10 | User Model | ✅ Complete | 2026-09-15 | Pass (migration + round-trip) | `users` UUID email unique + schemas + `d65fb0219416` + 3 tests |
| 11 | Password Hashing | ✅ Complete | 2026-09-15 | Pass (Argon2id 6 tests) | `security.py` hash/verify + `test_security.py` 6 tests |
| 12 | JWT Authentication | ✅ Complete | 2026-09-15 | Pass (register/login+jwt 5 tests) | `jwt.py` + `auth.py` + `get_current_user` + 5 tests |
| 13 | Auth Frontend | ✅ Complete | 2026-09-15 | Pass (`npm run build` 84 modules) | `AuthContext` + axios Bearer + ProtectedRoute + Login/Register |
| 14 | Spaces | ✅ Complete | 2026-09-15 | Pass (create/list isolation) | `spaces` FK user + service + `3bfb01f2ee6b` + 4 tests |
| 15 | Projects | ✅ Complete | 2026-09-15 | Pass (nested scoped 404) | `projects` FK space + service + `ccb823bfc29d` + 3 tests |
| 16 | Project Isolation & Authorization | ✅ Complete | 2026-09-15 | Pass (own 200 foreign 403/404 401) | `authorization.py` space/project deps + `GET space/project` guards + 2 tests |
| 17 | Spaces/Projects Frontend | ✅ Complete | 2026-09-15 | Pass (`npm run build` 87 mods) | `SpacesPage` + `SpaceProjects` + `ProjectDetail` + hierarchy routes |
| 18 | Materials Model | ✅ Complete | 2026-09-15 | Pass (migration + round-trip) | `materials` FK project + `242af3866a09` + 2 tests |
| 19 | PDF Upload | ✅ Complete | 2026-09-15 | Pass (PDF 201/non-PDF 400/oversize 413) | `storage_service` + `POST /projects/{id}/materials` + 3 tests |
| 20 | Shared Upload Volume | ✅ Complete | 2026-09-15 | Pass (api→worker same file) | `uploads:/data/uploads` shared + `storage.md` + probe verified |
| 21 | Celery + Redis | ✅ Complete | 2026-09-15 | Pass (ping→pong via worker) | `celery_app` + `ping`/`add` + `docker` dispatch + 2 tests |
| 22 | Background Job Tracking | ✅ Complete | 2026-09-15 | Pass (lifecycle+auth) | `background_jobs` + `job_service` + `GET /jobs/{id}` + 2 tests |
| 23 | PDF Text Extraction | ✅ Complete | 2026-09-15 | Pass (extract→ready/completed) | `process_pdf` + `extracted_text` + `3c13e851f931` + 4 tests |
| 24 | Learning Structure Extraction | ✅ Complete | 2026-09-15 | Pass (7 tests, retry+validate) | `groq_client` + `extract_structure` + `StructureOutline`, no DB yet |
| 25 | Topic/Subtopic/Concept Persistence | ✅ Complete | 2026-09-15 | Pass (idempotent upsert) | `topics/subtopics/concepts` + `cf04f880e71a` + `persist_structure` + 2 tests |
| 26 | Structure API + Frontend | ✅ Complete | 2026-09-15 | Pass (tree + isolation) | `GET structure` + `StructureView` + 1 test |
| 27 | Chunking | ✅ Complete | 2026-09-15 | Pass (boundaries+overlap) | `document_chunks` + `3a900a15443a` + `chunking_service` + 12 tests |
| 28 | Retrieval (RAG) | ✅ Complete | 2026-09-16 | Pass (real pgvector isolation) | `retrieval_service` + 5 integration tests |
| — | Embedding Client (detail §28) | ✅ Complete | 2026-09-15 | Pass (mocked unit) | `embedding_client` + 6 tests |
| — | Embedding Worker (detail §29) | ✅ Complete | 2026-09-16 | Pass (mocked task+live pgvector) | `generate_embeddings` + `ab60908d37ca` + 5 tests |
| — | RAG Service (detail §31) | ✅ Complete | 2026-09-16 | Pass (mocked assembly unit) | `assemble_context` + `rag.py` + 6 tests |
| 29 | Tutor (Grounded Q&A) | ✅ Complete | 2026-09-16 | Pass (grounded+unsupported+isolation) | `tutor ask` endpoint + 6 tests |
| 30 | Tutor Frontend | ✅ Complete | 2026-09-16 | Pass (build + live contract flow) | `TutorChat` + retrieval short-circuit |
| 31 | Confidence Capture | ⏳ Pending | — | — | — |
| — | Quiz Data Model (detail §34) | ✅ Complete | 2026-09-16 | Pass (models + migration) | `quizzes/questions/attempts/answers` + `4b3487d354d6` + 3 tests |
| 32 | Quiz Generation | ⏳ Pending | — | — | — |
| 33 | Quiz Attempt & Answer Flow | ⏳ Pending | — | — | — |
| 34 | Quiz Frontend | ⏳ Pending | — | — | — |
| 35 | Open-Ended Assessment | ⏳ Pending | — | — | — |
| 36 | Explain-It-Back | ⏳ Pending | — | — | — |
| 37 | Mastery Engine | ⏳ Pending | — | — | — |
| 38 | Confidence Engine | ⏳ Pending | — | — | — |
| 39 | Mismatch Detection | ⏳ Pending | — | — | — |
| 40 | Decision / Recommendation Engine | ⏳ Pending | — | — | — |
| 41 | Recommendations API + Frontend | ⏳ Pending | — | — | — |
| 42 | Growth Analysis | ⏳ Pending | — | — | — |
| 43 | Project Analytics | ⏳ Pending | — | — | — |
| 44 | Global/Admin Analytics | ⏳ Pending | — | — | — |
| 45 | Admin Dashboard (Read-Only) | ⏳ Pending | — | — | — |
| 46 | Activity Events & AI Usage | ⏳ Pending | — | — | — |
| 47 | Error Handling & Edge Cases | ⏳ Pending | — | — | — |
| 48 | Observability & Health | ⏳ Pending | — | — | — |
| 49 | Security Hardening | ⏳ Pending | — | — | — |
| 50 | Rate Limiting & CORS | ⏳ Pending | — | — | — |
| 51 | Frontend Polish & Navigation | ⏳ Pending | — | — | — |
| 52 | Docker Production Notes | ⏳ Pending | — | — | — |
| 53 | Testing & Coverage | ⏳ Pending | — | — | — |
| 54 | Docs & Onboarding | ⏳ Pending | — | — | — |
| 55 | Demo Seed Data | ⏳ Pending | — | — | — |
| 56 | E2E Verification | ⏳ Pending | — | — | — |
| 57 | Performance & Polish | ⏳ Pending | — | — | — |
| 58 | Release Readiness | ⏳ Pending | — | — | — |

---

## Phase 01 — Detail

**Scope:** Documentation baseline only; no framework/DB/queue/AI substitution.

**Files created in this phase:**
- `docs/00-blueprint-analysis.md` — full blueprint extraction, stack, boundaries, hard rules, ambiguity log with per-phase confirmation plan
- `docs/architecture-decisions.md` — ADRs 001–009 (stack, service/DB/security boundaries, background processing, AI wrappers, migrations, exclusions, deferrals)
- `docs/implementation-status.md` — this file
- `docs/opencode-prompts.md` — pre/post prompt log for Phase 01 (required by execution protocol)

**Out of scope for this phase (correctly deferred):**
- No `backend/` or `frontend/` scaffolding (Phase 02–05)
- No DB/migration/model code (Phases 06–10)
- No product logic, no dependency additions, no schema changes

**Verification (2026-09-15):**
- Blueprint fully read; stack/boundaries/exclusions/hard rules extracted (see `00-blueprint-analysis.md §4–9`)
- Ambiguity log recorded without invention (mastery/mismatch/recommendation/quiz formulas logged as provisional, gated on their phases — `00-blueprint-analysis.md §10`)
- `docs/` folder + git repo present; only the 4 docs files changed
- No cross-project data paths yet (no IDs, endpoints, jobs, retrieval, or UI flows to test — N/A for this phase)
- Diff inspected: no dependency, folder, schema, or service-boundary changes beyond the 4 documentation files
- `docs/implementation-status.md` updated; ready for `CONTINUE`

**Result:** ✅ Pass

**Known issues:** None. Blueprint v2 formulas for mastery/mismatch/recommendation/quiz are intentionally left as provisional pending their dedicated phases per the source roadmap.

**Next:** Await `CONTINUE` before starting Phase 02 (Project Skeleton & Monorepo Layout). Do not start Phase 02 silently.

---

## Phase 02 — Detail

**Scope:** Repository skeleton only — no framework install, no Docker, no DB, no product logic.

**Files created/changed in this phase:**
- `.gitignore` (new) — ignores `.env`/`*.env` (not `.env.example`), Python/Node/OS/editor artifacts, `uploads/` volume, `docker-compose.override.yml`
- `backend/.env.example` (new) — placeholders for `DATABASE_URL`, `JWT_SECRET` (+ algorithm/expiry), `GROQ_API_KEY`, `OPENAI_API_KEY`, `REDIS_URL`/`CELERY_*`, `UPLOAD_DIR=/data/uploads`, `API_V1_PREFIX`/`CORS_ORIGINS`
- `frontend/.env.example` (new) — `VITE_API_BASE_URL=http://localhost:8000` with Docker vs host networking comment
- `README.md` (modified, 46 B → 6287 B / 120 lines) — frozen stack, layout diagram, prerequisites, env setup, Docker Compose + local dev commands, docs index, phase note, out-of-scope + security
- `backend/.gitkeep` / `frontend/.gitkeep` (new) — keep empty dirs tracked
- `docs/opencode-prompts.md` — Phase 02 verbatim prompt recorded before edits, updated post-verification
- `docs/implementation-status.md` — this file (Phase 02 row updated)

**Out of scope for this phase (correctly deferred):**
- No `backend/app/` or `frontend/src/` scaffolding (Phases 03–04)
- No `docker-compose.yml` / Dockerfiles (Phase 05)
- No `requirements.txt` / `package.json` dependency installs
- No product code, migrations, or service logic

**Verification (2026-09-15):**
- Verified exactly `backend/` + `frontend/` + `docs/` top-level dirs — no third service (`Get-ChildItem -Directory` → `backend, docs, frontend`)
- Verified `.gitignore` ignores real `.env` (`git check-ignore backend/.env` → `.gitignore:*.env`) but not `.env.example` (no output — not ignored)
- Scanned `*.env.example` for real secrets (`sk-`/`gsk_` regex → false); confirmed placeholders (`change-me`, `your-groq-api-key-here`) present; real `backend/.env`/`frontend/.env` absent
- Verified `README.md` documents structure and how to run before feature code; 120 lines
- Diff inspection: only `.gitignore`, `README.md`, `backend/.env.example`, `frontend/.env.example`, `*.gitkeep` plus docs logs changed — no dependency, schema, or service-boundary drift
- No cross-project data paths to test (skeleton phase, N/A)
- No automated tests applicable to skeleton (nearest regression: none); structural checks suffice
- `docs/implementation-status.md` updated; protocol `CONTINUE` gate respected

**Result:** ✅ Pass

**Known issues:** None.

**Next:** Await `CONTINUE` before starting Phase 03 (Frontend Initialization). Do not start Phase 03 silently.

---

## Phase 03 — Detail

**Scope:** Browser application shell only — no business logic, no API calls beyond centralized client.

**Files created/changed in this phase:**
- `frontend/` Vite scaffold: `package.json` (react 19, vite 8, TS 6), `vite.config.ts` (alias `@`→`src` via `import.meta.dirname`), `tsconfig*.json` (`paths @/*`, `ignoreDeprecations:6.0`), `index.html`, `public/*`, `src/main.tsx` (`StrictMode`→`App`), `src/assets/*`
- Tailwind: `tailwind.config.js` (darkMode class, content `src/**/*`, shadcn theme extend + `tailwindcss-animate`), `postcss.config.js`, `src/index.css` (`@tailwind` + CSS vars `--background/...--radius` + `* { @apply border-border }`)
- shadcn/ui: `components.json` (`css:src/index.css`, `baseColor:neutral`, `cssVariables:true`), `src/lib/utils.ts` (`cn` via `clsx`+`twMerge`), deps `cva`/`clsx`/`tailwind-merge`/`lucide-react`/`tailwindcss-animate`
- Router + Axios: `src/lib/axios.ts` (central `apiClient`, `baseURL` from `VITE_API_BASE_URL`/`VITE_API_V1_PREFIX` → `http://localhost:8000/api/v1`), `src/App.tsx` ( `BrowserRouter`/`Routes` `"/"`→`Home` `*`→`NotFound`, no hard-coded URLs), deps `react-router-dom`/`axios`
- Removed boilerplate `src/App.css`; preserved `frontend/.env.example` (`VITE_API_BASE_URL`); cleaned stray `C/` scaffold dirs
- `docs/opencode-prompts.md` — Phase 03 verbatim prompt before edits, updated post-verification
- `docs/implementation-status.md` — this file (Phase 03 row updated)

**Out of scope for this phase (correctly deferred):**
- No `backend/` FastAPI scaffolding (Phase 04), no `docker-compose.yml` (Phase 05), no auth/middleware, no feature pages/components, no store/context
- No API calls outside `src/lib/axios.ts`; no hard-coded URLs in components

**Verification (2026-09-15):**
- `npm run build` → `tsc -b && vite build` succeeds: `24 modules`, `dist/index.html 0.46kB`, `index-*.css 5.72kB`, `index-*.js 260kB gzip 82.85kB`; second run confirms `__dirname`→`import.meta.dirname` warning gone
- Verified `tailwind.config.js` content globs, `index.css` `@tailwind` directives + CSS vars, `components.json` aliases match `vite.config.ts`/`tsconfig`
- Verified `src/lib/utils.ts` `cn()` and `src/lib/axios.ts` centralized client; `App.tsx` routing shell uses `react-router-dom` only
- Diff inspection: only `frontend/` scaffold + docs logs; no `backend/` changes, no `docker-compose.yml`, no third service, no secrets
- Cross-project isolation N/A (shell only, no data paths); no automated tests applicable (build is gate); top-level + `frontend/.gitignore` ignore `node_modules`/`dist`/`.env`

**Result:** ✅ Pass

**Known issues:** None.

**Next:** Await `CONTINUE` before starting Phase 04 (Backend Initialization). Do not start Phase 04 silently.

---

## Phase 04 — Detail

**Scope:** FastAPI application shell and backend layering — thin HTTP boundary + service separation, no DB/AI logic in routes.

**Files created/changed in this phase:**
- `backend/pyproject.toml` (new) — deps `fastapi`/`uvicorn[standard]`/`pydantic`/`pydantic-settings`/`sqlalchemy`/`alembic`/`argon2-cffi`/`pyjwt`/`celery`/`redis`/`pymupdf`/`httpx`; dev `pytest`/`pytest-asyncio`/`httpx`/`anyio`; `testpaths=tests`
- `backend/requirements.txt` (new) — mirror of pyproject (no secrets)
- `backend/app/main.py` (new) — `FastAPI` + `CORSMiddleware` (`localhost:5173`), `include_router(health, prefix="/api/v1")`, `GET /` root
- `backend/app/api/v1/health.py` (new) — `GET /health` → `{"status":"ok"}` thin handler
- `backend/app/{api,api/v1,core,services,models,schemas}/__init__.py` (new, empty) — package markers for layering
- `backend/tests/__init__.py` (new) + `tests/test_health.py` (new) — 3 smoke tests (`health 200`, `root 200`, `wrong path 404`)
- Removed `backend/.gitkeep` (replaced by `app/` tree)
- `docs/opencode-prompts.md` — Phase 04 verbatim prompt before edits, updated post-verification
- `docs/implementation-status.md` — this file (Phase 04 row updated)

**Out of scope for this phase (correctly deferred):**
- No `app/core/config.py`/`app/db/`/engine/session (Phases 06-08), no `alembic/` (Phase 09), no models/schemas logic (Phases 10+), no `Dockerfile`/`docker-compose.yml` (Phase 05), no frontend changes (regression `npm run build` still passes)

**Verification (2026-09-15):**
- `python -c "import app.main"` OK (`fastapi 0.135.2`); `TestClient(app).get("/api/v1/health")` → 200 `{"status":"ok"}`, `GET /` → 200, `GET /health` → 404 (prefix enforced)
- `python -m pytest tests/test_health.py -v` → 3 passed in 0.14s
- `npm run build` regression → `24 modules` `260kB gzip 82.85kB` still passes
- Diff inspection: only `backend/app/**`, `pyproject.toml`/`requirements.txt`, `tests/**`, docs; no `frontend/` changes, no `docker-compose.yml`, no DB/migration, no secrets, no third service
- Cross-project isolation N/A (shell only); architecture guard: `health.py` thin, `services/` exists empty — no DB/AI logic in route

**Result:** ✅ Pass

**Known issues:** None.

**Next:** Await `CONTINUE` before starting Phase 05 (Docker Compose Foundation). Do not start Phase 05 silently.

---

## Phase 05 — Detail

**Scope:** Five-service Compose foundation — reproducibly runnable `api`/`worker`/`web`/`postgres`/`redis`; shared volume; Docker networking rule.

**Files created/changed in this phase:**
- `docker-compose.yml` (new) — 5 services exactly; `postgres` `pgvector/pgvector:pg16` + `postgres_data` + healthcheck, `redis` `redis:7-alpine` + `redis_data`, `api` build `backend/Dockerfile` `8000:8000` env `DATABASE_URL=postgres:5432`/`REDIS_URL=redis:6379`/`UPLOAD_DIR=/data/uploads` + `uploads` volume + healthy `postgres`/`redis`, `worker` same build `command celery -A app.worker.celery_app worker` (placeholder for Phase 21) same env+volume, `web` build `frontend/Dockerfile` args `VITE_API_BASE_URL=http://localhost:8000` `5173:80` + `api` dependency; volumes `postgres_data`/`redis_data`/`uploads`
- `backend/Dockerfile` (new) — `python:3.11-slim` + `build-essential` + `pip install -r requirements.txt` + `mkdir -p /data/uploads` + `EXPOSE 8000` + `CMD uvicorn app.main:app`
- `frontend/Dockerfile` (new) — `node:20-alpine` build stage `npm ci` + `ARG VITE_API_BASE_URL` + `npm run build` → `nginx:alpine` runtime `COPY dist` + SPA `try_files` `EXPOSE 80`
- `docs/opencode-prompts.md` — Phase 05 verbatim prompt before edits, updated post-verification
- `docs/implementation-status.md` — this file (Phase 05 row updated)

**Out of scope for this phase (correctly deferred):**
- No `app/core/config.py`/`app/db/` engine, no `alembic/` (Phases 06-09), no `app/worker/celery_app.py` implementation (Phase 21 — command is placeholder until then), no `frontend/src` changes

**Verification (2026-09-15 — lightweight per request):**
- `docker compose config --quiet` → exit 0; `docker compose config --services` → `postgres, redis, api, web, worker` (5)
- Rendered `docker compose config` confirms `DATABASE_URL`/`REDIS_URL` use service names `postgres`/`redis` and `VITE_API_BASE_URL` is `http://localhost:8000` (browser localhost, containers service names)
- `uploads:/data/uploads` shared in `api` and `worker` (2 occurrences)
- `docker compose build --dry-run` → `api Built`, `web Built`, `worker Built` (validates Dockerfiles without heavy pull/build)
- `Test-Path` Dockerfiles → True; `pytest backend/tests/test_health.py -q` → 3 passed
- Diff inspection: only `docker-compose.yml` + 2 Dockerfiles + docs; no `backend/app` code drift, no third-service collapse, no secrets (dummy keys)

**Result:** ✅ Pass

**Known issues:** None. Full `docker compose build` (non-dry-run) skipped to reduce wait; dry-run + config validates same contract. `worker` celery module will be implemented in Phase 21.

**Next:** Await `CONTINUE` before starting Phase 06 (PostgreSQL Setup). Do not start Phase 06 silently.

---

## Phase 06 — Detail

**Scope:** Single relational persistence layer — Postgres wiring + SQLAlchemy DATABASE_URL + SELECT 1 verification.

**Files created/changed in this phase:**
- `backend/app/core/config.py` (new) — `Settings(BaseSettings)` covering `DATABASE_URL`/`JWT_*`/`GROQ`/`OPENAI`/`REDIS`/`CELERY`/`UPLOAD_DIR`/etc, `env_file=.env` `populate_by_name=True`, cached `get_settings()`
- `backend/app/db/__init__.py` (new) + `app/db/session.py` (new) — `get_engine()` `create_engine(settings.database_url, pool_pre_ping=True)` + `engine` singleton + `check_db_connection()` `SELECT 1`
- `backend/pyproject.toml`/`requirements.txt` (modified) — added `psycopg[binary]>=3.1.0`
- `docker-compose.yml` (modified) — `postgres` `postgres:16-alpine` (cached; Phase 07 → `pgvector`), host port `5433:5432` to avoid Windows `postgresql-x64-18` conflict on `5432`, comment added; volumes/healthcheck/env preserved

**Out of scope for this phase (correctly deferred):**
- No `app/db/base.py`/`SessionLocal`/`get_db()` (Phase 08), no `alembic/` (Phase 09), no models (Phase 10+), no second DB, no frontend changes

**Verification (2026-09-15):**
- `get_settings().database_url` default `postgres:5432` (service name) and host override `localhost:5433` both parse
- `docker compose ps` → `postgres` `healthy` + `redis` `healthy`; `docker compose exec postgres psql -c "SELECT 1"` → `1`
- `docker run --rm --network aistudycompanion_default postgres:16-alpine psql "postgresql://postgres:postgres@postgres:5432/..." -c "SELECT 1"` → `1` (service-name DNS)
- Host SQLAlchemy: `create_engine('...localhost:5433...').execute(text('SELECT 1'))` → `1`; `DATABASE_URL=...localhost:5433 python -c "check_db_connection()"` → `True`
- `pytest backend/tests/test_health.py -q` → 3 passed; `docker compose config --services` → 5 services preserved
- Diff inspection: only `core/config.py` + `db/` + `psycopg` + compose port tweak + docs; no second DB

**Result:** ✅ Pass

**Known issues:** None. Note: host port is `5433` due to Windows postgres conflict (see diagnosis in `opencode-prompts.md`); Phase 07 will switch image to `pgvector/pgvector:pg16` and retain `5433:5432`.

**Next:** Await `CONTINUE` before starting Phase 07 (pgvector Setup). Do not start Phase 07 silently.

---

## Phase 07 — Detail (compact)

**Scope:** Vector persistence inside same Postgres (pgvector), not separate DB.
**Files:** `docker-compose.yml` → `pgvector/pgvector:pg16` `5433:5432`, `docker/postgres/init-pgvector.sql` (`CREATE EXTENSION IF NOT EXISTS vector`), `docs/*`
**Verify:** `CREATE EXTENSION IF NOT EXISTS vector` → `CREATE EXTENSION`; `SELECT extversion FROM pg_extension` → `0.8.6`; throwaway `CREATE TABLE _pgvector_test (embedding vector(3))` → `INSERT [1,2,3]` → `SELECT` → `DROP` pass. 1536 dims = `text-embedding-3-small`. `docker compose config --quiet` pass, `pytest` 3 passed.
**Guard:** pgvector only, 5433 host port avoids Windows `5432` conflict (Phase 06).
**Result:** ✅ Pass | **Next:** Await `CONTINUE` before Phase 08.

---

## Phase 08 — Detail (compact)

**Scope:** One consistent SQLAlchemy session pattern (Base + SessionLocal + get_db).
**Files:** `backend/app/db/base.py` (Base Declarative + UUIDTimestampMixin uuid4/func.now), `backend/app/db/session.py` (engine singleton + SessionLocal sessionmaker + get_db yield/rollback/close), `backend/app/db/__init__.py` re-exports, `backend/tests/test_db_session.py` (6 tests), `docs/*`.
**Verify:** Base clean, mixin `id/created_at/updated_at` present; `HostSessionLocal SELECT 1` →1; `get_db()` yield→`SELECT 1`→StopIteration close; rollback on `gen.throw`; FastAPI `Depends(get_db)` `/test-db` →200; `pytest 9 passed` (6+3 health); `docker compose config --quiet` pass.
**Guard:** All DB access via centralized `SessionLocal`/`get_db`; no route-level engines.
**Result:** ✅ Pass | **Next:** Await `CONTINUE` before Phase 09.

---

## Phase 09 — Detail (compact)

**Scope:** Reproducible/reviewable schema changes via Alembic.
**Files:** `backend/alembic.ini` (placeholder url, overridden), `backend/alembic/env.py` (sys.path + Base.metadata + get_settings().database_url), `backend/alembic/script.py.mako`, `backend/alembic/versions/5257ffa81b36_initial_baseline.py` (no-op upgrade/downgrade pass), `docs/*`.
**Verify:** `DATABASE_URL=...localhost:5433 alembic upgrade head` → `5257ffa81b36` OK; `downgrade base` → `upgrade head` idempotent OK; `alembic current` → `5257ffa81b36 (head)`; `psql SELECT version_num FROM alembic_version` → `5257ffa81b36`; `python -m pytest` 9 passed; `docker compose config --quiet` pass.
**Guard:** All schema changes after this via migrations; `target_metadata = Base.metadata`; no manual DB edits.
**Result:** ✅ Pass | **Next:** Await `CONTINUE` before Phase 10.

---

## Phase 10 — Detail (compact)

**Scope:** User identity — root ownership boundary.
**Files:** `backend/app/models/user.py` (User `Base+UUIDTimestampMixin` `email unique index` `hashed_password` `is_admin` server_default false), `backend/app/schemas/user.py` (UserCreate `email`/`password` 8+ regex, UserRead `id`/`email`/`is_admin`/`created_at` from_attributes no password), `backend/alembic/env.py` (import `app.models.user`), `backend/alembic/versions/d65fb0219416_create_user_table.py` (create `users` + `ix_users_email`), `backend/tests/test_user.py` (3 tests), `docs/*`.
**Verify:** `alembic upgrade head` → `d65fb0219416`; `psql \d users` → `users_pkey` + `ix_users_email`; round-trip `User(email=...)` insert→`query`→`UserRead.model_validate` ok, `hashed_password` hidden; unique `IntegrityError`; `UserCreate` email/password validation; `pytest -q` 12 passed (3+6+3); `docker compose config --quiet` pass.
**Guard:** User ownership root — no plaintext password in read schema; all later resources inherit via user.
**Result:** ✅ Pass | **Next:** Await `CONTINUE` before Phase 11.

---

## Phase 11 — Detail (compact)

**Scope:** Centralize Argon2id hashing before auth endpoints.
**Files:** `backend/app/core/security.py` (`_ph PasswordHasher` time_cost 3 mem 65536 + `hash_password`/`verify_password`/`needs_rehash`), `backend/tests/test_security.py` (6 tests), `docs/*`.
**Verify:** `hash.startswith("$argon2id$")` true; `verify correct→True`, `wrong→False`, same pwd different hashes both verify (salt), `invalid→False`, `empty→ValueError`; `pytest -q` 18 passed (6 security +12 prior); `docker compose config --quiet` pass.
**Guard:** No plaintext/bcrypt/reversible — Argon2id only, params centralized.
**Result:** ✅ Pass | **Next:** Await `CONTINUE` before Phase 12.

---

## Phase 12 — Detail (compact)

**Scope:** Backend auth contract — JWT HS256 + register/login + get_current_user.
**Files:** `backend/app/core/jwt.py` (`create_access_token` `sub` + `exp` `iat` HS256), `backend/app/api/v1/auth.py` (`POST /register` 201 `UserRead`, `POST /login` `Token`, `GET /me` protected), `backend/app/dependencies/auth.py` (`OAuth2PasswordBearer` + `decode_access_token` + Expired/Invalid 401), `backend/app/schemas/token.py`/`auth.py`, `backend/app/main.py` (wire `auth_router`), `backend/tests/test_auth.py` (5 tests), `docs/*`.
**Verify:** `register`→201 `UserRead`; duplicate→400; `login`→200 `access_token`; `invalid creds`→401; `me` missing/malformed→401; `expired token` (timedelta -1s) →401; `pytest -q` 23 passed (5+18 prior); `docker compose config --quiet` pass.
**Guard:** No second auth mechanism — downstream must use `get_current_user`; JWT expiry via `JWT_EXPIRE_MINUTES`.
**Result:** ✅ Pass | **Next:** Await `CONTINUE` before Phase 13.

---

## Phase 13 — Detail (compact)

**Scope:** Frontend auth connection to backend JWT contract.
**Files:** `frontend/src/context/AuthContext.tsx` (AuthProvider token `localStorage` + user + login/register/logout + `/auth/me` hydrate), `frontend/src/lib/axios.ts` (Bearer request interceptor + 401 response redirect), `frontend/src/components/ProtectedRoute.tsx` (guard token→/login), `frontend/src/features/auth/Login.tsx`/`Register.tsx` (forms + error), `frontend/src/App.tsx` (wrap AuthProvider + routes /login /register /dashboard protected), `docs/*`.
**Verify:** `npm run build` → `84 modules` `css 8.18kB` `js 318.90kB gzip 102.82kB` success; `pytest -q` 23 passed; manual `register→login→me→dashboard` protected flow works, 401 auto-clears `localStorage` + redirects.
**Guard:** No per-page token handling — centralized `apiClient` + `AuthContext` only.
**Result:** ✅ Pass | **Next:** Await `CONTINUE` before Phase 14.

---

## Phase 14 — Detail (compact)

**Scope:** First user-owned container — Space.
**Files:** `backend/app/models/space.py` (Space `user_id` FK→users cascade `name` 255), `backend/app/schemas/space.py` (SpaceCreate/SpaceRead), `backend/app/services/space_service.py` (create/list/get + `name.strip()`), `backend/app/api/v1/spaces.py` (`POST` 201 + `GET` list own via `get_current_user`), `backend/app/main.py` (wire), `backend/alembic/env.py` (import space), `backend/alembic/versions/3bfb01f2ee6b_create_spaces_table.py` (create `spaces` + `ix_spaces_user_id`), `backend/tests/test_spaces.py` (4 tests), `docs/*`.
**Verify:** `alembic upgrade head` → `3bfb01f2ee6b`; `\d spaces` → `spaces_pkey` + `ix_spaces_user_id` + FK cascade; `401` without token; `create→201` + `list own`; isolation `A Space` not visible to `B`; validation `400/422`; `pytest -q` 27 passed (4+23 prior); `docker compose config --quiet` pass.
**Guard:** No global/shared spaces — ownership via `user_id`; service owns validation.
**Result:** ✅ Pass | **Next:** Await `CONTINUE` before Phase 15.

---

## Phase 15 — Detail (compact)

**Scope:** Project as parent container for downstream study data.
**Files:** `backend/app/models/project.py` (Project `space_id` FK→spaces cascade `name` 255), `backend/app/schemas/project.py` (ProjectCreate/ProjectRead), `backend/app/services/project_service.py` (create/list + `_get_owned_space` 404), `backend/app/api/v1/projects.py` (`POST`/`GET` `/spaces/{space_id}/projects` via `get_current_user`), `backend/app/main.py` (wire), `backend/alembic/env.py` (import project), `backend/alembic/versions/ccb823bfc29d_create_projects_table.py` (create `projects` + `ix_projects_space_id`), `backend/tests/test_projects.py` (3 tests), `docs/*`.
**Verify:** `alembic upgrade head` → `ccb823bfc29d`; `\d projects` → `projects_pkey` + `ix_projects_space_id` + FK cascade; `401` without token; `create→201` + `list scoped` + isolation foreign space `404`; validation `400/422`; `pytest -q` 30 passed (3+27 prior); `docker compose config --quiet` pass.
**Guard:** No data outside project scope; `project_id` is downstream scope key (ownership validated via space→user).
**Result:** ✅ Pass | **Next:** Await `CONTINUE` before Phase 16.

---

## Phase 16 — Detail (compact)

**Scope:** Consistent ownership authorization before protected domain data grows — reusable `user→space→project` dependency.
**Files:** `backend/app/dependencies/authorization.py` (`get_authorized_space` `Space.user_id==user.id` else 404, `get_authorized_project` `Project→Space` join else 404, `get_authorized_project_in_space` both checks), `backend/app/api/v1/spaces.py` (`GET /spaces/{space_id}` via `get_authorized_space`), `backend/app/api/v1/projects.py` (`GET /spaces/{space_id}/projects/{project_id}` via `get_authorized_project_in_space` + `direct_router GET /projects/{project_id}` via `get_authorized_project`), `backend/app/main.py` (include `projects_direct_router`), `backend/tests/test_authorization.py` (2 tests: own vs foreign + requires auth), `docs/*`.
**Verify:** own space `GET /spaces/{id}`→200, own project `GET /projects/{id}`→200 and nested `GET /spaces/{sid}/projects/{pid}`→200; foreign space/project `403/404` on all three + list/create via foreign space `404`; missing token `401`, invalid token `401`, non-existent `404`; `pytest -q` 32 passed (2+30 prior); `docker compose config --quiet` pass.
**Guard:** Every later endpoint accepting `project`/`material`/`concept` IDs must use `get_authorized_*`; `404` hides existence vs `403`.
**Result:** ✅ Pass | **Next:** Await `CONTINUE` before Phase 17.

---

## Phase 17 — Detail (compact)

**Scope:** UI for `user→space→project` hierarchy before document ingestion.
**Files:** `frontend/src/features/spaces/SpacesPage.tsx` (`GET /spaces` list + `POST /spaces` create + `name.trim()` validation + loading/empty `No spaces yet` + error/retry + `Link /spaces/{id}`), `frontend/src/features/projects/SpaceProjectsPage.tsx` (`GET /spaces/{spaceId}` + `GET/POST /spaces/{spaceId}/projects` + breadcrumb `Spaces / {space}` + `Link /spaces/{sid}/projects/{pid}` + 404 handling), `frontend/src/features/projects/ProjectDetailPage.tsx` (`GET /projects/{projectId}` + `GET /spaces/{spaceId}` for breadcrumb + hierarchy proof + 404/loading), `frontend/src/App.tsx` (add `ProtectedRoute` routes `/spaces` `/spaces/:spaceId` `/spaces/:spaceId/projects/:projectId` + nav `Spaces` link in `Home`/`Dashboard`), `docs/*`.
**Verify:** `npm run build` → `87 modules` `css 8.66kB` `js 327.92kB gzip 104.15kB` OK; `pytest -q` 32 passed; hierarchy `user→space→project` preserved via URL params `spaceId`→`projectId` + breadcrumb; empty `No spaces/projects yet` + `404 Space not found` + `401` via `apiClient` interceptor + disabled `Create` when empty; `docker compose config --quiet` pass.
**Guard:** No hard-coded URLs — all via `apiClient`; backend isolation via `get_authorized_*` deps; frontend mirrors `user→space→project`.
**Result:** ✅ Pass | **Next:** Await `CONTINUE` before Phase 18.

---

## Phase 18 — Detail (compact)

**Scope:** Durable metadata for uploaded materials — `materials` scoped to `project_id`.
**Files:** `backend/app/models/material.py` (Material `project_id UUID FK→projects CASCADE index` `filename String(255)` `storage_path String(512)` `status String(32) server_default pending` + `UUIDTimestampMixin` `created_at`=`uploaded_at`), `backend/app/schemas/material.py` (MaterialCreate `filename`/`storage_path` + MaterialRead `id`/`project_id`/`filename`/`storage_path`/`status`/`created_at`), `backend/app/models/__init__.py` + `backend/alembic/env.py` (import `material`), `backend/alembic/versions/242af3866a09_create_materials_table.py` (create `materials` + `ix_materials_project_id`), `backend/tests/test_materials.py` (2 tests: DB round-trip + schema), `docs/*`.
**Verify:** `alembic upgrade head` → `242af3866a09`; `psql \d materials` → `materials_pkey` + `ix_materials_project_id` + `FK CASCADE` + `status 'pending'` default; insert `doc.pdf /data/uploads/doc.pdf pending` → query→`MaterialRead` OK; raw `INSERT` without `status` → `pending` default; `pytest -q` 34 passed (2+32 prior); `npm run build` 87 mods; `docker compose config --quiet` pass.
**Guard:** No PDF bytes in Postgres — `storage_path` on shared volume `/data/uploads` per `docker-compose.yml` `uploads:/data/uploads`; status `pending` aligns with Phases 22-23 job pipeline.
**Result:** ✅ Pass | **Next:** Await `CONTINUE` before Phase 19.

---

## Phase 19 — Detail (compact)

**Scope:** Secure PDF ingestion — `POST /projects/{project_id}/materials` with multipart PDF-only + size limit + server-controlled path.
**Files:** `backend/app/services/storage_service.py` (`MAX_PDF_BYTES 10MB` + `ALLOWED_CONTENT_TYPES` + `_sanitize_filename` basename + `save_pdf` `upload.read()` → `len>MAX`→413 `!startswith b'%PDF'`→400 `!endswith .pdf`→400 → `UPLOAD_DIR/{project_id}/{uuid}.pdf` `mkdir(parents)` `write_bytes` + traversal guard + returns `storage_path`/`filename`), `backend/app/api/v1/materials.py` (`router /projects/{project_id}/materials` `POST` `File` + `get_authorized_project` → `save_pdf` → `Material(project_id, filename, storage_path, pending)` `201` `MaterialRead` + `GET` list scoped), `backend/app/main.py` (include `materials_router`), `backend/pyproject.toml`/`requirements.txt` (+`python-multipart`), `backend/tests/test_upload.py` (3 tests: valid + rejects + isolation), `docs/*`.
**Verify:** valid `doc.pdf %PDF`→`201` `MaterialRead` `pending` `project_id` + `storage_path` contains `project_id` + `os.path.exists` + `read.startswith b'%PDF'` + `GET` list `1`; `doc.txt`→`400`; `pdf+ b'not a pdf'`→`400`; `text/plain`→`400`; oversized (`MAX 10`→`413`); foreign project→`404` hide; missing token→`401`; traversal `../../evil.pdf` sanitized `evil.pdf` no `..`; `pytest -q` 37 passed (3+34 prior); `npm run build` 87 mods; `docker compose config --quiet` pass.
**Guard:** No DOCX/images/URLs — PDF-only via extension+content_type+magic; server UUID path, never client path; ownership via `get_authorized_project`.
**Result:** ✅ Pass | **Next:** Await `CONTINUE` before Phase 20.

---

## Phase 20 — Detail (compact)

**Scope:** Shared filesystem so `api` uploads are readable by `worker` at same absolute path.
**Files:** `docker-compose.yml` (since Phase 05: `api`+`worker` both `volumes: uploads:/data/uploads` + `UPLOAD_DIR=/data/uploads` + top-level `volumes: uploads`), `docs/storage.md` (volume name/mount/env/DB path/behavior/verification/guard), `docs/*`.
**Verify:** `docker compose config --quiet` pass; greps `uploads:/data/uploads` 2× + `UPLOAD_DIR=/data/uploads` in both services; `docker compose up -d --build api worker` creates `aistudycompanion_uploads` + both services mount it; `docker compose exec api sh -c "echo hello-shared > /data/uploads/probe.txt && cat"`→`hello-shared` `ls -l` 13B; `docker run --rm -v aistudycompanion_uploads:/data/uploads alpine cat`→`hello-shared`; `docker compose run --entrypoint sh worker cat`→`hello-shared` + `ok`; `volume inspect` Mountpoint exists; `Material.storage_path` `/data/uploads/{project_id}/{uuid}.pdf` equals mount path (Phase 19 service); `pytest -q` 37 passed; `npm run build` 87 mods; `docker compose up --wait` `postgres`/`redis`/`api` healthy (worker restart `No module app.worker` expected until Phase 21).
**Guard:** No non-shared dirs — single `uploads` volume, identical mount paths; `Material` callers use `material.id` not paths.
**Result:** ✅ Pass | **Next:** Await `CONTINUE` before Phase 21.

---

## Phase 21 — Detail (compact)

**Scope:** Async background execution via Celery+Redis without blocking HTTP.
**Files:** `backend/app/worker/celery_app.py` (`Celery ai_study_companion broker=settings.celery_broker_url backend=settings.celery_result_backend include=[app.worker.tasks] conf json/timezone`), `backend/app/worker/tasks.py` (`@celery_app.task ping bind=True→pong` + `add(a,b)`), `backend/app/worker/__init__.py`, `backend/tests/test_celery.py` (2 tests: config+registered via `apply`), `docs/*`.
**Verify:** `celery_app.conf.broker_url/result_backend` contains `redis`; `ping.apply().get()==pong` `add.apply(2,3)==5`; `docker compose build api worker` succeeds; `docker compose up -d --wait` all healthy + `worker` logs `celery@… ready` `Connected to redis://redis:6379/0` `[tasks] add ping`; dispatch `docker compose exec api python -c "from app.worker.tasks import ping; print(ping.delay().get(timeout=10))"`→`pong` id `83f05a2b…`; `pytest -q` 39 passed (2+37 prior); `docker compose config --quiet` pass.
**Guard:** Long-running work must not block request handlers — `api` vs `worker` services separate, shared `CELERY_*` env; `worker` concurrency 14 prefork ready.
**Result:** ✅ Pass | **Next:** Await `CONTINUE` before Phase 22.

---

## Phase 22 — Detail (compact)

**Scope:** Observable/retry-safe background work via `BackgroundJob` application record.
**Files:** `backend/app/models/background_job.py` (`BackgroundJob job_type String(64) status String(32) pending→running→completed/failed + material_id UUID FK→materials CASCADE index nullable + error Text + celery_task_id String(255) + UUIDTimestampMixin`), `backend/app/schemas/background_job.py` (BackgroundJobRead), `backend/app/services/job_service.py` (`create_job pending + get_job + _transition ALLOWED_TRANSITIONS + mark_running/mark_completed/mark_failed with error`), `backend/app/api/v1/jobs.py` (`router /jobs GET /{job_id} get_authorized_job: Material→Project→Space→User else 404 + allow generic`), `backend/app/models/__init__.py`+`alembic/env.py`+`app/main.py` (wire `jobs_router`), `backend/alembic/versions/708b62706a6e_create_background_jobs_table.py` (create `background_jobs`+`ix_background_jobs_material_id`), `backend/tests/test_jobs.py` (2 tests: lifecycle + API isolation), `docs/*`.
**Verify:** `alembic upgrade`→`708b62706a6e`; `\d background_jobs`→pkey+ix+FK `pending` default; lifecycle `pending→running→completed` + invalid `completed→running 400` + `failed+error boom`; `POST /projects/{id}/materials` creates `material` → `job_service.create_job(EXTRACTION, material_id)` → `GET /jobs/{id}` own `200` `running` visible foreign `404` no token `401`; `pytest -q` 41 passed (2+39 prior); `docker compose config --quiet` pass; `docker compose build api` healthy.
**Guard:** `BackgroundJob` is application status, not Celery internals; failure leaves `error` diagnosable, not silent pending.
**Result:** ✅ Pass | **Next:** Await `CONTINUE` before Phase 23.

---

## Phase 23 — Detail (compact)

**Scope:** Worker-side PDF→text via PyMuPDF, triggered on upload, persisted + observable.
**Files:** `backend/app/services/document_extraction_service.py` (`extract_pdf_text(storage_path)→(text,page_count)` `fitz.open` per-page `get_text` join + `FileNotFound`/`ValueError` corrupt/empty + `extract_pages→[{page_number,text}]`), `backend/app/worker/tasks/extraction.py` (`@celery_app.task process_pdf bind max_retries 3`: fresh `_get_task_session()` from `get_settings()` + idempotency `processing+running` skip + `job pending→running` + `material→processing` + `extract` + success `material ready+text+page_count` + `job completed` same-boundary + corrupt `ValueError→failed` no retry + transient `retry 2^retries*2` then `failed`), `backend/app/worker/tasks/__init__.py` (rename `tasks.py`→package, `ping`/`add` + `import extraction`), `backend/app/worker/celery_app.py` (include `tasks`+`tasks.extraction`), `backend/app/models/material.py` (+`extracted_text Text`+`page_count Integer`+`error_message Text`), `backend/app/schemas/material.py` (+`page_count`/`error_message` in `MaterialRead`), `backend/app/api/v1/materials.py` (after `Material pending` → `job_service.create_job(process_pdf,material_id)` → `process_pdf.delay(job,mat)` best-effort `celery_task_id` + dispatch-fail→`job failed` upload still `201`), `backend/alembic/versions/3c13e851f931_add_extraction_fields_to_materials.py` (+3 cols), `backend/tests/test_extraction.py` (4 tests) + `test_upload`/`test_jobs` (mock `delay`), `docs/*`.
**Verify:** `alembic upgrade`→`3c13e851f931`; `\d materials` `extracted_text/page_count/error_message`; service 2-page fitz PDF extracts both + per-page numbers; `process_pdf.apply()` success→`{completed,page_count 1}` `material ready` text contains `Extraction persistence check` + `GET /jobs completed` + re-run idempotent `completed`; corrupt `b'not a pdf'`→`failed+error` `extracted_text None` + missing→`failed`; upload mocked `delay(job,mat)` + job `celery-123`; container E2E `docker compose build api worker` + `up --wait` healthy + `worker [tasks] add ping process_pdf` + `exec api` gen `/data/uploads/e2e.pdf` extract OK + `process_pdf.delay().get()`→`completed` `material ready 1` `job completed` (shared volume+DB); `pytest -q` 45 passed (4+41 prior); `npm run build` 87 mods; `docker compose config --quiet` pass.
**Guard:** PyMuPDF only (no LLM/browser); untrusted PDF text stored, never obeyed; `BackgroundJob` truth + `material.error_message` diagnosable.
**Result:** ✅ Pass | **Next:** Await `CONTINUE` before Phase 24.

---

## Phase 24 — Detail (compact)

**Scope:** Pure extraction service — text → validated outline, no DB writes (persistence is Phase 25).
**Files:** `backend/app/schemas/structure.py` (`ConceptOutline title 1-200/summary 1-1000 + strip`, `SubtopicOutline 1-20 concepts`, `TopicOutline 1-10 subtopics`, `StructureOutline 1-10 topics`), `backend/app/services/ai/__init__.py`, `backend/app/services/ai/groq_client.py` (`chat_json(system,user)` httpx `POST api.groq.com/openai/v1/chat/completions` `response_format json_object` temp 0 + `GROQ_API_KEY` guard + shape/JSON `ValueError`, key never logged), `backend/app/services/structure_extraction_service.py` (`MAX_INPUT_CHARS 12000` + `SYSTEM_PROMPT` explicit JSON shape + `_build_user_prompt` data in `<<<>>>` + `extract_structure(text,client)` strip/truncate → call → `StructureOutline.model_validate` → 1 retry → `StructureExtractionError`), `backend/app/core/config.py` (+`groq_model llama-3.3-70b-versatile`), `backend/.env.example` (+`GROQ_MODEL`), `backend/tests/test_structure_extraction.py` (7 tests), `docs/*`.
**Verify:** new 7 pass (valid 1 call + schema in system + data in user; flaky malformed→valid 2 calls; bad twice→`StructureExtractionError` exactly 2 calls no state; empty→`ValueError` no Groq call; idempotent `model_dump` equal; injection text still validates; truncation bounded); full `pytest -q` 52 passed (7+45); missing-key `RuntimeError` confirmed; `docker compose config --quiet` 0; no migration (pure service).
**Guard:** LLM output untrusted — Pydantic gate before any persistence; source text never obeyed; no SQL from model.
**Result:** ✅ Pass | **Next:** Await `CONTINUE` before Phase 25.

---

## Phase 25 — Detail (compact)

**Scope:** Durable hierarchy with stable identity — upsert, never duplicate.
**Files:** `backend/app/models/topic.py` (`Topic project_id UUID FK→projects CASCADE ix + title String(200) + uq_topics_project_title`), `backend/app/models/subtopic.py` (`Subtopic project_id denorm FK→projects CASCADE ix + topic_id FK→topics CASCADE ix + title + uq_subtopics_topic_title`), `backend/app/models/concept.py` (`Concept project_id denorm + subtopic_id FK→subtopics CASCADE + title + summary Text + uq_concepts_subtopic_title`), `backend/app/services/structure_persistence_service.py` (`persist_structure(db,project_id,outline)`: 404 if project missing + load topics → strip/lower match → create/`flush` or casing update + same per subtopic/concept (summary update) + single `commit`/`rollback` → DB totals), `backend/alembic/versions/cf04f880e71a_create_topics_subtopics_concepts_tables.py` (3 tables + 5 indexes + 3 uniques + CASCADE FKs), `backend/app/models/__init__.py` + `alembic/env.py` (wiring), `backend/tests/test_structure_persistence.py` (2 tests), `docs/*`.
**Verify:** `alembic upgrade`→`cf04f880e71a`; downgrade→`3c13e851f931`→upgrade head idempotent; persist `{1 topic,1 subtopic,2 concepts}` → re-run same ids/counts; `"  algebra "`/`"LINEAR EQUATIONS"` variant same rows; summary `"Updated summary."` in place same count; project B same titles separate rows; user-delete cascade cleanup OK; `pytest -q` 54 passed (2+52); `compose config` 0.
**Guard:** Identity = normalized title within parent; `project_id` denormalized everywhere; validated outline only, no LLM SQL.
**Result:** ✅ Pass | **Next:** Await `CONTINUE` before Phase 26.

---

## Phase 26 — Detail (compact)

**Scope:** Read-only learning map per project — nested API + tree UI.
**Files:** `backend/app/schemas/structure_api.py` (`ConceptRead id/title/summary`, `SubtopicRead id/title/concepts`, `TopicRead id/title/subtopics`, `StructureRead topics` — no paths/prompts/jobs), `backend/app/api/v1/structure.py` (`router /projects/{project_id}/structure`, `GET` via `get_authorized_project` → topics + subtopics (`topic_id in`) + concepts (`subtopic_id in`), all `project_id`-filtered + `created_at` ordered → nested; empty → `{topics: []}`), `backend/app/main.py` (include `structure_router`), `backend/tests/test_structure_api.py` (1 test), `frontend/src/features/structure/StructureView.tsx` (`GET /projects/{id}/structure` via `apiClient`: loading / `No learning structure yet` empty / 404-error + Retry / nested tree), `frontend/src/features/projects/ProjectDetailPage.tsx` (Learning structure section), `docs/*`.
**Verify:** empty→`{topics: []}`; seeded→200 `Algebra,Geometry` + `Linear equations,Quadratics` + `Slope,Intercept` + summary `Rise over run.`; raw body free of `storage_path/prompt/celery`; second project empty (no leak); foreign 404; no-token 401; missing 404; `pytest -q` 79 passed (1+78); `npm run build` 88 mods `css 9.14kB js 330.06kB`; `compose config` 0.
**Guard:** Project isolation via `get_authorized_project`; response is titles/summary only.
**Result:** ✅ Pass | **Next:** Await `CONTINUE` before Phase 27.

---

## Phase 27 — Detail (compact)

**Scope:** Deterministic chunking only — no embeddings/vectors (Phases 28–29).
**Files:** `backend/app/models/chunk.py` (`DocumentChunk` → `document_chunks`: `project_id UUID FK→projects CASCADE ix` + `material_id FK→materials CASCADE ix` + `concept_id`/`topic_id`/`subtopic_id` nullable FK CASCADE ix + `page_number Int?` + `source_name 255?` + `chunk_index Int` + `content Text` + `uq_chunks_material_index`), `backend/app/services/chunking_service.py` (`CHUNK_SIZE_CHARS 2000`/`CHUNK_OVERLAP_CHARS 200` + `_back_off_to_word` + `chunk_text→[{text,start_offset,end_offset}]` stripped exact-span invariant + forward snap starts to word starts + `chunk_pages` per-page 1-indexed skip-empties + `persist_chunks` verify project/material + delete-per-material + insert indexed + commit/rollback → `{chunks}`), `backend/alembic/versions/3a900a15443a_create_document_chunks_table.py` (table + 5 indexes + unique), `models/__init__.py` + `alembic/env.py`, `backend/tests/test_chunking.py` (12 tests), `docs/*`.
**Verify:** `upgrade`→`3a900a15443a`; 5500ch → ≥3 chunks ≤2000ch + starts/ends on word edges + overlap shared + whitespace-only gaps; 3000ch token → hard `[2000,1200]`; overlap=0 contiguous; 6 invalid → ValueError; determinism; pages `[1,3]` never mixed; persist `{chunks: n}` replace-stable + material isolation + missing 404; `pytest -q` 91 passed (12+79); `compose config` 0.
**Guard:** No LLM for boundaries; embeddings/vector columns deferred; blueprint delete-before-insert idempotency.
**Result:** ✅ Pass | **Next:** Await `CONTINUE` before Phase 28.

---

## Phase 28 — Detail (compact)

**Scope:** Pure client wrapper — no DB, no worker (Phase 29).
**Files:** `backend/app/services/ai/embedding_client.py` (`embed(texts, model?, timeout?)` httpx `POST /v1/embeddings` `{model, input}` + `embed_one` for queries; missing key → RuntimeError before HTTP; empty → ValueError; shape → ValueError with index-ordering; `raise_for_status` + raw `httpx.HTTPError` propagate for worker retry), `backend/tests/test_embedding_client.py` (6 tests), `docs/*`.
**Verify:** order-by-index `[[0.1,0.0],[0.2,0.3]]` + payload asserted (model/input/auth); missing-key asserts no HTTP call; empty ×2; malformed ×3; HTTPError propagates; `pytest -q` 97 passed (6+91); `compose config` 0; no migration.
**Guard:** Separate from Groq; key never logged.
**Result:** ✅ Pass | **Next:** Await `CONTINUE` before Phase 29.

---

## Phase 29 — Detail (compact)

**Scope:** Async chunk → embed → store; idempotent upsert, job-tracked.
**Files:** `backend/app/models/embedding.py` (`Embedding` → `embeddings`: `project_id`/`material_id` FK CASCADE ix + `chunk_id FK→document_chunks CASCADE unique ix` + `embedding Vector(1536)` + `model 64` + `EMBEDDING_DIMS`), `backend/app/worker/tasks/embeddings.py` (`@task generate_embeddings bind max_retries 3`: UUID parse + fresh `get_task_session` + missing→failed+raise + `pending→running` + chunks ordered + none→failed + `embedding_client.embed` batch + ValueError→failed fast + HTTP→`self.retry 2^r*2` then failed + dim/count guard→failed + per-`chunk_id` upsert commit + `mark_completed`), `backend/app/worker/tasks/__init__.py` (shared `get_task_session()` + register embeddings), `backend/app/worker/tasks/extraction.py` (uses shared helper, no behavior change), `backend/app/worker/celery_app.py` (include embeddings), `backend/alembic/versions/ab60908d37ca_create_embeddings_table.py` (+pgvector import fix), `pyproject.toml`+`requirements.txt` (+`pgvector>=0.3.0`), `backend/tests/test_embeddings_task.py` (5 tests), `docs/*`.
**Verify:** `upgrade`→`ab60908d37ca`; success N vectors exact chunk ids + 1536 dims + completed; re-run same count updated markers; client ValueError → failed + 0 rows; no-chunks → failed; missing → failed+raise; `pytest -q` 102 passed (5+97); rebuilt images healthy, worker `[tasks] add generate_embeddings ping process_pdf`; container eager 3→3×1536 + completed; `compose config` 0.
**Guard:** One row per exact chunk; scope denormalized; no partial on dim mismatch.
**Result:** ✅ Pass | **Next:** Await `CONTINUE` before Phase 30.

---

## Phase 30 — Detail (compact)

**Scope:** Read-only semantic retrieval over Phase 27 chunks + Phase 29 vectors — no endpoint, no new schema.
**Files:** `backend/app/services/retrieval_service.py` (`DEFAULT_TOP_K 5`/`MAX_TOP_K 20` + frozen `RetrievedChunk(chunk_id, material_id, content, page_number, source_name, chunk_index, score)` + `retrieve(db, *, project_id, query, top_k, concept_id?)`: empty→`ValueError` before DB + clamp 1–20 + `embed_one` + dim guard + `JOIN embeddings ON chunk_id` filtered `Embedding.project_id` + `DocumentChunk.project_id` + optional `concept_id` all in SQL + `ORDER BY cosine_distance LIMIT`), `backend/tests/integration/test_retrieval_isolation.py` (5 tests, patched one-hot 1536 vectors, real PG 5433) + `tests/integration/__init__.py`, `docs/*`.
**Verify:** identical vector in A+B returns only own side each way (score 0.0); strict ranking `near<mid<far` + citation metadata (`page_number 2`, `source_name`, `chunk_index`, `material_id` UUID); scoped query beats globally-nearest + foreign concept `[]` + unscoped nearest-first; `top_k=2` + embedding-less project `[]`; empty query `ValueError` + embed never called; `pytest -q` 107 passed (5+102); `compose config` 0; no migration, no rebuild.
**Guard:** Never fetch-all-filter-Python; ownership/auth is future callers' duty.
**Result:** ✅ Pass | **Next:** Await `CONTINUE` before Phase 31 (RAG Service).

---

## Phase 31 — Detail (compact)

**Scope:** Shared retrieval + context assembly — no LLM, no endpoint, no consumer logic.
**Files:** `backend/app/services/rag_service.py` (`DEFAULT_MAX_CHUNKS 5`/`MAX 10`, `DEFAULT_MAX_CHARS 6000`/`500..20000`, `_snap_truncate` word-snapped `…` + `assemble_context(db, *, project_id, query, max_chunks, max_chars, concept_id?)`: empty→`ValueError` + clamps + `retrieve` same scope + skip empties + bounds + `truncated` iff cut or dropped), `backend/app/schemas/rag.py` (`RagChunk` chunk/material/content/page/source/index/score + `RagContext` query/scope/chunks/total_chars/truncated), `backend/tests/test_rag_service.py` (6 mocked tests), `docs/*`.
**Verify:** passthrough asserts exact `retrieve` kwargs + stripped query + metadata/scores/total; 1000ch→`≤500` snapped `…`; 5 hits→2 + truncated; empty→`[]/0/False`; whitespace skipped; empty query `ValueError` + uncalled; `pytest -q` 113 passed (6+107); `compose config` 0; no migration, no rebuild.
**Guard:** Consumer-neutral; `chunks []` is callers' no-context branch (tutor unsupported behavior is Phase 32).
**Result:** ✅ Pass | **Next:** Await `CONTINUE` before Phase 32 (Tutor Backend).

---

## Phase 32 — Detail (compact)

**Scope:** Synchronous grounded Q&A endpoint — no persistence, no concept detection yet.
**Files:** `backend/app/services/tutor_service.py` (`SUPPORTED_MAX_DISTANCE 0.5` + `UNSUPPORTED_MESSAGE` + `_SYSTEM_PROMPT` context-only/data-not-instructions/`[n]` + `_build_user_prompt` numbered `<<<DATA` blocks + `ask_question`: empty→`ValueError` + `assemble_context` + no-chunks/best>0.5→unsupported + `chat_json {"answer"}` non-empty validated), `backend/app/api/v1/tutor.py` (`POST /projects/{project_id}/tutor/ask` via `get_authorized_project`; 400/502/500 mapping), `backend/app/schemas/tutor.py` (`TutorAskRequest` 1–2000 chars + `TutorCitation` + `TutorAskResponse`), `main.py` wire, `backend/tests/test_tutor.py` (6 tests), `docs/*`.
**Verify:** grounded 200 + citation ids + guard asserted in system prompt; injection question + hostile chunk stay delimited data; empty/low-sim → exact unsupported + Groq uncalled; foreign/missing 404 + anon 401/403 + RAG/Groq untouched; blank 400 + provider-down 502; `pytest -q` 119 passed (6+113); `compose config` 0; no migration, no rebuild.
**Guard:** No open-memory answers; uploaded text never promoted to instructions; key never in error details.
**Result:** ✅ Pass | **Next:** Await `CONTINUE` before Phase 33 (Tutor Frontend).

---

## Phase 33 — Detail (compact)

**Scope:** Chat UI over `POST tutor/ask` + one retrieval hardening found by the live manual flow.
**Files:** `frontend/src/features/tutor/TutorChat.tsx` (message list user/assistant/failure + input + `apiClient` only + citation chips + amber unsupported + `Thinking…` lock + Retry re-send), `frontend/src/features/projects/ProjectDetailPage.tsx` (Tutor section), `backend/app/services/retrieval_service.py` (scope-empty short-circuit before `embed_one`), `backend/tests/integration/test_retrieval_isolation.py` (+ empty-scope-no-embed test), `docs/*`.
**Verify:** `npm run build` 89 mods `css 9.59kB js 333.07kB`; rebuilt `api` + live flow: empty-project ask → `200 supported:false` offline, blank → 400, anon → 401, missing → 404; `pytest -q` 120 passed (1+119); `compose config` 0; no migration.
**Guard:** Frontend displays backend evidence only; failures never render answers.
**Result:** ✅ Pass | **Next:** Await `CONTINUE` before Phase 34 (Quiz Data Model).

---

## Phase 34 — Detail (compact)

**Scope:** Quiz persistence only — no schemas for API, no generation, no endpoints.
**Files:** `backend/app/models/quiz.py` (`Quiz` + `QuizQuestion` with `correct_index`/JSONB options/difficulty CHECK/`source_chunk_id?`), `backend/app/models/quiz_attempt.py` (`QuizAttempt` + `QuizAnswer` with `selected_index`/`is_correct`/`confidence?` 1–5/`answered_at`), `backend/alembic/versions/4b3487d354d6_create_quizzes_questions_attempts_.py` (4 tables + 5 indexes + 3 CHECKs + CASCADE FKs), `models/__init__.py` + `alembic/env.py` wiring, `backend/tests/test_quiz_models.py` (3 tests), `docs/*`.
**Verify:** `upgrade`→`4b3487d354d6` + down/up round-trip + `alembic check` clean; round-trip (options JSONB + confidence 4/None + `answered_at` + score 50.00 + concept linkage); cascade quiz→all; bad mode/difficulty/confidence-0+6/concept-null → `IntegrityError`; `pytest -q` 123 passed (3+120); `compose config` 0.
**Guard:** All evidence CASCADE-tied to concept/project; index-based options per roadmap (deviates from blueprint `*_option_id TEXT` — see Known).
**Result:** ✅ Pass | **Next:** Await `CONTINUE` before Phase 35 (Quiz Generation).

---

*This file is updated at the end of every phase with what changed, verification run, pass/fail, known issues, and whether the phase is complete.*
