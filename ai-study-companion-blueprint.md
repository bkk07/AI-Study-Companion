# AI Study Companion — Revised Blueprint (v2)

Prototype scope: 3–4 day Full Stack AI Engineer candidate challenge. This revision keeps the same product and differentiator as v1 and corrects specific architecture issues: Docker/browser networking, shared file storage between backend and worker, the confidence data model, and an over-complicated AI "tool" framing that's replaced with plain service classes.

---

## 1. Product Overview

The AI Study Companion is a project-scoped learning partner. A student uploads course material; the system builds a personalized model of what they actually understand — not just what they can recognize on a multiple-choice test — by tracking two independent mastery signals per concept (`mcq_mastery`, `applied_mastery`) and detecting the gap between them. This is the product's entire reason for existing beyond "ChatGPT + a PDF uploader": it notices when recognition-level performance is outrunning actual understanding, tells the student in plain language, and routes them to the one action most likely to close that gap.

Before any of that can happen, uploaded material is first turned into a structured learning map — Topic → Subtopic → Concept (Part 7-9) — during PDF processing. Every quiz question, mastery score, mismatch flag, and recommendation in the system ultimately traces back to one of those extracted concepts. Uploaded material becomes a structured learning map, and that map is the foundation everything else in this document is built on top of.

---

## 2. Core Learning Loop

This is the central domain concept the whole product is organized around. "Learning Evidence" is not a metaphor — it's a real, append-only table (`mastery_evidence`) that every other engine reads from or writes to.

```
Learning Action  (MCQ answer, open-ended answer, Explain-It-Back, confidence rating)
       |
       v
Learning Evidence  (append-only record: score, type, difficulty, recency)
       |
       v
+-------------------------------+
|  Mastery Engine               |  -> mcq_mastery / applied_mastery (per concept)
|  Confidence Engine            |  -> confidence calibration (per concept)
+---------------+---------------+
                |
                v
        Mismatch Detection   (deterministic comparison, not AI-decided)
                |
                v
        Decision Engine       (deterministic scoring, not AI-decided)
                |
                v
      Recommended Next Action
                |
                v
  Tutor / Quiz / Explain-Back / Review
                |
                v
      More Learning Evidence  (loop closes)
```

This entire loop operates within a `concept_id` scope. Where that concept comes from — the Topic → Subtopic → Concept structure extracted from uploaded material during PDF processing — is covered in Parts 7-9; nothing about this loop changes based on that upstream detail.

Two things are deliberate here and worth stating explicitly, because they're the parts most likely to come up in an interview:

