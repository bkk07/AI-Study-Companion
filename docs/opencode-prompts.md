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

### Post-implementation record (Phase 03 — to be filled after verification)

**Status:** _pending — pre-implementation record only_

**Files changed:** _to be updated after implementation_

**Verification result:** _to be updated after implementation_

**Notes:** _to be updated after implementation_
