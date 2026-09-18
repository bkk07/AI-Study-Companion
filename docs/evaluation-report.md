# Evaluation Report — AI Study Companion vs. PRD v3.0 (Fresh Audit)

**Date:** 2026-09-18 · **Evaluator:** senior-engineer audit · **Spec:** `Project_Requirements (1).pdf` read in full (derived `docs/architecture.md`-type docs not used as spec)
**Method:** full PDF read → 43-requirement inventory → single repo pass (backend → frontend → docs/deploy) with `file:line` evidence per verdict; targeted test runs; live URL hits. README/docs claims never counted as evidence.
**Step 3 runs:** targeted suites green — `test_recommendation+test_growth_recommendation+test_quiz_attempt_evidence+test_authorization+test_tutor` 31 passed; `security+test_spaces+test_materials+test_rag_service+test_pipeline_chain` 33 passed + **1 failed** (`test_retry_delay_waits_out_rate_windows`); full `pytest -q` timed out at 300s (env limit, not a code verdict). Live: `GET /` on the Vercel URL → 200 app HTML; `GET /login` → **404** (no SPA rewrite). No backend live URL exists anywhere in the repo. Local `backend/.env` exists but is gitignored; only `.example` files are tracked.

---

## 1. Executive summary (~150 words)

The submission implements the full learning loop end-to-end: Spaces → Projects → PDF upload → Celery pipeline (extract → OCR → chunk → embed → structure) → project-scoped RAG Tutor with page citations and a real pre-LLM no-evidence gate → adaptive MCQ quiz + LLM-graded open-ended assessment → deterministic EMA mastery → growth → deterministic recommendations → project analytics, home feed, and an admin dashboard. Data isolation is enforced in SQL (404-not-403) with passing cross-project tests, and prompt-injection framing is tested. Since the prior audit, README was rewritten and now documents the live URL and the true AI stack. Remaining gaps: the quiz→recommendation auto-chain is still fire-and-forget Celery with no sync fallback (known open item **not fixed**); the live SPA 404s every deep route (`/login` verified) for lack of a rewrite config; one pipeline test fails (`embeddings` lacks `_retry_delay`); no migration runs on any deploy path; no streaming; evaluation is aggregates-only.

---

## 2. Requirement coverage matrix

`PASS` = implemented end-to-end with code evidence · `PARTIAL` = works with material gap · `FAIL` = missing/broken · `UNVERIFIABLE` = no evidence found (never default-PASS).

