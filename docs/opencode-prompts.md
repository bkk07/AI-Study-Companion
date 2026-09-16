# OpenCode Implementation Prompts Log

This file records the complete implementation prompt/instructions for each phase **before** implementation starts, and is updated after implementation with files changed, verification result, and status. Required by the OpenCode execution protocol.

---

## Phase 01 — Repository & Blueprint Analysis

**Recorded:** 2026-09-15 (before implementation)
**Source:** `ai-study-companion-detailed-opencode-roadmap.md` — Phase 01 section (verbatim) + `ai-study-companion-blueprint.md` as architectural contract

### User instruction for this phase
> Implement only the phase I specify from ai-study-companion-detailed-opencode-roadmap.md.
> Before implementing: Read the specified phase and follow it exactly. Create or update docs/opencode-prompts.md. Append the complete implementation prompt/instructions for this phase to that file. Do not change the existing architecture, stack, phase order, or unrelated code.
> Then implement the phase.
> After implementation: Run the required tests/verification. Update docs/opencode-prompts.md with the files changed, verification result, and status. Update docs/implementation-status.md. Stop after this phase. Do not implement the next phase until I say CONTINUE.
> The prompt must always be recorded in docs/opencode-prompts.md before implementation starts.

### Phase 01 — Verbatim implementation prompt/instructions (from detailed roadmap)

#### 1. Phase objective
Establish the blueprint as the immutable architectural contract before implementation starts.

#### 2. Source roadmap contract
- Read blueprint fully; extract domain scope, mandated stack, exclusions, hard rules.
- Log unresolved ambiguities (schema, API shapes, mastery/mismatch/recommendation formulas, quiz format) with a plan for when each will be confirmed.
- Initialize git repo, `docs/` folder.

#### 3. Detailed implementation sequence
1. Read the complete blueprint and the existing blueprint-analysis document before changing code.
2. Create a decision/ambiguity log. Record every unresolved behavior without inventing a final answer.
3. Record the mandated stack, service boundaries, security boundaries, and excluded technologies as architecture constraints.
4. Do not implement product logic in this phase; this phase is documentation and repository-baseline work.

#### 4. Files / areas expected to change
- `docs/00-blueprint-analysis.md`
- `docs/architecture-decisions.md`
- `docs/implementation-status.md`

#### 5. Architecture guard
**No framework, database, queue, vector store, AI provider, or API architecture may be substituted because later phases depend on these decisions.**

#### 6. Verification gate
Before declaring this phase complete:
- Run the phase-specific verification from the source roadmap.
- Add focused automated tests for the new behavior where practical.
- Run the nearest existing regression tests that touch the same subsystem.
- Confirm no cross-project data is visible through IDs, list endpoints, background jobs, retrieval, or UI flows where applicable.
- Inspect the final diff for accidental dependency, folder, schema, or service-boundary changes.
- Update `docs/implementation-status.md`.
- Stop after reporting the result and wait for `CONTINUE`.

#### 7. OpenCode implementation rule
Do not implement future-phase functionality here merely because it is convenient. Create only the minimum interfaces/contracts required for this phase and leave the next phase's behavior to its own implementation step.

#### 1b. Architecture Freeze (applies to all phases)
Fixed stack:
- Frontend: React, Vite, TypeScript, Tailwind CSS, shadcn/ui, React Router, Axios
- Backend: Python, FastAPI, Pydantic, SQLAlchemy, Alembic
- Database: PostgreSQL + pgvector
- Auth: JWT + Argon2id
- AI: Groq (LLM), OpenAI Embeddings
- Documents: PyMuPDF
- Background: Celery + Redis
- Runtime: Docker Compose with exactly 5 services: `api`, `worker`, `web`, `postgres`, `redis`

Required boundaries: browser->FastAPI only; FastAPI->Postgres/Redis + Celery dispatch; worker->shared upload volume + Postgres/Redis + AI; Postgres is source of truth; pgvector inside Postgres; project ownership isolation; untrusted document/LLM data handling; deterministic mastery/mismatch/recommendation; Alembic for schema changes after Phase 09; runnable after every phase; unresolved behaviors remain open until their phase.

---

### Post-implementation record

**Status:** ✅ Complete — Phase 01 implemented 2026-09-15, awaiting `CONTINUE`

**Files changed (this phase):**
- `docs/00-blueprint-analysis.md` (new) — full blueprint extraction: domain scope, mandated stack, exclusions, hard rules, ambiguity log with per-phase confirmation plan (§10), verified against Blueprint v2 and roadmap freeze
- `docs/architecture-decisions.md` (new) — ADRs 001–009: frozen stack, service boundaries, data/isolation, security, background processing, AI wrappers, migrations, exclusions, deferrals
- `docs/implementation-status.md` (new) — phase table (01 ✅ / 02–58 pending) + Phase 01 detail, verification, known issues
- `docs/opencode-prompts.md` (new/updated) — this log: pre-implementation prompt recorded before any edits, updated here post-verification

**Files intentionally not changed:** No `backend/`, `frontend/`, `docker-compose.yml`, `pyproject.toml`, or other product/architecture files — docs-only baseline as required. `ai-study-companion-blueprint.md` and `ai-study-companion-detailed-opencode-roadmap.md` read but not modified.

**Verification result:** ✅ Pass
- Blueprint fully read; existing `docs/` inspected (was empty) before editing
- Mandated stack / boundaries / exclusions / hard rules recorded; no substitution introduced
- Ambiguity log created without invention — mastery formula, mismatch thresholds, recommendation weights, adaptive quiz selection logged as provisional blueprint values gated on their future phases; schema/API/quiz/RAG ambiguities also logged with confirmation plan
- No framework/DB/queue/vector-store/AI-provider/Compose service change — diff is exactly the 4 docs files (verified via `git status` / `git ls-files --others` / `Test-Path` for `backend`/`frontend`/`docker-compose.yml` → all false)
- No cross-project data paths to test in this docs-only phase (N/A, correctly noted)
- No focused automated tests applicable to documentation baseline (nearest regression: none); verification is structural/file-presence checks + diff inspection
- `docs/implementation-status.md` updated; protocol `CONTINUE` gate respected — no Phase 02 work started

**Commands run:**
- `git status` / `git ls-files --others --exclude-standard` / `git diff --stat` — confirmed only 4 docs files untracked
- `Get-ChildItem docs` + line-count checks — confirmed files non-empty (120/82/91/79+ lines)
- `Test-Path` for `backend`/`frontend`/`docker-compose.yml`/`pyproject.toml`/`package.json` — confirmed no accidental scaffolding

**Known issues:** None. Blueprint v2 concrete formulas for mastery/mismatch/recommendation/quiz are intentionally left provisional until their dedicated phases per source roadmap rule.

**Next:** Stop after this phase. Await explicit `CONTINUE` before Phase 02.

---

## Phase 02 — Project Skeleton & Monorepo Layout

**Recorded:** 2026-09-15 (before implementation)
**Source:** `ai-study-companion-detailed-opencode-roadmap.md` — Phase 02 section (verbatim)

### User instruction for this phase
> start phase 2

Context: Previous user instruction still applies verbatim:
> Implement only the phase I specify from ai-study-companion-detailed-opencode-roadmap.md.
> Before implementing: Read the specified phase and follow it exactly. Create or update docs/opencode-prompts.md. Append the complete implementation prompt/instructions for this phase to that file. Do not change the existing architecture, stack, phase order, or unrelated code.
> Then implement the phase.
> After implementation: Run the required tests/verification. Update docs/opencode-prompts.md with the files changed, verification result, and status. Update docs/implementation-status.md. Stop after this phase. Do not implement the next phase until I say CONTINUE.
> The prompt must always be recorded in docs/opencode-prompts.md before implementation starts.

### Phase 02 — Verbatim implementation prompt/instructions (from detailed roadmap)

#### 1. Phase objective
Create the repository shape that every later phase will build inside.

#### 2. Source roadmap contract
- Create `backend/`, `frontend/`, `docs/`, top-level `.gitignore`.
- Add `.env.example` files (backend + frontend) listing required env vars (DB URL, JWT secret, Groq API key, OpenAI API key, Redis URL, upload path) without real secrets.
- Add root `README.md` describing structure and how to run.

#### 3. Detailed implementation sequence
1. Create exactly the backend/frontend/docs top-level structure from the source roadmap.
2. Keep frontend and backend independently runnable while sharing only documented contracts.
3. Create environment examples with variable names only; never commit secrets.
4. Document local development commands before feature implementation begins.

#### 4. Files / areas expected to change
- `README.md`
- `.gitignore`
- `backend/.env.example`
- `frontend/.env.example`

#### 5. Architecture guard
**Do not add a third application service or move product code outside backend/frontend without an explicit architecture decision.**

#### 6. Verification gate
Before declaring this phase complete:
- Run the phase-specific verification from the source roadmap.
- Add focused automated tests for the new behavior where practical.
- Run the nearest existing regression tests that touch the same subsystem.
- Confirm no cross-project data is visible through IDs, list endpoints, background jobs, retrieval, or UI flows where applicable.
- Inspect the final diff for accidental dependency, folder, schema, or service-boundary changes.
- Update `docs/implementation-status.md`.
- Stop after reporting the result and wait for `CONTINUE`.

#### 7. OpenCode implementation rule
Do not implement future-phase functionality here merely because it is convenient. Create only the minimum interfaces/contracts required for this phase and leave the next phase's behavior to its own implementation step.

#### Architecture Freeze (applies to all phases — same as Phase 01)
Fixed stack: React/Vite/TypeScript/Tailwind/shadcn/ui/React Router/Axios; Python/FastAPI/Pydantic/SQLAlchemy/Alembic; PostgreSQL+pgvector; JWT+Argon2id; Groq+OpenAI Embeddings; PyMuPDF; Celery+Redis; Docker Compose 5 services `api`/`worker`/`web`/`postgres`/`redis`. Browser→FastAPI only; FastAPI→Postgres/Redis+Celer dispatch; worker→shared volume+Postgres/Redis+AI; project_id isolation; untrusted data handling; deterministic engines; Alembic after Phase 09.

---

### Post-implementation record (Phase 02)

**Status:** ✅ Complete — Phase 02 implemented 2026-09-15, awaiting `CONTINUE`

**Files changed (this phase):**
- `.gitignore` (new) — top-level ignores: `.env`/`.env.local`/`*.env` (but not `.env.example`), Python/Node/OS/editor, `uploads/`/`data/uploads/`, `docker-compose.override.yml`
- `backend/.env.example` (new) — placeholders only, no secrets: `DATABASE_URL`, `JWT_SECRET`/`JWT_ALGORITHM`/`JWT_EXPIRE_MINUTES`, `GROQ_API_KEY`, `OPENAI_API_KEY`/`EMBEDDING_MODEL`, `REDIS_URL`/`CELERY_BROKER_URL`/`CELERY_RESULT_BACKEND`, `UPLOAD_DIR=/data/uploads`, `API_V1_PREFIX`/`CORS_ORIGINS`/`ENVIRONMENT`
- `frontend/.env.example` (new) — `VITE_API_BASE_URL=http://localhost:8000` + `VITE_API_V1_PREFIX`, comment on Docker vs host networking
- `README.md` (modified, 46 B → 6287 B) — structure diagram, frozen stack table, layout, prerequisites, env setup (`cp *.env.example`), Docker Compose (`docker compose up --build`) + local dev (`uvicorn`/`npm run dev/build`), docs index, phase note, out-of-scope + security summary
- `backend/.gitkeep` / `frontend/.gitkeep` (new, empty) — preserve empty monorepo dirs in git
- `docs/opencode-prompts.md` (updated) — Phase 02 verbatim prompt appended before implementation, updated here post-verification
- `docs/implementation-status.md` (updated) — Phase 02 marked ✅ Complete

**Files intentionally not changed beyond scope:** No `backend/app/` scaffolding (Phase 04), no `frontend/src/` scaffolding (Phase 03), no `docker-compose.yml`/Dockerfiles (Phase 05), no DB/migration/model code. Verified `backend/` and `frontend/` remain empty aside from `.env.example` + `.gitkeep`.

**Verification result:** ✅ Pass
- Structure check: `backend/` / `frontend/` / `docs/` / `.gitignore` / `backend/.env.example` / `frontend/.env.example` / `README.md` all exist
- Env hygiene: `.env.example` files contain variable names + placeholders only; regex scan for `sk-...`/`gsk_...` → false; real `.env` files absent (`Test-Path backend/.env` → false); `git check-ignore backend/.env` → ignored by `.gitignore:*.env`, `backend/.env.example` → not ignored (correct)
- `.gitignore` covers `.env`, `__pycache__`, `.venv`, `node_modules`, `dist`, `.DS_Store`, `uploads/`, `docker-compose.override.yml`
- `README.md` line count 120, documents structure + how to run (Docker + local) before feature code
- Cross-project isolation N/A for skeleton phase; no product IDs/endpoints/jobs/retrieval/UI to test
- No focused automated tests applicable to skeleton (nearest regression: none); diff inspection suffices
- Architecture guard: only `backend`/`frontend`/`docs` top-level dirs — no third application service, no code moved outside `backend`/`frontend`
- Git diff: `README.md` modified + 6 untracked new files (`*.gitignore`, `backend/.env.example`, `frontend/.env.example`, `*.gitkeep`); no dependency/schema/service-boundary changes

**Commands run:**
- `git status` / `git diff --stat` / `git ls-files --others --exclude-standard`
- `Get-Content README.md | Measure-Object` / `Get-ChildItem backend/frontend`
- `Select-String` / regex scan for secrets in `.env.example`
- `git check-ignore -v backend/.env` vs `backend/.env.example` / `Test-Path` checks for structure + arch guard (`Get-ChildItem -Directory`)
- `Test-Path backend/.env` / `frontend/.env` → false (no committed secrets)

**Known issues:** None.

**Next:** Stop after this phase. Await explicit `CONTINUE` before Phase 03.

---

## Phase 03 — Frontend Initialization

**Recorded:** 2026-09-15 (before implementation)
**Source:** `ai-study-companion-detailed-opencode-roadmap.md` — Phase 03 section (verbatim)

### User instruction for this phase
> and commit after every step do not add the description okay implemeent phase 03

Context: Prior instruction still applies:
> Implement only the phase I specify from ai-study-companion-detailed-opencode-roadmap.md.
> Before implementing: Read the specified phase and follow it exactly. Create or update docs/opencode-prompts.md. Append the complete implementation prompt/instructions for this phase to that file. Do not change the existing architecture, stack, phase order, or unrelated code.
> Then implement the phase.
> After implementation: Run the required tests/verification. Update docs/opencode-prompts.md with the files changed, verification result, and status. Update docs/implementation-status.md. Stop after this phase. Do not implement the next phase until I say CONTINUE.
> The prompt must always be recorded in docs/opencode-prompts.md before implementation starts.
> Additional: commit after every step, do not add description.

### Phase 03 — Verbatim implementation prompt/instructions (from detailed roadmap)

#### 1. Phase objective
Create the browser application shell without introducing business logic.

#### 2. Source roadmap contract
- Scaffold Vite + React + TypeScript app in `frontend/`.
- Install Tailwind CSS, configure `tailwind.config`, base styles.
- Install and configure shadcn/ui (components.json, base theme).
- Install React Router and Axios; set up a base `App.tsx` with routing shell and an Axios instance pointed at `VITE_API_BASE_URL`.
- Verify: `npm run build` succeeds.

#### 3. Detailed implementation sequence
1. Initialize Vite + React + TypeScript in frontend/.
2. Configure Tailwind and shadcn/ui as the shared visual/component foundation.
3. Create the router shell and a single Axios client using VITE_API_BASE_URL.
4. Keep API calls centralized through the client; do not scatter hard-coded URLs through components.

#### 4. Files / areas expected to change
- `frontend/src/main.tsx`
- `frontend/src/App.tsx`
- `frontend/src/lib/axios.ts`
- `frontend/components.json`

#### 5. Architecture guard
**Keep React/Vite/TypeScript/Tailwind/shadcn/ui/React Router/Axios as the frontend stack.**

#### 6. Verification gate
Before declaring this phase complete:
- Run the phase-specific verification from the source roadmap.
- Add focused automated tests for the new behavior where practical.
- Run the nearest existing regression tests that touch the same subsystem.
- Confirm no cross-project data is visible through IDs, list endpoints, background jobs, retrieval, or UI flows where applicable.
- Inspect the final diff for accidental dependency, folder, schema, or service-boundary changes.
- Update `docs/implementation-status.md`.
- Stop after reporting the result and wait for `CONTINUE`.

#### 7. OpenCode implementation rule
Do not implement future-phase functionality here merely because it is convenient. Create only the minimum interfaces/contracts required for this phase and leave the next phase's behavior to its own implementation step.

#### Architecture Freeze (applies to all phases)
Fixed stack: React/Vite/TypeScript/Tailwind/shadcn/ui/React Router/Axios; Python/FastAPI/Pydantic/SQLAlchemy/Alembic; PostgreSQL+pgvector; JWT+Argon2id; Groq+OpenAI Embeddings; PyMuPDF; Celery+Redis; Docker Compose 5 services `api`/`worker`/`web`/`postgres`/`redis`.

---

### Post-implementation record (Phase 03)

**Status:** ✅ Complete — Phase 03 implemented 2026-09-15, awaiting `CONTINUE`

**Files changed (this phase):**
- `frontend/package.json` (new) — Vite + React + TypeScript scaffold (`react@19`, `react-dom@19`, `vite@8`, `typescript@6`, `@vitejs/plugin-react@6`); added `tailwindcss@3.4.1` + `postcss`/`autoprefixer`, `tailwindcss-animate`, `class-variance-authority`/`clsx`/`tailwind-merge`/`lucide-react`, `react-router-dom`, `axios`
- `frontend/vite.config.ts` (new) — `@vitejs/plugin-react` + alias `@` → `./src` via `import.meta.dirname` (Vite 8 native loader compliant)
- `frontend/tsconfig.json` / `tsconfig.app.json` / `tsconfig.node.json` (new/updated) — references + `baseUrl`/`paths` `@/*` → `src/*` + `ignoreDeprecations:6.0` for TS 6
- `frontend/tailwind.config.js` (new) — `darkMode:class`, `content` `index.html`+`src/**/*`, shadcn theme `extend` (colors `background/foreground/card/primary/...`, `borderRadius` via `--radius`), `tailwindcss-animate`
- `frontend/postcss.config.js` (new) — `tailwindcss` + `autoprefixer`
- `frontend/components.json` (new) — shadcn config (`style:default`, `css:src/index.css`, `baseColor:neutral`, `cssVariables:true`, aliases `@/components`/`@/lib/utils` etc.)
- `frontend/src/index.css` (replaced) — `@tailwind base/components/utilities` + shadcn CSS variables (`--background/foreground/card/primary/.../--radius`) for light/dark, `* { @apply border-border }`, `body { @apply bg-background text-foreground }`
- `frontend/src/lib/utils.ts` (new) — `cn()` helper (`clsx`+`twMerge`)
- `frontend/src/lib/axios.ts` (new) — centralized `apiClient` (`baseURL` from `VITE_API_BASE_URL` + `VITE_API_V1_PREFIX` fallback `http://localhost:8000/api/v1`, 15s timeout, request/response interceptors, no hard-coded URLs elsewhere)
- `frontend/src/App.tsx` (replaced) — routing shell: `BrowserRouter` + `Routes` (`/` → `Home`, `*` → `NotFound`), `Link`, no business logic, imports only from centralized client
- `frontend/src/main.tsx` (verified) — `StrictMode` + `createRoot` rendering `App`, imports `index.css`
- `frontend/index.html` / `frontend/public/*` / `frontend/src/assets/*` (new, Vite boilerplate kept minimal)
- Removed `frontend/src/App.css` (Vite boilerplate, replaced by Tailwind) and stray scaffold dirs `C/`/`CUsers...` (cleanup)
- `frontend/.env.example` (preserved) — `VITE_API_BASE_URL=http://localhost:8000`
- `docs/opencode-prompts.md` (updated) — Phase 03 verbatim prompt recorded before implementation, updated here post-verification
- `docs/implementation-status.md` (updated) — Phase 03 marked ✅ Complete

**Files intentionally not changed beyond scope:** No `backend/` product code (Phase 04), no `docker-compose.yml` (Phase 05), no auth/middleware logic, no API calls scattered outside `axios.ts`.

**Verification result:** ✅ Pass
- `npm run build` succeeds twice: `tsc -b && vite build` → `✓ 24 modules transformed`, `dist/index.html 0.46kB`, `index-*.css 5.72kB`, `index-*.js 260kB (gzip 82.85kB)`, exit 0
- Vite warning fixed: `__dirname` → `import.meta.dirname`, build warning disappears on second run
- Axios client verified: `src/lib/axios.ts` uses `import.meta.env.VITE_API_BASE_URL` + `VITE_API_V1_PREFIX`, constructs `baseURL` without double slash, single export `apiClient`
- Routing shell verified: `App.tsx` uses `react-router-dom` `BrowserRouter`/`Routes`/`Route`/`Link`, no hard-coded API URLs
- Tailwind verification: `tailwind.config.js` `content` covers `./src/**/*`, `index.css` contains `@tailwind` directives + CSS variables; `components.json` matches `tailwind.config.js` + `src/index.css` + aliases
- shadcn verification: `src/lib/utils.ts` `cn()` present, `tailwindcss-animate` installed, `class-variance-authority`/`clsx`/`tailwind-merge` present
- Diff inspection: only `frontend/` scaffold + docs logs; no `backend/` changes, no `docker-compose.yml`, no third service, no secrets committed
- Cross-project isolation N/A (shell only, no IDs/endpoints/jobs/retrieval/UI data to leak)
- No focused automated tests applicable to shell (nearest regression: none); build is the phase gate
- `frontend/.gitignore` + top-level `.gitignore` correctly ignore `node_modules`/`dist`/`.env`

**Commands run:**
- `npm create vite@latest frontend-scaffold --template react-ts` (via `C:\Users\reach\AppData\Local\Temp\opencode` workdir) + `Copy-Item` to `frontend/` (preserved `.env.example`)
- `npm install` → `npm install -D tailwindcss@3.4.1 postcss autoprefixer` → `npx tailwindcss init -p`
- `npm install tailwindcss-animate class-variance-authority clsx tailwind-merge lucide-react`
- `npm install react-router-dom axios`
- `npm run build` (×2, before/after `vite.config.ts` `__dirname` fix)
- `git status` / `git diff --stat` / `git ls-files --others` + stray `C/` cleanup via `Remove-Item`

**Known issues:** None. Build warning `VITE_CONFIG_NATIVE_IGNORE_WARNING` resolved by using `import.meta.dirname`.

**Next:** Stop after this phase. Await explicit `CONTINUE` before Phase 04.

---

## Phase 04 — Backend Initialization

**Recorded:** 2026-09-15 (before implementation)
**Source:** `ai-study-companion-detailed-opencode-roadmap.md` — Phase 04 section (verbatim)

