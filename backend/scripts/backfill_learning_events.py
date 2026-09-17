"""One-off backfill: derive historical learning_events from domain rows (Phase 2).

Usage:
    python scripts/backfill_learning_events.py

Idempotent: every INSERT uses the same idempotency_key format as the live
emit sites with ON CONFLICT DO NOTHING, so re-runs are safe. Run once
after the e5f6a7b8c9d0 migration so the admin timeline isn't empty.
Live emits remain the source of truth going forward.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text  # noqa: E402

STATEMENTS = [
    # project.created
    ("""INSERT INTO learning_events
        (id, created_at, updated_at, user_id, project_id, space_id,
         event_type, entity_type, entity_id, payload, idempotency_key)
        SELECT gen_random_uuid(), p.created_at, now(),
               s.user_id, p.id, p.space_id,
               'project.created', 'project', p.id,
               '{"backfilled": true}', 'project:' || p.id || '\\:created'
        FROM projects p JOIN spaces s ON s.id = p.space_id
        ON CONFLICT (idempotency_key) DO NOTHING""", "project.created"),
    # material.uploaded (all materials were uploaded once)
    ("""INSERT INTO learning_events
        (id, created_at, updated_at, user_id, project_id, space_id,
         event_type, entity_type, entity_id, payload, idempotency_key)
        SELECT gen_random_uuid(), m.created_at, now(),
               s.user_id, m.project_id, p.space_id,
               'material.uploaded', 'material', m.id,
               '{"backfilled": true}', 'material:' || m.id || '\\:uploaded'
        FROM materials m
        JOIN projects p ON p.id = m.project_id
        JOIN spaces s ON s.id = p.space_id
        ON CONFLICT (idempotency_key) DO NOTHING""", "material.uploaded"),
    # material.ready
    ("""INSERT INTO learning_events
        (id, created_at, updated_at, user_id, project_id, space_id,
         event_type, entity_type, entity_id, payload, idempotency_key)
        SELECT gen_random_uuid(), m.updated_at, now(),
               s.user_id, m.project_id, p.space_id,
               'material.ready', 'material', m.id,
               '{"backfilled": true}', 'material:' || m.id || '\\:ready'
        FROM materials m
        JOIN projects p ON p.id = m.project_id
        JOIN spaces s ON s.id = p.space_id
        WHERE m.status = 'ready'
        ON CONFLICT (idempotency_key) DO NOTHING""", "material.ready"),
    # material.failed (key per material; live failures key per job — both dedupe safely)
    ("""INSERT INTO learning_events
        (id, created_at, updated_at, user_id, project_id, space_id,
         event_type, entity_type, entity_id, payload, idempotency_key)
        SELECT gen_random_uuid(), m.updated_at, now(),
               s.user_id, m.project_id, p.space_id,
               'material.failed', 'material', m.id,
               '{"backfilled": true}', 'material:' || m.id || '\\:failed'
        FROM materials m
        JOIN projects p ON p.id = m.project_id
        JOIN spaces s ON s.id = p.space_id
        WHERE m.status = 'failed'
        ON CONFLICT (idempotency_key) DO NOTHING""", "material.failed"),
    # tutor.message (assistant replies only — one row per exchange, like live)
    ("""INSERT INTO learning_events
        (id, created_at, updated_at, user_id, project_id, space_id,
         event_type, entity_type, entity_id, payload, idempotency_key)
        SELECT gen_random_uuid(), tm.created_at, now(),
               tc.user_id, tc.project_id, p.space_id,
               'tutor.message', 'message', tm.id,
               '{"backfilled": true}', 'message:' || tm.id
        FROM tutor_messages tm
        JOIN tutor_conversations tc ON tc.id = tm.conversation_id
        JOIN projects p ON p.id = tc.project_id
        WHERE tm.role = 'assistant'
        ON CONFLICT (idempotency_key) DO NOTHING""", "tutor.message"),
    # quiz.started
    ("""INSERT INTO learning_events
        (id, created_at, updated_at, user_id, project_id, space_id,
         event_type, entity_type, entity_id, payload, idempotency_key)
        SELECT gen_random_uuid(), COALESCE(qa.started_at, qa.created_at), now(),
               qa.user_id, q.project_id, p.space_id,
               'quiz.started', 'attempt', qa.id,
               '{"backfilled": true}', 'attempt:' || qa.id || '\\:started'
        FROM quiz_attempts qa
        JOIN quizzes q ON q.id = qa.quiz_id
        JOIN projects p ON p.id = q.project_id
        ON CONFLICT (idempotency_key) DO NOTHING""", "quiz.started"),
    # quiz.completed
    ("""INSERT INTO learning_events
        (id, created_at, updated_at, user_id, project_id, space_id,
         event_type, entity_type, entity_id, payload, idempotency_key)
        SELECT gen_random_uuid(), qa.completed_at, now(),
               qa.user_id, q.project_id, p.space_id,
               'quiz.completed', 'attempt', qa.id,
               jsonb_build_object('score', qa.score, 'backfilled', true),
               'quiz:' || qa.id || '\\:completed'
        FROM quiz_attempts qa
        JOIN quizzes q ON q.id = qa.quiz_id
        JOIN projects p ON p.id = q.project_id
        WHERE qa.completed_at IS NOT NULL
        ON CONFLICT (idempotency_key) DO NOTHING""", "quiz.completed"),
    # question.answered
    ("""INSERT INTO learning_events
        (id, created_at, updated_at, user_id, project_id, space_id,
         event_type, entity_type, entity_id, payload, idempotency_key)
        SELECT gen_random_uuid(), qans.answered_at, now(),
               qa.user_id, q.project_id, pr.space_id,
               'question.answered', 'answer', qans.id,
               jsonb_build_object('is_correct', qans.is_correct, 'backfilled', true),
               'answer:' || qans.id
        FROM quiz_answers qans
        JOIN quiz_attempts qa ON qa.id = qans.attempt_id
        JOIN quizzes q ON q.id = qa.quiz_id
        JOIN projects pr ON pr.id = q.project_id
        ON CONFLICT (idempotency_key) DO NOTHING""", "question.answered"),
    # mastery.updated (every evidence row banked mastery)
    ("""INSERT INTO learning_events
        (id, created_at, updated_at, user_id, project_id, space_id,
         event_type, entity_type, entity_id, payload, idempotency_key)
        SELECT gen_random_uuid(), me.created_at, now(),
               me.user_id, me.project_id, p.space_id,
               'mastery.updated', 'evidence', me.id,
               jsonb_build_object('source', me.source, 'backfilled', true),
               'evidence:' || me.id || '\\:mastery'
        FROM mastery_evidence me
        JOIN projects p ON p.id = me.project_id
        ON CONFLICT (idempotency_key) DO NOTHING""", "mastery.updated"),
    # assessment.completed (applied evidence only)
    ("""INSERT INTO learning_events
        (id, created_at, updated_at, user_id, project_id, space_id,
         event_type, entity_type, entity_id, payload, idempotency_key)
        SELECT gen_random_uuid(), me.created_at, now(),
               me.user_id, me.project_id, p.space_id,
               'assessment.completed', 'evidence', me.id,
               jsonb_build_object('score', me.raw_score, 'backfilled', true),
               'evidence:' || me.id || '\\:assessment'
        FROM mastery_evidence me
        JOIN projects p ON p.id = me.project_id
        WHERE me.evidence_type IN ('explain_back', 'open_ended')
        ON CONFLICT (idempotency_key) DO NOTHING""", "assessment.completed"),
    # recommendation.generated
    ("""INSERT INTO learning_events
        (id, created_at, updated_at, user_id, project_id, space_id,
         event_type, entity_type, entity_id, payload, idempotency_key)
        SELECT gen_random_uuid(), r.created_at, now(),
               r.user_id, r.project_id, p.space_id,
               'recommendation.generated', 'recommendation', r.id,
               jsonb_build_object('action', r.action_type, 'backfilled', true),
               'recommendation:' || r.id
        FROM recommendations r
        JOIN projects p ON p.id = r.project_id
        ON CONFLICT (idempotency_key) DO NOTHING""", "recommendation.generated"),
]


def main() -> None:
    url = os.getenv("DATABASE_URL")
    if not url:
        print("DATABASE_URL is not set", file=sys.stderr)
        raise SystemExit(1)
    engine = create_engine(url, pool_pre_ping=True, future=True)
    total = 0
    with engine.begin() as conn:
        for sql, label in STATEMENTS:
            result = conn.execute(text(sql))
            n = result.rowcount if result.rowcount and result.rowcount > 0 else 0
            total += n
            print(f"{label}: {n} inserted")
    print(f"done: {total} events backfilled")
    engine.dispose()


if __name__ == "__main__":
    main()
