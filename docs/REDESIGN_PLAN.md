# nb-cartographer Redesign Plan

## Goals

- Separate CSV ingestion, domain normalization, and presentation/export concerns.
- Make parsing deterministic by persisting explicit column mappings.
- Move to API-first flow so UI and exports consume the same normalized graph.
- Keep backward compatibility during migration.

## Target Architecture

### Layers

1. `ingest`: file upload, encoding detection, schema mapping, validation.
2. `domain`: canonical entities and graph derivation.
3. `application`: import jobs, orchestration, persistence boundaries.
4. `interfaces`: HTTP API, web UI, exporters (drawio/json/csv).

### Suggested Directory Layout

```text
nb-cartographer/
  app/
    __init__.py
    config.py
    api/
      routes_imports.py
      routes_graphs.py
      routes_exports.py
      schemas.py
    ingest/
      parser.py
      mapping.py
      validators.py
      encoding.py
    domain/
      models.py
      role_classifier.py
      graph_builder.py
    application/
      services/
        import_service.py
        graph_service.py
        export_service.py
      repositories/
        import_repo.py
        artifact_repo.py
    infrastructure/
      db.py
      storage.py
      queue.py
      logging.py
    exporters/
      drawio.py
      graph_json.py
      csv_original.py
  frontend/
    src/
      pages/
      components/
      store/
      graph/
      api/
  migrations/
  tests/
    unit/
    contract/
    integration/
    e2e/
  docs/
    REDESIGN_PLAN.md
```

## Data Model

### Core Entities

- `ImportRun`: upload metadata, status, errors, mapping version.
- `RawCableRow`: immutable raw row snapshot.
- `Device`: canonical device identity.
- `Endpoint`: typed termination bound to device.
- `Cable`: logical cable connecting two endpoints.
- `Rack`, `Location`: optional placement hierarchy.
- `GraphArtifact`: derived view metadata (`device_graph`, `interface_graph`, `drawio`).

### Storage Tables (Initial)

- `import_runs`
- `column_mappings`
- `raw_cable_rows`
- `devices`
- `endpoints`
- `cables`
- `racks`
- `locations`
- `graph_artifacts`

## API Contract (V1)

- `POST /api/imports`
  - Accepts CSV.
  - Returns `import_id` and detected mapping candidates.
- `PUT /api/imports/{id}/mapping`
  - Confirms mapping to run deterministic parse.
- `POST /api/imports/{id}/execute`
  - Runs normalization (sync first, async-ready).
- `GET /api/imports/{id}`
  - Status, validation errors, stats.
- `GET /api/graphs/{id}?view=device|interface`
  - Returns normalized graph payload.
- `GET /api/exports/{id}?format=json|drawio|csv`
  - Stream export artifact.

## Migration Strategy

### Phase 1: Strangler Entry

1. Introduce `app/` package and move current logic behind services.
2. Keep existing HTML route endpoints working.
3. Add API endpoints that call same service layer.
4. Add drawio XML validity tests and mapping persistence tests.

### Phase 2: Deterministic Mapping

1. Replace implicit `choose_columns()` flow with:
   - candidate suggestion
   - user-confirmed mapping
   - persisted mapping profile
2. Add schema mismatch warnings with row-level diagnostics.

### Phase 3: Frontend Split

1. Move large inline JS from template into `frontend/`.
2. Consume `GET /api/graphs/{id}` only.
3. Keep feature parity (filters, focus, saved layout, legend toggles).

### Phase 4: Decommission

1. Remove old monolithic `app.py` flow.
2. Keep compatibility redirects for `/result/<id>` and `/files/...`.
3. Freeze and document final API version.

## Testing Strategy

- Unit
  - parser normalization
  - role classification
  - exporter escaping (XML/HTML safety)
- Contract
  - API response schema and error model
- Integration
  - import -> normalize -> graph -> export end-to-end
- E2E
  - upload, filter, focus, save/load layout in browser

## Immediate Backlog (First 8 Tasks)

1. Create `app/` package skeleton and app factory.
2. Extract CSV parsing into `app/ingest/parser.py`.
3. Extract domain graph builders into `app/domain/graph_builder.py`.
4. Add `app/exporters/drawio.py` with strict attribute escaping.
5. Add `POST /api/imports` and `GET /api/imports/{id}`.
6. Add migration framework (`alembic`) and first schema migration.
7. Add contract tests for import and graph endpoints.
8. Wire existing template route to new services (no UI change yet).

## Definition of Done (for Redesign Cutover)

- Monolithic parsing/render logic removed from top-level `app.py`.
- All exports generated from normalized domain model.
- Mapping profiles persisted and reusable.
- Existing user workflows (upload/view/download/filter) still functional.
- Tests cover parser, API contract, drawio validity, and key UI interactions.

---

## 日本語訳

### 目的

- CSV 取り込み、ドメイン正規化、表示/エクスポートの関心を分離する。
- 明示的な列マッピングを保存し、解析を決定的にする。
- API-first フローへ移行し、UI とエクスポートが同じ正規化グラフを利用する。
- 移行中の後方互換性を維持する。

### 目標アーキテクチャ

#### レイヤー