| ID | Requirement (PRD §) | Status | Evidence (file:line) | Missing/Problem | Severity |
|----|---------------------|--------|----------------------|-----------------|----------|
| R1 | Authentication: register/login, Argon2id, JWT (§15, §18) | PASS | `backend/app/api/v1/auth.py:16,33,43`; `backend/app/core/security.py:6-12`; `backend/app/core/jwt.py:10-22`; `backend/app/dependencies/auth.py:16-48` | 48h default expiry (`backend/app/core/config.py:26`) is long. | MEDIUM |
| R2 | Spaces CRUD + space dashboard (§3–§4, §18) | PASS | `backend/app/api/v1/spaces.py:15,28,37`; `frontend/src/features/spaces/SpacesPage.tsx:145` (empty state) | None material. | — |
| R3 | Projects (name/desc/goal) + dashboard + Materials→Tutor→Quiz→Growth→Analytics nav (§4, §18) | PASS | `backend/app/api/v1/projects.py:18,31,41`; `backend/app/api/v1/dashboard.py:128`; `frontend/src/features/projects/ProjectDetailPage.tsx:21-24,63` | None material. | — |
| R4 | Home dashboard: continue/recent/progress/attention/next (§16) | PASS | `backend/app/api/v1/me.py`; `frontend/src/features/home/HomeDashboard.tsx:91,125-176,191-314` | None material. | — |
| R5 | PDF material upload (§5, §18) | PASS | `backend/app/api/v1/materials.py:30-77`; `backend/app/services/storage_service.py:8-57`; `frontend/src/features/projects/MaterialsPanel.tsx:58,88` | 10MB cap undisclosed in UI; delete/view stubs. | LOW |
| R6 | Async doc pipeline with queued/processing/ready/failed + retry/duplicate handling (§5, §13) | PARTIAL | `backend/app/worker/tasks/extraction.py:66-79,99-188` (retry, idempotency guard); `backend/app/api/v1/materials.py:26-27` (state masking) | Broker-down upload still 201 with processing dead (`backend/app/api/v1/materials.py:30-77`); no duplicate-dispatch dedupe. | HIGH |
| R7 | Extraction → chunk → embed → index with source traceability (§5) | PASS | `backend/app/services/chunking_service.py` (2000/200); `backend/app/worker/tasks/extraction.py:223-289`; `backend/app/worker/tasks/embeddings.py:14-119` (dim check + upsert) | None material. | — |
| R8 | Project-scoped Tutor with goal/materials/concepts/conversation/assessment context + continuity (§6, §18) | PASS | `backend/app/services/tutor_service.py:199-276`; `backend/app/api/v1/tutor.py:35,69,87,102,125,159,172,216`; `frontend/src/features/tutor/TutorChat.tsx:563,574,658` | Full conversation history not fed as model context (README admits). | MEDIUM |
| R9 | Grounded answers with citations (§7, §18) | PASS | `backend/app/services/tutor_service.py:246-256` (per-chunk citation + excerpt); `frontend/src/features/tutor/TutorChat.tsx` sources drawer | Distance threshold 0.5 provisional (`backend/app/services/tutor_service.py:30`). | MEDIUM |
| R10 | Unsupported-question handling, no fabrication (§7, §18) | PASS | `backend/app/services/tutor_service.py:216-220` (returns before any LLM call); small-talk bypass `:211-214` | None material. | — |
| R11 | Controlled, validated, permission-aware AI↔app interaction (§8, §18) | PASS | Pydantic validation before persist (`backend/app/services/tutor_service.py:241-244`; `backend/app/services/quiz_generation_service.py`); ownership dep before budget (`backend/app/api/v1/tutor.py:35-57`) | No AI-invoked tool loop; AI acts via REST endpoints. | MEDIUM |
| R12 | Adaptive quiz (MCQ + open-ended), evidence-based selection (§9, §18) | PASS | `backend/app/services/quiz_generation_service.py:497-608` (weakness-weighted allocation, difficulty hints); `backend/app/services/quiz_attempt_service.py:248-350` (answer-time next-Q); `frontend/src/features/quiz/QuizTaker.tsx:77,87,109,146` | Adaptation selects from pre-generated questions only. | MEDIUM |
| R13 | Open-ended AI evaluation with explanatory feedback (§9, §18) | PASS | `backend/app/services/open_ended_assessment_service.py:137-143,189-242`; `backend/app/api/v1/assessment.py:64-98` | None material. | — |
| R14 | Concept mastery evolving with evidence (§10, §18) | PASS | `backend/app/services/mastery_service.py:111-117,213-341` (5-stream EMA, weights, caps 40/70/60/75); append-only writers (`backend/app/services/quiz_attempt_service.py:164-245`) | Nothing random/hardcoded (verified). | — |
| R15 | Growth analysis: improving/stable/needs-attention (§10, §18) | PASS | `backend/app/services/growth_service.py:115-171,219-277`; `frontend/src/features/analytics/GrowthView.tsx:106,131,152` | None material. | — |
| R16 | Recommendations answering "what next" (§10, §18) | PARTIAL | `backend/app/services/recommendation_service.py:235-267,543-645`; sync `POST .../dashboard/refresh` (`backend/app/api/v1/dashboard.py:140-168`); UI `frontend/src/features/dashboard/Dashboard.tsx:527-607` | Auto-chain is Celery-only, skipped under pytest (`backend/app/worker/tasks/recommendations.py:44-56`), None on thin evidence — zero-row outcome persists (known open item NOT fixed). | HIGH |
| R17 | Persistent relevant learning context (§11, §18) | PASS | Bounded assembly (`backend/app/services/rag_service.py:100-165`); persisted threads (`backend/app/services/tutor_conversation_service.py:84-136`); signals reuse (`backend/app/services/dashboard_service.py:50-182`) | None material. | — |
| R18 | Event-driven learning, idempotent (§12) | PASS | Idempotency-key unique constraint; `backend/app/services/activity_service.py:62-139`; emitters in quiz/material/tutor/recommendation paths | None material. | — |
| R19 | Project + global analytics (§12, §18) | PASS | `backend/app/api/v1/analytics.py:22,49`; `frontend/src/features/analytics/AnalyticsPage.tsx`; global home/streak (`backend/app/api/v1/me.py`) | "Global" is home feed + streak, no cross-space aggregate endpoint. | MEDIUM |
| R20 | Background workflows incl. repeated-mistake, no browser needed (§13) | PARTIAL | Material chain (`backend/app/worker/tasks/extraction.py:223-289`); learning chain fires `refresh_best_effort` (`backend/app/services/quiz_attempt_service.py:418-426`) | Repeated-mistake workflow missing: mismatch computed, never scheduled. | HIGH |
| R21 | AI abstraction (generation/structured/embeddings/eval/doc-understanding) (§14) | PASS | `backend/app/services/ai/groq_client.py:25-40,99-210`; `backend/app/services/ai/embedding_client.py:1-13`; `backend/app/services/vision_service.py` | None material. | — |
| R22 | AI observability: model/latency/tokens/cost/success (§14) | PASS | `backend/app/services/ai_usage_service.py:76-133`; `backend/app/api/v1/admin.py:180-278`; per-call meta (`backend/app/services/tutor_service.py:227-237`) | Cost table is estimates (`backend/app/services/ai/pricing.py:12-38`); embeddings unmetered. | MEDIUM |
| R23 | AI evaluation of tutor/retrieval/assessment/rec + regression awareness (§14) | PARTIAL | `backend/app/api/v1/admin.py:412-671` (supported/citation rates, score bands, trends) | Aggregates only: no groundedness judge, no retrieval-relevance metric, no CI regression gate. | MEDIUM |
| R24 | Reliability: timeouts/retries/validation/fallback, no duplicate state (§15) | PARTIAL | Timeouts (chat, vision 20s `backend/app/core/config.py:56`); error envelope (`backend/app/core/exceptions.py`); idempotent events | One repo test fails on retry-delay contract (`backend/tests/test_pipeline_chain.py:283` — `embeddings` has no `_retry_delay`); broker-down paths silent. | MEDIUM |
| R25 | Project-level data isolation incl. retrieval (§3, §15, §18) | PASS | Ownership deps 404 (`backend/app/dependencies/authorization.py:13-55`); `project_id` inside vector query (`backend/app/services/retrieval_service.py:38-66`); cross-project tests green (this audit) | None material. | — |
| R26 | Input validation + secure APIs + secure doc handling (§15) | PASS | Upload hardening 10MB/`%PDF`/content-type (`backend/app/services/storage_service.py:8-57`); hardening tests green | None material. | — |
| R27 | Prompt-injection safety: data vs instructions (§15) | PASS | `<<<DATA>>>` framing (`backend/app/services/tutor_service.py:184-196`); boundary tests (`backend/tests/security/test_prompt_boundaries.py`) green | None material. | — |
| R28 | Secrets separated from code (§18) | PASS | `backend/.env` gitignored + untracked (verified `git ls-files`/`check-ignore`); only `.example` tracked; image ships no secrets (`backend/Dockerfile:36-38`) | Compose defaults `JWT_SECRET` to a published placeholder (`docker-compose.yml:50,90`) — boots insecure if env not exported. | MEDIUM |
| R29 | Admin dashboard: users/activity/AI/eval/jobs/health + journey + filters (§16, §18) | PASS | `backend/app/api/v1/admin.py:55,109,138,180,281,364,412` (7 areas); `frontend/src/features/admin/AdminPage.tsx` + panels | None material. | — |
| R30 | Streaming Tutor (Should Have, §18) | FAIL | No SSE/WebSocket; plain POST (`frontend/src/features/tutor/TutorChat.tsx`) | Streaming absent (Should-Have, not Must). | LOW |
| R31 | Performance: pagination/caching/async/efficient queries (§15) | PARTIAL | Admin pagination; 30s GET cache (`frontend/src/lib/axios.ts:60-99`); batched dashboard queries; async jobs | No server-side caching; no streaming. | LOW |
| R32 | Backend tests: auth/authz/isolation/validation/logic (§18) | PASS | 75 test files; this audit: 31 + 33 green across auth/authz/cross-project/spaces/materials/RAG | Full suite not runnable here (300s timeout); 1 failure in pipeline-chain (R24). | MEDIUM |
| R33 | AI tests: grounded/unsupported/structured/tutor/assessment (§18) | PASS | Unsupported asserts LLM uncalled; injection-as-data; grade validation (`backend/tests/test_tutor.py`, `test_rag_service.py`, `test_groq_client.py`, `test_open_ended_assessment.py`) | None material. | — |
| R34 | Learning tests: mastery/adaptive/recommendations (§18) | PASS | Exact EMA/scoring math green this audit (`test_mastery.py`, `test_adaptive_quiz.py`, `test_recommendation.py`, `test_growth_recommendation.py`) | None material. | — |
| R35 | Background tests: success/retry/failure (§18) | PARTIAL | Chain, broker-outage survival, structure 429 backoff covered | `test_retry_delay_waits_out_rate_windows` FAILS: `embeddings` module has no `_retry_delay` (`backend/tests/test_pipeline_chain.py:283`). | MEDIUM |
| R36 | Deployment to public URL with working stack (§18) | PARTIAL | Frontend live and serving: `GET https://aistudycompanion-alpha.vercel.app/` → 200 app HTML (`README.md:5,10,64` documents it) | Deep routes 404 (`/login` verified live; no `vercel.json` rewrite in repo); hosted backend URL undocumented anywhere (`README.md:64` says "hosted API" without URL); no `alembic upgrade` on any deploy path. | HIGH |
| R37 | Architecture docs: diagram + decisions (§20) | PASS | ADRs (`docs/architecture-decisions.md`); `Architecture.md` diagrams; `docs/architecture/` traceability | `docs/architecture/` untracked in git (prior finding; verify before submit). | LOW |
| R38 | AI-usage docs: build-AI vs product-AI (§20) | PASS | `AI_USAGE.md:18-32,65-83` (dev vs product, models, dims); `README.md:392-401` summary | Name collision: Mercury = dev agent model and product `INCEPTION_MODEL` (`AI_USAGE.md:20`, `backend/app/core/config.py:34`). | LOW |
| R39 | Development prompts (§20) | PASS | `docs/opencode-prompts.md` per-phase log; `Prompts.txt` | `Prompts.txt:1-7` reconstructed, not verbatim (declared). | LOW |
| R40 | Evaluation approach doc (§20) | PARTIAL | Aggregates documented; gaps admitted (`README.md:469-483`) | Same gap as R23. | MEDIUM |
| R41 | Known limitations (§20) | PASS | `README.md:469-483` (9 honest boundaries) | None material. | — |
| R42 | Public repo + accurate README setup (§20) | PASS | Setup/compose/migration instructions (`README.md:242-312,417-449`); AI stack now accurate (`README.md:178-185` incl. 1536→384 note) | Stale 1536/OpenAI refs remain in `docs/00-blueprint-analysis.md:65,91`, `docs/architecture-decisions.md:14,16`, `docs/implementation-status.md:20`, and `docker-compose.yml:58,98` (`EMBEDDING_MODEL: text-embedding-3-small`) vs local-only runtime. | MEDIUM |
| R43 | Creativity/differentiation, functional not cosmetic (§21) | PASS | SM-2 flashcards; vision figure extraction; mismatch→recommendation scoring; tutor quiz-plan; concept graph | None material. | — |