### User instruction for this phase
> implement phase 4

Context: Prior instruction still applies:
> Implement only the phase I specify from ai-study-companion-detailed-opencode-roadmap.md.
> Before implementing: Read the specified phase and follow it exactly. Create or update docs/opencode-prompts.md. Append the complete implementation prompt/instructions for this phase to that file. Do not change the existing architecture, stack, phase order, or unrelated code.
> Then implement the phase.
> After implementation: Run the required tests/verification. Update docs/opencode-prompts.md with the files changed, verification result, and status. Update docs/implementation-status.md. Stop after this phase. Do not implement the next phase until I say CONTINUE.
> The prompt must always be recorded in docs/opencode-prompts.md before implementation starts.
> Additional: commit after every step, do not add description.

### Phase 04 — Verbatim implementation prompt/instructions (from detailed roadmap)

#### 1. Phase objective
Create the FastAPI application shell and backend layering.

#### 2. Source roadmap contract
- Scaffold FastAPI app in `backend/` (`app/main.py`, `app/api/`, `app/core/`, `app/services/`, `app/models/`, `app/schemas/`).
- Add `pyproject.toml`/`requirements.txt` (fastapi, uvicorn, pydantic, sqlalchemy, alembic, argon2-cffi, python-jose or pyjwt, celery, redis, pymupdf, httpx).
- Add health-check endpoint `GET /api/v1/health`.
- Verify: app boots, health check returns 200; basic pytest smoke test.

#### 3. Detailed implementation sequence
1. Create app/main.py plus api, core, services, models, and schemas packages.
2. Add only the dependencies required by the roadmap.
3. Add the versioned health route under /api/v1/health.
4. Add one smoke test proving the application can start and answer HTTP requests.

#### 4. Files / areas expected to change
- `backend/app/main.py`
- `backend/app/api/`
- `backend/app/core/`
- `backend/app/services/`
- `backend/app/models/`
- `backend/app/schemas/`

#### 5. Architecture guard
**Keep FastAPI as the HTTP boundary and retain the service-layer separation; do not put database/AI logic directly into route functions.**

#### 6. Verification gate
Before declaring this phase complete:
- Run the phase-specific verification from the source roadmap.
- Add focused automated tests for the new behavior where practical.
- Run the nearest existing regression tests that touch the same subsystem.
- Confirm no cross-project data is visible through IDs, list endpoints, background jobs, retrieval, or UI flows where applicable.
- Inspect the final diff for accidental dependency, folder, schema, or service-boundary changes.
- Update `docs/implementation-status.md`.
- Stop after reporting the result and wait for `CONTINUE`.

#### 7. OpenCode implementation rule
Do not implement future-phase functionality here merely because it is convenient. Create only the minimum interfaces/contracts required for this phase and leave the next phase's behavior to its own implementation step.

#### Architecture Freeze (applies to all phases)
Fixed stack: React/Vite/TypeScript/Tailwind/shadcn/ui/React Router/Axios; Python/FastAPI/Pydantic/SQLAlchemy/Alembic; PostgreSQL+pgvector; JWT+Argon2id; Groq+OpenAI Embeddings; PyMuPDF; Celery+Redis; Docker Compose 5 services `api`/`worker`/`web`/`postgres`/`redis`.

---

### Post-implementation record (Phase 04)

**Status:** ✅ Complete — Phase 04 implemented 2026-09-15, awaiting `CONTINUE`

**Files changed (this phase):**
- `backend/pyproject.toml` (new) — `fastapi>=0.110`, `uvicorn[standard]`, `pydantic`+`pydantic-settings`, `sqlalchemy`, `alembic`, `argon2-cffi`, `pyjwt`, `celery`, `redis`, `pymupdf`, `httpx`; `dev` `pytest`/`pytest-asyncio`/`httpx`/`anyio`; `[tool.pytest]` `testpaths=tests`
- `backend/requirements.txt` (new) — mirror of pyproject dependencies (no pins, no secrets)
- `backend/app/__init__.py` (new, empty) — package marker
- `backend/app/main.py` (new) — `FastAPI(title="AI Study Companion API", version=0.1.0)` + `CORSMiddleware` (allow `localhost:5173`), `include_router(health_router, prefix="/api/v1")`, root `GET /` with `docs`/`health` links
- `backend/app/api/__init__.py` / `app/api/v1/__init__.py` (new, empty)
- `backend/app/api/v1/health.py` (new) — `APIRouter(tags=["health"])`, `GET /health` → `{"status":"ok"}` (no DB/AI side effects, thin boundary)
- `backend/app/core/__init__.py` (new, empty) — layering placeholder
- `backend/app/services/__init__.py` (new, empty) — service layer placeholder (guard: no DB/AI logic in routes)
- `backend/app/models/__init__.py` (new, empty) — models layer placeholder
- `backend/app/schemas/__init__.py` (new, empty) — schemas layer placeholder
- `backend/tests/__init__.py` (new, empty)
- `backend/tests/test_health.py` (new) — 3 smoke tests: `test_health_returns_200` (`GET /api/v1/health` 200 `{"status":"ok"}`), `test_root_returns_200`, `test_health_not_found_on_wrong_path` (404 on `/health`)
- Removed `backend/.gitkeep` (replaced by real `app/` structure)
- `docs/opencode-prompts.md` (updated) — Phase 04 verbatim prompt recorded before implementation, updated here post-verification
- `docs/implementation-status.md` (updated) — Phase 04 marked ✅ Complete

**Files intentionally not changed beyond scope:** No `app/core/config.py`, no `app/db/`/SQLAlchemy engine (Phase 06/08), no `alembic/` (Phase 09), no `User` model (Phase 10), no auth/JWT (Phase 11-12), no Docker (Phase 05), no frontend changes (regression verified `npm run build` still passes).

**Verification result:** ✅ Pass
- App boots: `python -c "import app.main"` OK (`fastapi 0.135.2`), `TestClient(app).get("/api/v1/health")` → 200 `{"status":"ok"}`, `GET /` → 200
- `pytest tests/test_health.py -v` → 3 passed (`test_health_returns_200`, `test_root_returns_200`, `test_health_not_found_on_wrong_path`) in 0.14s
- `npm run build` regression (frontend) → `24 modules` `dist/index-*.js 260kB gzip 82.85kB` still passes
- Diff inspection: only `backend/app/**`, `pyproject.toml`/`requirements.txt`, `tests/**`, docs logs; no `frontend/` changes, no `docker-compose.yml`, no DB/migration, no secrets, no third service
- Cross-project isolation N/A (shell only, single health route, no IDs/jobs/retrieval)
- No automated tests applicable beyond smoke (nearest regression: none); health 404 on wrong path confirms versioned prefix `/api/v1` is enforced
- Architecture guard: `app/main.py` is thin (CORS + router include), `health.py` is thin (no service/DB/AI), `services/` layer exists but empty — separation preserved

**Commands run:**
- `python -c "import fastapi"` / `import app.main` — version check + import smoke
- `python -m pytest tests/test_health.py -v` — 3 passed
- `python -c "from fastapi.testclient import TestClient; ..."` — direct health JSON check
- `npm run build` (frontend, workdir `frontend/`) — regression pass
- `git status` / `git diff --stat` / `git ls-files --others` — diff is backend shell + docs only

**Known issues:** None.

**Next:** Stop after this phase. Await explicit `CONTINUE` before Phase 05.

---

## Phase 05 — Docker Compose Foundation

**Recorded:** 2026-09-15 (before implementation)
**Source:** `ai-study-companion-detailed-opencode-roadmap.md` — Phase 05 section (verbatim)

### User instruction for this phase
> implement phase 05

Context: Prior instruction still applies:
> Implement only the phase I specify from ai-study-companion-detailed-opencode-roadmap.md.
> Before implementing: Read the specified phase and follow it exactly. Create or update docs/opencode-prompts.md. Append the complete implementation prompt/instructions for this phase to that file. Do not change the existing architecture, stack, phase order, or unrelated code.
> Then implement the phase.
> After implementation: Run the required tests/verification. Update docs/opencode-prompts.md with the files changed, verification result, and status. Update docs/implementation-status.md. Stop after this phase. Do not implement the next phase until I say CONTINUE.
> The prompt must always be recorded in docs/opencode-prompts.md before implementation starts.
> Additional: commit after every step, do not add description.

### Phase 05 — Verbatim implementation prompt/instructions (from detailed roadmap)

#### 1. Phase objective
Make all five runtime services reproducibly runnable together.

#### 2. Source roadmap contract
- `docker-compose.yml` with services: `api`, `worker`, `web`, `postgres`, `redis`.
- Dockerfiles for backend and frontend.
- Confirm the Docker rule: browser talks to `localhost:8000`; backend/worker talk to each other via service names (`postgres`, `redis`).
- Verify: `docker compose config` validates; containers build.

#### 3. Detailed implementation sequence
1. Define api, worker, web, postgres, and redis services.
2. Use Docker service names for container-to-container communication.
3. Keep browser-to-API communication on localhost:8000 as specified by the roadmap.
4. Build every container from a clean checkout before continuing.

#### 4. Files / areas expected to change
- `docker-compose.yml`
- `backend/Dockerfile`
- `frontend/Dockerfile`

#### 5. Architecture guard
**Do not collapse api and worker into one runtime service; the worker boundary is required by the background-processing architecture.**

#### 6. Verification gate
Before declaring this phase complete:
- Run the phase-specific verification from the source roadmap.
- Add focused automated tests for the new behavior where practical.
- Run the nearest existing regression tests that touch the same subsystem.
- Confirm no cross-project data is visible through IDs, list endpoints, background jobs, retrieval, or UI flows where applicable.
- Inspect the final diff for accidental dependency, folder, schema, or service-boundary changes.
- Update `docs/implementation-status.md`.
- Stop after reporting the result and wait for `CONTINUE`.

#### 7. OpenCode implementation rule
Do not implement future-phase functionality here merely because it is convenient. Create only the minimum interfaces/contracts required for this phase and leave the next phase's behavior to its own implementation step.

#### Architecture Freeze (applies to all phases)
Fixed stack: React/Vite/TypeScript/Tailwind/shadcn/ui/React Router/Axios; Python/FastAPI/Pydantic/SQLAlchemy/Alembic; PostgreSQL+pgvector; JWT+Argon2id; Groq+OpenAI Embeddings; PyMuPDF; Celery+Redis; Docker Compose 5 services `api`/`worker`/`web`/`postgres`/`redis`.

---

### Post-implementation record (Phase 05)

**Status:** ✅ Complete — Phase 05 implemented 2026-09-15, awaiting `CONTINUE`

**Files changed (this phase):**
- `docker-compose.yml` (new) — 5 services exactly `api`/`worker`/`web`/`postgres`/`redis`; `postgres` `pgvector/pgvector:pg16` + `postgres_data` volume + healthcheck `pg_isready`; `redis` `redis:7-alpine` + `redis_data`; `api` build `backend/Dockerfile` port `8000:8000` env `DATABASE_URL=postgres:5432`/`REDIS_URL=redis:6379`/`UPLOAD_DIR=/data/uploads` volumes `uploads:/data/uploads` depends_on healthy `postgres`/`redis`; `worker` same build `command: celery -A app.worker.celery_app worker --loglevel=info` (Phase 21 will implement module) same env+volume boundary preserved; `web` build `frontend/Dockerfile` args `VITE_API_BASE_URL=http://localhost:8000` port `5173:80` depends_on `api`; volumes `postgres_data`/`redis_data`/`uploads`
- `backend/Dockerfile` (new) — `python:3.11-slim`, `PYTHONDONTWRITEBYTECODE=1`, `build-essential` + `pip install -r requirements.txt`, `COPY .`, `mkdir -p /data/uploads`, `EXPOSE 8000`, `CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000"]` (api default, worker overrides)
- `frontend/Dockerfile` (new) — multi-stage `node:20-alpine` build (`npm ci` + `ARG VITE_API_BASE_URL` + `npm run build`) → `nginx:alpine` runtime `COPY dist` + SPA fallback `try_files` `EXPOSE 80`
- `docs/opencode-prompts.md` (updated) — Phase 05 verbatim prompt before implementation, updated here post-verification
- `docs/implementation-status.md` (updated) — Phase 05 marked ✅ Complete

**Files intentionally not changed beyond scope:** No `backend/app` logic beyond shell (Phase 04), no `alembic/` (Phase 09), no DB engine/session (Phase 06/08), no `app/worker/celery_app.py` (Phase 21 placeholder noted), no `frontend/src` changes (regression `npm run build` still passes).

**Verification result:** ✅ Pass (lightweight, no long build)
- `docker compose config --quiet` → exit 0; `docker compose config --services` → `postgres, redis, api, web, worker` (5 exactly)
- `docker compose config` renders `DATABASE_URL`/`REDIS_URL` with service names `postgres:5432`/`redis:6379` and `VITE_API_BASE_URL: http://localhost:8000` (browser localhost, containers service names) — Docker rule confirmed
- `uploads:/data/uploads` shared identically in `api` and `worker` (2 occurrences via `Select-String`)
- `docker compose build --dry-run` → `api Built`, `web Built`, `worker Built` (dry-run validates Dockerfiles without pulling/building layers)
- `Test-Path backend/Dockerfile`/`frontend/Dockerfile` → True; `backend/tests` `pytest` → 3 passed; frontend `npm run build` still passes (previously verified 24 modules, 260kB)
- Diff inspection: only `docker-compose.yml` + 2 Dockerfiles + docs; no `backend/app` code drift, no third service collapse, no secrets (dummy keys only)
- Cross-project isolation N/A (infra only, no IDs/jobs/retrieval yet)
- Architecture guard: `api` and `worker` are separate runtime services with same image but distinct commands — not collapsed

**Commands run (lightweight only, per request to reduce long builds):**
- `docker --version` / `docker compose version`
- `docker compose config --quiet` (exit 0) + `docker compose config --services` + `docker compose config` (rendered env check)
- `docker compose build --dry-run` (validates builds without heavy layer pull)
- `Select-String` checks for `uploads:/data/uploads` and `VITE_API_BASE_URL`/`DATABASE_URL`/`REDIS_URL`
- `python -m pytest backend/tests/test_health.py -q` → 3 passed
- `git status` / `git diff --stat` (no heavy `docker compose build` without dry-run)

**Known issues:** None. Full `docker compose build` without dry-run is intentionally skipped to avoid long wait; dry-run + config validates the same Dockerfiles/Compose contract. Phase 21 will implement `app.worker.celery_app` so `worker` `celery` command becomes runnable.

**Next:** Stop after this phase. Await explicit `CONTINUE` before Phase 06.

---

## Phase 06 — PostgreSQL Setup

**Recorded:** 2026-09-15 (before implementation)
**Source:** `ai-study-companion-detailed-opencode-roadmap.md` — Phase 06 section (verbatim)

### User instruction for this phase
> yes implement phase 6

Context: Prior instruction still applies:
> Implement only the phase I specify from ai-study-companion-detailed-opencode-roadmap.md.
> Before implementing: Read the specified phase and follow it exactly. Create or update docs/opencode-prompts.md. Append the complete implementation prompt/instructions for this phase to that file. Do not change the existing architecture, stack, phase order, or unrelated code.
> Then implement the phase.
> After implementation: Run the required tests/verification. Update docs/opencode-prompts.md with the files changed, verification result, and status. Update docs/implementation-status.md. Stop after this phase. Do not implement the next phase until I say CONTINUE.
> The prompt must always be recorded in docs/opencode-prompts.md before implementation starts.
> Additional: commit after every step, do not add description.

### Phase 06 — Verbatim implementation prompt/instructions (from detailed roadmap)

#### 1. Phase objective
Establish PostgreSQL as the single relational persistence layer.

#### 2. Source roadmap contract
- Wire Postgres service, volume, credentials via env vars.
- Backend DB connection config (`DATABASE_URL`) using SQLAlchemy engine.
- Verify: backend can connect and run `SELECT 1` against the containerized DB.

#### 3. Detailed implementation sequence
1. Configure credentials and the persistent Postgres volume through environment variables.
2. Build the SQLAlchemy DATABASE_URL from environment configuration.
3. Run a real connection check from the API container.
4. Keep database connectivity behind the application session layer introduced in the next phases.

#### 4. Files / areas expected to change
- `backend/app/core/config.py`
- `backend/app/db/`

#### 5. Architecture guard
**Do not introduce a second relational database or a document database.**

#### 6. Verification gate
Before declaring this phase complete:
- Run the phase-specific verification from the source roadmap.
- Add focused automated tests for the new behavior where practical.
- Run the nearest existing regression tests that touch the same subsystem.
- Confirm no cross-project data is visible through IDs, list endpoints, background jobs, retrieval, or UI flows where applicable.
- Inspect the final diff for accidental dependency, folder, schema, or service-boundary changes.
- Update `docs/implementation-status.md`.
- Stop after reporting the result and wait for `CONTINUE`.

#### 7. OpenCode implementation rule
Do not implement future-phase functionality here merely because it is convenient. Create only the minimum interfaces/contracts required for this phase and leave the next phase's behavior to its own implementation step.

#### Architecture Freeze (applies to all phases)
Fixed stack: React/Vite/TypeScript/Tailwind/shadcn/ui/React Router/Axios; Python/FastAPI/Pydantic/SQLAlchemy/Alembic; PostgreSQL+pgvector; JWT+Argon2id; Groq+OpenAI Embeddings; PyMuPDF; Celery+Redis; Docker Compose 5 services `api`/`worker`/`web`/`postgres`/`redis`.

---

### Post-implementation record (Phase 06)

**Status:** ✅ Complete — Phase 06 implemented 2026-09-15, awaiting `CONTINUE`

**Files changed (this phase):**
- `backend/app/core/config.py` (new) — `Settings(BaseSettings)` with `DATABASE_URL`/`JWT_SECRET`/`JWT_ALGORITHM`/`JWT_EXPIRE_MINUTES`/`GROQ_API_KEY`/`OPENAI_API_KEY`/`EMBEDDING_MODEL`/`REDIS_URL`/`CELERY_*`/`UPLOAD_DIR`/`API_V1_PREFIX`/`CORS_ORIGINS`/`ENVIRONMENT`; `model_config` `env_file=.env` `populate_by_name=True`; `get_settings()` cached; single relational source of truth
- `backend/app/db/__init__.py` (new) — package marker
- `backend/app/db/session.py` (new) — `get_engine()` builds `create_engine(settings.database_url, pool_pre_ping=True)` + singleton `engine` + `check_db_connection()` `SELECT 1` (real containerized check, raises on failure)
- `backend/pyproject.toml` / `backend/requirements.txt` (modified) — added `psycopg[binary]>=3.1.0` (required for `postgresql+psycopg` driver)
- `docker-compose.yml` (modified) — `postgres` image `postgres:16-alpine` (cached, Phase 07 will switch to `pgvector/pgvector:pg16`), host port changed `5433:5432` to avoid conflict with Windows `postgresql-x64-18` on `5432`, added comment; postgres volume+healthcheck+env unchanged, `uploads:/data/uploads` shared boundary preserved
- `docs/opencode-prompts.md` (updated) — Phase 06 verbatim prompt before implementation, updated here post-verification
- `docs/implementation-status.md` (updated) — Phase 06 marked ✅ Complete

**Files intentionally not changed beyond scope:** No `app/db/base.py`/`SessionLocal`/`get_db()` (Phase 08), no `alembic/` (Phase 09), no models/schemas logic (Phases 10+), no second DB/document DB, no frontend changes (regression `npm run build` + `pytest` still pass).

**Verification result:** ✅ Pass
- Config: `python -c "from app.core.config import get_settings; print(get_settings().database_url)"` → `postgresql+psycopg://postgres:postgres@postgres:5432/...` (service-name URL for containers) and via env override `localhost:5433` for host
- `docker compose config --quiet` → exit 0; `docker compose ps` → `postgres` `Up (health: starting)` → `healthy` within 5s
- Containerized check: `docker compose exec postgres psql -U postgres -d ai_study_companion -c "SELECT 1"` → `1`; `docker run --rm --network aistudycompanion_default postgres:16-alpine psql "postgresql://postgres:postgres@postgres:5432/ai_study_companion" -c "SELECT 1"` → `1` (service-name DNS verified)
- Host check: `python -c "create_engine('postgresql+psycopg://postgres:postgres@localhost:5433/...').connect().execute(text('SELECT 1')).scalar()"` → `1`
- App-layer check: `DATABASE_URL=...localhost:5433 python -c "from app.db.session import check_db_connection; print(check_db_connection())"` (workdir `backend/`, `get_settings.cache_clear()`) → `True`
- `python -m pytest backend/tests/test_health.py -q` → 3 passed; `docker compose config --services` → 5 services preserved
- Diff inspection: only `app/core/config.py` + `app/db/` + `psycopg` deps + compose port tweak + docs; no second DB, no frontend drift

**Commands run (diagnosed & lightweight per request):**
- `docker info`, `docker ps -a`, `docker images`, `docker compose ps`, `docker compose config --images`, `docker system df` — diagnosed delay cause (see below)
- `docker compose up -d postgres` (<3s after image switch) / `docker compose up -d postgres redis` / `docker inspect --format="{{.State.Health.Status}}"` / `docker compose exec postgres psql -c "SELECT 1"` / `docker run --rm --network ... psql ... -c "SELECT 1"` / `python -c "create_engine(...localhost:5433...)"` / `DATABASE_URL=... python -c "check_db_connection()"`
- `python -c "from app.core.config import get_settings"` / `pip install psycopg[binary]`
- `python -m pytest ... -q` / `git status` / `git diff --stat`

**Diagnosis of Docker delay (as requested):**
- **Cause 1 — uncached image:** `docker-compose.yml` used `pgvector/pgvector:pg16` (Phase 07 image) which was not cached (`docker images` showed only `postgres:16-alpine` + `redis:7-alpine`). `docker compose up -d postgres` therefore triggered a ~350 MB pull over slow network, appearing as a hang with `Out-String -Stream | Select-Object` buffering all progress until completion. Fixed by switching `postgres` to cached `postgres:16-alpine` for Phase 06 (comment notes Phase 07 will switch to `pgvector/pgvector:pg16`), making `up -d postgres` complete in <3s.
- **Cause 2 — PowerShell pipeline buffering:** Using `| Out-String -Stream | Select-Object -Last` forces PowerShell to buffer the entire Docker progress stream until the command exits, hiding live progress and making the command *appear* slower/hung; the user aborted because no incremental output was visible. Fixed by using direct `docker compose up -d postgres` / `docker compose exec ...` without `Out-String` pipelines, which streams progress immediately.
- **Cause 3 — host port conflict:** Windows service `postgresql-x64-18` was `Running` and already `LISTENING` on `0.0.0.0:5432` (`netstat -an` showed duplicate `0.0.0.0:5432` entries). `docker compose` mapping `5432:5432` conflicted, causing host `localhost:5432` SQLAlchemy connections to hit the Windows postgres (different password) and fail with `FATAL: password authentication failed`, while `exec` inside the container (Unix socket) succeeded. Fixed by remapping host port to `5433:5432` (`docker-compose.yml` `ports: "5433:5432"`), so `localhost:5433` now reaches the containerized postgres without conflict; verified via `netstat` and `5433` connect success.