1. **Mastery and Confidence are computed independently, then combined downstream.** Confidence does not directly move `mcq_mastery` or `applied_mastery` — it feeds its own calibration signal, and *that* signal (specifically "confidently wrong") is one input among several to the Decision Engine. This avoids a single noisy signal (a nervous student who's actually correct) from distorting the mastery estimate itself.
2. **Mismatch Detection and the Decision Engine are plain deterministic code, not an LLM call.** The LLM is used exactly twice in this loop — evaluating a free-text response (Explain-It-Back / open-ended) and answering Tutor questions. It is never asked "what should the student do next" — that's a scored formula the team can explain line by line.

---

## 3. Feature Scope

**In scope (build):**
- Auth (JWT + Argon2id), Spaces, Projects, project isolation
- PDF upload + async processing (Celery)
- RAG: chunking, embeddings, project-scoped retrieval
- Grounded Tutor with citations + unsupported-question handling
- Adaptive Quiz (practice mode) + Exam Mode (config of the same engine)
- Confidence capture (1-5, before reveal)
- Open-ended assessment
- Explain-It-Back (streak-triggered, manual, and mismatch-triggered)
- Two-dimensional Concept Mastery (`mcq_mastery`, `applied_mastery`)
- Mismatch Detection (primary differentiator) + confidence-calibration mismatch (secondary)
- Decision Engine -> single recommended next action with a visible "why"
- Growth Analysis (read-time view over `mastery_evidence`, not a separate engine)
- Project Analytics + minimal Global Analytics
- Lightweight, read-only Admin Dashboard

**Explicitly out of scope (do not build):** flashcards, standalone AI notes, concept dependency maps, study planner, spaced repetition, audio/video, collaboration, gamification, notifications, exam readiness score, live lecture features, LangChain/LangGraph/agent frameworks, Kafka/RabbitMQ, microservices, a separate vector database.

---

## 4. Architecture

```
Browser (React)
   |   HTTP, JWT bearer
   v
FastAPI  (auth, validation, authorization)
   |
   v
Service layer  (TutorService, RAGService, QuizService, MasteryService,
               ConfidenceService, MismatchService, RecommendationService,
               AssessmentService)
   |                              |
   v                              v
PostgreSQL + pgvector      AI clients (GroqClient, EmbeddingClient)
   |
   v
Celery workers  (PDF processing, embeddings, evaluation, mastery/recommendation recompute)
   |   broker + result state
   v
Redis
```

Every arrow above is a plain function call or a well-understood protocol (HTTP, SQL, a Celery task dispatch) — there is no framework-managed "agent loop" anywhere in this system.

---

## 5. Frontend Architecture

React + Vite + TypeScript + Tailwind + shadcn/ui + React Router + Axios. The frontend never computes mastery, mismatch, or recommendations — it only renders values the API returns.

**Browser networking (important correction from v1):** the browser talks to FastAPI over a URL it can actually resolve — Docker Compose service names (`backend`, `postgres`, `redis`) only exist on the Compose network and are invisible to the host browser. See Part 28 for the exact configuration.

```
src/
|-- pages/          # route-level: Home, SpaceDashboard, ProjectDashboard, LearningStructure, Tutor, Quiz, Mastery, Growth, Admin
|-- features/        # tutor/, quiz/, learningStructure/, mastery/, recommendations/, admin/ - components + hooks per feature
|-- components/      # generic shared UI (StatusBadge, MasteryBar, ConfidenceSlider, ConceptTree)
|-- layouts/         # AppLayout (header + project sidebar), AdminLayout
|-- hooks/           # usePolling, useAuth
|-- services/        # axios instance + JWT interceptor, pointed at VITE_API_URL
|-- contexts/        # AuthContext, ProjectContext
|-- types/           # TS types mirroring backend Pydantic schemas
`-- utils/
```

`ConceptTree` is a single recursive component (Topic -> Subtopic -> Concept) reused in two places: the `LearningStructure` page (Part 19's `/materials/{mid}/structure`, read-only outline once a material is `ready`) and the `Mastery` page (same tree, each concept row now also rendering `MasteryBar` for `mcq_mastery`/`applied_mastery` and a mismatch badge — one component, two data sources, no separate tree implementation).

---

## 6. Backend Architecture

FastAPI is thin: request validation (Pydantic), authorization (`require_project_access`), delegate to a service, return a typed response. All decision logic — mastery math, mismatch comparison, recommendation scoring — lives in the service layer, which is what gets unit-tested.

```
app/
|-- main.py
|-- core/            # settings, JWT/Argon2 security, db session, exceptions
|-- db/              # SQLAlchemy models, Alembic migrations
|-- auth/
|-- spaces/
|-- projects/         # includes require_project_access dependency
|-- materials/         # upload handling - writes to the shared uploads volume (Part 8b)
|-- rag/                # chunking, EmbeddingClient wrapper, retrieval query
|-- tutor/              # TutorService - synchronous grounded Q&A
|-- quiz/               # QuizService - adaptive selection, practice + exam config
|-- assessment/         # AssessmentService - open-ended + Explain-It-Back (shared evaluator)
|-- mastery/             # MasteryService, ConfidenceService, MismatchService
|-- recommendations/     # RecommendationService (Decision Engine)
|-- analytics/
|-- admin/
|-- ai/                   # GroqClient, EmbeddingClient - thin provider wrappers, no orchestration
|-- workers/              # celery app + one task module per job
`-- schemas/              # shared Pydantic response models
```

Each feature module: `routes.py` (thin), `schemas.py`, `service.py` (logic, tested), and a `repository.py` only where a module's queries are complex enough to warrant separating from `service.py` — most modules query directly in the service to avoid an unnecessary layer.

---

## 7. Database Schema

Conventions: UUID PKs via `gen_random_uuid()`. Every table hanging off a project carries `project_id` directly so isolation checks are a single indexed filter, not a join chain.

```sql
users (
  id UUID PK, email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL,  -- Argon2id
  is_admin BOOLEAN DEFAULT false, created_at, updated_at
)

spaces (
  id UUID PK, user_id UUID FK->users NOT NULL,
  name TEXT NOT NULL, description TEXT, created_at, updated_at
)
INDEX (user_id)

projects (
  id UUID PK, space_id UUID FK->spaces NOT NULL, user_id UUID FK->users NOT NULL,
  name TEXT NOT NULL, goal TEXT, created_at, updated_at
)
INDEX (user_id), INDEX (space_id)

materials (
  id UUID PK, project_id UUID FK->projects NOT NULL, user_id UUID FK->users NOT NULL,
  filename TEXT NOT NULL, file_path TEXT NOT NULL,   -- path inside the shared uploads volume
  status TEXT CHECK (status IN ('queued','processing','ready','failed')) DEFAULT 'queued',
  page_count INT, error_message TEXT, created_at, updated_at
)
INDEX (project_id), INDEX (status)

topics (   -- top level of the extracted learning structure (Part 8/9)
  id UUID PK, project_id UUID FK->projects NOT NULL,   -- denormalized, same isolation convention as every other table below
  material_id UUID FK->materials NOT NULL,
  name TEXT NOT NULL, order_index INT NOT NULL, created_at
)
UNIQUE (material_id, name)
INDEX (project_id)

subtopics (
  id UUID PK, project_id UUID FK->projects NOT NULL,
  topic_id UUID FK->topics NOT NULL,
  name TEXT NOT NULL, order_index INT NOT NULL, created_at
)
UNIQUE (topic_id, name)
INDEX (project_id), INDEX (topic_id)

concepts (   -- the smallest unit of learning/mastery; everything downstream references concept_id
  id UUID PK, project_id UUID FK->projects NOT NULL,
  subtopic_id UUID FK->subtopics NOT NULL,
  name TEXT NOT NULL, description TEXT, order_index INT NOT NULL, created_at
)
UNIQUE (subtopic_id, name)
INDEX (project_id), INDEX (subtopic_id)

document_chunks (
  id UUID PK, material_id UUID FK->materials NOT NULL,
  project_id UUID FK->projects NOT NULL,   -- denormalized: retrieval filters this directly, no join
  topic_id UUID FK->topics, subtopic_id UUID FK->subtopics, concept_id UUID FK->concepts,
    -- all three nullable: best-effort association from structure extraction (Part 8), never required for retrieval or isolation to work
  chunk_index INT NOT NULL, page_number INT, content TEXT NOT NULL,
  embedding VECTOR(1536), created_at
)
INDEX (project_id), INDEX (concept_id)
INDEX USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)

conversations (
  id UUID PK, project_id UUID FK->projects NOT NULL, user_id UUID FK->users NOT NULL,
  title TEXT, created_at, updated_at
)
INDEX (project_id)

messages (
  id UUID PK, conversation_id UUID FK->conversations NOT NULL,
  role TEXT CHECK (role IN ('user','assistant')) NOT NULL,
  content TEXT NOT NULL, citations JSONB,   -- [{chunk_id, page_number, material_id}]
  is_unsupported BOOLEAN DEFAULT false,
  concept_id UUID FK->concepts,   -- nullable: set only when TutorAnswer confidently identifies a relevant concept (Part 9); left null rather than guessing
  created_at
)
INDEX (conversation_id), INDEX (concept_id)

quizzes (
  id UUID PK, project_id UUID FK->projects NOT NULL,
  mode TEXT CHECK (mode IN ('practice','exam')) NOT NULL,
  question_count INT NOT NULL, time_limit_seconds INT, created_at
)

quiz_questions (
  id UUID PK, quiz_id UUID FK->quizzes NOT NULL, concept_id UUID FK->concepts NOT NULL,
  question_text TEXT NOT NULL, options JSONB NOT NULL, correct_option_id TEXT NOT NULL,
  difficulty TEXT CHECK (difficulty IN ('easy','medium','hard')) NOT NULL,
  source_chunk_id UUID FK->document_chunks, created_at
)
INDEX (quiz_id), INDEX (concept_id)

quiz_attempts (
  id UUID PK, quiz_id UUID FK->quizzes NOT NULL, user_id UUID FK->users NOT NULL,
  started_at TIMESTAMPTZ, completed_at TIMESTAMPTZ, score NUMERIC(5,2)
)
INDEX (user_id), INDEX (quiz_id)

quiz_answers (
  id UUID PK, attempt_id UUID FK->quiz_attempts NOT NULL, question_id UUID FK->quiz_questions NOT NULL,
  selected_option_id TEXT NOT NULL, is_correct BOOLEAN NOT NULL, answered_at TIMESTAMPTZ DEFAULT now()
)
INDEX (attempt_id)

assessments (
  id UUID PK, project_id UUID FK->projects NOT NULL, concept_id UUID FK->concepts NOT NULL,
  user_id UUID FK->users NOT NULL, prompt TEXT NOT NULL, created_at
)

assessment_answers (
  id UUID PK, assessment_id UUID FK->assessments NOT NULL,
  response_text TEXT NOT NULL, ai_score NUMERIC(5,2), ai_feedback JSONB, created_at
)

explain_back_attempts (
  id UUID PK, project_id UUID FK->projects NOT NULL, concept_id UUID FK->concepts NOT NULL,
  user_id UUID FK->users NOT NULL,
  trigger_reason TEXT CHECK (trigger_reason IN ('correct_streak','manual','mismatch_probe')) NOT NULL,
  response_text TEXT NOT NULL, ai_score NUMERIC(5,2), ai_feedback JSONB, created_at
)
INDEX (concept_id)

-- CONFIDENCE_RECORDS - explicit nullable FKs, not a polymorphic reference (v1 correction)
confidence_records (
  id UUID PK, user_id UUID FK->users NOT NULL, project_id UUID FK->projects NOT NULL,
  concept_id UUID FK->concepts NOT NULL,
  quiz_answer_id UUID FK->quiz_answers,
  assessment_answer_id UUID FK->assessment_answers,
  explain_back_attempt_id UUID FK->explain_back_attempts,
  confidence_level INT CHECK (confidence_level BETWEEN 1 AND 5) NOT NULL,
  actual_correct BOOLEAN NULL,   -- NULL until evaluation completes for open-ended/Explain-It-Back; known immediately for MCQ (final correction, see Part 11)
  created_at,
  CHECK (
    (quiz_answer_id IS NOT NULL)::int +
    (assessment_answer_id IS NOT NULL)::int +
    (explain_back_attempt_id IS NOT NULL)::int = 1
  )
)
INDEX (user_id, concept_id)

concept_mastery (   -- current state, one row per user+project+concept
  id UUID PK, user_id UUID FK->users NOT NULL, project_id UUID FK->projects NOT NULL,
  concept_id UUID FK->concepts NOT NULL,
  mcq_mastery NUMERIC(5,2) DEFAULT 0, applied_mastery NUMERIC(5,2) DEFAULT 0,
  mismatch_active BOOLEAN DEFAULT false,
  mismatch_type TEXT CHECK (mismatch_type IN ('mcq_high_applied_low','overconfident','underconfident')),
  last_evidence_at TIMESTAMPTZ, updated_at
)
UNIQUE (user_id, project_id, concept_id)
INDEX (project_id)

mastery_evidence (   -- append-only; also the Growth Analysis source
  id UUID PK, user_id UUID FK->users NOT NULL, concept_id UUID FK->concepts NOT NULL,
  evidence_type TEXT CHECK (evidence_type IN ('mcq','open_ended','explain_back')) NOT NULL,
  raw_score NUMERIC(5,2) NOT NULL, weight NUMERIC(3,2) NOT NULL,
  resulting_mcq_mastery NUMERIC(5,2), resulting_applied_mastery NUMERIC(5,2),
  source_id UUID, created_at
)
INDEX (concept_id, created_at)

recommendations (
  id UUID PK, user_id UUID FK->users NOT NULL, project_id UUID FK->projects NOT NULL,
  concept_id UUID FK->concepts,
  action_type TEXT CHECK (action_type IN ('ask_tutor','targeted_quiz','explain_back','review_material','exam_mode')) NOT NULL,
  score NUMERIC(6,2) NOT NULL, reasoning TEXT NOT NULL,
  status TEXT CHECK (status IN ('active','accepted','dismissed','expired')) DEFAULT 'active', created_at
)
INDEX (user_id, project_id, status)

activity_events (
  id UUID PK, user_id UUID FK->users NOT NULL, project_id UUID FK->projects,
  event_type TEXT NOT NULL, metadata JSONB, created_at
)
INDEX (user_id, created_at), INDEX (project_id, created_at)

ai_usage (
  id UUID PK, user_id UUID FK->users, project_id UUID FK->projects,
  feature TEXT NOT NULL,   -- 'tutor'|'quiz_gen'|'assessment_eval'|'explain_back_eval'|'embedding'
  model TEXT NOT NULL, input_tokens INT, output_tokens INT, latency_ms INT,
  estimated_cost_usd NUMERIC(8,5), success BOOLEAN NOT NULL, error_message TEXT, created_at
)
INDEX (feature, created_at)

background_jobs (
  id UUID PK, job_type TEXT NOT NULL, related_id UUID, celery_task_id TEXT,
  status TEXT CHECK (status IN ('pending','running','succeeded','failed')) DEFAULT 'pending',
  attempts INT DEFAULT 0, last_error TEXT, created_at, updated_at
)
INDEX (job_type, status)
```

**Isolation:** every project-scoped query filters on `project_id` (or `user_id` for materials/chunks) at the service layer, enforced by a shared `require_project_access(user, project_id)` dependency on every project-scoped route (404, not 403, to avoid leaking existence). `document_chunks.project_id` is denormalized specifically so retrieval is one indexed filter with no join to get wrong. `topics`, `subtopics`, and `concepts` follow the same convention — `project_id` is denormalized onto all three rather than requiring a join up through `subtopic_id -> topic_id -> material_id` just to check ownership, so a concept from Project A can never be selected, quizzed, or scored against Project B by any code path in this system.

---

## 8. RAG Architecture

```
PDF upload -> FastAPI saves file to shared uploads volume (Part 8b)
  -> materials row (status=queued) -> Celery task `process_pdf`
  -> PyMuPDF text extraction (per page)
  -> Celery task `extract_learning_structure` (Groq, structured/Pydantic output, Part 9)
       -> runs on the full extracted document text (needs whole-document context to find real topics, not a single 500-700 token chunk)
       -> LLM proposes Topic -> Subtopic -> Concept, identifying meaningful educational structure rather than copying PDF headings verbatim
       -> Pydantic-validated; on validation failure, one automatic re-prompt, then materials.status='failed' (Part 23) -- never inserts partial or corrupt structure
       -> persisted as topics / subtopics / concepts rows (Part 7), each carrying project_id
       -> a document with no identifiable educational structure persists zero topics and still reaches materials.status='ready' -- an empty Learning Structure is not a processing failure
  -> chunking: ~500-700 tokens, 50-100 token overlap, page-aware (never split across a page boundary if avoidable)
  -> metadata per chunk: material_id, project_id, page_number, chunk_index, source_name, plus a best-effort topic_id/subtopic_id/concept_id assigned by matching each chunk's page range against the extracted structure (nullable -- retrieval and project isolation never depend on this match succeeding)
  -> Celery task `generate_embeddings` (OpenAI text-embedding-3-small)
  -> insert into document_chunks
  -> materials.status = ready  (or failed + error_message on any step exception)
```

Three separate Celery tasks (not one) so a failure in embeddings or structure extraction doesn't force re-extraction of the others, and so `background_jobs` gives granular per-step status for the UI's processing indicator.

**Retrieval:**
```
Question -> OpenAI embedding
  -> pgvector cosine similarity, WHERE project_id = :authenticated_project_id   -- from require_project_access, never client-supplied; filter happens inside the vector query itself, before ranking
     [AND concept_id = :concept_id]  -- added when retrieval is grounding a specific concept (Explain-It-Back evaluation, targeted quiz generation, Part 9); omitted for general Tutor questions
  -> top 5 chunks
  -> similarity threshold check -> below threshold = unsupported (Part 9)
  -> Groq (question + chunks) -> answer + structured citations (chunk_id -> material/page)
```

This is intentionally simple — no semantic chunking, no re-ranking model, no separate vector store. pgvector inside the existing Postgres instance is sufficient at this scale and keeps the isolation guarantee (`project_id` filter) as a single SQL clause instead of a cross-system concern.

### 8b. Shared File Storage (v1 correction)

The backend and Celery worker run in **separate containers**. If `process_pdf` runs in the worker, the worker must be able to read the exact file the backend saved. This requires a **named Docker volume mounted into both containers**:

```yaml
volumes:
  uploads:

services:
  backend:
    volumes:
      - uploads:/data/uploads
  worker:
    volumes:
      - uploads:/data/uploads
```

Both containers reference the same `UPLOAD_DIR=/data/uploads` environment variable, so `materials.file_path` is a path that resolves identically in both containers.

**Full upload workflow:**
```
Browser -> POST /projects/{id}/materials (multipart PDF)
  -> FastAPI validates file (size, content-sniffed MIME), saves to /data/uploads/{material_id}.pdf
  -> creates Material(status='queued')
  -> creates background_jobs row (job_type='process_pdf', status='pending')
  -> dispatches Celery task
  -> returns 202 to the browser immediately (browser now polls status)
Celery worker:
  -> reads /data/uploads/{material_id}.pdf  (same path, same volume)
  -> PyMuPDF -> extract learning structure (topics/subtopics/concepts) -> chunk -> embed -> insert document_chunks
  -> Material.status = 'ready'
```

For production beyond the prototype, this volume is swapped for S3-compatible object storage — noted in Part 33, not built now.

---

## 9. AI Architecture

No agent framework, no tool-calling runtime, no LangChain/LangGraph. Plain Python services call two thin AI provider clients:

```
FastAPI route
   |
   v
TutorService / QuizService / AssessmentService / MasteryService / RecommendationService
   |
   v
GroqClient (text generation, quiz generation, free-text evaluation)
EmbeddingClient (OpenAI embeddings only)
```

The AI never touches the database. A service method (e.g. `AssessmentService.evaluate()`) is the only thing that (a) calls `GroqClient` and (b) writes the result to Postgres — the model itself has no ability to issue a query or a write. This is a much simpler guarantee than a permissioned "tool layer": there is no tool-call surface for the model to misuse in the first place, because the model's only output is text (constrained to a JSON schema for evaluation calls) that the calling service parses and validates with Pydantic before doing anything with it.

**Typed schemas around AI calls** (kept, because they make responses safe to parse — not because of any agent architecture):

```python
class ExplainBackEvaluation(BaseModel):
    concept_coverage: int   # 0-100
    accuracy: int
    missing_ideas: list[str]
    misconceptions: list[str]
    clarity: int
    overall_score: int

class TutorAnswer(BaseModel):
    answer: str
    source_chunk_ids: list[UUID]
    is_unsupported: bool
    detected_concept_id: UUID | None = None   -- set only when the question clearly maps to one of the project's extracted concepts

class ConceptExtraction(BaseModel):
    name: str
    description: str | None = None

class SubtopicExtraction(BaseModel):
    name: str
    concepts: list[ConceptExtraction]

class TopicExtraction(BaseModel):
    name: str
    subtopics: list[SubtopicExtraction]

class LearningStructureExtraction(BaseModel):
    topics: list[TopicExtraction]
```

`GroqClient.evaluate_explanation(response_text, retrieved_chunks) -> ExplainBackEvaluation` — one Groq call, JSON-mode response, parsed straight into the Pydantic model; a parse failure triggers exactly one re-prompt with a stricter format instruction, then falls back to a "pending manual review" state (Part 23) rather than guessing a score.

`GroqClient.extract_learning_structure(document_text) -> LearningStructureExtraction` — one Groq call, structured/Pydantic output, run once per material against the full extracted PDF text (Part 8). The prompt explicitly asks for *meaningful educational* topics/subtopics/concepts, not a copy of the PDF's own headings — a document with flat or absent headings should still yield a sensible structure, and a document with no real educational content should yield an empty `topics` list rather than the model inventing structure to fill the schema. Same failure contract as `evaluate_explanation`: a validation failure triggers one re-prompt, then the material is marked `failed` (Part 23) — corrupt structure is never written to `topics`/`subtopics`/`concepts`.

**Tutor concept association:** `TutorService` passes the project's concept list (name + description, cheap since it's just text) alongside the question in the same Groq call that produces the grounded answer, and `TutorAnswer.detected_concept_id` is populated only when the model is confident of a match — `messages.concept_id` is left `NULL` otherwise rather than forcing a guess. This is used for analytics (which concepts students actually ask about) and an `activity_events` row tagged with the concept, so a project's Analytics view (Part 25) can surface "most-asked-about concepts." It deliberately does **not** write `mastery_evidence` or move `mcq_mastery`/`applied_mastery` — a free-form question isn't a graded response, and folding it into the mastery formula (Part 10) would require inventing a difficulty/weight for something that has none. Tutor stays a read/explain surface; MCQ, open-ended, and Explain-It-Back remain the only three evidence-producing paths (Part 10).