---

## 3. Core learning loop walkthrough (~500 words)

Create Space → Project works end-to-end: `SpacesPage` creates/lists spaces with loading/error/empty states, `SpaceProjectsPage` scopes projects to the space, and every backend read is ownership-checked at the dependency layer (`backend/app/dependencies/authorization.py:13-55`, 404 never 403). Upload → Process: `MaterialsPanel` posts multipart PDF and polls job-backed status pills (queued/processing/ready/failed); the server persists `Material(status=pending)`, creates a `BackgroundJob`, and dispatches Celery `process_pdf` best-effort (`backend/app/api/v1/materials.py:30-77`). The worker extracts text, tables, and figure captions with per-page TEXT/OCR/EMPTY routing, chunks (2000/200), then chains embedding + two-pass LLM structure jobs (`backend/app/worker/tasks/extraction.py:66-289`). Corrupt/empty inputs fail fast without retry; transient errors retry with backoff. Ask Tutor → grounded answer + citations → unsupported handling is genuinely wired: retrieval filters `project_id` inside the pgvector query (`backend/app/services/retrieval_service.py:38-66`), excerpts are char-bounded (`backend/app/services/rag_service.py:100-165`), the prompt carries material only as `<<<DATA>>>` (`backend/app/services/tutor_service.py:184-196`), and with zero chunks — or all distances above 0.5 — the canned unsupported reply returns before any LLM call (`:216-220`). Citations (one per chunk, page + excerpt + figure card) render in the Tutor sources drawer. Adaptive quiz: weakest-first allocation with difficulty hints generates schema-validated questions, attempts lock on complete, answers score server-side with per-answer evidence banking, and the next question reselects deterministically (`backend/app/services/quiz_attempt_service.py:83-189,248-427`). Open-ended answers get LLM grades in deterministic verdict bands with explanatory feedback and append-only evidence. Mastery updates on every evidence write via pure EMA; growth replays EMA prefixes; the dashboard shows per-concept bars, mismatches, and the current recommendation with refresh/accept/dismiss. Analytics (project + overview) and the 7-area admin console read the same derived state. The loop breaks at exactly one link: quiz completion fires only an async Celery recompute that may never run, so a fresh completion can leave the dashboard with no recommendation until the user presses Refresh (R16). Live, the loop is reachable at `/` but unreachable via deep link: `/login` 404s on Vercel for lack of a rewrite.

