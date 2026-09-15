# Shared Upload Volume — Phase 20

This document describes the shared filesystem used for PDF uploads between the `api` and `worker` services.

## Volume

- **Name:** `uploads` (named volume, `docker-compose.yml:110-113`)
- **Mount point (both services):** `uploads:/data/uploads`
  - `api:  volumes: ["uploads:/data/uploads"]`
  - `worker: volumes: ["uploads:/data/uploads"]`
- **Environment:** Both `api` and `worker` set `UPLOAD_DIR=/data/uploads` (also `backend/app/core/config.py:39` default).
- **Database:** `Material.storage_path` stores the full container path (e.g. `/data/uploads/{project_id}/{uuid}.pdf`), consistent with the mount.

## Behavior

- `backend/app/services/storage_service.py:save_pdf` writes to `UPLOAD_DIR/{project_id}/{uuid}.pdf` (server-controlled, no client path trust).
- The same absolute path is readable from either container; callers use `material.id`, not paths.

## Phase 19 → 20 integration

- Phase 19 `POST /api/v1/projects/{project_id}/materials` creates a `Material` row `status pending` and writes the PDF bytes to the shared volume.
- Phase 20 guarantees the later background jobs (Celery `worker`) can read the same file for extraction/embeddings via the same `storage_path`.

## Verification

```sh
docker compose up -d --build api worker  # or `docker compose up -d`
docker compose exec api sh -c "echo hello-shared > /data/uploads/probe.txt && cat /data/uploads/probe.txt"
docker compose exec worker cat /data/uploads/probe.txt  # must print hello-shared
docker volume inspect aistudycompanion_uploads  # Mountpoint on host
```

Isolation: volumes `postgres_data`, `redis_data`, `uploads` are distinct; only `uploads` is shared.

## Guard

Do not create separate, non-shared upload directories for `api` vs `worker`. Keep mount paths identical.