**Which calls are synchronous vs background** (v1 correction — no more FastAPI `BackgroundTasks`; every non-trivial job goes through Celery, but not every request needs to be async):

| Operation | Execution | Why |
|---|---|---|
| Tutor message | **Synchronous**, inline in the request | Target <3s; a chat UI needs to feel responsive, and there's nothing to checkpoint/retry mid-answer |
| Quiz question generation | **Synchronous** if a pre-generated question exists for the (concept, difficulty); otherwise a single fast Groq call inline | Fast enough not to need a job; no multi-step pipeline |
| PDF processing (extract/chunk) | **Celery** (`process_pdf`) | Can take 10s-2min depending on PDF size; must survive the browser closing |
| Learning structure extraction | **Celery** (`extract_learning_structure`) | Full-document-context Groq call, slower than a per-chunk call; must complete before chunking so chunks can be associated with structure, and must survive the browser closing like the rest of PDF processing |
| Embedding generation | **Celery** (`generate_embeddings`) | Batch API call, retryable independently of extraction |
| Open-ended / Explain-It-Back evaluation | **Celery** (`evaluate_assessment`) | LLM eval call (2-5s) plus a mastery/mismatch recompute — bundling into one background unit avoids blocking the submit button |
| Mastery + mismatch recompute | **Celery** (`update_mastery`, runs mismatch check inline as the last step) | Triggered after every evidence-producing event; cheap but async so it never blocks the triggering request |
| Recommendation recompute | **Celery** (`generate_recommendation`) | Reads multiple tables; recomputed after mastery changes, not on every page load |