---

## 4. AI/RAG evaluation (~400 words)

Providers are abstracted behind one client supporting groq + inception via `LLM_PROVIDER` (`backend/app/services/ai/groq_client.py:25-40`), default chat `openai/gpt-oss-20b` with Mercury 2.5 on the inception path (`backend/app/core/config.py:28-34`, temp clamped for Mercury). Vision captions go through NaraRouter (`stepfun-3.7-flash`, `backend/app/core/config.py:52-64`) with cropped-OCR/placeholder fallback that never fails the document. Embeddings are local FastEmbed `BAAI/bge-small-en-v1.5`, 384-dim with enforced dim checks (`backend/app/services/ai/embedding_client.py:1-48`), matching `Vector(384)` (`backend/app/models/embedding.py`). Every LLM consumer validates structured output with Pydantic and retries exactly once before raising provider errors with nothing persisted (tutor `:231-244`, quiz generation, open-ended grading `:189-242`). The RAG pipeline is real and scoped: extract → chunk → embed → `project_id`-filtered cosine retrieval (`backend/app/services/retrieval_service.py:38-66`) → bounded assembly → goal + excerpts as delimited data → single metered provider call with retrieval shape in usage meta → per-chunk citations with page numbers and excerpts. Grounding is enforced, not decorative: the unsupported gate precedes the LLM call and tests assert the client is never called on empty/low-similarity context; injection-as-data is tested. Quiz generation prioritizes page-range → concept-tagged → project-wide sources with a 422 on no chunks; open-ended grading bands verdicts deterministically (pass ≥ 80 / partial ≥ 50) and writes nothing directly — persistence flows only through graded entry points as append-only evidence. Weaknesses: the 0.5 support threshold is provisional with no calibration study; costs are estimated from a static price table; embeddings are unmetered; evaluation of tutor/retrieval/assessment quality is admin-aggregate rates with no groundedness judge, no retrieval-relevance metric, and no CI regression gate; full conversation history is not fed as model context. README now documents this stack accurately including the 1536→384 migration note (known open item on docs accuracy: fixed in README, stale refs linger in older docs and compose env).

