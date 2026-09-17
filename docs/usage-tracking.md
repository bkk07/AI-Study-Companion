# Usage Tracking — Architecture Note (Phases 0–3, 5)

Two additive observability streams. Neither changes existing user-facing
behavior; both are best-effort and never break requests.

## Why two tables, not one

| | `learning_events` (§12) | `ai_usage` (§14) |
|---|---|---|
| Answers | who did what, where, when | what each LLM call cost, did it work |
| Write session | caller's session (atomic with domain write) | dedicated `SessionLocal` (survives caller rollback — tokens were spent even when the request fails) |
| Dedup | `idempotency_key` unique + `ON CONFLICT DO NOTHING` (retries safe by construction) | append-only, one row per provider attempt incl. retries (each retry is real spend) |
| Reads | user journey timeline, activity feed | cost/latency/error aggregates per feature × model × day |

A single table would force one write semantic on two different needs:
events must roll back with failed domain writes (no phantom
`quiz.completed`), while usage must persist through them. Separate
tables keep both correct.

## Choke-point instrumentation

All LLM traffic flows through `groq_client.chat_json`. It appends one
`LLMCallRecord` per HTTP attempt (success or failure) to a
context-local scope — never prompt/response text. Call sites wrap the
existing call in `ai_usage_service.track_llm_call(user_id, project_id,
feature, meta)`, which drains the scope on exit and persists rows. No
caller signatures changed; injected test fakes bypass `chat_json`, so
unit tests record nothing. Token counts come from the provider `usage`
block, falling back to `len/4` flagged with `tokens_estimated=true`.

Events use the mirror pattern: `activity_service.record_event(db, …,
idempotency_key)` joins the caller's transaction via savepoint
(`record_event_committed` for post-commit emit sites).

## Cost is an estimate

`app/services/ai/pricing.py` holds USD-per-1M-token rates, computed at
write time into `cost_usd`. Mercury 2.5 uses the verified promo rate
($0.04/$0.15 per 1M in/out); other models are placeholders. Unknown
models store `NULL` rather than a fabricated number. These are for
relative attribution across features/models, not billing. Rows written
before a rate change keep the old cost (write-time snapshot).

## PII discipline

`ai_usage` columns: feature, provider, model, token counts,
`tokens_estimated`, latency, success, `error_type`, `http_status`,
`cost_usd`, `meta`. `learning_events` columns: scope ids, event type,
`(entity_type, entity_id)`, small payload (scores/counts/ids),
`idempotency_key`. There is deliberately no prompt, response, document,
answer-text, or free-text error column — exception text can echo user
content, so `(error_type, http_status)` is all we keep. Enforced by
`test_ai_usage.py` / `test_learning_events.py` column assertions.

## Event catalog

`project.created`, `material.uploaded`, `material.ready`,
`material.failed`, `tutor.message`, `quiz.started`, `quiz.completed`,
`question.answered`, `assessment.completed`, `mastery.updated`,
`recommendation.generated` — closed set via `ck_learning_events_type`.
Emitters: `project_service`, `materials` API, `extraction` worker,
`tutor_conversation_service`, `quiz_attempt_service`,
`explain_it_back_service`, `flashcard_service`, `mastery_service`,
`recommendation_service.recommend` (single choke point covering worker
+ dashboard + direct callers).

## Backfill

`backend/scripts/backfill_learning_events.py` derives history from
domain `created_at` with live key formats, `ON CONFLICT DO NOTHING`
(idempotent re-runs). Run once after migration `e5f6a7b8c9d0`.

## Known limitations

- Token fallback (`len/4`, flagged) when a provider omits `usage`. The
  parser accepts both `prompt_tokens`/`completion_tokens` and
  `input_tokens`/`output_tokens` shapes so provider variants record
  exact counts (test: `test_chat_json_accepts_input_output_token_aliases`).
  Verified live against Inception: usage carries standard
  `prompt_tokens`/`completion_tokens`/`total_tokens` keys; Mercury's
  `completion_tokens` includes reasoning tokens (billed as output), so
  recorded output counts look large next to the tiny JSON returned.
- No streaming-token counts: all calls are non-streaming JSON mode.
- Embeddings not metered (local model, no provider spend).
- Read-only `grade_open_ended` API emits no event until persisted as evidence.
- Backfilled `material.failed` keys use `material:{id}:failed`; live failures key per job (`job:{id}:failed`).
- Admin aggregates capped (500 grouped rows, page limit 100); p50/p95 need non-null latencies.
- `recommendation.generated` fires only when a winner is persisted (`recommend` returns `None` on nothing scorable).

## Verification (Phase 5)

- Idempotency: `test_learning_events.py::test_double_emit_same_key_yields_one_row`.
- Never breaks: `test_ai_usage.py` (metering DB down), `test_learning_events.py`
  (bad-FK event preserves caller txn), `test_tracking_resilience.py`
  (tutor ask + quiz submit/complete still HTTP 200 with tracking broken).
- PII: column assertions in both tracking test files.
- Admin auth: `test_admin_reads.py::test_non_admin_refused_on_all_new_endpoints`
  (401 anon, 403 non-admin, 200 admin on all four endpoints).
