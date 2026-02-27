# Migration Operations

## Overview

Database schema is managed by SQL files under `migrations/`.
Each migration is applied once and tracked in `schema_migrations`.

## Runtime Behavior

- On app startup, `init_storage()` calls `apply_migrations()`.
- New `*.sql` files in `migrations/` are applied in lexicographical order.
- Applied versions are persisted in `schema_migrations.version`.

## Adding a Migration

1. Create a new SQL file with an incremented prefix, for example:
   - `0003_add_indexes.sql`
2. Keep migrations idempotent when possible (`CREATE TABLE IF NOT EXISTS`, etc.).
3. Avoid destructive changes without backup.

## Deployment Runbook

1. Backup `data/results.db`.
2. Deploy new code.
3. Start app once and confirm startup logs show no migration errors.
4. Verify `schema_migrations` contains new version rows.
5. Run smoke tests on API endpoints.

## Rollback Guidance

- There is no automatic rollback runner.
- For failed forward migration:
  - stop app,
  - restore DB backup,
  - fix SQL,
  - redeploy.

## Notes

- This lightweight migration approach is intentional for the current local SQLite deployment.
- If multi-environment deployment grows, replace with Alembic and explicit revision metadata.