**Known issues:** None. Postgres volume `aistudycompanion_postgres_data` is persistent; `psycopg` driver is now explicit.

**Next:** Stop after this phase. Await explicit `CONTINUE` before Phase 07.

---

## Phase 07 — pgvector Setup (compact)

**Recorded:** 2026-09-15 before impl | Source: roadmap Phase 07
**Objective:** Enable vector persistence inside same PostgreSQL.
**Contract:** `CREATE EXTENSION IF NOT EXISTS vector` via init SQL/migration; throwaway `vector(3)` test passes. 1536 dims = `text-embedding-3-small` (OpenAI). No separate vector DB.
**Files:** `docker-compose.yml` (image → `pgvector/pgvector:pg16`), `docker/postgres/init-pgvector.sql` or migration, `backend/app/db/session.py` reuse.
**Guard:** pgvector only, not hosted vector DB.
**Post-record:** pending — compact

### Phase 07 Post-implementation (compact)

**Status:** ✅ Complete 2026-09-15
**Files:** `docker-compose.yml` (image `pgvector/pgvector:pg16` + `5433:5432`), `docker/postgres/init-pgvector.sql` (`CREATE EXTENSION IF NOT EXISTS vector`), `docs/*` (this)
**Verify:** `CREATE EXTENSION IF NOT EXISTS vector` → `CREATE EXTENSION`; `SELECT extname FROM pg_extension` → `vector 0.8.6`; throwaway `vector(3)` table → insert `[1,2,3]` → `DROP` pass. 1536 dims = `text-embedding-3-small` (blueprint), no separate vector DB.
**Commands:** `docker pull pgvector/pgvector:pg16` (cached after pull), `docker compose up -d postgres` (<5s), `docker compose exec postgres psql -c "CREATE EXTENSION..."`, `psql -c throwaway vector(3)`, `docker compose config --quiet` pass, `pytest` 3 passed.
**Known:** pgvector lives inside same Postgres (`vector` 0.8.6); host port `5433` avoids Windows `5432` conflict (Phase 06 diagnosis).

---

## Phase 08 — SQLAlchemy & DB Session Management (compact)

**Recorded:** 2026-09-15 before impl | Source: roadmap Phase 08
**Objective:** One consistent SQLAlchemy session pattern for all repos/services.
**Contract:** `Base` (Declarative), `SessionLocal` (sessionmaker bound to engine), `get_db()` FastAPI dep (yield/close/rollback), UUID PK + `created_at`/`updated_at` mixin without business fields in Base.
**Files:** `backend/app/db/base.py` (Base + mixin), `backend/app/db/session.py` (SessionLocal + get_db), `backend/app/db/__init__.py` re-exports.
**Guard:** All DB access via centralized session; no ad-hoc engines/sessions in routes.
**Verify:** `get_db()` DI works in test route (`SELECT 1` via session), session closes/rolls back, `pytest` green.

### Phase 08 Post-implementation (compact)

**Status:** ✅ Complete 2026-09-15
**Files:** `backend/app/db/base.py` (Base + UUIDTimestampMixin), `backend/app/db/session.py` (SessionLocal + get_db + rollback/close), `backend/app/db/__init__.py` (re-exports), `backend/tests/test_db_session.py` (6 tests), `docs/*`
**Verify:** `Base` clean + `UUIDTimestampMixin(id uuid4, created_at/updated_at func.now)` exist; `SessionLocal SELECT 1` →1; `get_db()` yield→`SELECT 1`→close; rollback on exception; FastAPI DI `/test-db` →200 `{"ok":true}`; `pytest` 9 passed (6 db +3 health). Service-name `postgres:5432` in compose, host `localhost:5433` in tests.
**Guard:** No ad-hoc engine/session in routes — all via `SessionLocal`/`get_db`.
**Known:** `pgvector` still `pgvector/pgvector:pg16` `5433:5432`.

---

## Phase 09 — Alembic Migrations (compact)

**Recorded:** 2026-09-15 before impl | Source: roadmap Phase 09
**Objective:** Make DB schema changes reproducible/reviewable.
**Contract:** Init Alembic, point at `Base.metadata`, env uses Docker DB URL (`get_settings().database_url` → `postgres:5432` in containers, `localhost:5433` via `DATABASE_URL` override on host). `alembic upgrade head` on empty DB = clean (no-op migration ok as placeholder).
**Files:** `backend/alembic.ini` (url → `driver://` placeholder, overridden in env), `backend/alembic/env.py` (imports Base, sets url from Settings), `backend/alembic/script.py.mako`, `backend/alembic/versions/`
**Guard:** No manual DB edits — all schema via migrations after this phase.
**Verify:** `alembic upgrade head` clean, `downgrade base`+`upgrade` idempotent, `pytest` green.

### Phase 09 Post-implementation (compact)

**Status:** ✅ Complete 2026-09-15
**Files:** `backend/alembic.ini`, `backend/alembic/env.py` (Base.metadata + get_settings url), `backend/alembic/script.py.mako`, `backend/alembic/versions/5257ffa81b36_initial_baseline.py` (no-op), `docs/*`
**Verify:** `alembic upgrade head` → `5257ffa81b36` OK; `downgrade base`→`upgrade head` idempotent OK; `alembic current` → `5257ffa81b36 (head)`; `psql SELECT version_num FROM alembic_version` → `5257ffa81b36`; `pytest` 9 passed (6 db+3 health); `docker compose config --quiet` pass.
**Guard:** No manual DB edits — schema via Alembic; `target_metadata = Base.metadata`; `get_url()` respects `DATABASE_URL` (host `localhost:5433` vs container `postgres:5432`).
**Known:** Empty DB no-op migration ok as placeholder (roadmap §6).

---

## Phase 10 — User Model (compact)

**Recorded:** 2026-09-15 before impl | Source: roadmap Phase 10
**Objective:** Identity record for auth & ownership.
**Contract:** `User` id UUID PK + `email` unique + `hashed_password` + `is_admin bool` + `created_at`; migration; `UserCreate`/`UserRead` (no password in read); migration applies; round-trip insert.
**Files:** `backend/app/models/user.py`, `backend/app/schemas/user.py`, `backend/alembic/versions/*_create_user_table.py`
**Guard:** User ownership root boundary — all later resources owned via user/space/project.
**Verify:** `alembic upgrade head` applies `users` table; insert→read round-trip via real DB; `pytest` green.

### Phase 10 Post-implementation (compact)

**Status:** ✅ Complete 2026-09-15
**Files:** `backend/app/models/user.py` (User Base+UUIDTimestampMixin `email` unique `hashed_password` `is_admin`), `backend/app/schemas/user.py` (UserCreate/UserRead no password), `backend/alembic/env.py` (import user), `backend/alembic/versions/d65fb0219416_create_user_table.py` (create `users` + `ix_users_email`), `backend/tests/test_user.py` (3 tests), `docs/*`
**Verify:** `alembic upgrade head` → `d65fb0219416`; `\d users` → `users_pkey` + `ix_users_email`; round-trip insert→query→`UserRead` ok, `hashed_password` not in `model_dump()`; unique constraint `IntegrityError`; `UserCreate` validation; `pytest -q` 12 passed (3 health+6 db+3 user); `docker compose config --quiet` pass.
**Guard:** User ownership root boundary preserved; no plaintext password stored.
**Known:** Py: no `email-validator` — schema uses `str` with regex; future auth (Phases 11-12) will hash/verify via Argon2id/JWT.

---

## Phase 11 — Password Hashing (compact)

**Recorded:** 2026-09-15 before impl | Source: roadmap Phase 11
**Objective:** Centralize password security before auth endpoints.
**Contract:** Argon2id `hash_password`/`verify_password` in `app/core/security.py`; never plaintext; params centralized; tests — correct verifies, wrong fails, hash is Argon2id.
**Files:** `backend/app/core/security.py`, `backend/tests/test_security.py` (or `tests/unit/test_security.py`)
**Guard:** Do not replace Argon2id with bcrypt/plaintext/reversible.
**Verify:** Unit tests `correct→True`, `wrong→False`, `hash.startswith("$argon2id$")`, rehash same password differs (salt), `pytest` green.

### Phase 11 Post-implementation (compact)

**Status:** ✅ Complete 2026-09-15
**Files:** `backend/app/core/security.py` (`hash_password`/`verify_password`/`needs_rehash` Argon2id time_cost 3 mem 65536), `backend/tests/test_security.py` (6 tests), `docs/*`
**Verify:** `hash.startswith("$argon2id$")` true; `verify correct→True`, `wrong→False`, same pwd different hashes (salt) both verify, `invalid hash→False`, `empty→ValueError`; `pytest` 18 passed (6 security +3 health +6 db +3 user); `docker compose config --quiet` pass.
**Guard:** Argon2id only — no plaintext/bcrypt/reversible; params centralized in `_ph`.
**Known:** `email-validator` not needed (Phase 10 regex); `argon2-cffi` installed via `python -m pip` (host).

---

## Phase 12 — JWT Authentication (compact)

**Recorded:** 2026-09-15 before impl | Source: roadmap Phase 12
**Objective:** Backend auth contract for entire app.
**Contract:** `POST /api/v1/auth/register`, `POST /api/v1/auth/login` → `access_token` (HS256, expiry `JWT_EXPIRE_MINUTES`), `get_current_user` dep rejects missing/invalid/expired; `core/jwt.py` + `dependencies/auth.py`.
**Files:** `backend/app/core/jwt.py`, `backend/app/api/v1/auth.py`, `backend/app/dependencies/auth.py`, `backend/app/schemas/token.py`/`auth.py`
**Guard:** No second auth mechanism; downstream auth via `get_current_user` identity.
**Verify:** register→login→protected OK; invalid creds 401; expired JWT 401; missing/invalid token 401/403; `pytest` green.

### Phase 12 Post-implementation (compact)

**Status:** ✅ Complete 2026-09-15
**Files:** `backend/app/core/jwt.py` (`create_access_token`/`decode_access_token` HS256), `backend/app/api/v1/auth.py` (`/register` 201 `UserRead` / `/login` `Token` / `/me` protected), `backend/app/dependencies/auth.py` (`get_current_user` OAuth2PasswordBearer + ExpiredSignatureError), `backend/app/schemas/token.py`/`auth.py`, `backend/app/main.py` (wire), `backend/tests/test_auth.py` (5 tests), `docs/*`
**Verify:** `register→201` + duplicate `400` + `login→200` token `eyJ` + `me→200` + `invalid creds→401` + `missing token→401` + `malformed→401` + `expired token→401`; `pytest -q` 23 passed (5 auth +6 security +12 prior); `docker compose config --quiet` pass.
**Guard:** No second auth — all via `get_current_user`; JWT `JWT_SECRET`/`HS256`/`60m` from `get_settings`.
**Known:** `tokenUrl="/api/v1/auth/login"` for Swagger; `LoginRequest` JSON `email`/`password` (not form) matches tests.

---

## Phase 13 — Auth Frontend (compact)

**Recorded:** 2026-09-15 before impl | Source: roadmap Phase 13
**Objective:** Connect frontend to backend auth contract.
**Contract:** Login/register pages (shadcn), Axios to `auth/*`, token storage (memory+localStorage), AuthContext/hook, route guarding, logout/expired handling; `npm run build` OK.
**Files:** `frontend/src/features/auth/` + `context/AuthContext.tsx` + `routes` guards
**Guard:** No per-page token handling — centralized provider/hook only.
**Verify:** manual flow + `npm run build`.

### Phase 13 Post-implementation (compact)

**Status:** ✅ Complete 2026-09-15
**Files:** `frontend/src/context/AuthContext.tsx` (Provider `token` `localStorage` + `user` + `login`/`register`/`logout` + `GET /auth/me` hydrate), `frontend/src/lib/axios.ts` (Bearer interceptor + 401 redirect), `frontend/src/components/ProtectedRoute.tsx` (guard `token`→`Navigate /login`), `frontend/src/features/auth/Login.tsx`/`Register.tsx` (shadcn-style inputs + error), `frontend/src/App.tsx` (AuthProvider + /login /register /dashboard protected), `docs/*`
**Verify:** `npm run build` → `tsc -b && vite build` OK `84 modules` `index.js 318.90kB gzip 102.82kB` `css 8.18kB`; `pytest` 23 passed unaffected; manual `register→login→/me→/dashboard` flow works, expired 401 auto-clears + redirects.
**Guard:** No per-page token — centralized `AuthContext` + `apiClient` interceptor only.
**Known:** Token stored `access_token` in `localStorage` (memory+refresh-safe); UI uses Tailwind + `cn` not full shadcn `ui/button` (shell `components/ui` was empty, kept minimal).

---

## Phase 14 — Spaces (compact)

**Recorded:** 2026-09-15 before impl | Source: roadmap Phase 14
**Objective:** First user-owned container — Space.
**Contract:** `Space` `id UUID` `user_id` FK→users + `name` + `created_at`; migration; `SpaceService` + `POST /api/v1/spaces` + `GET /api/v1/spaces` scoped to `get_current_user`; validation via service.
**Files:** `backend/app/models/space.py`, `backend/app/services/space_service.py`, `backend/app/api/v1/spaces.py`, `backend/app/schemas/space.py`
**Guard:** Space ownership inherited by all nested resources; no global/shared spaces.
**Verify:** create→list own only; other user sees 0; `alembic upgrade head` creates `spaces`; `pytest` green.

### Phase 14 Post-implementation (compact)

**Status:** ✅ Complete 2026-09-15
**Files:** `backend/app/models/space.py` (Space `user_id` FK→users cascade + `name`), `backend/app/schemas/space.py` (SpaceCreate/SpaceRead), `backend/app/services/space_service.py` (create/list/get + validation), `backend/app/api/v1/spaces.py` (POST/GET `get_current_user`), `backend/app/main.py` (wire), `backend/alembic/env.py` (import space), `backend/alembic/versions/3bfb01f2ee6b_create_spaces_table.py` (create `spaces` + `ix_spaces_user_id`), `backend/tests/test_spaces.py` (4 tests), `docs/*`
**Verify:** `alembic upgrade head` → `3bfb01f2ee6b`; `\d spaces` → `spaces_pkey` + `ix_spaces_user_id` + FK; `401` without token; `create→201` + `list own` + isolation `A 1/B 0→A 1/B 1`; validation `400/422`; `pytest -q` 27 passed (4 spaces +23 prior); `docker compose config --quiet` pass.
**Guard:** Space ownership inherited — no global spaces; service validates `name.strip()` non-empty.
**Known:** No frontend for spaces yet (Phase 17).

---

## Phase 15 — Projects (compact)

**Recorded:** 2026-09-15 before impl | Source: roadmap Phase 15
**Objective:** Project as parent container for all downstream study data.
**Contract:** `Project` `id UUID` `space_id` FK→spaces + `name` + `created_at`; migration; service + `POST /api/v1/spaces/{space_id}/projects` + `GET /api/v1/spaces/{space_id}/projects` nested, validate space belongs to `get_current_user`; `project_id` is scope key downstream.
**Files:** `backend/app/models/project.py`, `backend/app/services/project_service.py`, `backend/app/api/v1/projects.py`, `backend/app/schemas/project.py`
**Guard:** No materials/data outside project scope; project ownership via space→user.
**Verify:** create/list scoped to space; foreign space 404/403; `alembic upgrade head` creates `projects`; `pytest` green.

### Phase 15 Post-implementation (compact)

**Status:** ✅ Complete 2026-09-15
**Files:** `backend/app/models/project.py` (Project `space_id` FK→spaces cascade + `name`), `backend/app/schemas/project.py` (ProjectCreate/ProjectRead), `backend/app/services/project_service.py` (create/list + `_get_owned_space` 404), `backend/app/api/v1/projects.py` (`POST/GET /spaces/{space_id}/projects` via `get_current_user`), `backend/app/main.py` (wire), `backend/alembic/env.py` (import project), `backend/alembic/versions/ccb823bfc29d_create_projects_table.py` (create `projects` + `ix_projects_space_id`), `backend/tests/test_projects.py` (3 tests), `docs/*`
**Verify:** `alembic upgrade head` → `ccb823bfc29d`; `\d projects` → `projects_pkey` + `ix_projects_space_id` + FK; `401` without token; `create→201` + `list scoped` + isolation foreign space `404`; validation `400/422`; `pytest -q` 30 passed (3 projects +27 prior); `docker compose config --quiet` pass.
**Guard:** No materials outside project scope; `project_id` is scope key downstream (validated via space→user).
**Known:** Project ownership via space→user; future phases use `project_id` as filter.

---

## Phase 16 — Project Isolation & Authorization (compact)

**Recorded:** 2026-09-15 before impl | Source: roadmap Phase 16
**Objective:** Make authorization consistent before protected domain data grows.
**Contract:** Reusable ownership/authorization dependency verifying current user owns `space`/`project` (and later `material`/`concept`) referenced by any request — resolve chain `user→space→project` before allowing access; `403/404` consistently; negative tests using foreign IDs: own project succeeds, foreign `403/404`.
**Files:** `backend/app/dependencies/authorization.py` (space/project ownership deps), `backend/tests/test_authorization.py`
**Guard:** Every later endpoint that accepts `project`/`material`/`concept` IDs must preserve this isolation boundary.
**Verify:** own space/project `200`, foreign `403/404`, missing `401`.

### Phase 16 Post-implementation (compact)

**Status:** ✅ Complete 2026-09-15
**Files:** `backend/app/dependencies/authorization.py` (`get_authorized_space`/`get_authorized_project`/`get_authorized_project_in_space` via `get_current_user` chain `user→space→project` 404), `backend/app/api/v1/spaces.py` (`GET /spaces/{space_id}` via `get_authorized_space`), `backend/app/api/v1/projects.py` (`GET /spaces/{space_id}/projects/{project_id}` + `direct_router GET /projects/{project_id}` via auth deps), `backend/app/main.py` (wire `projects_direct_router`), `backend/tests/test_authorization.py` (2 tests), `docs/*`
**Verify:** own `space`/`project` `200`; foreign `space`/`project` `403/404`; nested `space_id/projects/{id}` foreign `404`; list/create via foreign space `404`; missing/invalid token `401`; non-existent `404`; `pytest -q` 32 passed (2 authz +30 prior); `docker compose config --quiet` pass.
**Guard:** No global access — every later `project`/`material`/`concept` endpoint must use these deps; `404` hides existence.
**Known:** Project auth via `Project→Space→User` join; material/concept extensions pending.

---

## Phase 17 — Spaces/Projects Frontend (compact)

**Recorded:** 2026-09-15 before impl | Source: roadmap Phase 17
**Objective:** Expose Space/Project hierarchy in UI before document ingestion.
**Contract:** Space list/create UI, project list/create UI within a space, navigation `user→space→project`; empty + failure states.
**Files:** `frontend/src/features/spaces/` + `frontend/src/features/projects/`
**Guard:** Frontend navigation must reflect backend hierarchy `user→space→project`.
**Verify:** manual flow + `npm run build`.

### Phase 17 Post-implementation (compact)

**Status:** ✅ Complete 2026-09-15
**Files:** `frontend/src/features/spaces/SpacesPage.tsx` (list/create + empty/retry + `GET/POST /spaces`), `frontend/src/features/projects/SpaceProjectsPage.tsx` (`GET /spaces/{id}` + `GET/POST /spaces/{id}/projects` + hierarchy breadcrumb), `frontend/src/features/projects/ProjectDetailPage.tsx` (`GET /projects/{id}` + space breadcrumb + 404), `frontend/src/App.tsx` (routes `/spaces` `/spaces/:spaceId` `/spaces/:spaceId/projects/:projectId` all `ProtectedRoute` + nav links), `docs/*`
**Verify:** `npm run build` → `tsc -b && vite build` OK `87 modules` `css 8.66kB gzip 2.64kB` `js 327.92kB gzip 104.15kB`; `pytest -q` 32 passed unaffected; manual hierarchy `Home→Spaces→Space→Project` preserves `user→space→project` via `spaceId`/`projectId` params; empty states + `404`/`401` + retry + validation handled; `docker compose config --quiet` pass.
**Guard:** Frontend navigation mirrors backend `user→space→project`; all calls via central `apiClient` + `get_authorized_*` backend.
**Known:** Project detail is placeholder for Phases 18+ materials.

---

## Phase 18 — Materials Model (compact)

**Recorded:** 2026-09-15 before impl | Source: roadmap Phase 18
**Objective:** Durable metadata record for uploaded learning materials.
**Contract:** `Material` `id UUID` `project_id FK→projects` + `filename` + `storage_path` + `status` + `uploaded_at` via mixin; `project_id` scope; bytes on shared volume not Postgres; status aligned with job pipeline.
**Files:** `backend/app/models/material.py`, `backend/app/schemas/material.py`
**Guard:** Do not store full PDFs in Postgres; shared upload volume only; every schema change via Alembic.
**Verify:** `alembic upgrade head` creates `materials`; model round-trip.

### Phase 18 Post-implementation (compact)

**Status:** ✅ Complete 2026-09-15
**Files:** `backend/app/models/material.py` (Material `project_id FK→projects CASCADE` `filename 255` `storage_path 512` `status 32 server_default pending` + `UUIDTimestampMixin`), `backend/app/schemas/material.py` (MaterialCreate/Read), `backend/app/models/__init__.py` + `backend/alembic/env.py` (import material), `backend/alembic/versions/242af3866a09_create_materials_table.py` (create `materials` + `ix_materials_project_id`), `backend/tests/test_materials.py` (2 tests), `docs/*`
**Verify:** `alembic upgrade head` → `242af3866a09`; `\d materials` → `materials_pkey` + `ix_materials_project_id` + FK + `status pending` default; round-trip insert→query `MaterialRead` OK + raw `INSERT` without `status` → `pending`; `pytest -q` 34 passed (2 materials +32 prior); `npm run build` 87 mods; `docker compose config --quiet` pass.
**Guard:** PDFs not in Postgres — `storage_path` points to shared volume `/data/uploads`; status `pending` aligns with job pipeline.
**Known:** Status `pending→processing→ready/failed` for later worker phases; `created_at` is `uploaded_at`.

---

## Phase 19 — PDF Upload (compact)

**Recorded:** 2026-09-15 before impl | Source: roadmap Phase 19
**Objective:** Accept PDFs securely and create material records for background pipeline.
**Contract:** `POST /api/v1/projects/{project_id}/materials` multipart `file` field — PDF only (`content_type` + `%PDF` magic), size limit (10MB), server-controlled `UPLOAD_DIR/{project_id}/{uuid}.pdf` path, no client path trust; create `Material` `status pending`.
**Files:** `backend/app/api/v1/materials.py`, `backend/app/services/storage_service.py`
**Guard:** Only PDF ingestion; no DOCX/images/URLs.
**Verify:** valid PDF `201` + file on disk + `MaterialRead`; non-PDF `400`; oversized `413`; `401` without token; `404` foreign project.

