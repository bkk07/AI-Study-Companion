-- Phase 07: enable pgvector extension inside same PostgreSQL
-- Idempotent, runs on first init via /docker-entrypoint-initdb.d
CREATE EXTENSION IF NOT EXISTS vector;