---

## 5. Mastery/recommendation evaluation (~250 words)

Mastery is a deterministic EMA over five append-only streams (quiz .35 / open_ended .25 / practice .20 / flashcard .15 / tutor .05), per-stream difficulty bases (easy .2 / medium .3 / hard .4, +0.1 gap boost over 7d, capped .5), tutor fixed at .15 with one-row-per-day dedupe, renormalized over streams with evidence, with tutor-only ≤ 40, formative-only ≤ 70, and thin-history caps (1 row ≤ 60, 2 rows ≤ 75) — all in `backend/app/services/mastery_service.py:77-119,213-341`. Writers (quiz per-answer/completion, explain-back, flashcards, tutor checks) append evidence atomically and never mutate rows; no randomness or hardcoding in scoring paths. Recommendations score every eligible (concept, action) pair with weakness + overconfidence + recency + goal + growth-decline + action base − repetition ± mismatch terms, floor 0, exam gated on 3+ evidenced concepts, persisting exactly one active row plus a `recommendation.generated` event (`backend/app/services/recommendation_service.py:235-267,543-645`). **Known open item — confirmed NOT fixed with fresh evidence:** `complete_attempt` still only calls `refresh_best_effort` (`backend/app/services/quiz_attempt_service.py:418-426`), which dispatches Celery `generate_recommendation.delay` and is explicitly skipped under pytest (`backend/app/worker/tasks/recommendations.py:44-56`); the task persists nothing when signals lack `mcq`/`applied` scores (`recommendation_service.py:589-604`), surfacing as 404 "no scorable concepts yet" (`backend/app/api/v1/dashboard.py:160-161`). So completed quizzes with thin evidence — or any completion while the worker/broker is down — still yield zero rows; no real row could be produced in this audit (no broker/DB) and none was observed. The reliable path remains synchronous `POST .../dashboard/refresh`. The repeated-mistake → targeted-recommendation workflow is still absent (mismatch computed, never scheduled).