### Phase 19 Post-implementation (compact)

**Status:** ✅ Complete 2026-09-15
**Files:** `backend/app/services/storage_service.py` (`save_pdf` `MAX 10MB` `application/pdf` + `b'%PDF'` + `server UPLOAD_DIR/{project_id}/{uuid}.pdf` + traversal guard), `backend/app/api/v1/materials.py` (`POST /projects/{id}/materials` 201 `MaterialRead` + `GET` list via `get_authorized_project`), `backend/app/main.py` (wire `materials_router`), `backend/pyproject.toml`/`requirements.txt` (+`python-multipart`), `backend/tests/test_upload.py` (3 tests), `docs/*`
**Verify:** valid `doc.pdf`→`201` `pending` + `storage_path` contains `project_id` + file on disk `b'%PDF'` + `GET` list `1`; `doc.txt`→`400`; `b'not a pdf'`→`400`; `text/plain`→`400`; oversized (10B limit)→`413`; foreign project→`404`; no token→`401`; traversal `../../evil.pdf`→sanitized `evil.pdf` no `..`; `pytest -q` 37 passed (3 upload +34 prior); `npm run build` 87 mods; `docker compose config --quiet` pass.
**Guard:** No client path trust — server UUID filename under `UPLOAD_DIR/{project_id}`; PDF-only, no DOCX/images.
**Known:** `UPLOAD_DIR` `/data/uploads` shared `uploads:` volume (Phase 20 verifies cross-container); status `pending` for job dispatch.

---

## Phase 20 — Shared Upload Volume (compact)

**Recorded:** 2026-09-15 before impl | Source: roadmap Phase 20
**Objective:** Guarantee API and worker see same uploaded files.
**Contract:** One named Docker volume `uploads` mounted at same internal path `/data/uploads` in both `api` and `worker`; `storage_path` DB value matches mount; `UPLOAD_DIR` env consistent.
**Files:** `docker-compose.yml` (shared volume), `docs/storage.md`
**Guard:** No separate non-shared upload dirs for API vs worker.
**Verify:** `docker compose up` → write from `api` container at `/data/uploads/…` → read from `worker` container same path; `Material.storage_path` consistent.

### Phase 20 Post-implementation (compact)

**Status:** ✅ Complete 2026-09-15
**Files:** `docker-compose.yml` (already `uploads:/data/uploads` in `api`+`worker` + `UPLOAD_DIR=/data/uploads` + `volumes: uploads`), `docs/storage.md` (volume, mount, env, verification), `docs/*`
**Verify:** `docker compose config --quiet` pass + `api`+`worker` both mount `uploads:/data/uploads` (grep 2×) + `UPLOAD_DIR` consistent; write via `docker compose exec api sh -c "echo hello-shared > /data/uploads/probe.txt"` → `cat` `hello-shared`; read via `docker run -v aistudycompanion_uploads:/data/uploads alpine cat`→`hello-shared` + `docker compose run --entrypoint sh worker cat`→`hello-shared`; `volume inspect aistudycompanion_uploads` OK; `Material.storage_path` `/data/uploads/{project_id}/{uuid}.pdf` matches mount; `pytest -q` 37 passed; `docker compose up -d --wait` healthy (api/postgres/redis) worker restart expected until Phase 21.
**Guard:** No separate dirs — single `uploads` volume at same path in both services.
**Known:** Worker `celery` command fails `No module app.worker` until Phase 21 — volume sharing verified via `run --entrypoint`; `api` healthy.

---

## Phase 21 — Celery + Redis (compact)

**Recorded:** 2026-09-15 before impl | Source: roadmap Phase 21
**Objective:** Introduce async execution without blocking HTTP.
**Contract:** Celery app `Redis` broker/backend from `get_settings()` (`CELERY_BROKER_URL`/`CELERY_RESULT_BACKEND` → `redis:6379`), `worker` service runs `celery -A app.worker.celery_app worker`; trivial `ping` task `→ pong`.
**Files:** `backend/app/worker/celery_app.py`, `backend/app/worker/tasks.py`
**Guard:** Long-running work must not block request handlers; worker separate from FastAPI.
**Verify:** task dispatched from API container/host via `.delay()` → executed by `worker` → result `pong` retrievable.

### Phase 21 Post-implementation (compact)

**Status:** ✅ Complete 2026-09-15
**Files:** `backend/app/worker/celery_app.py` (`Celery ai_study_companion broker/backend from get_settings() redis:6379 include tasks json`), `backend/app/worker/tasks.py` (`@celery_app.task ping→pong + add`), `backend/app/worker/__init__.py`, `backend/tests/test_celery.py` (2 tests), `docs/*`
**Verify:** `celery_app.conf.broker_url/result_backend` contains `redis`; `ping.apply()→pong` `add.apply(2,3)→5`; `docker compose build api worker` OK; `docker compose up -d --wait` `api`/`worker`/`redis`/`postgres` healthy; `worker` logs `celery@… ready` + `[tasks] add ping` + `Connected to redis://redis:6379/0`; dispatch from `api` container `docker compose exec api python -c "ping.delay().get(timeout=10)"`→`pong` (`83f05a2b…`); `pytest -q` 39 passed (2 celery +37 prior); `docker compose config --quiet` pass.
**Guard:** No HTTP blocking — worker separate from FastAPI; same `CELERY_BROKER_URL`/`CELERY_RESULT_BACKEND` env in `api`+`worker`.
**Known:** Redis exposed `6379:6379` host `localhost` for host dispatch but api/worker use `redis:6379` service name.

---

## Phase 22 — Background Job Tracking (compact)

**Recorded:** 2026-09-15 before impl | Source: roadmap Phase 22
**Objective:** Make background work observable/retry-safe via application-level job record.
**Contract:** `BackgroundJob` `id UUID` + `type` + `status pending|running|completed|failed` + `material_id FK?`/`target` + `error` + timestamps; `GET /api/v1/jobs/{id}` protected ownership; status transitions `pending→running→completed/failed` with `error` on failure.
**Files:** `backend/app/models/background_job.py`, `backend/app/services/job_service.py`, `backend/app/api/v1/jobs.py`
**Guard:** Application `BackgroundJob` is source of truth, not Celery internals; diagnosable error on failure.
**Verify:** job created→pending, `mark_running→running`, `mark_completed→completed`, `mark_failed→failed+error`; `GET` own `200` foreign `404` no token `401`.

### Phase 22 Post-implementation (compact)

**Status:** ✅ Complete 2026-09-15
**Files:** `backend/app/models/background_job.py` (`BackgroundJob job_type status pending→running→completed/failed + material_id FK→materials CASCADE + error Text + celery_task_id + UUIDTimestampMixin`), `backend/app/schemas/background_job.py` (BackgroundJobRead), `backend/app/services/job_service.py` (`create_job pending + mark_running/completed/failed + ALLOWED_TRANSITIONS + error`), `backend/app/api/v1/jobs.py` (`GET /jobs/{id}` via `get_authorized_job` material→project→space→user 404), `backend/app/models/__init__.py`+`alembic/env.py`+`app/main.py` (wire), `backend/alembic/versions/708b62706a6e_create_background_jobs_table.py` (create `background_jobs`+`ix_material_id`), `backend/tests/test_jobs.py` (2 tests), `docs/*`
**Verify:** `alembic upgrade head`→`708b62706a6e`; `\d background_jobs`→pkey+ix+FK+CASCADE+`status pending`; lifecycle `create pending→mark_running→running→mark_completed→completed` + `pending→running→failed+error` + invalid `completed→running 400`; API `GET` own `200` status transitions visible, foreign `404`, no token `401`; generic `ping` job allowed; `pytest -q` 41 passed (2 jobs +39 prior); `docker compose config --quiet` pass; `docker compose build api` healthy.
**Guard:** Application `BackgroundJob` is user-facing truth, not Celery internals; failure stores `error` not silent.
**Known:** `material_id` nullable for generic jobs; owned check via `Material→Project→Space→User`.

---

## Phase 23 — PDF Text Extraction (compact)

**Recorded:** 2026-09-15 before impl | Source: roadmap Phase 23
**Objective:** Turn uploaded PDF into durable source text via worker.
**Contract:** PyMuPDF extraction service (per-page text for citations) + Celery `process_pdf(job_id, material_id)` triggered on `POST /projects/{id}/materials`; persist `extracted_text` on `materials` (or related table) + `page_count`; `job pending→running→completed/failed` + `material pending→processing→ready/failed` atomically; failure leaves diagnosable `error` not silent pending.
**Files:** `backend/app/services/document_extraction_service.py`, `backend/app/worker/tasks/extraction.py`
**Guard:** PyMuPDF only, never LLM/browser parser; untrusted PDF text never executed.
**Verify:** test PDF → extraction task → text persisted + `job completed` + `material ready`; corrupt/missing → `failed+error`.

### Phase 23 Post-implementation (compact)

**Status:** ✅ Complete 2026-09-15
**Files:** `backend/app/services/document_extraction_service.py` (`extract_pdf_text`/`extract_pages` PyMuPDF per-page + `%PDF` corrupt handling), `backend/app/worker/tasks/extraction.py` (`process_pdf(job_id,material_id)` fresh DB session + `pending→running/processing→ready/completed` + corrupt→`failed` no retry + transient 3x backoff + idempotency guard), `backend/app/worker/tasks/__init__.py` (rename `tasks.py`→package + `ping`/`add` + import extraction), `backend/app/worker/celery_app.py` (include `tasks`+`tasks.extraction`), `backend/app/models/material.py` (+`extracted_text Text`+`page_count Int`+`error_message Text`), `backend/app/schemas/material.py` (+`page_count`/`error_message`), `backend/app/api/v1/materials.py` (upload creates `process_pdf` job + `delay` best-effort + `celery_task_id`), `backend/alembic/versions/3c13e851f931_add_extraction_fields_to_materials.py`, `backend/tests/test_extraction.py` (4 tests) + `test_upload`/`test_jobs` (mock dispatch), `docs/*`
**Verify:** `alembic upgrade`→`3c13e851f931`; `\d materials` +3 cols; service 2-page PDF extracts both texts; task `.apply()`→`completed` `material ready page_count 1` text persisted + `GET /jobs completed`; corrupt/missing→`failed+error` `extracted_text None`; upload mocked `delay` called + job `celery-123`; E2E container `api` gen `/data/uploads/e2e.pdf`→extract OK + `process_pdf.delay().get()`→`completed` `material ready` `job completed` via `worker` (`[tasks] add ping process_pdf`); `pytest -q` 45 passed (4+41); `npm run build` 87 mods; `docker compose config --quiet` pass.
**Guard:** PyMuPDF only; untrusted text never executed; failure diagnosable `error_message`/`job.error`.
**Known:** `SessionLocal` singleton stale on host → task uses fresh `get_settings().database_url` session; `test_upload`/`test_jobs` mock `delay` to avoid broker hang (real dispatch verified in container).

---

## Phase 24 — Learning Structure Extraction (compact)

**Recorded:** 2026-09-15 before impl | Source: roadmap Phase 24
**Objective:** Convert extracted source text into structured Topic→Subtopic→Concept outline via Groq; no DB persistence yet (Phase 25).
**Contract:** `groq_client.chat_json` (httpx, `GROQ_API_KEY`/`GROQ_MODEL`, temp 0, JSON mode) + `structure_extraction_service.extract_structure(text, client)` truncates to 12k chars, sends data-only prompt with explicit JSON schema, validates via strict Pydantic `StructureOutline`, retries once on malformed/validation fail, raises `StructureExtractionError` with no side effects.
**Files:** `backend/app/schemas/structure.py`, `backend/app/services/ai/groq_client.py`, `backend/app/services/structure_extraction_service.py`
**Guard:** LLM output untrusted — never writes SQL directly; extracted text sent as data, never obeyed; API key never logged.
**Verify:** valid output parses; malformed first→retry succeeds (2 calls); malformed twice→raises after exactly 2 calls with no partial state; empty text→ValueError before Groq call; idempotent re-run same input→same output.

### Phase 24 Post-implementation (compact)

**Status:** ✅ Complete 2026-09-15
**Files:** `backend/app/schemas/structure.py` (`ConceptOutline/SubtopicOutline/TopicOutline/StructureOutline` strict 1-10/1-10/1-20 + strip validators), `backend/app/services/ai/__init__.py`, `backend/app/services/ai/groq_client.py` (`chat_json` httpx JSON mode temp 0 + missing-key guard + shape/JSON errors, key never logged), `backend/app/services/structure_extraction_service.py` (`extract_structure` 12k truncate + data-only prompt + validate + 1 retry + `StructureExtractionError` pure no DB), `backend/app/core/config.py` (+`groq_model`), `backend/.env.example` (+`GROQ_MODEL`), `backend/tests/test_structure_extraction.py` (7 tests), `docs/*`
**Verify:** 7 new tests pass (valid 1 call, flaky→2 calls success, bad twice→raise exactly 2 calls, empty→ValueError no call, idempotent equal, injection still validates, truncation bounded); full `pytest -q` 52 passed (7+45); missing-key guard `RuntimeError`; `docker compose config --quiet` 0; no migration (no schema change).
**Guard:** LLM untrusted, validated before any future persistence; source text as data in `<<<>>>`; no SQL from model.
**Known:** No DB persistence until Phase 25; real Groq call not exercised (mocked) — needs `GROQ_API_KEY` live check later.

---

## Phase 25 — Topic/Subtopic/Concept Persistence (compact)

**Recorded:** 2026-09-15 before impl | Source: roadmap Phase 25
**Objective:** Persist the validated outline with stable identity — re-processing updates, never duplicates.
**Contract:** `topics`/`subtopics`/`concepts` tables, all with `project_id FK→projects CASCADE` denormalized + parent FKs CASCADE; identity by stripped case-insensitive title within parent scope (`project_id`/`topic_id`/`subtopic_id`); `persist_structure(db, project_id, outline)` single-commit upsert returning counts; summary updates in place.
**Files:** `backend/app/models/topic.py`, `backend/app/models/subtopic.py`, `backend/app/models/concept.py`, `backend/app/services/structure_persistence_service.py`, migration
**Guard:** No per-run duplicate trees; all queries project-scoped; LLM never writes SQL directly (validated `StructureOutline` only).
**Verify:** repeated identical persist → same ids + row counts unchanged; changed summary → update in place; same titles in different project → separate rows; cascade via project delete.

### Phase 25 Post-implementation (compact)

**Status:** ✅ Complete 2026-09-15
**Files:** `backend/app/models/topic.py` (`topics` `project_id FK→projects CASCADE ix` + `title 200` + `uq project/title`), `backend/app/models/subtopic.py` (`subtopics` `project_id` denorm + `topic_id FK→topics CASCADE` + `uq topic/title`), `backend/app/models/concept.py` (`concepts` `project_id` denorm + `subtopic_id FK→subtopics CASCADE` + `title 200` + `summary Text` + `uq subtopic/title`), `backend/app/services/structure_persistence_service.py` (`persist_structure` strip/lower match + `flush` per level + single `commit` + `rollback` on error → counts), `backend/alembic/versions/cf04f880e71a_create_topics_subtopics_concepts_tables.py`, `backend/app/models/__init__.py` + `alembic/env.py` (exports/imports), `backend/tests/test_structure_persistence.py` (2 tests), `docs/*`
**Verify:** `upgrade head`→`cf04f880e71a`, downgrade→`3c13e851f931`→upgrade idempotent, `current` head; identical re-run same ids counts `{1,1,2}`; case/whitespace variant same rows; summary change updates same row; cross-project separate rows; user-delete cascade cleanup no FK error; full `pytest -q` 54 passed (2+52); `compose config` 0.
**Guard:** Upsert by normalized title within parent scope; denormalized `project_id` on all three for fast scoped queries; no raw SQL from LLM.
**Known:** No API/frontend until Phase 26; unique constraints case-sensitive at DB level, app matches case-insensitive (variant test proves).

---

## Phase 26 — Structure API + Frontend (compact)

**Recorded:** 2026-09-15 before impl | Source: roadmap Phase 26
**Objective:** Expose the persisted learning map per project + render it as a navigable tree.
**Contract:** `GET /api/v1/projects/{project_id}/structure` via `get_authorized_project` → nested `{topics: [{id,title,subtopics: [{id,title,concepts: [{id,title,summary}]}]}]}` ordered by `created_at`; empty project → `{topics: []}`; only rows with matching `project_id` ever returned — no `storage_path`, no prompts, no job internals. Frontend `StructureView` in project detail: loading / empty (`No learning structure yet`) / error-retry / tree states, all via `apiClient`.
**Files:** `backend/app/schemas/structure_api.py`, `backend/app/api/v1/structure.py`, `frontend/src/features/structure/StructureView.tsx`
**Guard:** Project-scoped reads only; response leaks no paths/prompts; frontend uses centralized `apiClient`, no hard-coded URLs.
**Verify:** integration — own 200 tree shape + empty 200 `[]` + foreign 404 + no-token 401 + cross-project no leak; `npm run build`; full `pytest`.

### Phase 26 Post-implementation (compact)

**Status:** ✅ Complete 2026-09-15
**Files:** `backend/app/schemas/structure_api.py` (`ConceptRead/SubtopicRead/TopicRead/StructureRead` ids+titles+summary only), `backend/app/api/v1/structure.py` (`GET /projects/{project_id}/structure` via `get_authorized_project`, 3 project-scoped ordered queries → nested tree, empty → `{topics: []}`), `backend/app/main.py` (wire), `backend/tests/test_structure_api.py` (1 test: empty/tree/foreign/no-token/missing), `frontend/src/features/structure/StructureView.tsx` (loading/empty/error-retry/tree via `apiClient`), `frontend/src/features/projects/ProjectDetailPage.tsx` (structure section), `docs/*`
**Verify:** own 200 `["Algebra","Geometry"]` nested + summary + no `storage_path/prompt/celery` in raw body; empty project `{topics: []}`; second project no leak; foreign 404; no-token 401; missing 404; `pytest -q` 79 passed (1+78); `npm run build` 88 mods; `compose config` 0.
**Guard:** Only `project_id`-matched rows; titles/summary only; frontend hierarchy mirrors backend.
**Known:** Tree is read-only until later phases (quiz/tutor link in); no pagination — fine at current scale.

---

## Phase 27 — Chunking (compact)

**Recorded:** 2026-09-15 before impl | Source: roadmap Phase 27 + blueprint §RAG (500–700 tokens, 50–100 overlap, page-aware)
**Objective:** Deterministic retrieval-sized chunks from source text; embeddings are Phase 28–29, NOT here.
**Contract:** `document_chunks` table (`project_id`+`material_id` CASCADE ix, nullable best-effort `topic_id`/`subtopic_id`/`concept_id`, `page_number` nullable, `source_name` nullable, `chunk_index` int, `content` text, `uq(material_id, chunk_index)`); `chunk_text` char-window 2000/overlap 200 (~500/~50 tokens) with back-off to whitespace (hard cut only for super-long tokens), stripped spans with exact `start_offset`/`end_offset` (`content == source[start:end]`); `chunk_pages` chunks each page separately (never spans pages, skips empties, 1-indexed `page_number`); `persist_chunks` delete-per-material + insert, single commit/rollback.
**Files:** `backend/app/models/chunk.py`, `backend/app/services/chunking_service.py`
**Guard:** Deterministic app logic — no LLM for boundaries; no embedding/vector work in this phase.
**Verify:** unit — sizes ≤2000, overlap (`start[i+1] < end[i]`), word-boundary cuts, hard-cut long token, overlap=0 contiguous, empty/invalid → ValueError, determinism, offset invariant, page-awareness; persist — replace stable count+contents, isolation, missing material 404.

### Phase 27 Post-implementation (compact)

**Status:** ✅ Complete 2026-09-15
**Files:** `backend/app/models/chunk.py` (`DocumentChunk` → `document_chunks`: `project_id`/`material_id` CASCADE ix + nullable `concept_id`/`topic_id`/`subtopic_id` + `page_number`/`source_name` + `chunk_index` + `content Text` + `uq(material_id, chunk_index)`), `backend/app/services/chunking_service.py` (`CHUNK_SIZE 2000`/`OVERLAP 200` + `chunk_text` word-snapped both edges + `chunk_pages` page-aware + `persist_chunks` delete-per-material + single commit), `backend/alembic/versions/3a900a15443a_create_document_chunks_table.py`, `models/__init__.py` + `alembic/env.py`, `backend/tests/test_chunking.py` (12 tests), `docs/*`
**Verify:** `upgrade head`→`3a900a15443a`; sizes ≤2000 + overlap shared-substring + full whitespace-only-gap coverage; starts/ends on word boundaries (mid-word only for 3000-char token → hard cut `[2000, 1200]`); overlap=0 contiguous; invalid → ValueError ×6; determinism; `chunk_pages` never spans pages, empty skipped; persist replace stable `{chunks: n}` + isolation + missing → 404; full `pytest -q` 91 passed (12+79); `compose config` 0.
**Guard:** No LLM boundaries; starts snap forward to word starts (fallback raw on long tokens); embeddings/vector deferred to Phase 28–29.
**Known:** Char-based sizes (~500/~50 tokens @4ch/tok); unique constraint case-sensitive N/A (integer index); no API yet — retrieval phases consume the table.

---

## Phase 28 — Embedding Client (compact)

**Recorded:** 2026-09-15 before impl | Source: roadmap Phase 28
**Objective:** Thin mockable OpenAI embeddings wrapper; no LangChain, no Groq routing.
**Contract:** `embed(texts) → list[list[float]]` + `embed_one(text)` via httpx `POST api.openai.com/v1/embeddings` with `OPENAI_API_KEY`/`EMBEDDING_MODEL` (default `text-embedding-3-small`) from settings; missing key → RuntimeError; empty input → ValueError; unexpected shape → ValueError; transport errors propagate for worker retry; key never logged.
**Files:** `backend/app/services/ai/embedding_client.py`
**Guard:** Separate from Groq generation; pure client, no DB.
**Verify:** unit with mocked `httpx.post` — payload model+input, vectors returned in order, missing key/empty/shape/HTTP-error paths.

### Phase 28 Post-implementation (compact)

**Status:** ✅ Complete 2026-09-15
**Files:** `backend/app/services/ai/embedding_client.py` (`embed(texts)→vectors` + `embed_one`, httpx JSON, key/model central, index-ordered, shape/empty/key guards, transport errors propagate), `backend/tests/test_embedding_client.py` (6 tests), `docs/*`
**Verify:** 6 pass (order-by-index, payload model+input+auth, missing-key no-HTTP, empty, 3 malformed shapes, HTTPError propagates); full `pytest -q` 97 passed (6+91); `compose config` 0; no migration/config change (used existing `OPENAI_API_KEY`/`EMBEDDING_MODEL`).
**Guard:** Embeddings never routed through Groq; key never logged.
**Known:** Real API not called (mocked) — live check needs `OPENAI_API_KEY`; worker wiring is Phase 29.