1. `ingest`: ファイルアップロード、文字コード判定、スキーママッピング、バリデーション。
2. `domain`: 正規化されたエンティティとグラフ導出。
3. `application`: import ジョブ、オーケストレーション、永続化境界。
4. `interfaces`: HTTP API、Web UI、エクスポーター（drawio/json/csv）。

#### 推奨ディレクトリ構成

```text
nb-cartographer/
  app/
    __init__.py
    config.py
    api/
      routes_imports.py
      routes_graphs.py
      routes_exports.py
      schemas.py
    ingest/
      parser.py
      mapping.py
      validators.py
      encoding.py
    domain/
      models.py
      role_classifier.py
      graph_builder.py
    application/
      services/
        import_service.py
        graph_service.py
        export_service.py
      repositories/
        import_repo.py
        artifact_repo.py
    infrastructure/
      db.py
      storage.py
      queue.py
      logging.py
    exporters/
      drawio.py
      graph_json.py
      csv_original.py
  frontend/
    src/
      pages/
      components/
      store/
      graph/
      api/
  migrations/
  tests/
    unit/
    contract/
    integration/
    e2e/
  docs/
    REDESIGN_PLAN.md
```

### データモデル

#### コアエンティティ

- `ImportRun`: アップロードメタデータ、状態、エラー、マッピングバージョン。
- `RawCableRow`: 不変な生データ行スナップショット。
- `Device`: 正規化されたデバイス識別子。
- `Endpoint`: デバイスに紐づく型付き終端。
- `Cable`: 2つの終端を結ぶ論理ケーブル。
- `Rack`, `Location`: 任意の配置階層。
- `GraphArtifact`: 派生ビューのメタデータ（`device_graph`, `interface_graph`, `drawio`）。

#### 初期テーブル

- `import_runs`
- `column_mappings`
- `raw_cable_rows`
- `devices`
- `endpoints`
- `cables`
- `racks`
- `locations`
- `graph_artifacts`

### API 契約（V1）

- `POST /api/imports`
  - CSV を受け付ける。
  - `import_id` と推定マッピング候補を返す。
- `PUT /api/imports/{id}/mapping`
  - マッピングを確定し、決定的な解析を実行可能にする。
- `POST /api/imports/{id}/execute`
  - 正規化を実行する（まず同期、将来的に非同期対応）。
- `GET /api/imports/{id}`
  - 状態、バリデーションエラー、統計情報を返す。
- `GET /api/graphs/{id}?view=device|interface`
  - 正規化グラフペイロードを返す。
- `GET /api/exports/{id}?format=json|drawio|csv`
  - エクスポート成果物をストリーム返却する。

### 移行戦略

#### Phase 1: Strangler Entry

1. `app/` パッケージを導入し、既存ロジックをサービス層の背後へ移す。
2. 既存の HTML ルートを動作維持する。
3. 同じサービス層を呼ぶ API を追加する。
4. drawio XML 妥当性テストとマッピング永続化テストを追加する。

#### Phase 2: Deterministic Mapping

1. 暗黙的な `choose_columns()` を以下の流れへ置き換える:
   - 候補提示
   - ユーザー確定マッピング
   - マッピングプロファイル永続化
2. 行単位診断付きのスキーマ不一致警告を追加する。

#### Phase 3: Frontend Split

1. テンプレート内の大きなインライン JS を `frontend/` へ移す。
2. `GET /api/graphs/{id}` のみを利用する。
3. 機能同等性（フィルタ、フォーカス、レイアウト保存、凡例トグル）を維持する。

#### Phase 4: Decommission

1. 旧来の単一 `app.py` フローを削除する。
2. `/result/<id>` と `/files/...` の互換リダイレクトを維持する。
3. 最終 API バージョンを固定し、文書化する。

### テスト戦略

- Unit
  - パーサ正規化
  - ロール分類
  - エクスポーターのエスケープ（XML/HTML 安全性）
- Contract
  - API レスポンススキーマとエラーモデル
- Integration
  - import -> normalize -> graph -> export の E2E 連携
- E2E
  - ブラウザで upload, filter, focus, save/load layout

### 直近バックログ（最初の8タスク）

1. `app/` パッケージ骨組みと app factory を作成。
2. CSV 解析を `app/ingest/parser.py` へ分離。
3. ドメイングラフ構築を `app/domain/graph_builder.py` へ分離。
4. 厳密な属性エスケープを行う `app/exporters/drawio.py` を追加。
5. `POST /api/imports` と `GET /api/imports/{id}` を追加。
6. マイグレーション基盤（`alembic`）と初回スキーマを追加。
7. import/graph エンドポイントの契約テストを追加。
8. 既存テンプレートルートを新サービスへ接続（UI 変更なし）。

### 完了条件（再設計カットオーバー）

- トップレベル `app.py` から単一の解析/描画ロジックが除去されている。
- すべてのエクスポートが正規化済みドメインモデルから生成される。
- マッピングプロファイルが永続化され、再利用できる。
- 既存ユーザーフロー（upload/view/download/filter）が継続動作する。
- パーサ、API 契約、drawio 妥当性、主要 UI 操作をテストで担保する。