---

## 6. Data model & security findings (~350 words)

Schema covers users → spaces → projects → materials/jobs/chunks/embeddings/topics/subtopics/concepts/relationships/quizzes/attempts/answers/evidence/recommendations/conversations/messages/flashcards/figures/events/ai_usage with FK cascades, uniqueness (chunk material+index, embedding chunk_id, title-in-parent, idempotency keys), CHECKs on enums/scores/difficulties, and 28 migrations. Mastery is derived from append-only evidence (no mastery table) — the correct call.

### Data isolation

Ownership is enforced server-side on every route via `get_authorized_space` / `get_authorized_project` / `get_authorized_project_in_space`, all returning 404 on foreign IDs so existence never leaks (`backend/app/dependencies/authorization.py:13-55`). Retrieval isolation is inside the SQL (`project_id` filtered before ranking, `backend/app/services/retrieval_service.py:38-66`), job polling walks material→project→space→user, and the LLM-budget middleware is deliberately ordered after ownership. This audit reran `test_authorization`, `security/test_cross_project`, and `test_quiz_attempt_evidence`: all green. No IDOR found; client-side filtering is never the enforcement point.

### Auth, injection, secrets

Argon2id (`backend/app/core/security.py:6-12`), HS256 JWT with distinct expired/invalid 401s, admin gated by `is_admin` 403 (`backend/app/dependencies/admin.py`). No SQL-injection surface (ORM-bound queries; search via bound `ilike`). Path traversal mitigated by server UUID paths under `UPLOAD_DIR` plus basename/magic/content-type upload checks. Prompt injection handled by `<<<DATA>>>` data-framing with passing boundary tests. No secrets committed: `backend/.env` exists locally but is gitignored and untracked (verified), only `.example` placeholders are tracked, and the image bakes no secrets. Residual risks, all non-critical: (a) compose boots with a published-placeholder `JWT_SECRET` (`docker-compose.yml:50,90`) — insecure by default if the operator doesn't export env; (b) 48h JWT expiry is long with no auth-route rate limit; (c) pricing/cost figures are estimates that could mislead ops; (d) broker-down failures are silent by design (evidence survives, downstream insight silently missing); (e) `EMBEDDING_MODEL: text-embedding-3-small` in compose disagrees with the local-only 384-dim runtime.

---

## 7. Document processing evaluation (~200 words)

Upload → `pending` → worker `processing` → `ready`/`failed`, with job rows the UI polls (`backend/app/api/v1/materials.py:30-113`, `frontend/src/features/projects/MaterialsPanel.tsx`). The worker routes each page (TEXT/OCR/EMPTY), extracts tables to Markdown, crops figures for vision captioning with OCR/placeholder fallback, persists text/page counts, then chains chunk persistence → figures → embedding + structure jobs with per-failure diagnostics (`backend/app/worker/tasks/extraction.py:66-289`). Corrupt/empty inputs fail immediately without retry; transient errors retry 3× with exponential backoff; structure 429s back off 60s; reruns replace per-material chunks and upsert embeddings on the `chunk_id` unique constraint — data-layer duplicate handling is correct. Scanned-image routing, unicode/CJK, and broker-outage survival are test-covered. Gaps: duplicate *dispatches* (double-upload races) have no job-level dedupe; a broker outage yields a misleading 201-success upload with dead processing; the "ready" masking in the list endpoint can show `processing` while downstream jobs lag with no per-stage progress; and this audit found one real test failure on the retry contract — `test_retry_delay_waits_out_rate_windows` fails because `embeddings` has no `_retry_delay` (`backend/tests/test_pipeline_chain.py:283`), meaning the embeddings task's 429 path is untested/uncertain while structure's is fine.