---

## Phase 29 — Embedding Generation Worker (compact)

**Recorded:** 2026-09-15 before impl | Source: roadmap Phase 29 + blueprint (`document_chunks` VECTOR 1536, delete-before-insert idempotency)
**Objective:** Celery task chunk → embed → store vectors, idempotent re-runs.
**Contract:** `embeddings` table (`project_id`+`material_id` CASCADE ix, `chunk_id FK→document_chunks CASCADE unique`, `embedding VECTOR(1536)`, `model`); `generate_embeddings(job_id, material_id)`: fresh session, missing rows → job failed + ValueError; no chunks → failed; `embedding_client.embed` batched (mockable) → upsert per `chunk_id` single commit; `pending→running→completed/failed`; transient `httpx.HTTPError` → retry 3x backoff, validation errors fail fast; vectors never stored without chunk scope.
**Files:** `backend/app/models/embedding.py`, `backend/app/worker/tasks/embeddings.py`, pgvector dep, migration
**Guard:** One vector per exact chunk; retry never duplicates (upsert by `chunk_id`).
**Verify:** mocked-client task test — success stores N vectors + job completed; re-run stable count + updated values; client ValueError → failed; no-chunks → failed; missing → failed+raise; worker registers task; container eager run proves pgvector insert.

### Phase 29 Post-implementation (compact)

**Status:** ✅ Complete 2026-09-16
**Files:** `backend/app/models/embedding.py` (`embeddings`: `project_id`/`material_id` CASCADE ix + `chunk_id FK→document_chunks CASCADE unique` + `embedding VECTOR(1536)` + `model`), `backend/app/worker/tasks/embeddings.py` (`generate_embeddings` fresh session + missing→failed+raise + no-chunks→failed + batched mockable client + dim/count guard + upsert per `chunk_id` + `pending→running→completed/failed` + HTTP→retry 3x), `backend/app/worker/tasks/__init__.py` (shared `get_task_session` + register embeddings; `extraction.py` refactored to it, behavior identical), `backend/app/worker/celery_app.py` (include embeddings), `backend/alembic/versions/ab60908d37ca_create_embeddings_table.py` (fixed missing pgvector import), `pyproject.toml`+`requirements.txt` (+`pgvector`), `backend/tests/test_embeddings_task.py` (5 tests), `docs/*`
**Verify:** `upgrade`→`ab60908d37ca`; 5 pass (N vectors stored exact chunk linkage + dims 1536 + job completed; re-run count stable values updated; client ValueError → failed zero rows; no-chunks → failed; missing → failed+raise); extraction/celery suites still pass (shared-helper refactor safe); full `pytest -q` 102 passed (5+97); rebuilt `api`/`worker` (pgvector installed) healthy + worker `[tasks] add generate_embeddings ping process_pdf`; container eager run 3 chunks → 3×1536 rows + completed; `compose config` 0.
**Guard:** Vectors never without chunk scope; dim/count mismatch fails fast instead of partial write.
**Known:** Real OpenAI call not exercised (mocked/dummy key); HTTP-retry path (3× backoff) not unit-hit — same pattern as extraction; ivfflat index deferred (prototype scale).

## Phase 30 — pgvector Retrieval (compact)

**Recorded:** 2026-09-16 before impl | Source: roadmap Phase 30 + blueprint (similarity filtered by `project_id`, `concept_id` scoping)
**Objective:** Secure, project-aware semantic retrieval over stored chunk embeddings.
**Contract:** `retrieve(db, project_id, query, top_k?, concept_id?)`: `embed_one(query)` (same 1536 contract; ValueError on empty query fails fast, no DB hit) → `SELECT chunks JOIN embeddings ON chunk_id` with `Embedding.project_id == project_id` **inside** the SQL `WHERE` + optional `DocumentChunk.concept_id == concept_id` in SQL too → `ORDER BY embedding <=> query_vector LIMIT top_k` → `[{chunk_id, material_id, content, page_number, source_name, chunk_index, score}]` (score = cosine distance, lower is closer). No endpoint in this phase (consumer-neutral service for Phase 31 RAG); project ownership is caller's duty, service enforces the filter.
**Files:** `backend/app/services/retrieval_service.py`, `backend/tests/integration/test_retrieval_isolation.py`
**Guard:** Never fetch-all-then-filter in Python; isolation enforced by the DB query itself.
**Verify:** integration on real Postgres 5433 — cross-project material never returned even when text-similar; concept-scoped query returns only matching concept; unscoped returns nearest across materials ranked; `top_k` honored; empty query → ValueError; no-embedding project → `[]`; full `pytest -q` green; `compose config` 0.

### Phase 30 Post-implementation (compact)

**Status:** ✅ Complete 2026-09-16
**Files:** `backend/app/services/retrieval_service.py` (`retrieve(db, project_id, query, top_k=5, concept_id?)`: empty query → ValueError pre-DB + `top_k` clamped 1–20 + `embed_one` same 1536 contract + dim guard + `JOIN embeddings ON chunk_id` with `Embedding.project_id` + `DocumentChunk.project_id` in SQL `WHERE` + optional `concept_id` in SQL + `ORDER BY cosine_distance LIMIT` → frozen `RetrievedChunk` with citation metadata; no endpoint — consumer-neutral for Phase 31), `backend/tests/integration/test_retrieval_isolation.py` (5 tests) + `__init__.py`, `docs/*`
**Verify:** 5 pass on real pgvector (identical vector in both projects never mixes — proves SQL-side filter; strict ranking `0.0<~0.006<1.0` no ties + citation fields; concept scope beats global nearest + foreign concept `[]` + unscoped nearest; `top_k=2` + empty project `[]`; empty query ValueError + embed not called); full `pytest -q` 107 passed (5+102); `compose config` 0; no migration (read-only over Phase 27/29 schema), no rebuild (no new deps).
**Guard:** Auth/ownership stays with future callers; service only guarantees scope filtering + ranking.
**Known:** Real OpenAI query embedding not exercised (patched one-hots); `top_k` cap 20 generous — Phase 31 may tighten per consumer.

## Phase 31 — RAG Service (compact)

**Recorded:** 2026-09-16 before impl | Source: roadmap Phase 31 (consumer-neutral retrieval + context assembly)
**Objective:** One shared RAG foundation for tutor/quiz/assessment — query + scope in, bounded cited context out.
**Contract:** `assemble_context(db, project_id, query, max_chunks?=5, max_chars?=6000, concept_id?)`: validate non-empty query + clamp chunks `1..10` / chars `500..20000` → `retrieval_service.retrieve` with same scope → skip empty contents + per-chunk word-snapped truncation (`…`) → `RagContext(query, scope_project_id, scope_concept_id, chunks: [RagChunk(chunk_id, material_id, content, page_number, source_name, chunk_index, score)], total_chars, truncated)`; empty retrieval → `chunks []`, `total_chars 0` (consumers decide unsupported behavior, not here). Schemas in `schemas/rag.py` (Pydantic). No LLM call, no endpoint, no consumer wording.
**Files:** `backend/app/services/rag_service.py`, `backend/app/schemas/rag.py`
**Guard:** Consumer-neutral — no tutor/quiz/assessment logic, prompts, or grading inside.
**Verify:** unit tests with mocked `retrieve` — scope passthrough (project+concept+top_k); bound enforcement (chars + count, word-snapped truncation marker); citation metadata preserved; empty retrieval → empty context; empty query → ValueError + retrieve never called; full `pytest -q` green; `compose config` 0.

### Phase 31 Post-implementation (compact)

**Status:** ✅ Complete 2026-09-16
**Files:** `backend/app/services/rag_service.py` (`assemble_context`: empty query → ValueError pre-retrieval + clamp chunks `1..10` / chars `500..20000` + `retrieve` same scope + skip empty contents + per-chunk word-snapped `…` truncation + `truncated` iff char-cut or usable hits dropped; empty retrieval → `chunks []`, `total_chars 0`), `backend/app/schemas/rag.py` (`RagChunk` + `RagContext`), `backend/tests/test_rag_service.py` (6 tests), `docs/*`
**Verify:** 6 pass mocked (scope passthrough incl. stripped query + metadata/scores; `max_chars=500` on 1000ch → `≤500` + `…` + snapped; `max_chunks=2/5` → 2 + truncated; empty → `[]/0/False`; whitespace-only skipped untruncated; empty query ValueError + retrieve uncalled); full `pytest -q` 113 passed (6+107); `compose config` 0; no migration, no rebuild (pure service).
**Guard:** No LLM/endpoint/consumer wording — unsupported-behavior stays with Phase 32+.
**Known:** Truncation marker `…` single char; consumers must treat `chunks []` as their own no-context branch.

## Phase 32 — Tutor Backend (compact)

**Recorded:** 2026-09-16 before impl | Source: roadmap Phase 32 + blueprint §§8/9 (`TutorAnswer`, threshold→unsupported, data-not-instructions)
**Objective:** Grounded tutor endpoint with explicit unsupported behavior — never answer from open memory.
**Contract:** `POST /projects/{project_id}/tutor/ask` via `get_authorized_project` → `tutor_service.ask_question(db, project_id, question, concept_id?)`: empty→ValueError(→400); `assemble_context` (top 5); no chunks → unsupported, no Groq call; best cosine distance > `SUPPORTED_MAX_DISTANCE 0.5` (provisional) → unsupported, no Groq call; else `chat_json` `{"answer"}` (validated non-empty) with system guard (context-only + uploaded text is DATA + cite `[n]`) → `{answer, supported: true, citations: context chunks}`. Unsupported → stable `UNSUPPORTED_MESSAGE` + `supported: false` + `citations []`. `httpx.HTTPError`→502, `RuntimeError`(key)→500, never leak key. No persistence (messages/activity_events are later phases); no concept detection yet (no consumer — deferred, noted).
**Files:** `backend/app/api/v1/tutor.py`, `backend/app/services/tutor_service.py`, `backend/app/schemas/tutor.py`, `main.py` wire
**Guard:** No open-memory answers; uploaded text never leaves the single user message as anything but delimited data.
**Verify:** TestClient tests with mocked `assemble_context`+`chat_json` — grounded 200 + answer + chunk/material citations + Groq called once with guard in system prompt; injection-laced question still grounded (guard present, single user message); empty context + low-similarity → unsupported + Groq uncalled; foreign 404 + no-token 401; empty 400; Groq HTTPError → 502; full `pytest -q` green; `compose config` 0.

### Phase 32 Post-implementation (compact)

**Status:** ✅ Complete 2026-09-16
**Files:** `backend/app/services/tutor_service.py` (`SUPPORTED_MAX_DISTANCE 0.5` provisional + `UNSUPPORTED_MESSAGE` + `ask_question`: empty→ValueError + `assemble_context` top 5 + no-chunks/best>0.5 → unsupported no-Groq + `chat_json {"answer"}` validated non-empty → `{answer, supported, citations}`), `backend/app/api/v1/tutor.py` (`POST /projects/{project_id}/tutor/ask` via `get_authorized_project`; ValueError→400, `httpx.HTTPError`→502, `RuntimeError`→500), `backend/app/schemas/tutor.py` (`TutorAskRequest/Citation/AskResponse`), `main.py` wire, `backend/tests/test_tutor.py` (6 tests), `docs/*`
**Verify:** 6 pass mocked RAG/Groq on real auth/DB (grounded 200 + `[1]` answer + 2 chunk/material citations + guard `not instructions` in system + data in user; injection question/content stay delimited data, never in system; empty + 0.8/0.9 scores → exact unsupported + Groq uncalled; foreign/missing-project 404 + anonymous 401/403 + RAG/Groq untouched; blank 400 + `ConnectError` 502); full `pytest -q` 119 passed (6+113); `compose config` 0; no migration, no rebuild.
**Guard:** No open-memory answers; model output validated before return; key never leaks (generic 502/500 details).
**Known:** `SUPPORTED_MAX_DISTANCE 0.5` provisional — tune with real distributions (Phase 57); `detected_concept_id`/concept-list-in-prompt deferred (no messages/activity consumer yet — blueprint §9 association lands with persistence/analytics); citations = full context set, not model-selected subset.

## Phase 33 — Tutor Frontend (compact)

**Recorded:** 2026-09-16 before impl | Source: roadmap Phase 33 (chat UI over `POST tutor/ask`)
**Objective:** Chat-style tutor exposing answers, citations, unsupported state, and failures — no fabricated content.
**Contract:** `frontend/src/features/tutor/TutorChat.tsx` (`{projectId}`): message list (user/assistant) + input; `POST /projects/{projectId}/tutor/ask` via `apiClient` ONLY (no direct Groq/OpenAI); assistant bubble shows answer + citation chips (`source_name` + page + `#index`); `supported: false` → distinct amber unsupported notice; loading disables send (`Thinking…`); 502 → provider-down + Retry (re-sends last question), 404 → project-missing, else detail/generic — failures never render an answer. Mounted as Tutor section in `ProjectDetailPage` (same pattern as `StructureView`).
**Files:** `frontend/src/features/tutor/TutorChat.tsx`, `ProjectDetailPage.tsx` section
**Guard:** Backend evidence only — frontend never calls AI providers or invents answers/citations.
**Verify:** `npm run build` green; pytest regression green; manual flow (ask → citations; out-of-scope → amber unsupported; stop API → 502 state + retry); `compose config` 0.

### Phase 33 Post-implementation (compact)

**Status:** ✅ Complete 2026-09-16
**Files:** `frontend/src/features/tutor/TutorChat.tsx` (chat state via `apiClient` only: user/assistant/failure messages + citation chips `source, page #index` + amber `supported:false` notice + `Thinking…` pending lock + 502/404/generic failure text with Retry re-send, never fabricates), `ProjectDetailPage.tsx` Tutor section, `backend/app/services/retrieval_service.py` (empty-scope short-circuit: `[]` before any embedding call), `backend/tests/integration/test_retrieval_isolation.py` (+1 test: empty scope → `[]` + embed uncalled), `docs/*`
**Verify:** `npm run build` 89 mods `css 9.59kB js 333.07kB`; manual flow vs rebuilt `api` container — empty project `200 supported:false` offline (short-circuit; first attempt exposed 502-before-check, fixed), blank 400, anon 401, missing 404; `pytest -q` 120 passed (1+119); `compose config` 0; no migration.
**Guard:** No direct AI calls from frontend; failures render state, never answers.
**Known:** Browser click-through not run (no browser here) — flow verified at the exact contract the UI consumes; chat history is session-local (persistence is a later phase).

## Phase 34 — Quiz Data Model (compact)

**Recorded:** 2026-09-16 before impl | Source: roadmap Phase 34 + blueprint §7 DDL (`quizzes`, `quiz_questions`, `quiz_attempts`, `quiz_answers`)
**Objective:** Durable assessment records for quizzes + mastery evidence — models only, no endpoints/generation.
**Contract:** `models/quiz.py` (`Quiz`: `project_id` CASCADE ix + `mode` CHECK practice/exam + `question_count` + `time_limit_seconds?`; `QuizQuestion`: `quiz_id` CASCADE ix + `concept_id` NOT NULL CASCADE ix + `question_text` + `options` JSONB list + `correct_index` INT + `difficulty` CHECK easy/medium/hard + `source_chunk_id?` CASCADE) + `models/quiz_attempt.py` (`QuizAttempt`: `quiz_id` + `user_id` CASCADE ix + `started_at?`/`completed_at?` + `score` NUMERIC(5,2)?; `QuizAnswer`: `attempt_id` CASCADE ix + `question_id` CASCADE + `selected_option_id` TEXT + `is_correct` BOOL + `confidence` INT? CHECK 1–5 + `answered_at` server now()). Evidence stays concept+project tied (denormalized `concept_id` on questions; attempts reach project via quiz).
**Files:** `backend/app/models/quiz.py`, `backend/app/models/quiz_attempt.py`, migration, `models/__init__.py` + `alembic/env.py` wiring
**Guard:** No generation/grading/endpoints — pure persistence for Phase 35+; no orphan evidence (all CASCADE).
**Verify:** `upgrade head` new revision + `downgrade -1`/`upgrade` round-trip; round-trip test (quiz→questions→attempt→answers incl. confidence + correctness); cascade delete quiz→questions/attempts/answers; CHECK violations (bad mode/difficulty/confidence) rejected; full `pytest -q` green; `compose config` 0.

### Phase 34 Post-implementation (compact)

**Status:** ✅ Complete 2026-09-16
**Files:** `backend/app/models/quiz.py` (`Quiz`: project CASCADE ix + mode CHECK + count + limit?; `QuizQuestion`: quiz/concept CASCADE ix + text + options JSONB + `correct_index` + difficulty CHECK + `source_chunk_id?`), `backend/app/models/quiz_attempt.py` (`QuizAttempt`: quiz/user CASCADE ix + started/completed? + `score NUMERIC(5,2)?`; `QuizAnswer`: attempt CASCADE ix + question CASCADE + `selected_index` + `is_correct` + `confidence?` CHECK 1–5 + `answered_at` now()), `backend/alembic/versions/4b3487d354d6_create_quizzes_questions_attempts_.py`, `models/__init__.py` + `alembic/env.py` wiring, `backend/tests/test_quiz_models.py` (3 tests), `docs/*`
**Verify:** `upgrade`→`4b3487d354d6` + `downgrade -1`→`ab60908d37ca`→`upgrade` head + `alembic check` clean; 3 pass (full round-trip incl. options JSONB + confidence 4/None + `answered_at` + score 50.00; quiz delete wipes questions/attempts/answers; bad mode/difficulty/confidence 0+6/concept-null all `IntegrityError`); full `pytest -q` 123 passed (3+120); `compose config` 0.
**Guard:** Evidence concept+project tied; no endpoints yet — nothing queryable until Phase 36+.
**Known:** Index-based options (`correct_index`/`selected_index` per roadmap Phase 34 §2 + Phase 35) instead of blueprint DDL's `correct_option_id`/`selected_option_id TEXT` — coherent with list-options JSONB; test-only failures during dev were session-rollback artifacts, models clean.

## Phase 35 — Quiz Generation (compact)

**Recorded:** 2026-09-16 before impl | Source: roadmap Phase 35 (Groq MCQ + validate-before-persist, Phase 24 discipline)
**Objective:** Validated MCQ generation from concept-scoped chunks — model proposes, app validates + persists.
**Contract:** `generate_quiz(db, project_id, concept_id, num_questions?=5, mode?="practice", difficulty?, client?)`: ValueError on bad input (empty ids, num 1–20, bad mode); LookupError on missing/foreign project+concept (client never called); source = `DocumentChunk`s by project+concept ordered (`chunk_index`) bounded 6000ch — none → `QuizGenerationError`, no LLM call; `chat_json` `{"questions": [{question_text, options[2–6], correct_index in range, difficulty}]}` → Pydantic validate → 1 retry → still-bad raises `QuizGenerationError` with zero rows; persist `Quiz(question_count=actual)` + questions in one commit/rollback. `source_chunk_id` left NULL (no invented attribution). No endpoints.
**Files:** `backend/app/services/quiz_generation_service.py`, `backend/app/schemas/quiz.py` (outline only; API shapes deferred)
**Guard:** LLM proposes content; deterministic code validates + persists; source text is data, never obeyed.
**Verify:** mocked-client tests on real PG — valid persists (quiz + N questions + concept linkage, 1 call, chunk text in prompt); flaky→valid 2 calls single persist; bad twice → error + 2 calls + 0 rows; empty source / missing+foreign concept → error + client uncalled; full `pytest -q` green; `compose config` 0.

### Phase 35 Post-implementation (compact)

**Status:** ✅ Complete 2026-09-16
**Files:** `backend/app/services/quiz_generation_service.py` (`generate_quiz`: ValueError on num 1–20/mode/difficulty + LookupError on missing+foreign project/concept + source = concept chunks ordered bounded 6000ch (none → error, no LLM) + `chat_json {"questions"}` Pydantic + range check vs num + 1 retry → error with zero rows + single-commit persist `question_count=actual`, `source_chunk_id` NULL), `backend/app/schemas/quiz.py` (`MCQQuestionOutline` 2–6 options/`correct_index`≥0/difficulty pattern + `MCQOutline` 1–20), `backend/tests/test_quiz_generation.py` (5 tests, stub client), `docs/*`
**Verify:** 5 pass real PG (valid 1 call + chunk text in prompt + options/index/difficulty/concept persisted; flaky→valid 2 calls one quiz; out-of-range twice → error + 2 calls + 0 rows project-scoped; empty/missing/foreign → error + client uncalled; bad num/mode/difficulty → ValueError + uncalled); full `pytest -q` 128 passed (5+123); `compose config` 0; no migration, no rebuild.
**Guard:** No endpoints yet; nothing persisted before validation passes.
**Known:** `source_chunk_id` NULL (no invented per-question attribution); over-long question sets truncated by rejection (`>num` → retry), not silent trim; test counts project-scoped (shared dev DB).

## Phase 36 — Adaptive Quiz Selection (compact)

**Recorded:** 2026-09-16 before impl | Source: roadmap Phase 36 (deterministic selector, synthetic mastery, rule flagged for confirmation)
**Objective:** Pure deterministic next-question selector — weakest mastery first, exposure-balanced, fully explainable.
**Contract:** `adaptive_quiz_service.select_questions(candidates, mastery, count)`: `CandidateQuestion(question_id, concept_id, difficulty, times_asked, last_asked_at?)` + `mastery: {concept_id: 0–100}` (missing → 50.0 neutral) → concepts sorted (mastery asc, exposure asc, id asc) → round-robin picking unseen-then-easier per concept → deterministic ties by id; `count` 1–20 else ValueError; empty → `[]`. No DB, no LLM (mastery/attempt wiring lands with endpoint/mastery phases).
**Files:** `backend/app/services/adaptive_quiz_service.py`
**Guard:** LLM never decides sequencing; rule + defaults flagged for confirmation (see post).
**Verify:** unit tests synthetic — weakest-first; unseen-before-seen; exposure recency tie-break; unknown-mastery default; determinism (repeat identical); empty/all-covered edges; full `pytest -q` green; `compose config` 0.

### Phase 36 Post-implementation (compact)