---

## 10. Mastery Engine

Two independent scores per `(user, concept)`: `mcq_mastery` (recognition) and `applied_mastery` (production — open-ended + Explain-It-Back). They're separate because selecting a correct MCQ option and generating a correct explanation from scratch are different cognitive tasks; collapsing them into one number would hide exactly the gap this product exists to surface.

`concept` here is always a row produced by `extract_learning_structure` (Part 8/9) — the leaf of a project's Topic → Subtopic → Concept tree. Nothing about the formulas below changes; they're unchanged from v1, just now always operating on an extraction-derived, project-scoped concept rather than an arbitrary label.

Simple, explainable weighted-average update — deliberately fewer tuned constants than v1:

```python
def update_mastery(current: float, evidence_score: float, weight: float) -> float:
    # weight in (0, 1]. Bounded weighted average - no compounding multipliers.
    updated = current + weight * (evidence_score - current)
    return max(0.0, min(100.0, updated))

def evidence_weight(difficulty: str, days_since_last: float) -> float:
    base = {"easy": 0.2, "medium": 0.3, "hard": 0.4}[difficulty]
    recency_boost = 0.1 if days_since_last > 7 else 0.0   # a fresh data point after a gap counts a bit more
    return min(0.5, base + recency_boost)                  # single cap, no per-type multiplier stacking
```

- `evidence_type = 'mcq'` -> updates `mcq_mastery` only.
- `evidence_type in ('open_ended','explain_back')` -> updates `applied_mastery` only.
- Confidence is **not** an input to this formula (v1 correction — see Part 11). Mastery reflects correctness and difficulty only.