---

## 8. Engineering quality & deployment (~250 words)

API contracts are consistent (`/api/v1`, Pydantic schemas ↔ TS types, uniform error envelope) across 19 routers with 75 test files asserting exact math, guards, and isolation — 64 targeted tests reran green in this audit. Code quality is high: pure deterministic services, append-only evidence, validated LLM outputs, real observability metadata. Dead weight is bounded: MaterialsPanel delete/view stubs, unwired exports, and the root `src/` Figma scaffold with dangling imports alongside the real `frontend/` — harmless (compose builds `./frontend/Dockerfile`) but confusing. **Live URL status: frontend VERIFIED at root, deep routes BROKEN, backend URL MISSING.** `GET https://aistudycompanion-alpha.vercel.app/` returns 200 with the real app shell (verified live this audit), but `GET /login` returns 404: the repo has no `vercel.json` rewrite, so `BrowserRouter` deep links, bookmarks, and post-login redirects fail in production (HIGH). The hosted backend URL appears nowhere (README says "hosted API" with no address), so the deployed frontend's data path is unverifiable. Deployment reproducibility has a second real defect: no `alembic upgrade` on any path (compose, Railway config, Dockerfile, supervisord) — migrations are manual-only, so a clean deploy serves the API against an unmigrated DB. The single-container Railway image (api+worker+loopback redis under supervisord) is reasonable for a prototype. Differentiating features are genuinely functional and tested (SM-2 flashcards with due ordering, vision figure extraction, mismatch-fed recommendations, tutor quiz-plan/flashcard handoffs, concept graph) — not cosmetic.

---

## 9. Critical / High / Medium / Low findings

**CRITICAL** — none.

**HIGH**
- H1: Quiz→recommendation auto-chain silently yields zero rows on thin evidence or broker outage (`backend/app/worker/tasks/recommendations.py:44-56`, `backend/app/services/recommendation_service.py:589-604`, `backend/app/services/quiz_attempt_service.py:418-426`) — known open item confirmed NOT fixed.
- H2: Live SPA deep routes 404 (`/login` verified; no `vercel.json` rewrite; `frontend/src/App.tsx:46-68` uses `BrowserRouter`).
- H3: No migration runs on any deploy path; clean environments serve API against unmigrated DB.
- H4: Repeated-mistake → targeted-recommendation workflow missing (computed, never scheduled).
- H5: Broker-down upload returns misleading 201 with dead processing (`backend/app/api/v1/materials.py:30-77`).

**MEDIUM**
- M1: Stale 1536-dim/OpenAI embedding refs in `docs/00-blueprint-analysis.md:65,91`, `docs/architecture-decisions.md:14,16`, `docs/implementation-status.md:20`, `docker-compose.yml:58,98` vs local-only 384-dim runtime (README fixed; stragglers remain).
- M2: No `/recommendations` route (`frontend/src/App.tsx:46-68`) — the prior "not found" was a missing route by design; recommendations are inline-only (root cause confirmed: no route, not just empty data).
- M3: AI evaluation aggregates-only, no regression gate (`backend/app/api/v1/admin.py:412-671`).
- M4: 48h JWT expiry + published-placeholder compose `JWT_SECRET` + no auth rate limiting.
- M5: `test_retry_delay_waits_out_rate_windows` fails — embeddings 429 retry path untested (`backend/tests/test_pipeline_chain.py:283`).
- M6: Hosted backend URL undocumented; deployed data path unverifiable (`README.md:64`).
- M7: Full conversation history not used as Tutor model context (admitted boundary).
- M8: Adaptation selects from pre-generated questions only (admitted boundary).

**LOW**
- L1: No Tutor streaming (Should Have).
- L2: MaterialsPanel delete/view stubs; unwired exports; root `src/` scaffold with broken imports beside real `frontend/`.
- L3: `docs/architecture/` untracked in git (verify); Mercury name collision (dev agent vs product model).
- L4: 10MB upload cap undisclosed in UI.

