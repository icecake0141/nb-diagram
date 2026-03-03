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

---

## 日本語訳

### 概要

データベーススキーマは `migrations/` 配下の SQL ファイルで管理します。
各マイグレーションは 1 回だけ適用され、`schema_migrations` に記録されます。

### 実行時の挙動

- アプリ起動時、`init_storage()` から `apply_migrations()` が呼ばれます。
- `migrations/` 内の新しい `*.sql` は辞書順で適用されます。
- 適用済みバージョンは `schema_migrations.version` に保存されます。

### マイグレーション追加手順

1. 連番プレフィックス付きで新しい SQL ファイルを作成します（例: `0003_add_indexes.sql`）。
2. 可能な限り冪等にします（`CREATE TABLE IF NOT EXISTS` など）。
3. バックアップなしの破壊的変更は避けます。

### デプロイ手順

1. `data/results.db` をバックアップします。
2. 新しいコードをデプロイします。
3. アプリを一度起動し、起動ログにマイグレーションエラーがないことを確認します。
4. `schema_migrations` に新しいバージョン行があることを確認します。
5. API エンドポイントのスモークテストを実施します。

### ロールバック指針

- 自動ロールバック実行機能はありません。
- 順方向マイグレーションが失敗した場合:
  - アプリ停止
  - DB バックアップ復元
  - SQL 修正
  - 再デプロイ

### 補足

- この軽量マイグレーション方式は、現状のローカル SQLite 運用に意図的に合わせています。
- 複数環境での運用が拡大した場合は、Alembic と明示的なリビジョン管理へ移行してください。