Every update writes one `mastery_evidence` row first (append-only, powers Growth Analysis) then updates `concept_mastery`. Mastery is surfaced in the UI with an explicit caveat: *"Mastery is an estimate based on your recent answers — it improves in accuracy as you answer more questions."* — it is not presented as a validated measurement.

**Worked example — Gradient Descent:** 4 correct MCQs at medium difficulty -> `mcq_mastery` climbs toward ~85-90. A vague Explain-It-Back response missing the role of the learning rate -> `applied_mastery` stays ~55-60. Result: `mcq_mastery=92, applied_mastery=54` -> mismatch (Part 13).

---

## 11. Confidence Engine

Confidence is captured in the **same request** that submits an answer (one round trip, not two): `POST /quiz/attempts/{id}/answer` takes `{question_id, selected_option_id, confidence_level}`; the server computes `is_correct` first, then writes both the `quiz_answers` row and the `confidence_records` row (with `quiz_answer_id` set and `actual_correct` already known) in one transaction. The same pattern applies to open-ended and Explain-It-Back submissions — confidence goes in with the response text while `actual_correct` is written as `NULL` (final correction), and `actual_correct`/score is backfilled once evaluation completes and `confidence_records.actual_correct` is updated at that point.

```python
def confidence_gap(confidence_level: int, actual_correct: bool) -> float:
    expected = {1: 0.2, 2: 0.4, 3: 0.6, 4: 0.8, 5: 0.95}[confidence_level]
    actual = 1.0 if actual_correct else 0.0
    return actual - expected   # negative = overconfident, positive = underconfident

def classify(gap: float) -> str:
    if gap <= -0.4: return "overconfident"
    if gap >= 0.4:  return "underconfident"
    return "well_calibrated"
```