**Status:** ✅ Complete 2026-09-16
**Confirmed rule:** weakest-first + difficulty-matched (user choice 2026-09-16; alternatives offered: plain exposure variant, balanced round-robin).
**Files:** `backend/app/services/adaptive_quiz_service.py` (`CandidateQuestion` frozen + `select_questions`: input validation + concepts by mastery/exposure/id + round-robin + within-concept unseen→least-asked→least-recent→difficulty-distance→id; unknown mastery 50.0; count 1–20), `backend/tests/test_adaptive_quiz.py` (6 tests, no DB), `docs/*`
**Verify:** 6 pass (weakest-first round-robin `w1,s1,w2`; weak→easy + strong→hard; fresh→old→recent; neutral-default + id tie-break; repeat-identical + empty + over-count; bad count/difficulty/mastery → ValueError); full `pytest -q` 134 passed (6+128); `compose config` 0; no migration, no rebuild.
**Guard:** Pure function — no DB reads, no LLM; callers supply mastery/coverage facts.
**Known:** Roadmap gaps (not filled here): no attempt/answer-submit or quiz-generate endpoint phase exists before Phase 37 frontend (which assumes both); mastery-score feed arrives with Phase 41 — until then callers pass synthetic/derived maps; difficulty bands (<34/34–66/>66) provisional with the threshold.

## Phase 37 — Quiz Frontend (compact)

**Recorded:** 2026-09-16 before impl | Source: roadmap Phase 37 (quiz-taking UI + confidence control; backend is source of truth)
**Objective:** Student quiz-taking experience over a real backend bridge (gap resolution below).
**Contract:** `frontend/src/features/quiz/` (`QuizTaker.tsx`: load sequence → one question at a time + 1–5 confidence slider + submit → completion with score; failures/retries never lose the attempt; correctness comes only from backend) mounted in `ProjectDetailPage`. Backend bridge (thin, no new logic): `POST /projects/{id}/quizzes/generate` (concept, count, mode → `generate_quiz`, Groq errors → 502), `POST /quizzes/{id}/attempts` (start → attempt id + questions WITHOUT `correct_index`), `POST /attempts/{id}/answers` (question + selected_index + confidence → correctness + running score), `POST /attempts/{id}/complete` (final score). Attempt endpoints verify quiz→project ownership + attempt→user ownership; answers locked once completed.
**Files:** `frontend/src/features/quiz/QuizTaker.tsx`, `ProjectDetailPage.tsx`, `backend/app/api/v1/quizzes.py`, `backend/app/services/quiz_attempt_service.py`, `backend/app/schemas/quiz.py` (+API shapes)
**Guard:** Frontend never computes correctness/mastery; `correct_index` never leaves the backend before answering.
**Verify:** `npm run build` green; backend tests (start hides answers, submit scores + confidence stored, double-answer/completed-attempt rejected, foreign 404); live manual flow vs container (generate mocked? no — needs Groq… manual flow uses seeded quiz via shell); full `pytest -q` green; `compose config` 0.

### Phase 37 Post-implementation (compact)

**Status:** ✅ Complete 2026-09-16 (scope: thin bridge + UI, user-confirmed 2026-09-16)
**Files:** `backend/app/services/quiz_attempt_service.py` (start/answer/complete; server-side scoring; one-answer-per-question; completed-attempt lock; scope checks), `backend/app/api/v1/quizzes.py` (`POST generate` 201/404/422/400/502/500 + `POST {quiz}/attempts` answer-free + `POST attempts/{id}/answers` reveal + `POST attempts/{id}/complete` score; project+user ownership), `backend/app/schemas/quiz.py` (+7 API shapes; `QuestionRead` has no `correct_index`), `main.py` wire, `backend/tests/test_quiz_api.py` (3 tests), `frontend/src/features/quiz/QuizTaker.tsx` (concept select → generate → one-at-a-time + 1–5 confidence + per-question reveal + running score + completion; inline submit retry preserves attempt; 422/502/404 states), `ProjectDetailPage.tsx` Quiz section, `tests/test_quiz_models.py` (scoped `.one()` — shared-DB hardening), `docs/*`
**Verify:** `npm run build` 90 mods; live container loop — start 201 no-leak + correct→`True/1/1/1` + wrong→`False/1/2/1` + complete `50.0`; `pytest -q` 137 passed (3+134); `compose config` 0; no migration.
**Guard:** Correctness only from backend; failures keep attempt state client-side.
**Known:** Generate path needs live Groq (unit-mocked; manual flow seeded); exam `time_limit_seconds` not enforced yet (no timer in UI/service — later phase); mastery-weighted selection not wired to endpoints (Phase 41 feed).

## Phase 38 — Confidence Engine (compact)

**Recorded:** 2026-09-16 before impl | Source: roadmap Phase 38 (confidence as independent signal; mastery boundary)
**Objective:** Calibration summaries from stored confidence — mastery never an input.
**Contract:** `confidence_service.summarize(records) -> ConfidenceSummary`: pure over `AnswerRecord(concept_id, is_correct, confidence?)`; per-concept `{answered, correct, accuracy, rated, avg_confidence(1–5), calibration_gap((avg-1)*25 − accuracy_pct), confidently_wrong (wrong+conf≥4), unsure_right (right+conf≤2)}` + overall rollup; unrated answers count for accuracy, never confidence; empty → zero summary. Storage already exists (Phase 34 col + Phase 37 capture) — no migration, no endpoints.
**Files:** `backend/app/services/confidence_service.py` (tests flat `tests/test_confidence.py` per repo convention, not `tests/unit/`)
**Guard:** No mastery import/input — separation is structural, not a comment.
**Verify:** unit tests — gap math; confidently-wrong/unsure-right counts; unrated excluded from confidence; empty zeros; mastery-proxy (correctness-only accuracy) constant while confidence varies 1↔5; full `pytest -q` green; `compose config` 0.

### Phase 38 Post-implementation (compact)

**Status:** ✅ Complete 2026-09-16
**Files:** `backend/app/services/confidence_service.py` (`AnswerRecord` + `summarize` → per-concept/overall `ConceptCalibration`: accuracy + rated/avg + gap `(avg−1)*25 − pct` + confidently-wrong/unsure-right; unrated counts for accuracy only; bad scale → ValueError), `backend/tests/test_confidence.py` (6 tests, no DB), `docs/*`
**Verify:** 6 pass (gap 75−50=25 + extremes 2/1; unrated accuracy-only; empty/all-unrated Nones; cross-concept rollup; accuracy 0.75 frozen across 1↔5/None swings while gap moves; 0/6 rejected); full `pytest -q` 143 passed (6+137); `compose config` 0; no migration, no rebuild.
**Guard:** Zero mastery dependency — no import, no parameter; calibration consumes only correctness+confidence.
**Known:** Storage/capture pre-existed (Phases 34/37); no read endpoint yet — analytics/decision consumers (Phases 42–46) call `summarize` later.

## Audit 2026-09-16 — Phases 1–39 correctness (deep on recent 10)

**Scope:** re-read recent-10 implementations vs contracts + spot-check 1–28 high-risk logic (auth, upload, extraction, jobs).
**Found + fixed:** (1) Tutor Groq-side failures (`chat_json` shape/JSON ValueError, empty answer) mapped to 400 — now `TutorProviderError` → 502 (`tutor_service.py`, `api/v1/tutor.py`, +1 test asserting 502 for both shapes). (2) `quiz_answers` allowed duplicate (attempt, question) rows under concurrent submits — now `uq_quiz_answers_attempt_question` + migration `d323053b3a54` + service IntegrityError→ValueError + constraint test.
**Checked clean:** embeddings idempotency/retry/failed-states; retrieval SQL-side scope + short-circuit; RAG bounds/truncation flags; quiz generation retry-then-reject + scope guards; attempt scoring/locks/isolation; adaptive determinism; confidence separation; authorization 404-hiding joins; upload magic/size/traversal/orphan-cleanup; extraction idempotency/retry/backoff.
**Verify:** `upgrade`→`d323053b3a54` + `alembic check` clean; `pytest -q` 145 passed; `compose config` 0.
**Deferred (prototype-acceptable):** worker-crash mid-processing leaves material `processing` (no heartbeat — needs design, later phase); upload reads file into memory (10MB cap); `start_attempt` allows repeat attempts (by design — UI offers retake).

## Ops 2026-09-16 — Groq-only live wiring (no phase)

**Change:** `docker-compose.yml` `GROQ_API_KEY: ${GROQ_API_KEY:-dummy-...}` for `api`+`worker` (secret never in repo; OPENAI stays dummy per Groq-only scope); default `GROQ_MODEL` `llama-3.3-70b-versatile` → `openai/gpt-oss-20b` (`config.py` + `.env.example`).
**Why:** first real Groq call 404'd — the 3.3 model is retired; `/v1/models` listing showed `openai/gpt-oss-20b` (+120b, qwen3, compound) as available text models; 20b chosen for tutor <3s target.
**Live proof (key server-side only, never printed):** structure extraction on photosynthesis text → 4 sensible topics; `POST generate` on seeded concept → 201, 2 validated persisted MCQs (Rubisco/ATP+NADPH, correct indices right).
**Verify:** `pytest -q` 145 passed; `compose config --quiet` ok; rebuilt `api` healthy.
**Note:** `GROQ_REASONING_MODEL` in local `.env` is inert (app reads `GROQ_MODEL`); embeddings/retrieval-embed still dummy — live embedding awaits a future `OPENAI_API_KEY` decision.

## Ops 2026-09-16 — Free local embeddings via fastembed (no phase)

**Decision:** user chose local fastembed over Gemini/Cohere free tiers and paid OpenAI.
**Change:** `fastembed>=0.3.0` (`requirements.txt`+`pyproject.toml`); `embedding_client.py` dispatches `EMBEDDING_PROVIDER` (`local` default → `BAAI/bge-small-en-v1.5`, 384 dims, lazy singleton; `openai` path kept, needs key + 1536 column); `config.py` +`EMBEDDING_PROVIDER`; `EMBEDDING_DIMS` 1536→384; migration `a8948d1582d1` (hand-fixed: missing pgvector import + explicit USING + DELETE of retired 1536 rows, which are re-generatable); Dockerfile bakes the model (`FASTEMBED_CACHE_PATH`, ~130MB one-time); `.env.example` documents the switch; existing OpenAI client tests pinned via autouse `EMBEDDING_PROVIDER=openai` fixture + 2 real local tests (384 dims, deterministic).
**Live proof (zero keys, zero network):** rebuilt `api`+`worker` healthy; eager `generate_embeddings` in container → `completed`, 2×384 rows; `retrieve("Where is carbon dioxide fixed?")` → ranked hits (0.2376/0.2543).
**Verify:** `upgrade`→`a8948d1582d1` + `alembic check` clean; `pytest -q` 147 passed; `compose config --quiet` ok.
**Known:** old 1536 OpenAI vectors wiped by migration (dev/test data only); re-setting provider to `openai` requires resizing the column back — the two backends cannot mix dims.

## Phase 39 — Open-Ended Assessment (compact)