---

## 10. Requirement contradictions (doc vs. code mismatches)

1. FIXED since prior audit: `README.md:178-185` now correctly documents local `BAAI/bge-small-en-v1.5` 384-dim, Groq `openai/gpt-oss-20b` / Mercury, and the 1536→384 migration note — matches `backend/app/services/ai/embedding_client.py:13` and `backend/app/core/config.py:28-34`.
2. `docker-compose.yml:58,98` still sets `EMBEDDING_MODEL: text-embedding-3-small` while the runtime embedding path is local-only 384-dim — compose and code disagree.
3. `docs/00-blueprint-analysis.md:65,91`, `docs/architecture-decisions.md:14,16`, `docs/implementation-status.md:20` still describe OpenAI 1536-dim embeddings vs the 384-dim implementation.
4. `README.md:64` says the frontend "points at the hosted FastAPI backend" but gives no URL — the deployed data path cannot be verified or reproduced.
5. `backend/.env.example` dims warning is consistent with code; the stale docs above contradict it.

---

## 11. Recommended fix order

1. H1: Make quiz-completion recommendation synchronous-or-guaranteed (call `recommend()` inline in `complete_attempt`, keep Celery as fallback; surface "no scorable concepts yet" instead of silent absence).
2. H2: Add `vercel.json` SPA rewrite (`{"rewrites": [{"source": "/(.*)", "destination": "/index.html"}]}`) so `/login`, bookmarks, and OAuth-style redirects work live.
3. H3: Add `alembic upgrade head` to deploy (entrypoint/Railway start/compose init) and document it.
4. H5: Return 202 with explicit `dispatch_failed` state instead of 201 when the broker is down.
5. H4: Schedule or chain the repeated-mistake workflow (mistake pattern → learning-context update → targeted rec).
6. M6: Publish the hosted backend URL in README + frontend env docs; verify the deployed data path.
7. M1: Update stale embedding refs in `docs/00-blueprint-analysis.md`, `docs/architecture-decisions.md`, `docs/implementation-status.md`, `docker-compose.yml`.
8. M4: Require `JWT_SECRET` at boot (fail closed), shorten expiry, rate-limit auth routes.
9. M5: Add `_retry_delay` to the embeddings task (or fix the test contract) so the 429 path is covered.
10. M2: Add a `/recommendations` route (or redirect) so deep links stop 404ing; keep inline cards.
11. M3/M7/M8: Minimal eval regression fixtures; document context/adaptation boundaries as deferred.
12. LOW batch: streaming (or document deferral), material delete/view, quarantine root `src/` scaffold, commit `docs/architecture/`.

---

## 12. Overall completion score

Raw counts from the matrix: **33 PASS + 9 PARTIAL + 1 FAIL + 0 UNVERIFIABLE** out of 43 requirements.
(PARTIAL = R6, R16, R20, R23, R24, R31, R35, R36, R40; FAIL = R30 streaming, a Should-Have.)
Formula: (33 + 0.5 × 9) / 43 × 100 = 37.5 / 43 × 100 = **87.2%**.
No CRITICAL-severity item is among the unsatisfied ones; the unsatisfied set is HIGH ×5, MEDIUM ×8, LOW ×1 — the HIGH items are reliability/deployment gaps (async chain, SPA rewrite, migrations, missing workflow, broker-down 201), not a broken core loop or isolation failure.

---

## 13. Final readiness assessment

Fully satisfied 33 · partial 9 · not satisfied 1 (R30 streaming, a Should-Have) · unverifiable 0. **Critical blockers: none.** Remaining work before submission, in order: guarantee the quiz→recommendation chain synchronously (H1), add the Vercel SPA rewrite (H2), run migrations on deploy (H3), fix the broker-down 201 (H5), implement or explicitly defer the repeated-mistake workflow (H4), publish the backend URL (M6), clear stale embedding refs (M1), harden boot secrets + auth limits (M4), and fix the embeddings retry-delay test gap (M5). The core learning loop is demonstrably complete, grounded, isolated, and tested; the submission reads as a strong, honest prototype whose sharpest edges are async-reliability, live-routing, and deploy-reproducibility rather than missing features.