**Important boundary (v1 correction):** confidence does **not** feed back into the mastery formula. It is tracked as its own signal (`confidence_accuracy` — mean of `1 - |gap|` over recent **evaluated** records for a concept, excluding any record where `actual_correct` is still `NULL` pending async evaluation — final correction) and consumed downstream, only by the Decision Engine, as a distinct input alongside mastery and mismatch. Being "confidently wrong" changes what gets *recommended* (it's a strong signal that a review is needed even if raw MCQ mastery still looks okay), but it never silently discounts or inflates the mastery numbers themselves — keeping mastery legible as "correctness over time," full stop.

---

## 12. Explain-It-Back Engine

Three trigger paths, all producing the same evidence record:

1. **Correct-streak** — 3 consecutive correct MCQs on the same concept within a session (checked after each answer via a lightweight query on the last 3 `quiz_answers` joined to `quiz_questions.concept_id`).
2. **Manual** — a permanent "Explain this concept" action available on the Mastery page for any concept.
3. **Mismatch probe** — if `MismatchService` detects `mcq_high_applied_low` for a concept with thin applied evidence, the Decision Engine can recommend Explain-It-Back directly (Part 16), which is effectively this same trigger surfaced through the recommendation UI rather than an automatic interrupt.

**Flow:**
```
Trigger fires -> UI: "Teach this concept back to me" (interrupt card or Mastery-page action)
  -> student writes response_text + confidence_level (single submit)
  -> explain_back_attempts row created (trigger_reason recorded), confidence_records row created (actual_correct pending)
  -> Celery task `evaluate_assessment` (target_type='explain_back')
     -> retrieves the concept's top source chunks (grounds the evaluation in the actual material)
     -> GroqClient.evaluate_explanation() -> ExplainBackEvaluation (Part 9)
     -> writes ai_score / ai_feedback back to explain_back_attempts
     -> backfills confidence_records.actual_correct (score >= 60 treated as "correct" for calibration purposes)
     -> writes mastery_evidence (evidence_type='explain_back') -> MasteryService.update_mastery() on applied_mastery
     -> MismatchService re-check -> RecommendationService recompute
  -> frontend polls the attempt until ai_score is non-null, then reveals structured feedback
```

---

## 13. Mismatch Engine

**Primary — the product's differentiator — HIGH MCQ + LOW APPLIED:**

```python
MISMATCH_GAP_THRESHOLD = 25     # percentage points
MISMATCH_MIN_EVIDENCE = 3       # don't flag on thin data

def detect_mismatch(mcq_mastery, applied_mastery, mcq_evidence_count, applied_evidence_count):
    if mcq_evidence_count < MISMATCH_MIN_EVIDENCE or applied_evidence_count < 1:
        return None
    if mcq_mastery - applied_mastery >= MISMATCH_GAP_THRESHOLD:
        return "mcq_high_applied_low"
    return None
```

Runs as the last step of the `update_mastery` Celery task — always current, no batch job. On detection: `concept_mastery.mismatch_active=true`, `mismatch_type` set, `activity_events` row written (read by the Decision Engine).

**UI copy:** *"You're answering recognition questions well (92%), but your explanation suggests the underlying concept isn't fully secure (54%)."* — specific numbers, non-judgmental framing, immediate call to action ("Explain This Concept").

**Secondary — confidence-calibration mismatch** (from `ConfidenceService`, not `MismatchService` — kept as a distinct, lower-priority signal):

```python
def confidence_mismatch(recent_confidence_records) -> str | None:
    evaluated = [r for r in recent_confidence_records if r.actual_correct is not None]  # final correction: exclude open-ended/Explain-It-Back records still awaiting Celery evaluation
    if not evaluated:
        return None
    avg_conf = mean(r.confidence_level for r in evaluated)
    accuracy = mean(1.0 if r.actual_correct else 0.0 for r in evaluated)
    if avg_conf >= 4 and accuracy <= 0.5: return "overconfident"
    if avg_conf <= 2 and accuracy >= 0.8: return "underconfident"
    return None
```

Only one `mismatch_type` is stored per concept at a time; priority order is `mcq_high_applied_low` > `overconfident` > `underconfident` — the primary differentiator always wins the badge if both are true.

**Effect on recommendations:** an active mismatch adds a fixed score bonus to `explain_back`/`review_material` actions for that concept in the Decision Engine (Part 16), specifically so more MCQs are never recommended for a concept that's already showing shallow-recognition signs — that would reinforce the exact pattern the product is designed to catch.

---

## 14. Adaptive Quiz Engine

Concept selection first, difficulty second — not a simple correct->harder ladder:

```python
def select_next_concept(concepts: list[ConceptState]) -> ConceptState:
    def priority(c):
        weakness = 100 - min(c.mcq_mastery, c.applied_mastery)
        low_evidence_bonus = 20 if c.evidence_count < 3 else 0
        mismatch_bonus = 30 if c.mismatch_active else 0
        overrepresented_penalty = -10 * c.times_asked_this_session
        return weakness + low_evidence_bonus + mismatch_bonus + overrepresented_penalty
    return max(concepts, key=priority)

def select_difficulty(c: ConceptState) -> str:
    if c.mcq_mastery < 40: return "easy"
    if c.mcq_mastery < 75: return "medium"
    return "hard"
```

Loop: pick concept -> pick difficulty -> reuse an existing `quiz_questions` row for that (concept, difficulty) if one exists, else generate one via a single synchronous Groq call grounded in that concept's chunks (Part 9) -> serve -> capture answer + confidence in one request -> dispatch `update_mastery` async -> repeat for `question_count`.

Generation receives the concept as structured context, not just a bare name string — `{topic_name, subtopic_name, concept_name, concept_description, retrieved_chunks}` — so a concept like "Entropy" is generated against "Classification > Decision Trees > Entropy" rather than the word in isolation, which matters once a project has multiple topics that could each contain a similarly-named concept.

---

## 15. Exam Mode

A configuration of the same `quizzes`/`QuizService` code path (`mode='exam'`), not a separate system:

| | Practice | Exam |
|---|---|---|
| `question_count` | 5 | 15 |
| `time_limit_seconds` | null | e.g. 900 |
| concept selection | `select_next_concept`, session-aware | forced spread across all concepts with evidence |
| difficulty | adaptive per question | fixed mixed distribution set at session start |
| feedback timing | immediate per question | deferred to a results screen |

`start_quiz(project_id, mode)` branches only on `mode` to pick a concept-spread strategy and a feedback-timing flag — scoring, mastery updates, and confidence capture are identical code paths for both modes.

---

## 16. Decision Engine

Five recommendation types only (v1 correction — simplified from seven): `ASK_TUTOR`, `TARGETED_QUIZ`, `EXPLAIN_BACK`, `REVIEW_MATERIAL`, `EXAM_MODE`.

```python
ACTION_BASE_VALUE = {
    "ask_tutor": 10, "targeted_quiz": 15, "explain_back": 20,
    "review_material": 5, "exam_mode": 8,
}

def score_action(concept, action_type, context) -> float:
    weakness = 100 - min(concept.mcq_mastery, concept.applied_mastery)
    uncertainty = 25 if concept.confidence_mismatch in ("overconfident",) else 0
    recency = 15 if concept.days_since_last_evidence > 5 else 0
    goal_relevance = 10 if concept.name in context.project_goal_keywords else 0
    repetition_penalty = 25 * context.times_recommended_recently(concept.id, action_type)

    score = weakness + uncertainty + recency + goal_relevance + ACTION_BASE_VALUE[action_type] - repetition_penalty

    if concept.mismatch_active and action_type in ("explain_back", "review_material"):
        score += 40   # mismatch always pulls toward applied practice, never more MCQs
    if concept.mismatch_active and action_type == "targeted_quiz":
        score -= 20   # explicit downrank, not just an absence of bonus

    return max(0, score)

def recommend(concepts, context) -> Recommendation:
    candidates = [
        (c, action, score_action(c, action, context))
        for c in concepts
        for action in ACTION_BASE_VALUE
        if action_eligible(c, action, context)   # e.g. no exam_mode with <3 concepts evidenced
    ]
    concept, action, score = max(candidates, key=lambda x: x[2])
    return Recommendation(concept=concept, action=action, score=score, reasoning=explain(concept, action, context))
```

`explain()` produces the visible "Why this recommendation?" copy from whichever factors actually drove the winning score — e.g. *"Your MCQ mastery is 92%, but your applied mastery is 54%. Your last explanation also missed the role of learning rate."* Because `concept` now always resolves to a Topic → Subtopic → Concept path (Part 7), the recommendation card can additionally show that path (e.g. "Classification > Decision Trees > Entropy") as breadcrumb context — a formatting detail read off the existing joins, not a new scoring input. The engine is fully deterministic; the LLM never participates in this decision.

Recommendations recompute (as a Celery task) after every mastery-affecting event; the previous `active` recommendation is marked `expired` when superseded, so the UI always shows exactly one current recommendation.

---

## 17. Growth Analysis

No separate engine — a read-time aggregation over `mastery_evidence`:

```sql
SELECT date_trunc('week', created_at) AS week, concept_id,
       avg(resulting_mcq_mastery) AS mcq, avg(resulting_applied_mastery) AS applied
FROM mastery_evidence
WHERE concept_id = :concept_id
GROUP BY week, concept_id ORDER BY week;
```

```python
def classify_trend(weekly: list[float]) -> str:
    if len(weekly) < 2: return "not_enough_data"
    delta = weekly[-1] - weekly[0]
    recent_slope = weekly[-1] - weekly[-2]
    if delta >= 15: return "improving"
    if delta <= -10: return "declining"
    if recent_slope <= -8: return "needs_attention"
    return "stable"
```

Rendered as a sparkline (both `mcq` and `applied` lines) with a trend badge on the Growth page.

**Drill-down (Topic -> Subtopic -> Concept):** the same query above, parameterized by `topic_id` or `subtopic_id` instead of `concept_id` (`mastery_evidence.concept_id IN (SELECT id FROM concepts WHERE subtopic_id = :id)`, etc.) rather than a separate progress engine — Growth Analysis was already "a read-time view over mastery/evidence history," so a coarser grouping key is the entire change. The Project Dashboard's overall `Overall Progress: 72%` figure is the same aggregation one level further up (all concepts in the project); no new table, no new Celery job.

---

## 18. Celery + Redis Architecture

```
FastAPI (dispatch) -> Celery (task registry) -> Redis (broker + result backend) -> Worker -> PostgreSQL
```

**Jobs:** `process_pdf`, `extract_learning_structure` (Groq structured output -> topics/subtopics/concepts), `generate_embeddings`, `evaluate_assessment` (shared by open-ended + Explain-It-Back), `update_mastery` (runs mismatch check as its final step, not a separate dispatch), `generate_recommendation`. **Not Celery** — Tutor messages and (usually) quiz question generation, per the sync/async table in Part 9.

**Task states:** a `background_jobs` row is written `pending` before dispatch; Celery's `on_success`/`on_failure` hooks flip it to `running`->`succeeded`/`failed`. This gives the frontend a pollable status independent of Celery's own result backend and survives a Redis flush.

**Retries:** `process_pdf`/`generate_embeddings` retry up to 3x with exponential backoff (2s/8s/32s) on transient errors; a corrupt-PDF parse error does not retry (retrying won't fix a malformed file) and goes straight to `failed`. `extract_learning_structure` follows the same one-re-prompt-then-fail contract as `evaluate_explanation` (Part 9) — a model that keeps returning malformed JSON on a well-formed document is treated as a processing failure, not retried indefinitely against the same bad prompt.

**Idempotency:** `process_pdf` checks `materials.status != 'processing'` before starting, to avoid a double-enqueue racing itself on a manual retry click. `generate_embeddings` deletes any existing chunks for that `material_id` before inserting, so a retried run never duplicates chunks. `extract_learning_structure` is **not** delete-and-recreate like `generate_embeddings` — it first checks whether `topics` rows already exist for `material_id` and skips if so, because concept identity must stay stable once created: `quiz_questions.concept_id`, `mastery_evidence.concept_id`, and `concept_mastery.concept_id` all point at a specific concept row, and deleting/recreating concepts on a retry would orphan or silently reset a student's existing mastery and quiz history for that material.

**Redis is also used, separately, for:** Celery's broker/result backend only — no ad hoc caching layer added for this scope.

---

## 19. API Specification

All routes under `/api`, JWT bearer auth except `/auth/*`.

**Auth**
- `POST /auth/register` `{email,password}` -> `{access_token}`
- `POST /auth/login` `{email,password}` -> `{access_token}`

**Spaces / Projects**
- `GET /spaces`, `POST /spaces` `{name,description}`
- `GET /spaces/{id}/projects`, `POST /spaces/{id}/projects` `{name,goal}`
- `GET /projects/{id}` — 404 if not owner

**Materials**
- `POST /projects/{id}/materials` — multipart PDF -> `Material(status=queued)`, dispatches `process_pdf`
- `GET /projects/{id}/materials/{mid}/status` -> `{status, page_count, error_message}` — polled
- `POST /projects/{id}/materials/{mid}/retry`
- `GET /projects/{id}/materials/{mid}/structure` -> nested `{topics: [{id, name, subtopics: [{id, name, concepts: [{id, name}]}]}]}` — empty `topics` array once `status='ready'` on a document with no detected structure; 404 while still `queued`/`processing`

**Tutor** (synchronous)
- `POST /projects/{id}/tutor/message` `{conversation_id?, content}` -> `{message, citations, is_unsupported}`

**Quiz**
- `POST /projects/{id}/quiz/start` `{mode}` -> `{quiz_id, first_question}`
- `GET /quiz/attempts/{aid}/next` -> `Question | {complete:true}`
- `POST /quiz/attempts/{aid}/answer` `{question_id, selected_option_id, confidence_level}` -> `{is_correct, explanation}` (dispatches `update_mastery`)

**Assessment / Explain-It-Back**
- `POST /projects/{id}/assessments` `{concept_id, prompt}` -> `Assessment`
- `POST /assessments/{aid}/answer` `{response_text, confidence_level}` -> `{id, status:"evaluating"}` (dispatches `evaluate_assessment`)
- `GET /assessment-answers/{id}` -> `{ai_score, ai_feedback}` — polled
- `POST /projects/{id}/explain-back` `{concept_id, response_text, confidence_level, trigger_reason}` -> `{id, status:"evaluating"}`
- `GET /explain-back/{id}` -> `{ai_score, ai_feedback}` — polled

**Mastery / Growth / Recommendations**
- `GET /projects/{id}/mastery` -> `[{concept, topic_name, subtopic_name, mcq_mastery, applied_mastery, mismatch_active, mismatch_type}]`
- `GET /projects/{id}/growth?concept_id=|subtopic_id=|topic_id=` -> `{weekly_series, trend}` — exactly one of the three query params, per Part 17's drill-down
- `GET /projects/{id}/recommendation` -> current active `Recommendation`
- `POST /recommendations/{id}/dismiss`

**Analytics / Admin**
- `GET /projects/{id}/analytics`
- `GET /admin/analytics`, `GET /admin/users`, `GET /admin/activity` — admin only

---

## 20. Backend Folder Structure

See Part 6 above for the full listing — repeated here would only duplicate it; this section exists to satisfy the requested 33-part order.

---

## 21. Frontend Folder Structure

See Part 5 above for the full listing — same note as Part 20.

---

## 22. Security

- **JWT**: short-lived access token (60 min), HS256, `JWT_SECRET`; no refresh-token rotation at prototype scope (re-login on expiry is acceptable).
- **Password hashing**: Argon2id, never reversible storage.
- **Authorization**: `require_project_access(current_user, project_id)` on every project-scoped route (Part 14); `require_admin` on admin routes.
- **Project isolation**: enforced at the service layer via explicit `WHERE user_id=`/`WHERE project_id=` filters, tested explicitly (Part 27) — not an incidental side effect of a join. `topics`/`subtopics`/`concepts` carry the same denormalized `project_id` (Part 7) and go through the same `require_project_access` dependency as every other project-scoped route — no separate isolation mechanism was introduced for the new tables.
- **File access**: uploads live in the Docker volume, outside any web-servable path; served only through an authenticated, ownership-checked download endpoint.
- **RAG isolation**: `project_id` filter is inside the vector query's `WHERE` clause, applied before ranking — a bug can't leak another project's chunks into the candidate set at all.
- **AI has no DB access** (Part 9) — the strongest version of this guarantee, since there's no tool surface to misuse.
- **Prompt injection from PDFs**: retrieved chunk text is passed to Groq strictly as delimited reference data with an explicit system instruction that content inside the block is never to be treated as an instruction to the assistant; the system prompt itself is never rebuilt from chunk content.
- **Malicious documents**: PyMuPDF runs only inside the Celery worker (never inline on the request path); uploads are size-capped and content-sniffed, not just extension-checked.
- **API security**: CORS locked to the frontend origin; basic rate limiting on `/auth/*` and `/tutor/message` to bound AI cost exposure.

---

## 23. Error Handling

| Scenario | Backend behavior | User message | Retry |
|---|---|---|---|
| Invalid login | 401 | "Incorrect email or password." | manual |
| Expired JWT | 401 | redirect to login | manual |
| Unauthorized project access | 404 | "Project not found." | — |
| PDF upload failure | 400/413 | "Upload failed — check file type/size." | manual |
| PDF parsing failure | `materials.status='failed'` + `error_message` | inline failed state + Retry | manual |
| Malformed structure-extraction JSON | one automatic re-prompt, then `materials.status='failed'` + `error_message` (Part 9/18) | inline failed state + Retry | automatic x1 then manual |
| PDF with no detectable educational structure | zero `topics` rows persisted; processing continues normally | Learning Structure page shows an empty state; rest of the pipeline (chunks, Tutor, RAG) unaffected | — |
| Embedding failure | Celery retry x3 backoff, else `failed` | reflected via material status | automatic then manual |
| Groq failure (Tutor) | caught, graceful fallback text returned | "Having trouble responding — try again." | manual (per-message resend) |
| Malformed AI JSON (evaluation) | one automatic re-prompt, then "pending manual review" | "Evaluation is taking longer than expected." | automatic x1 then surfaced |
| Celery worker crash | job stuck `running` past timeout -> swept to `failed` | failed state, retry available | manual |
| Redis unavailable | dispatch raises -> 503 on triggering endpoint | "Service temporarily unavailable." | manual |
| Database failure | 500, transaction rolled back | generic error banner | manual |

---

## 24. Observability

`ai_usage` — one row per AI call (Tutor, quiz generation, evaluation, embeddings), success or failure, with feature/model/tokens/latency/cost. This is a deliberately single, simple table rather than a separate metrics pipeline — Admin's System tab reads it directly. Application logs are structured JSON (request id, user id, route, latency); Celery tasks log task id + outcome, cross-referenced to `background_jobs`.

---

## 25. Analytics

**Project**: activity count (7/30 days), quiz attempts + average score, mastery distribution across concepts, Tutor message count — one query per stat.

**Global (admin-only)**: total users, total projects, quiz attempts this week, `SUM(estimated_cost_usd)` from `ai_usage` this week — a single summary row, not a separate page.

---

## 26. Admin Dashboard

`users.is_admin` flag, three read-only tabs: **Users** (list + project count + last active), **Activity** (paginated `activity_events`), **System** (`background_jobs` by status, `ai_usage` weekly cost/latency). No admin write actions, no permissions system — explicitly out of scope for this build.

---

## 27. Testing

**pytest / pytest-asyncio:**
- Auth: Argon2 hash not plaintext; wrong password rejected; expired token rejected.
- Isolation: user A cannot `GET` user B's project (404); RAG retrieval never returns another project's chunks even on an identical query term (seed both, assert result set); a concept/subtopic/topic belonging to Project A is never resolvable through any Project B route, even by guessing its UUID (404 or empty result, not a leaked row).
- Structure extraction: malformed Groq JSON triggers exactly one re-prompt, then `materials.status='failed'` with no partial `topics`/`subtopics`/`concepts` rows committed (transaction rolled back, not just the top-level insert); a document with genuinely no structure reaches `status='ready'` with zero topics rather than failing.
- Structure extraction idempotency: retrying `extract_learning_structure` on a material that already has `topics` rows does not create duplicate or new concept rows, and does not orphan any `quiz_questions`/`mastery_evidence` already referencing the existing concepts.
- Mastery: `update_mastery` bounded to [0,100]; confidence never appears as an input to the formula (explicit regression test).
- Mismatch: gap at threshold triggers, one point below does not; insufficient evidence suppresses a flag despite a large gap.
- Decision Engine: a mismatched concept always scores `explain_back`/`review_material` above `targeted_quiz` for the same concept; repetition penalty reduces a repeated identical recommendation.

**Playwright:** login -> create project -> upload PDF -> wait for `ready` -> Learning Structure tree renders extracted topics/subtopics/concepts -> grounded Tutor question with citation -> out-of-scope question -> unsupported styling -> quiz with confidence (question generated against a specific concept) -> mastery updates visibly, drillable from topic down to concept -> Explain-It-Back triggered and evaluated -> recommendation updates afterward, showing the concept's topic/subtopic path.

---

## 28. Docker Compose Architecture

```yaml
services:
  frontend:
    build: ./frontend
    ports: ["5173:5173"]
    environment:
      - VITE_API_URL=http://localhost:8000     # browser-resolvable URL (v1 correction)

  backend:
    build: ./backend
    ports: ["8000:8000"]
    volumes:
      - uploads:/data/uploads
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/study_companion   # service name OK: container-to-container
      - REDIS_URL=redis://redis:6379/0                                      # service name OK: container-to-container
    depends_on: [postgres, redis]

  worker:
    build: ./backend            # same image as backend, different command
    command: celery -A app.workers worker --loglevel=info
    volumes:
      - uploads:/data/uploads   # same volume, same path - required for process_pdf to read what backend wrote
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/study_companion
      - REDIS_URL=redis://redis:6379/0
    depends_on: [postgres, redis]

  postgres:
    image: postgres:16
    volumes: ["pgdata:/var/lib/postgresql/data"]

  redis:
    image: redis:7

volumes:
  uploads:
  pgdata:
```

**The key distinction (v1 correction):** `backend`/`postgres`/`redis` are Docker Compose service names, resolvable only *inside* the Compose network — `backend` and `worker` correctly use `postgres`/`redis` as hostnames because container-to-container traffic stays on that network. The **browser** is not on that network; it runs on the developer's host machine and can only reach `localhost:8000` (the published port). `VITE_API_URL=http://backend:8000` would fail in the browser with a DNS error — it's set to `http://localhost:8000` in development and to the real public backend domain (`https://api.yourapp.com`, Part 33) in production.

---

## 29. Environment Variables

```
DATABASE_URL=postgresql://user:pass@postgres:5432/study_companion   # backend/worker only
REDIS_URL=redis://redis:6379/0                                       # backend/worker only
VITE_API_URL=http://localhost:8000                                   # browser-facing, dev
JWT_SECRET=change_me
JWT_EXPIRE_MINUTES=60
GROQ_API_KEY=
OPENAI_API_KEY=
UPLOAD_DIR=/data/uploads
MAX_UPLOAD_MB=20
EMBEDDING_MODEL=text-embedding-3-small
GROQ_MODEL=openai/gpt-oss-20b
MISMATCH_GAP_THRESHOLD=25
```

---

## 30. 3-4 Day Implementation Plan

**Day 1** — Auth, Spaces, Projects, full DB schema + Alembic, Docker Compose (all 5 services + shared uploads volume wired up front, not retrofitted later), `require_project_access` / project isolation.

**Day 2** — PDF upload -> shared volume -> Celery `process_pdf` -> `extract_learning_structure` (Groq/Pydantic -> topics/subtopics/concepts) -> `generate_embeddings` -> pgvector retrieval -> Tutor (synchronous, grounded, citations, unsupported handling).

**Day 3** — Adaptive Quiz, confidence-in-answer-submission, Open-ended Assessment, Explain-It-Back, MCQ + Applied mastery, Mismatch Detection.

**Day 4** — Decision Engine + recommendations, Project Dashboard, Exam Mode, Growth, Analytics, Admin, tests, error handling, UI polish.

**If behind schedule, never sacrifice (in order):** Topic/Subtopic/Concept extraction -> RAG grounding -> citations -> unsupported handling -> Adaptive Quiz -> confidence capture -> Explain-It-Back -> two-dimensional mastery -> mismatch detection -> Decision Engine. Structure extraction moves to the front of this list because every later item depends on a `concept_id` existing — quiz questions, mastery, and mismatch detection all have hard FK/logic dependencies on `concepts`. Compress Admin, Analytics, and Growth first — they're read-time views with no engine of their own to protect.

---

## 31. Demo Script (5-7 min)

1. Log in -> create Project "Gradient Descent" in an ML Space (0:30)
2. Upload a PDF, watch `queued->processing->ready` (0:30)
3. Learning Structure page: the extracted Topic -> Subtopic -> Concept tree — *"this came straight out of the PDF, not typed in by hand"* (0:30)
4. Tutor: grounded question with citation chip; then an out-of-scope question -> distinct unsupported response — *"this proves we're not hallucinating"* (1:00)
5. Quiz: answer several questions, confidence submitted with each answer, one deliberately confident-wrong (1:15)
6. Explain-It-Back triggers after a streak; give a deliberately shallow answer -> structured AI feedback (0:45)
7. Mastery page: `mcq_mastery=92 / applied_mastery=54` with the mismatch badge, same Topic -> Subtopic -> Concept tree from step 3 (0:30)
8. Project Dashboard: mismatch banner + Recommended Next Action card with its "Why" (0:30)
9. Growth: sparkline trend, drillable from topic down to concept (0:20)
10. Admin: Users / Activity / AI cost summary (0:30)

---

## 32. Known Limitations

- Mastery weights and the mismatch threshold (25 points) are hand-picked constants, presented honestly as practical defaults, not empirically validated.
- Chunking is fixed-size, not semantic — will occasionally split a concept mid-explanation.
- No refresh-token rotation, no full RBAC, no CSP headers — reasonable omissions at this scope, listed rather than silently skipped.
- `ivfflat` index parameters are untuned for real data volume (irrelevant at prototype scale — hundreds of chunks).
- Recommendation scoring weights are not learned from real student outcomes.
- Local Docker volume storage is a prototype-only choice; it doesn't survive a container rebuild without the named volume, and doesn't scale past a single host.

---

## 33. Future Improvements

Explicitly deferred, not designed further here: standalone AI notes, flashcards, concept dependency maps, a study planner, spaced repetition, audio/video, collaboration features, gamification, notifications, an exam-readiness score, live-lecture support, refresh-token rotation + full RBAC, semantic chunking, a learned/IRT-based quiz model, S3-compatible object storage in place of the local volume, and a managed Postgres/Redis + Vercel-frontend production deployment (frontend on Vercel, backend + worker on any Docker-compatible host, `VITE_API_URL` pointed at the real public backend domain instead of `localhost`).