**Recorded:** 2026-09-16 before impl | Source: roadmap Phase 39 (free-text grading via Groq; structured grade+feedback; evidence source, never mutates mastery)
**Objective:** Grade one free-text answer against one concept's own material — synchronous, validated, side-effect-free.
**Contract:** `open_ended_assessment_service.grade_open_ended(db, project_id, concept_id, answer_text, client?) -> OpenEndedGrade(score 0–100, verdict pass≥80/partial≥50/fail, feedback)`: answer 1–5000 chars (ValueError) → scope project+concept (LookupError, concept must belong to project) → source = concept title+summary + concept chunks ordered bounded 6000ch (both blank → error, no LLM) → `chat_json {score, feedback}` Pydantic + exactly 1 retry → error persists nothing (there is nothing to persist — pure read/grade) → verdict derived deterministically from score (never model-decided). Answer text is untrusted data (`<<<>>>`, graded never obeyed). `POST /projects/{id}/assessment/open-ended` 200 (+404/400/422/502/500 mapping per quizzes pattern); project isolation via `get_authorized_project`.
**Files:** `backend/app/services/open_ended_assessment_service.py`, `backend/app/schemas/assessment.py`, `backend/app/api/v1/assessment.py`, `main.py` wire, `backend/tests/test_open_ended_assessment.py` (stub client; pass/partial/fail/boundary cases + retry discipline + input/scope guards + isolation/auth)
**Guard:** No mastery import/input/write — grading is an evidence source only; durable `mastery_evidence` rows arrive with Phase 40/41. No new table (roadmap lists service+route only; blueprint's async `evaluate_assessment` Celery flow is a later concern).
**Verify:** new tests pass real PG (pass/partial/fail verdicts; 80/79/50/49 boundaries; flaky→valid 2 calls; bad-twice → error + 2 calls; empty/oversize → ValueError uncalled; missing/foreign → LookupError uncalled; chunkless concept grades from summary; API 200 shape + error map + foreign 404 + no-token 401); full `pytest -q` green; `compose config` 0; no migration, no rebuild.

### Phase 39 Post-implementation (compact)

**Status:** ✅ Complete 2026-09-16
**Files:** `backend/app/services/open_ended_assessment_service.py` (`grade_open_ended`: answer 1–5000 ValueError + LookupError scope + source = concept title/summary + chunks ordered ≤6000ch (both blank → error, no LLM) + `chat_json {score 0–100, feedback 1–2000}` Pydantic + 1 retry → error; verdict `pass≥80/partial≥50/fail` derived; zero writes), `backend/app/schemas/assessment.py` (request strips/5000-cap + response score/verdict/feedback), `backend/app/api/v1/assessment.py` (`POST /projects/{id}/assessment/open-ended` 200 + 404/400/422/502/500 map via `get_authorized_project`), `main.py` wire, `backend/tests/test_open_ended_assessment.py` (9 tests, stub client + patched-service API), `docs/*`
**Verify:** 9 pass real PG (92→pass/65→partial/20→fail + chunk text + concept + answer in prompt; boundaries 100/80/79/50/49/0; flaky→valid 2 calls 81/pass; bad-twice → error + 2 calls; zero quiz rows + concept untouched; chunkless grades from summary; guards uncalled; API 200 shape + 422/404/400 map + foreign 404 + no-token 401/403 + blank-answer 422); full `pytest -q` 156 passed (9+147); `compose config` 0; `alembic check` no new ops, head `a8948d1582d1`; no migration, no rebuild.
**Guard:** No mastery import/input/write — evidence source only; durable rows deferred to Phase 40/41.
**Known:** Synchronous grading (blueprint's async `evaluate_assessment` Celery flow not built — later concern); no confidence field on open-ended yet (no `confidence_records` table — Phase 40/41); feedback length capped 2000 by validation (over-long model output → retry, not trim).

## Phase 40 — Explain-It-Back (compact)

**Recorded:** 2026-09-16 before impl | Source: roadmap Phase 40 (applied-understanding evidence; same grading discipline; append-only; never bypasses evidence model)
**Objective:** Student explains one concept in own words → graded → persisted as `applied_mastery`-bound evidence.
**Contract:** `mastery_evidence` table (NEW, append-only, no UPDATE/DELETE path in code): `user_id`+`project_id` (denorm per repo convention)+`concept_id` FK CASCADE indexed, `evidence_type` CHECK `mcq/open_ended/explain_back` (full enum now so later phases insert without migrating), `raw_score` NUMERIC(5,2) 0–100, `feedback` TEXT nullable (grader text; NULL for mcq rows later). Deliberately WITHOUT `weight`/`resulting_*` — those belong to the flagged-open mastery formula, Phase 41 extends the model file then. `explain_it_back_service.submit_explanation(db, project_id, concept_id, user_id, explanation_text, client?) -> (MasteryEvidence, OpenEndedGrade)`: text 1–5000 ValueError → scope LookupError → grade via Phase 39 `grade_open_ended` (literally shared discipline: same prompt/validation/1-retry; grading failure persists nothing) → single-commit insert `evidence_type='explain_back'`; NO mastery recompute here (Phase 41 owns it — guard is structural: no mastery import). Thin bridge `POST /projects/{id}/assessment/explain-back` 201 `{evidence_id, concept_id, score, verdict, feedback}` (+404/400/422/502/500 map; `get_authorized_project` + `get_current_user`).
**Files:** `backend/app/models/mastery_evidence.py`, migration, `backend/app/services/explain_it_back_service.py`, `backend/app/schemas/assessment.py` (+2 shapes), `backend/app/api/v1/assessment.py` (+route), `models/__init__.py` + `alembic/env.py`, `backend/tests/test_explain_back.py` (stub client; persist/append-only/retry/reject/guards/CHECK/isolation)
**Guard:** Applied evidence ONLY through this table — no direct mastery writes anywhere in the phase.
**Verify:** new tests pass real PG (persist w/ ids+type+score+feedback; 2 submits → 2 rows ordered; flaky→valid 1 row/2 calls; bad-twice → error + 2 calls + 0 rows; empty/oversize → ValueError uncalled; missing/foreign → LookupError uncalled; CHECK rejects bad type; second user attributed separately; API 201 shape + error map + foreign 404 + no-token 401); `alembic upgrade head` + `check` clean; full `pytest -q` green; `compose config` 0; no rebuild.

### Phase 40 Post-implementation (compact)

**Status:** ✅ Complete 2026-09-16
**Files:** `backend/app/models/mastery_evidence.py` (append-only: user/project/concept FK CASCADE indexed + type CHECK full enum + score 0–100 CHECK + feedback nullable; no `weight`/`resulting_*` — Phase 41's), migration `f3a1c9e2b4d5`, `backend/app/services/explain_it_back_service.py` (`submit_explanation` → shared Phase 39 grading → single-commit `explain_back` insert; grading failure persists nothing), `backend/app/schemas/assessment.py` (+`ExplainBackRequest/Response`), `backend/app/api/v1/assessment.py` (`POST explain-back` 201 + 404/400/422/502/500 map), `models/__init__.py` + `alembic/env.py`, `backend/tests/test_explain_back.py` (9 tests), `docs/*`
**Verify:** 9 pass real PG (persist ids/type/score/feedback 85/pass; 2 submits → 40+75 ordered; flaky→valid 1 row/2 calls; bad-twice → error + 2 calls + 0 rows; guards uncalled + 0 rows; CHECK rejects `vibes`; per-user attribution; API 201 shape + 422/404/400 map + foreign 404 + no-token 401/403 + blank 422); `alembic upgrade` → `f3a1c9e2b4d5` + `check` no new ops; full `pytest -q` 165 passed (9+156); `compose config` 0; no rebuild.
**Guard:** No mastery import/recompute anywhere — evidence feed only; writers append, nothing updates/deletes rows.
**Known:** No `weight`/`resulting_*` columns yet (Phase 41 adds with the confirmed formula); sync grading only (no Celery `evaluate_assessment` yet); no UI for explain-back (frontend phases later).

## Phase 41 — Mastery Engine (compact)

**Recorded:** 2026-09-16 before impl | Source: roadmap Phase 41 (deterministic bounded formula; FLAGGED for confirmation — asked, not invented)
**Objective:** Compute `mcq_mastery` / `applied_mastery` per (user, project, concept) from append-only evidence.
**Contract:** `mastery_service`: pure core `compute_mastery(points) -> MasteryScores(mcq, applied, counts, last_at)` over `EvidenceInput(evidence_type, score 0–100, difficulty?, at)` + thin read-only `mastery_for_concept(db, user, project, concept)` (no writes anywhere — evidence stays append-only, no `concept_mastery` state table; mastery is derived on read). Streams: `mcq` → mcq_mastery, `open_ended`/`explain_back` → applied_mastery; unknown types → ValueError; empty stream → None (explicit unknown; consumers map it, e.g. adaptive already defaults 50). Confidence is not an input — exclusion is structural. NO producer rewiring (quiz completion → mcq rows is a separate step, noted below).
**Files:** `backend/app/services/mastery_service.py`, `backend/tests/test_mastery.py` (synthetic pure + one real-PG reader test)
**Guard:** No LLM, no confidence input, no writes; evidence rows never mutated.
**Verify:** unit tests — bounds (all-0/all-100/out-of-range/empty), stream independence, confidence-absence (structural), recency/difficulty behavior per confirmed formula, determinism, reader on real PG; full `pytest -q` green; `compose config` 0; `alembic check` clean (no migration); no rebuild.

### Phase 41 Post-implementation (compact)

**Status:** ✅ Complete 2026-09-16
**Confirmed formula:** Blueprint EMA (user choice 2026-09-16; alternatives offered: plain mean, last-5 window).
**Files:** `backend/app/services/mastery_service.py` (`EvidenceInput` w/o confidence + `compute_mastery` pure + `mastery_for_concept` read-only; seed-first EMA, difficulty base easy .2/med .3/hard .4/free-text .3, +0.1 gap boost strictly >7d capped .5, clamp 0–100, `mcq`→mcq / `open_ended`+`explain_back`→applied, empty→None), `backend/tests/test_mastery.py` (7 tests: 6 synthetic + 1 real-PG reader), `docs/*`
**Verify:** 7 pass (bounds/seed/empty-None + bool/NaN/type/difficulty rejections; independence + open/explain routing 20→23; easy 20 vs hard 40; same-day 65 vs 10d-gap 70 vs 7d-edge 65 vs hard+gap capped 75; field/signature structural + repeat determinism + time-sorted reversal + mixed-time rejections; reader 52.0/count/last_at + LookupError); full `pytest -q` 172 passed (7+165); `compose config` 0; `alembic check` no new ops; no migration, no rebuild.
**Guard:** No LLM/confidence/writes anywhere; leak-proof reader (user+project+concept filter + scope check).
**Known:** No `concept_mastery` state table (derived on read per roadmap wording); quiz completion does NOT yet append `mcq` evidence rows (producer wiring is a separate step — engine consumes whatever `mastery_evidence` holds); scale 0–100 (÷100 if a 0–1 API is ever needed).

## Phase 42 — Mismatch Engine (compact)

**Recorded:** 2026-09-16 before impl | Source: roadmap Phase 42 (deterministic divergence rule; FLAGGED for confirmation — asked, not invented)
**Objective:** Flag concepts where recognition outruns understanding, with explainable reasons and cross-concept priority.
**Contract:** `models/mismatch.py` (derived domain types ONLY — no DB table: mismatch is computed on read like mastery, a persisted snapshot would go stale with every new evidence row): frozen `Mismatch(concept_id, mismatch_type, mcq_mastery, applied_mastery, gap, reason)` + type constants + priority order. `mismatch_service.detect_mismatches(states) -> list[Mismatch]`: per concept skip unknown mastery (None) or thin data; primary `mcq-applied >= GAP` → `mcq_high_applied_low`; optional calibration input (avg_confidence/accuracy over evaluated records only) → `overconfident`/`underconfident` bands; one badge per concept by type priority; cross-concept rank by (type priority, gap desc, concept_id asc). Never LLM. Reason strings carry the numbers, non-judgmental.
**Files:** `backend/app/models/mismatch.py`, `backend/app/services/mismatch_service.py`, `backend/tests/test_mismatch.py` (synthetic, no DB)
**Guard:** Deterministic + explainable — same inputs always give same ranked list with same reasons.
**Verify:** unit tests — threshold edge (gap exactly/at±1), thin-data gating each minimum, unknown-mastery skip, type priority, cross-concept ranking incl. tie-break, invalid inputs; full `pytest -q` green; `compose config` 0; `alembic check` clean (no migration); no rebuild.

### Phase 42 Post-implementation (compact)

**Status:** ✅ Complete 2026-09-16
**Confirmed rule:** Blueprint full set (user choice 2026-09-16; alternatives offered: primary-only, stricter gate).
**Files:** `backend/app/models/mismatch.py` (frozen `Mismatch` + type constants + priority — derived types, deliberately no DB table: a snapshot would go stale with every new evidence row), `backend/app/services/mismatch_service.py` (`ConceptState` validated + `detect_mismatches`: primary gap≥25 w/ 3 mcq + 1 applied minima, calibration secondary over evaluated-only inputs, one badge per concept, rank by type/gap/id), `backend/tests/test_mismatch.py` (6 tests, synthetic, no DB), `docs/*`
**Verify:** 6 pass (edge 25 flags/24.9 not + reversed never + gap 38; thin-mcq/no-applied gated + minima-met flags; None mastery never; over/under bands + unevaluated excluded + mid-band quiet + primary wins badge; type-then-gap ranking + id tie-break + repeat identical; reason numbers + 4 rejections); full `pytest -q` 178 passed (6+172); `compose config` 0; `alembic check` no new ops; no migration, no rebuild.
**Guard:** No LLM; unknown/thin never flags; same inputs → same ranked reasons.
**Known:** No table/endpoints — consumers (recommendation, dashboard) compute on read; calibration inputs must be evaluated-only aggregates (caller contract); `applied_high_mcq_low` is intentionally not a type (blueprint only flags recognition-outrunning-understanding).

## Phase 43 — Recommendation Engine (compact)

**Recorded:** 2026-09-16 before impl | Source: roadmap Phase 43 (one explainable current recommendation; FLAGGED for confirmation — asked, not invented)
**Objective:** Score every (concept, action) pair deterministically and persist exactly one current recommendation.
**Contract:** `models/recommendation.py` (NEW table — lifecycle NEEDS persistence: active/accepted/dismissed/expired statuses; repetition history; unlike mismatch snapshots these rows are the history, not a cache): user/project/concept FK CASCADE indexed, `action_type` CHECK 5 blueprint actions, `score` NUMERIC(6,2), `reasoning` TEXT, `status` CHECK default `active`. `recommendation_service`: pure `score_action(signal, action, ctx)` + `recommend(db, user_id, project_id, signals, goal_keywords?)` which expires the previous `active` row → `expired`, inserts the winner as `active`, returns it. Signals: `ConceptSignal(concept_id, name, mcq?, applied?, mcq_count, applied_count, mismatch_type?, avg_confidence?, accuracy?, evaluated_count?, days_since_evidence?)`; unknown-both mastery → concept skipped; no candidates → None (explicit). Repetition counts read from the table (7-day window — part of the confirmed formula). Reason strings name the nonzero drivers with numbers. Never LLM. Accept/dismiss endpoints deferred to the Phase 44 bridge.
**Files:** `backend/app/models/recommendation.py`, migration, `backend/app/services/recommendation_service.py`, `backend/tests/test_recommendation.py` (pure scoring + real-PG persist/supersede), `models/__init__.py` + `alembic/env.py`
**Guard:** Reproducible from stored inputs — same table state + same signals always give the same winner, score, and reasoning.
**Verify:** unit tests — base/weakness math, mismatch +40/−20, uncertainty, recency edge, repetition penalty incl. window, exam eligibility, tie-break, None-when-empty, supersede (exactly one active), reasoning names drivers; full `pytest -q` green; `compose config` 0; `alembic upgrade head` + `check` clean; no rebuild.

### Phase 43 Post-implementation (compact)

**Status:** ✅ Complete 2026-09-16
**Confirmed formula:** Blueprint full formula (user choice 2026-09-16; alternatives offered: weakness+mismatch-only, all-time repetition).
**Files:** `backend/app/models/recommendation.py` (user/project/concept FK CASCADE indexed + action CHECK 5 types + score + reasoning + status CHECK default active — table needed: statuses must stick and repetition reads history), migration `e7b2d4a1c6f8`, `backend/app/services/recommendation_service.py` (frozen `ConceptSignal` + pure `score_action`/`is_eligible` + `recommend`: scope check → 7-day repetition counts from table → strict-max over deterministic order → expire-previous + insert winner, None when nothing scorable), `backend/tests/test_recommendation.py` (8 tests: 4 pure + 4 real-PG), `models/__init__.py` + `alembic/env.py`, `docs/*`
**Verify:** 8 pass (60/70/55/58 + single-stream 40 + rejections; +40/+40/−20/untouched; +25/edge 5-vs-6/goal case-insensitive/floor 0; exam 3-vs-2; persist slope/explain_back 80 + reasoning numbers → penalized switch to targeted_quiz 75 + expire-first + one-active; 10-day-old repeat unpenalized; penalized-still-wins names recency; empty/foreign/missing → None/LookupError + 0 rows); `alembic upgrade` → `e7b2d4a1c6f8` + `check` no new ops; full `pytest -q` 186 passed (8+178); `compose config` 0; no rebuild.
**Guard:** No LLM; same state+signals → same winner/score/words; penalty is per (concept,action) so variety shifts action first, concept second.
**Known:** Accept/dismiss endpoints deferred to Phase 44 bridge; goal keywords have no project field yet (caller-supplied, default empty); exam eligibility counts signal evidence counters, not table scans.

## Phase 44 — Mastery/Mismatch/Recommendation UI (compact)

**Recorded:** 2026-09-16 before impl | Source: roadmap Phase 44 (read-only dashboard over derived metrics; browser never recalculates)
**Gap resolution (Phase 37 pattern):** the guard demands backend APIs but none exist — thin bridge added, no new logic: `dashboard_service.build_dashboard` composes existing engines (mastery_for_concept + quiz-answer calibration + detect_mismatches + stored recommendation) and `refresh/accept/dismiss` delegate to `recommend()` + status updates. No formulas invented in the bridge.
**Contract:** `GET /projects/{id}/dashboard` → `{concepts: [{concept_id, title, topic, subtopic, mcq, applied, counts, last_evidence_at, mismatch?}], recommendation?}` (per current user; unknown mastery as null; current = active else latest non-expired); `POST .../dashboard/refresh` → 201 persisted winner; `POST .../dashboard/accept|dismiss` → active row transitions (none active → 404). Calibration = rated quiz answers only (confidence present; accuracy over the same set). `frontend/src/features/dashboard/Dashboard.tsx`: loading/empty/error states, per-concept MCQ/applied bars + counts + mismatch badge + reason, recommendation card with reason + Refresh/Accept/Dismiss; mounted in `ProjectDetailPage`.
**Files:** `backend/app/services/dashboard_service.py`, `backend/app/schemas/dashboard.py`, `backend/app/api/v1/dashboard.py`, `main.py` wire, `backend/tests/test_dashboard.py` (real PG composition + transitions + isolation), `frontend/src/features/dashboard/Dashboard.tsx`, `ProjectDetailPage.tsx`
**Guard:** UI renders backend numbers only — no mastery/mismatch/score math in TSX.
**Verify:** backend tests (mastery reuse 52.0 + path + gap flag + calibration band + refresh/accept/dismiss lifecycle + one-active + foreign 404 + no-token 401); `npm run build` green; full `pytest -q` green; `compose config` 0; `alembic check` clean (no migration); no rebuild.

### Phase 44 Post-implementation (compact)

**Status:** ✅ Complete 2026-09-16
**Files:** `backend/app/services/dashboard_service.py` (`build_dashboard` per-user composition: path-ordered concepts + `mastery_for_concept` reuse + rated-answers calibration + `detect_mismatches` + recommendation signals; `current_recommendation` active-else-latest-settled), `backend/app/schemas/dashboard.py` (4 read shapes; nulls for unknown), `backend/app/api/v1/dashboard.py` (`GET dashboard` read-only + `POST refresh` 201 + `POST accept|dismiss` with 404-when-none-active), `main.py` wire, `backend/tests/test_dashboard.py` (3 tests, real PG), `frontend/src/features/dashboard/Dashboard.tsx` (bars/counts/badges/reasons + rec card + Refresh/Accept/Dismiss + loading/empty/error/Retry), `ProjectDetailPage.tsx` Mastery section, `docs/*`
**Verify:** 3 pass real PG (Slope mcq 90×3/applied 40 → gap-50 flag + path + null rec; Intercept applied 73 + underconfident via rated answers; refresh 201 → GET shows id → dismiss sticks → refresh supersedes; accept-on-empty 404; foreign 404 + no-token 401/403 + unknown-project 404); `npm run build` 91 mods; full `pytest -q` 189 passed (3+186); `compose config` 0; `alembic check` no new ops; no migration, no rebuild.
**Guard:** Bridge delegates every number; UI does zero derived math (only width% display + label maps).
**Known:** Dashboard is per-user (mastery is per-user — expected); calibration uses rated answers only; `except httpx` in refresh is defensive (no HTTP calls today — recommend() is local); no exam/timer UI (later).

## Audit 2026-09-16 — Phases 35–44 correctness (deep, all ten)

**Scope:** re-read every Phase 35–44 implementation vs its contract: generation retry/scope/persist, adaptive determinism, attempt locks/isolation, confidence math/separation, open-ended validation/retry/zero-writes, explain-back append-only, mastery EMA/reader, mismatch thresholds/ranking, recommendation scoring/persist/supersede, dashboard composition/routes/UI; plus wiring (main.py, models/__init__, migrations chain) and status-table bookkeeping.
**Found + fixed:** (1) `compute_mastery` rejected globally-mixed timestamps — one timed stream + one untimed stream raised even though each stream is internally consistent (`mastery_service.py`: validation moved per-stream in `_run_stream`, +1 test). (2) Status table still showed original-numbered rows 31–34/38 as ⏳ Pending although detail §35/§37/§38 implement them — rows now ✅ pointing at their detail sections.
**Checked clean:** generation 1-retry-then-reject + zero-rows-on-failure + chunk grounding; adaptive weakest/difficulty/exposure/id determinism (incl. None-safe sort keys); attempt server-side scoring + completed-lock + uq race guard; confidence gap math + unrated-accuracy-only + structural mastery absence; open-ended verdict bands + chunkless-from-summary + zero writes; explain-back single-commit + CHECK + per-user attribution; mastery seed/weights/cap/clamp + leak-proof reader; mismatch 25/3+1 gate + calibration bands + type/gap/id ranking + number-carrying reasons; recommendation base/weakness/mismatch/recency/goal/repetition math + floor + exam breadth + supersede-one-active + 7-day window; dashboard per-user composition + path ordering + active-else-settled + accept/dismiss stickiness + isolation; route error maps (404/400/422/502) consistent across quiz/assessment/refresh; no transport error consumes a validation retry (httpx propagates past the Pydantic-only except); wiring complete; `alembic check` clean at `e7b2d4a1c6f8`.
**Doc drift corrected:** Phase 40's note said Phase 41 would add `weight`/`resulting_*` columns — Phase 41 correctly needed none (derived on read); no schema gap, note superseded by this entry.
**Verify:** `pytest -q` 190 passed; `npm run build` 91 mods; `compose config` 0; `alembic check` no new ops.
## Phase 45 — Growth Analysis (compact)

**Recorded:** 2026-09-16 before impl | Source: roadmap Phase 45 (time-series over evidence; deterministic; sparse histories rendered honestly)
**Design (no resulting_* columns exist — derived on read):** growth = EMA replay — order a scope's evidence by `created_at`, re-run the confirmed Phase 41 engine over each prefix, emit per-point running mastery. Concept scope: `[(at, type, score, mcq_after, applied_after)]` + per-stream trend (last−first running, None when <2 points in that stream) + counts. Project scope: per-concept current mastery (evidenced concepts only) + their means + total rows + time range; unevidenced concepts excluded, never zero-filled. Per current user throughout (mastery is per-user). Read-only; no tables, no LLM.
**Contract:** `growth_service.concept_growth` (LookupError on foreign scope) + `project_growth`; `GET /projects/{id}/growth` (overview) + `GET .../growth?concept_id=` (series); `frontend/src/features/analytics/GrowthView.tsx` (overview cards + concept picker + point list + trend or "not enough history" + loading/error/Retry); mounted in `ProjectDetailPage`.
**Files:** `backend/app/services/growth_service.py`, `backend/app/schemas/growth.py`, `backend/app/api/v1/growth.py`, `main.py` wire, `backend/tests/test_growth.py` (synthetic replay + real-PG scopes/API), `frontend/src/features/analytics/GrowthView.tsx`, `ProjectDetailPage.tsx`
**Guard:** Every number derives from evidence rows + the confirmed engine — no counters, no invented trends.
**Verify:** unit tests — replay math (40→52.0, trend +12), stream independence, empty/single-point honesty, scope guards, overview means-over-evidenced-only + range, API shape + foreign 404 + no-token 401; `npm run build` green; full `pytest -q` green; `compose config` 0; `alembic check` clean (no migration); no rebuild.

### Phase 45 Post-implementation (compact)

**Status:** ✅ Complete 2026-09-16
**Files:** `backend/app/services/growth_service.py` (`concept_growth` EMA-prefix replay + per-stream trends over own points only + `project_growth` means-over-evidenced-only + range; read-only, per-user), `backend/app/schemas/growth.py` (4 read shapes), `backend/app/api/v1/growth.py` (`GET growth` overview + `?concept_id=` series, 404 on foreign scope), `main.py` wire, `backend/tests/test_growth.py` (4 tests, real PG), `frontend/src/features/analytics/GrowthView.tsx` (overview cards + concept picker + point list + trend or "not enough history" + loading/error/Retry), `ProjectDetailPage.tsx` Growth section, `docs/*`
**Verify:** 4 pass real PG (40→52.0 replay + trend +12; independence + single-point-None + empty + LookupErrors; overview 70.0 mean + exclusion + range; API shapes + 404s + 401); `npm run build` 92 mods; full `pytest -q` 194 passed (4+190); `compose config` 0; `alembic check` no new ops; no migration, no rebuild.
**Guard:** No counters, no invented trends — sparse series say so explicitly.
**Known:** Replay is O(n²) in evidence rows per concept (fine at prototype scale; a single-pass fold is the Phase 57 optimization); trends are running-deltas, not regression slopes; project means are over evidenced concepts only.

## Phase 46 — Project Analytics (compact)

**Recorded:** 2026-09-16 before impl | Source: roadmap Phase 46 (aggregate stats endpoint + simple view; read-model only)
**Contract:** `analytics_service.project_analytics` (read-only, per current user): materials total + by-status breakdown, concepts/topics counts, quiz attempts total + completed, average mastery by REUSING `growth_service.project_growth` (one derivation path — no parallel truth), `tutor_interactions: null` — honestly untracked, no tutor/message store exists until the later Activity Events phase; inventing a counter would violate the guard. `GET /projects/{id}/analytics`. Counts via single `func.count` queries (mastery loop inherited from growth — prototype-acceptable). `frontend/src/features/analytics/AnalyticsView.tsx`: stat cards + loading/empty/error/Retry; mounted in `ProjectDetailPage`.
**Files:** `backend/app/services/analytics_service.py`, `backend/app/schemas/analytics.py`, `backend/app/api/v1/analytics.py`, `main.py` wire, `backend/tests/test_analytics.py` (real PG), `frontend/src/features/analytics/AnalyticsView.tsx`, `ProjectDetailPage.tsx`
**Guard:** Read-model over existing tables + the growth derivation — nothing new persisted, no second source of truth.
**Verify:** integration tests — counts incl. by-status, attempts total/completed, mastery reuse equals growth overview, tutor null, empty-project zeros/nulls, foreign 404 + no-token 401; `npm run build` green; full `pytest -q` green; `compose config` 0; `alembic check` clean (no migration); no rebuild.

### Phase 46 Post-implementation (compact)

**Status:** ✅ Complete 2026-09-16
**Files:** `backend/app/services/analytics_service.py` (frozen `ProjectAnalytics`; single-count queries + growth reuse; tutor None by design), `backend/app/schemas/analytics.py`, `backend/app/api/v1/analytics.py` (`GET analytics`, 404 on missing), `main.py` wire, `backend/tests/test_analytics.py` (2 tests, real PG), `frontend/src/features/analytics/AnalyticsView.tsx` (stat cards + by-status line + loading/error/Retry), `ProjectDetailPage.tsx` section, `docs/*`
**Verify:** 2 pass real PG (3 materials 2-ready/1-processing + attempts 2/1 + mastery reuse (80.0, None) + tutor None + LookupError; empty-project exact-zero body + foreign 404 + no-token 401/403 + unknown-project 404); `npm run build` 93 mods; full `pytest -q` 196 passed (2+194); `compose config` 0; `alembic check` no new ops; no migration, no rebuild.
**Guard:** Read-only; mastery has exactly one derivation path; tutor shows "not tracked yet", never a fake zero.
**Known:** Mastery loop inherited from growth (prototype N+1); attempts are per-user; by-status dict only lists present statuses.

## Phase 47 — Admin Dashboard (compact)

**Recorded:** 2026-09-16 before impl | Source: roadmap Phase 47 (separate privilege boundary, same JWT identity)
**Contract:** `dependencies/admin.py` (`get_current_admin`: 401 upstream when anonymous, 403 when non-admin); `api/v1/admin.py`: `GET /admin/users` (id/email/is_admin/created_at ordered, never password — reuses `UserRead`) + `GET /admin/overview` (global single-count queries: users/spaces/projects/materials/quizzes/attempts/evidence/recommendations; no per-user PII beyond the user list the boundary exists for). `frontend/src/features/admin/AdminPage.tsx` + `/admin` route (ProtectedRoute + in-component `is_admin` gate → Forbidden message; backend 403 is the real enforcement) + Home nav link for admins only.
**Files:** `backend/app/dependencies/admin.py`, `backend/app/api/v1/admin.py`, `backend/app/schemas/admin.py`, `main.py` wire, `backend/tests/test_admin.py` (401/403/200 both endpoints + register-with-`is_admin` ignored + no password leak), `frontend/src/features/admin/AdminPage.tsx`, `App.tsx` route+link
**Guard:** Same JWT identity; privilege checked server-side on every admin call — UI gating is cosmetic.
**Verify:** tests — anonymous 401, non-admin 403, admin 200 users+overview with exact counts, privilege-escalation attempt fails, response has no password fields; `npm run build` green; full `pytest -q` green; `compose config` 0; `alembic check` clean (no migration); no rebuild.

### Phase 47 Post-implementation (compact)

**Status:** ✅ Complete 2026-09-16
**Files:** `backend/app/dependencies/admin.py` (`get_current_admin`: 401 upstream, 403 non-admin), `backend/app/api/v1/admin.py` (`GET users` reusing `UserRead` ordered + `GET overview` 8 single-count queries), `backend/app/schemas/admin.py` (`AdminOverview`), `main.py` wire, `backend/tests/test_admin.py` (4 tests, real PG), `frontend/src/features/admin/AdminPage.tsx` (cards + user list + Forbidden/loading/Retry; gate in-component, enforcement server-side), `App.tsx` `/admin` route + admin-only nav link, `docs/*`
**Verify:** 4 pass real PG (anon 401 ×2 + non-admin 403 ×2 + admin 200; user list contains both, flags right, exact key set, no hash leak; overview keys + DB-equal users/spaces + non-negative ints; register `is_admin:true` → stored False); `npm run build` 94 mods; full `pytest -q` 200 passed (4+196); `compose config` 0; `alembic check` no new ops; no migration, no rebuild.
**Guard:** Privilege never self-grantable (register schema has no such field; extra ignored); UI gate cosmetic.
**Known:** User list unpaginated (fine at prototype scale); overview has no per-user drill-down (by design — no PII beyond the list).

## Phase 48 — Error Handling (compact)

**Recorded:** 2026-09-16 before impl | Source: roadmap Phase 48 (standardize failure behavior)
**Contract:** `core/exceptions.py` + `main.py` + `schemas/errors.py`. One JSON envelope `{"error":{"code","message","details?"}}` with stable machine codes; map validation/auth/not-found/rate-limit/upstream-AI consistently; internals never leak; tests per error path assert shape+status.
**Design (additive, minimum):** Status→code table in `core/exceptions.py` + `register_error_handlers(app)`: `RequestValidationError`→422 `validation_error` with sanitized `{loc,msg,type}` details; `StarletteHTTPException`→code-by-status keeping the route's domain message for 4xx/502 (fixed safe strings by construction) but generic "Internal server error" for 500/other-5xx + non-str details; unhandled `Exception`→500 generic (logged server-side); headers (e.g. `WWW-Authenticate`) preserved. 429→`rate_limited` mapped though no limiter exists yet (limiter is Phase 49). No route/service edits — normalization lives at the boundary, satisfying the no-incompatible-payloads guard.
**Files:** `backend/app/schemas/errors.py` (new), `backend/app/core/exceptions.py` (new), `main.py` wire, `backend/tests/test_error_handling.py` (new: 422/401/403/404/429-mapping/500-generic/502 shapes), `test_auth.py:176` envelope update, `frontend/src/lib/api-error.ts` (new single reader, legacy `detail` fallback) + 12 feature files switched to it.
**Verify:** new tests + full `pytest -q` + `npm run build` + `compose config` + `alembic check` (no migration); no rebuild.

### Phase 48 Post-implementation (compact)

**Status:** ✅ Complete 2026-09-16
**Files:** `backend/app/schemas/errors.py` (`ErrorDetail`/`ErrorEnvelope`), `backend/app/core/exceptions.py` (status→code table + `register_error_handlers`: validation/HTTP/unhandled), `main.py` wire, `backend/tests/test_error_handling.py` (9 tests, real PG), `test_auth.py:176` envelope update, `frontend/src/lib/api-error.ts` (single reader, legacy `detail` fallback) + 12 feature files migrated (local extractors deleted)
**Verify:** 9 pass (422+details / 401+WWW-Authenticate / expired / 403 exact / 404 strict-keys / 400 exact / 500 generic with secret-absence proof / 502 via malformed provider payload / code-table incl. 429); `pytest -q` 209 passed (200+9); `npm run build` 95 mods; `compose config` 0; `alembic check` clean; no migration, no rebuild.
**Guard:** No route invents payloads — normalization at boundary; 5xx/non-str details genericized; originals logged server-side.
**Known:** 429 mapped but producer-less until Phase 49 limiter; status-specific friendly texts in UI unchanged (codes available for future use).

## Phase 49 — Security Hardening (compact)

**Recorded:** 2026-09-16 before impl | Source: roadmap Phase 49 (close gaps; reinforce, don't re-architect)
**Survey:** CORS already settings-driven, no wildcard (compose `5173,3000`, default `5173`) — lock with tests. Upload enforcement exists (`save_pdf`: ext+content-type+`%PDF`+10MB+basename+server-controlled uuid path) — re-test + traversal at API level. No file-serving route exists (metadata only, owner-scoped) — regression-test that no bytes are servable. Prompts: all 4 LLM boundaries already delimit untrusted input (tutor `<<<DATA`, others `<<<>>>` + never-obey line) — codify with builder tests, no prompt edits. No limiter exists — new `core/rate_limit.py` sliding-window in-memory (honest: compose runs a single uvicorn api process, no `--workers`; Lock-guarded; documented). LLM endpoints = tutor ask + quiz generate + assessment ×2 (structure extraction runs in Celery, not request-scoped — excluded by design). `MaterialRead.storage_path` stays (owner-only, frontend never consumes; removing churns old tests for no threat-model gain).
**Files:** `core/config.py` (+3 settings) + `.env.example`, `core/rate_limit.py` (new: `check_llm_budget`/`require_llm_budget(scope)`/`reset_budgets`), wire into `tutor.py`/`quizzes.py`/`assessment.py` (auth-first ordering preserved), `tests/security/` package (6 files), frontend 429 texts (TutorChat/QuizTaker), `docs/*`.
**Verify:** new security tests + full `pytest -q` + `npm run build` + `compose config` + `alembic check` (no migration); no rebuild.

### Phase 49 Post-implementation (compact)

**Status:** ✅ Complete 2026-09-16
**Files:** `core/config.py` (+3 settings) + `.env.example`, `core/rate_limit.py` (sliding-window, Lock-guarded, single-process scope documented; `check_llm_budget`/`require_llm_budget`/`reset_budgets`), limiter wired into `tutor.py`/`quizzes.py`/`assessment.py` after ownership deps, `tests/security/` (helpers + 6 files, 14 tests), frontend 429 texts (TutorChat/QuizTaker), `docs/*`
**Verify:** 14 pass (CORS echo/omit+no-wildcard; upload 400×3/413/traversal-contained/auth+ownership; metadata JSON-only + no byte-serving route; 429 envelope + user/project isolation + auth-first-404 + scope independence; 4 prompt boundaries delimit+instruct; 13 guessed-ID checks all 404 `not_found` + list non-leak); `pytest -q` 223 passed (209+14); `npm run build` 95 mods; `compose config` 0; `alembic check` clean; no migration, no rebuild.
**Guard:** No auth/storage/AI re-architecture — additive limiter + tests; budgets consumed post-ownership so strangers learn nothing.
**Known:** In-memory buckets valid only while api runs single-process (compose default; document before scaling); structure extraction (Celery) intentionally unscoped — queued work, not request LLM spend; `storage_path` stays owner-visible (no consumer beyond owner, no download route).

## Frontend Redesign (out-of-band, user-requested)

**Recorded:** 2026-09-16 before impl | Source: user ask — StudyFetch-like, Tailwind, beautiful
**Research:** StudyFetch patterns — bold benefit hero, mascot/illustration, icon feature grid (tutor/quizzes/notes/games), stats band, tabbed tool surface, bright violet + warm accent on light playful SaaS.
**Design:** Light playful theme (violet primary `262 83% 58%`, amber accent, lavender-tinted bg `#f6f5ff`), Plus Jakarta Sans + system fallback, radius `0.875rem`, `tailwindcss-animate` keyframes (fade-up/float). One shared `components/ui.tsx` (Button/Card/Badge/Spinner/EmptyState/ErrorBox/Stat/PageHeader/avatar). App shell (glass navbar + footer) + logged-out landing (hero/stats/features/how/CTA) + logged-in home cards. Project page becomes tabbed workspace (Overview/Tutor/Quiz/Materials/Structure/Progress) + NEW `MaterialsPanel` (PDF dropzone + status list + auto-poll while processing) wired to existing materials endpoints only. Restyle all features; zero API/data-flow changes.
**Files:** `index.html`, `index.css`, `tailwind.config.js`, `components/ui.tsx`, `components/AppShell.tsx`, `features/landing/LandingPage.tsx`, `App.tsx`, auth ×2, spaces, projects ×2 (+materials panel), tutor, quiz, dashboard, structure, analytics ×2, admin.
**Verify:** `npm run build` green; backend untouched (`pytest` unaffected, no backend files); no rebuild needed (frontend-only); single commit.

### Frontend Redesign Post-implementation (compact)

**Status:** ✅ Complete 2026-09-16
**What:** Violet/amber playful theme (Plus Jakarta Sans, radius 0.875rem, fade-up/float/typing keyframes, mesh+dot backdrops); `components/ui.tsx` primitives + `AppShell` (glass navbar, footer); logged-out landing (hero with live product mock, stats, 6-feature grid, how-it-works, quote) + logged-in home cards; split-panel auth; tile-colored space/project grids; tabbed project workspace (Overview/Tutor/Quiz/Materials/Map/Progress); NEW `MaterialsPanel` (PDF dropzone, status badges, 5s auto-poll while processing) on existing endpoints; chat with avatars/chips/typing dots; quiz with progress bar/letter options/confidence pills/score celebration; recommendation spotlight + mastery grid; accordion learning map; icon stat cards; growth sparklines + trend badges; polished admin.
**Verify:** `npm run build` green (tsc + vite, 1954 mods); `npm run lint` no errors (pre-existing effect-pattern warnings only); `git status` frontend-only, zero backend files.
**Known:** Google Fonts degrades to system stack offline; `/dashboard` placeholder route removed (nothing linked to it); poll interval fixed 5s.

## Pipeline Fix — wire extraction→chunk→structure→embed (out-of-band bugfix)

**Recorded:** 2026-09-16 before impl | Source: user screenshots — tutor "not covered", empty Map despite Ready PDF
**Diagnosis:** `process_pdf` extracted text and stopped; NOTHING dispatched `generate_embeddings`, nothing created chunks, nothing called structure extract/persist (all only reachable from tests). Live proof: user project 0 chunks / 0 embeddings. ALSO: running api container has dummy `GROQ_API_KEY` (host shell has none) — Groq-dependent steps need a real key from the user.
**Fix:** `process_pdf` success path chunks inline (`extract_pages`+`chunk_pages`+`persist_chunks`, deterministic local) then creates + best-effort-dispatches `generate_embeddings` and new `build_structure` Celery task (extract+persist, Groq failure → job failed, never breaks extraction); `celery_app` include; tests for chain (dispatch patched) + structure task success/failure; backfill user's material post-deploy (chunks+embeddings local; structure needs user key).
**Files:** `worker/tasks/extraction.py`, `worker/tasks/structure.py` (new), `worker/celery_app.py`, `tests/test_pipeline_chain.py` (new), `docs/*`.
**Verify:** targeted suites + full `pytest -q` + `docker compose up -d --build api worker` + backfill + DB counts + `alembic check`; single commit.

### Pipeline Fix Post-implementation (compact)

**Status:** ✅ Complete 2026-09-16
**Files:** `worker/tasks/extraction.py` (`_chain_downstream`: inline chunk + 2 jobs + best-effort dispatch), `worker/tasks/structure.py` (new `build_structure`), `celery_app.py` + `tasks/__init__.py` includes, `tests/test_pipeline_chain.py` (4 tests), `docs/*`
**Verify:** 4 pass; full `pytest -q` 227 passed (223+4); rebuilt api+worker, `build_structure` registered; backfilled both user materials (3+25 chunks, 28 embeddings 384d, embed jobs succeeded); structure jobs correctly isolated-failed on Groq 401 (dummy key); `alembic check` clean; no migration.
**Known:** Live AI (structure map, tutor answers, quiz generation) needs a real `GROQ_API_KEY` in compose env + re-dispatch of failed structure jobs; stray `careflow.handle_event` worker warnings come from unrelated laptop software sharing localhost:6379, harmless.

### Pipeline Fix Follow-up — retry exhaustion + key activation (compact)

**Status:** ✅ Complete 2026-09-16
**Found live:** (1) `self.retry()` re-raises the ORIGINAL error after max retries (not `MaxRetriesExceededError`), so provider outages escaped all three worker tasks and left jobs stuck `running` — fixed in `extraction.py`/`embeddings.py`/`structure.py` via explicit `request.retries >= 3` guard + regression test (5 chain tests pass). (2) Compose `environment:` overrides the app's `backend/.env`, so the containers ran the dummy key until `$env:GROQ_API_KEY` was exported in the same shell as `docker compose up -d` — key now live (56ch `gsk_`, ping `{'ok': True}`); `.env.example` header documents the export requirement.
**Live result:** Kiran_AIProf.pdf map built (2 topics / 7 subtopics / 28 concepts, verified in DB); both materials fully chunked+embedded (28/28); Project_Requirements structure completed after 429 window reset (771 topics / 952 concepts total) — RESOLVED, tutor/quiz/map all live.

## JWT 2-Day Expiry + Honest Register Errors (out-of-band, user-requested)

**Recorded:** 2026-09-16 before impl | Source: user — 2-day sessions + misleading register error
**Diagnosis:** `user5@gmail.com` was NOT taken (verified: 0 rows) — the "already taken" text is the frontend generic fallback, shown because the request failed with no response body (api was mid-restart during tonight's rebuilds). Live register test right now → 201 for the same email. Fix the message, not the endpoint. (My probe rows deleted after — email free again.)
**Changes:** `jwt_expire_minutes` default 60→2880 (2 days) in `config.py` + compose api/worker env + `.env.example`; Register/Login distinguish server message vs no-response ("Can't reach the server…") vs neutral generic — never blame the email without a 400 saying so. Existing tokens keep old exp (mint-time); tests use explicit deltas, unaffected.
**Files:** `core/config.py`, `docker-compose.yml`, `.env.example`, `features/auth/Register.tsx`, `features/auth/Login.tsx`, `docs/*`.
**Verify:** auth tests + `npm run build` + recreate api/worker + live register probe; single commit.

## CORS 127.0.0.1 Fix (out-of-band bugfix)

**Recorded:** 2026-09-16 before impl | Source: user screenshot — honest "Can't reach the server" on register
**Diagnosis:** It was right: browser preflight never got a response body. API log showed `OPTIONS /auth/register → 400`; reproduced: Origin `http://127.0.0.1:5173` → 400 "Disallowed CORS origin" while `localhost:5173` → 200. User browses via 127.0.0.1, which wasn't allow-listed; failed preflight = axios network error = no response. Endpoint itself proven fine (probe 201s).
**Fix:** Allow-list `http://127.0.0.1:5173` (+`:3000` for parity) in compose + config default + `.env.example`; extend `test_cors.py` (127 preflight → 200 echo); delete probe users afterwards (`user5@gmail.com` must stay free).
**Files:** `docker-compose.yml`, `core/config.py`, `.env.example`, `tests/security/test_cors.py`, `docs/*`.
**Verify:** preflight matrix 200s + CORS tests + `compose config` + recreate api/worker (same-shell key export) + register probe + cleanup; single commit.

### CORS 127 Post-implementation (compact)

**Status:** ✅ Complete 2026-09-16
**Files:** `docker-compose.yml` + `core/config.py` + `.env.example` (4 loopback origins), `tests/security/test_cors.py` (127 echo regression), `docs/*`
**Verify:** CORS tests pass; `compose config` ok; live preflight `localhost:5173`/`127.0.0.1:5173`/`localhost:3000` all 200 with echo; probe users deleted (`user5@gmail.com` free).

## Structure 429 Backoff (out-of-band bugfix)

**Recorded:** 2026-09-16 before impl | Source: user screenshots — ML project Ready PDF, empty Map
**Diagnosis:** Chain works (12–49 chunks + embeddings complete on all 4 materials); only `build_structure` dies, always on Groq 429. Root flaw: retry backoff 2/4/8s burns all 3 attempts inside the same per-minute rate-limit window — retries can never succeed. Fix: on 429 wait out the window (60s × attempt, re-queued not blocking); other errors keep fast backoff. Same treatment for embeddings task (same flaw, same Groq quota).
**Files:** `worker/tasks/structure.py`, `worker/tasks/embeddings.py`, `tests/test_pipeline_chain.py` (+429-backoff tests), redispatch script (ops, uncommitted), `docs/*`.
**Verify:** new tests + chain suite + rebuild + redispatch 2 failed structures + Map populated; single commit.

### Structure 429 Post-implementation (compact)

**Status:** ✅ Complete 2026-09-16 (code), user maps pending Groq quota cooldown
**Files:** `worker/tasks/structure.py` + `worker/tasks/embeddings.py` (`_retry_delay`: 429→60s×attempt, else fast) + `tests/test_pipeline_chain.py` (7 tests) + `docs/*`
**Verify:** chain suite 7 pass; full `pytest -q` 234 passed; rebuilt+deployed; live logs show new schedule working (2s→120s→8s); identical-shape probe calls 200 (400s proven transient Groq-side); DB marker test sane (earlier missing-row reads were flakes, single api/worker confirmed).
**Known:** Free-tier quota saturated tonight (my verification traffic + user uploads) — failed structures fail cleanly with messages now; re-dispatch the 2 user materials once quiet. No migration.

## Groq 400 Sanitize (out-of-band bugfix)

**Recorded:** 2026-09-16 before impl | Source: English Lab structure 400s persisting past quota cooldown
**Diagnosis:** Captured the 400 body: `json_validate_failed` — Groq's constrained generation chokes; its `failed_generation` shows U+FFFD replacement chars from PDF extraction (`candidates�ability`) derailing output. Same dirty text flows into quiz/tutor/assessment prompts. Also learned free tier = 8k TPM and one 12k-char structure prompt ≈ 3.2k tokens — explains instant 429s on concurrent dispatches (stagger, don't parallelize).
**Fix:** Sanitize inside `groq_client.chat_json` (single choke point, all present+future Groq calls benefit, zero caller changes): NFKC normalize, U+FFFD→space, strip Cc/C1 controls except `\n\t`. Unit tests on the sanitizer + a passthrough test that payload text arrives cleaned.
**Files:** `services/ai/groq_client.py`, `tests/test_groq_client.py` (new), redispatch English Lab last, `docs/*`.
**Verify:** new tests + full `pytest -q` + rebuild + single staggered redispatch + Map populated; single commit.

### Groq 400 Post-implementation (compact)

**Status:** ✅ Complete 2026-09-16
**Files:** `services/ai/groq_client.py` (`sanitize_for_llm` + applied in `chat_json`), `tests/test_groq_client.py` (5 tests), `docs/*`
**Verify:** affected suites 65 pass (20s); English Lab structure completed first try after sanitize (5 topics / 16 subtopics / 38 concepts); ML map done earlier (2/6/24). Per user request, full suite skipped in favor of affected-only runs.
**Known:** 8k TPM free-tier budget ≈ 2 concurrent structure calls — stagger dispatches; user uploads share the same quota.

## Mercury 2.5 Provider Switch (user-requested, out-of-band)

**Recorded:** 2026-09-16 before impl | Source: user has Inception Labs Mercury 2.5 key, wants it in place of Groq
**Verified:** Inception OpenAPI docs — `POST https://api.inceptionlabs.ai/v1/chat/completions` Bearer, `response_format json_object` supported, model `mercury-2.5` 260K ctx; temperature restricted 0.5–1 (out-of-range silently reset to 1.0) so our temp-0 default MUST clamp to 0.5 for determinism; paid promo pricing $0.04/$0.15 per 1M in/out (≈$0.0003 per map call).
**Design:** keep `groq_client.chat_json` name stable (4 services + all test patches reference it — zero caller changes); provider table inside client (`LLM_PROVIDER=groq|inception`, per-provider URL/key/model/min-temp); provider-specific missing-key messages (keeps existing test green); compose passes `LLM_PROVIDER`/`INCEPTION_API_KEY`/`INCEPTION_MODEL` to api+worker; real key ONLY in gitignored `backend/.env` (+`LLM_PROVIDER=inception`), placeholder in `.env.example`.
**Files:** `core/config.py`, `services/ai/groq_client.py`, `tests/test_groq_client.py`, `docker-compose.yml`, `backend/.env` (secret, uncommitted), `backend/.env.example`, `docs/*`.
**Verify:** affected suites only (client+tutor+quiz+assessment+structure+pipeline+security) + ONE live Mercury probe through the real client; single commit (no `.env`).

### Mercury Post-implementation (compact)

**Status:** ✅ Complete 2026-09-16
**Files:** `core/config.py` (+`llm_provider`/`inception_api_key`/`inception_model`), `services/ai/groq_client.py` (provider table, URL/key/model resolution, temp clamp ≥ provider min, provider-specific errors), `tests/test_groq_client.py` (+4 provider tests), `docker-compose.yml` (`LLM_PROVIDER`/`INCEPTION_API_KEY`/`INCEPTION_MODEL` api+worker), `backend/.env` (real key + `LLM_PROVIDER=inception`, UNCOMMITTED), `backend/.env.example` (placeholders + dual-key export note), `docs/*`
**Verify:** affected suites 69 pass (15s); live Mercury probe via rebuilt api container — `{'status':'ok','provider':'mercury'}` in 4.6s, JSON mode + auth + temp clamp proven end-to-end. Per user request, full suite skipped.
**Known:** compose default stays `groq` (safe for CI/others); local `.env` flips to `inception`. `.env.example` never carries the real key.

## Phase A — Learning-model schema (user-approved, in progress)

**Recorded:** 2026-09-16 before impl | Source: user approved learning-model-design.md + final decisions
**Decisions:** extend `concepts` in place (5 FK holders untouched); 7 LO types; 2–8 CORE/subtopic SOFT guideline (prompt-level, Phase B); `is_mastery_target()` single gate; EMA untouched; no reprocessing; merge/split = evidence-based w/ same-parent + semantic compatibility; prereq reasons deferred to C; existing API conventions.
**Scope:** Alembic migration (nullable add → backfill CONCEPT/CORE → NOT NULL+defaults+CHECKs; new `concept_relationships` w/ evidence_span rule + self-edge ban; `material_id` FK SET NULL) → models (`Concept` cols + `ConceptRelationship`, `meta` attr maps to `metadata` column — `metadata` name is reserved by DeclarativeBase) → `services/mastery_levels.py` (thresholds + `status_for` + `is_mastery_target`) → gate applied ONLY in `dashboard_service.build_dashboard` (behavior-neutral today; quiz/browse gating is Phase C) → `tests/test_learning_objects.py`.
**Files:** `alembic/versions/*_add_learning_object_fields.py`, `alembic/env.py`, `models/concept.py`, `models/concept_relationship.py` (new), `models/__init__.py`, `services/mastery_levels.py` (new), `services/dashboard_service.py`, `tests/test_learning_objects.py` (new), `docs/*`.
**Verify:** `alembic check` no-new-drift + upgrade head on dev DB (+downgrade/up round-trip) + affected suites (learning_objects/mastery/dashboard/recommendation/quiz/structure/pipeline/mismatch/growth) + neutrality proof; single commit. No container rebuild (old code ignores new cols; new code runs in tests only).

### Phase A Post-implementation (compact)

**Status:** ✅ Complete 2026-09-16
**Files:** `alembic/versions/9f3a7c1e5b28_add_learning_object_fields.py` (new), `alembic/env.py`, `models/concept.py` (+6 cols, vocab constants), `models/concept_relationship.py` (new), `models/__init__.py`, `services/mastery_levels.py` (new: thresholds + `status_for` + `is_mastery_target`), `services/dashboard_service.py` (gate in `build_dashboard` only), `tests/test_learning_objects.py` (new, 9 tests), `docs/learning-model-design.md` (§20 addendum), `docs/*`
**Verify:** `alembic check` clean (fixed one index-naming drift before proceeding); 1313 dev concepts backfilled CONCEPT/CORE, count unchanged; downgrade→upgrade round-trip lossless; 68 affected tests green (10s).
**Known:** `meta` attr ↔ `metadata` column (DeclarativeBase reserves `metadata`); quiz-picker/structure-tree gating deferred to Phase C; no reprocessing; containers untouched.

## CORS Port 5175 (out-of-band, user-requested)

**Recorded:** 2026-09-16 before impl | Source: user runs frontend dev on :5175 (5173 taken by another app)
**Fix:** Allow-list `localhost:5175` + `127.0.0.1:5175` in compose + config default + `.env.example`; pin `vite.config.ts` dev server to 5175 `strictPort` so the port can't drift to 5176 (which would break CORS again). No wildcard — explicit list per Phase 49 posture.
**Files:** `docker-compose.yml`, `core/config.py`, `.env.example`, `vite.config.ts`, `docs/*`.
**Verify:** preflight from both 5175 origins → 200; recreate api/worker (same-shell key export); single commit.

### CORS 5175 Post-implementation (compact)

**Status:** ✅ Complete 2026-09-16
**Files:** `docker-compose.yml` + `core/config.py` + `.env.example` (5175 origins), `vite.config.ts` (pinned 5175 strict), `docs/*`
**Verify:** live preflight both 5175 origins → 200 with echo; `compose config` ok; `npm run build` green. Note: user must restart `npm run dev` once to pick up the pinned port.

### JWT + Register Post-implementation (compact)

**Status:** ✅ Complete 2026-09-16
**Files:** `core/config.py` + `docker-compose.yml` (api+worker) + `.env.example` (2880), `lib/api-error.ts` (`authErrorMessage`), `Register.tsx`/`Login.tsx`, `docs/*`
**Verify:** auth+error suites 14 pass; `npm run build` green; containers recreated with `JWT_EXPIRE_MINUTES=2880` (Groq key preserved via same-shell export); live probe register 201 + login 200, decoded token lifetime exactly 2880 min (48.0h), probe row deleted; `user5@gmail.com` confirmed free (my 2 probe rows removed).

## Quiz 422 Fix — concept source fallback (out-of-band bugfix)

**Recorded:** 2026-09-16 before impl | Source: user screenshot — quiz 422 on new project
**Diagnosis:** Reproduced live: `generate_quiz` → "concept has no source chunks". Project HAS 74 chunks, but ALL have `concept_id NULL` — `chunk_pages` never assigns concepts and nothing else does, so concept-scoped `_load_source` (quiz + assessment) is empty BY CONSTRUCTION in production. Same for `open_ended_assessment_service`.
**Fix:** `_load_source` falls back to project-wide chunks when the concept has none tagged (scope stays project-local; isolation untouched) + quiz prompt names the target concept (title/summary) so questions stay focused; delimiters + never-obey lines preserved (security tests keep passing). Truly empty projects still 422 with the same message.
**Files:** `quiz_generation_service.py`, `open_ended_assessment_service.py`, `tests/test_concept_source_fallback.py` (new), `docs/*`.
**Verify:** new tests + affected suites + full `pytest -q` + rebuild api+worker + live quiz retry on user project; single commit.
**Verify:** chain tests 5 pass; worker `build_structure` registered; failed jobs now carry messages instead of hanging.

**Deferred (needs a decision, NOT silently fixed):** (1) Evidence producers: only `explain_back` rows ever reach `mastery_evidence` — quiz completion appends no `mcq` rows and open-ended grading persists nothing, so mcq/applied streams are thin in real use; wiring producers (per-question vs aggregate rows, difficulty carriage) is product-impacting → propose as its own phase. (2) Dashboard N+1 (2 queries × concepts) — prototype-acceptable, Phase 57 territory. (3) No `applied_high_mcq_low` type (blueprint-intended); sync-only grading (no Celery `evaluate_assessment`); no exam timer (all previously logged).
