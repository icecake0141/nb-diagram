# Specification

## English

### Overview

- Input: NetBox `Cables` CSV
- Output: Aggregated topology (UI / JSON / CSV / drawio)
- Architecture: Flask backend + TypeScript frontend

### Key Features

- CSV upload and topology generation
- Aggregated device-to-device graph (edge width reflects link count)
- Rack-based parent-child structure
- Role-inference-based node type filtering
- SVG / drawio export
- Reconcile API (`payload` / `snmp` / `ssh`)

### Compatibility / Deprecation

- `POST /upload` is deprecated and returns `410`
- New clients should use the API-first workflow under `/api/...`
- Existing saved-result endpoints remain available:
  - `GET /result/<id>`
  - `GET /files/<id>/<kind>`

### Persistence

- Metadata: `data/results.db` (SQLite)
- Uploaded CSV files: `data/uploads/`
- Generated data: `data/results/`
- drawio is generated on demand at download time (not stored)

### CSV Column Mapping

- Column names are normalized and auto-detected (symbol/case tolerant)
- `Rack A/B` and `Location A/B` are fixed column names
- Required: A/B side device and port
  - e.g. `Termination A Device`, `Termination A Name`, `Termination B Device`, `Termination B Name`
  - e.g. `Termination A`, `Termination B` (auto-split from `device:port`)
- Optional:
  - `Termination A Type`, `Termination B Type`
  - `ID`, `Label`, `Type`, `Color`
  - `Rack A`, `Rack B`
  - `Location A`, `Location B`

### Data Transformation Rules

- Auto-detect encoding from `utf-8-sig` / `utf-8` / `cp932` / `shift_jis`
- If `Label` is empty, use `Cable-{ID}` (or row number if `ID` is missing)
- If `Type` is empty, use `Unknown`
- If `Color` is valid `#RRGGBB`, use it as-is
- If `Color` is empty/invalid, derive a stable color hash from `Type`
- If `Termination A/B` is `device:port`, split automatically
- Infer endpoint kind from termination type:
  - `front_port`, `rear_port`, `circuit_termination`, `power_port`, `power_outlet`, `power_feed`, `interface`
- Infer domain from endpoint kind:
  - `data`, `pass_through`, `circuit`, `power`

### API Workflow

Base flow:

1. `POST /api/imports`
2. `PUT /api/imports/<id>/mapping`
3. `POST /api/imports/<id>/execute`
4. `GET /api/graphs/<id>?view=device|interface`
5. `GET /api/exports/<id>?format=json|drawio|csv`

Related endpoints:

- `GET /api/imports/<id>`
- `POST /api/results/<id>/drawio-layout`
- `POST /api/reconcile-runs`
- `POST /api/reconcile-runs/<id>/execute` (`?async=true` supported)
- `GET /api/reconcile-runs/<id>`
- `POST /api/reconcile/compare`
- `GET /api/reconcile/ssh-vendors`
- `GET /api/openapi.yaml`

### UI and Endpoints

- `GET /`: initial page (saved result list)
- `GET /result/<id>`: reopen saved result
- `GET /files/<id>/csv|graph|drawio`: download artifacts

Main UI actions:

- Labels / Search + Hop / Clear / Reset View
- Save Layout / Load Layout
- Download SVG / Download drawio (Current Layout)
- Cable Media and Node Types legend toggles
- Column filters and two-way highlighting with the connection table

---

## 日本語訳

### 概要

- 入力: NetBox `Cables` CSV
- 出力: 集約トポロジ（画面表示 / JSON / CSV / drawio）
- アーキテクチャ: Flask バックエンド + TypeScript フロントエンド

### 主な機能

- CSV アップロードとトポロジ生成
- デバイス間を集約したグラフ表示（リンク本数をエッジ幅に反映）
- ラック単位の親子構造表示
- ロール推定ベースのノードタイプ表示切替
- SVG / drawio エクスポート
- 比較用 Reconcile API（`payload` / `snmp` / `ssh`）

### 互換性 / 非推奨

- `POST /upload` は非推奨（`410` を返却）
- 新規クライアントは `/api/...` の API-first ワークフローを利用
- 既存の結果取得エンドポイントは継続利用可能
  - `GET /result/<id>`
  - `GET /files/<id>/<kind>`

### 永続化

- メタデータ: `data/results.db` (SQLite)
- アップロードCSV: `data/uploads/`
- 生成データ: `data/results/`
- drawio はダウンロード時にオンデマンド生成（保存しない）

### CSV 列マッピング

- 列名は正規化して自動検出（記号・大文字小文字の揺らぎに対応）
- `Rack A/B` と `Location A/B` は列名固定
- 必須: A/B 側の device / port
  - 例: `Termination A Device`, `Termination A Name`, `Termination B Device`, `Termination B Name`
  - 例: `Termination A`, `Termination B`（`device:port` を自動分解）
- 任意:
  - `Termination A Type`, `Termination B Type`
  - `ID`, `Label`, `Type`, `Color`
  - `Rack A`, `Rack B`
  - `Location A`, `Location B`

### データ変換ルール

- 文字コードを `utf-8-sig` / `utf-8` / `cp932` / `shift_jis` から自動判定
- `Label` が空の場合は `Cable-{ID}`（`ID` なしの場合は行番号）
- `Type` が空の場合は `Unknown`
- `Color` が `#RRGGBB` ならそのまま利用
- `Color` が空/不正なら `Type` から安定ハッシュで色を割り当て
- `Termination A/B` が `device:port` 形式なら自動分解
- 終端タイプから endpoint 種別を判定
  - `front_port`, `rear_port`, `circuit_termination`, `power_port`, `power_outlet`, `power_feed`, `interface`
- endpoint 種別からドメインを判定
  - `data`, `pass_through`, `circuit`, `power`

### API ワークフロー

基本フロー:

1. `POST /api/imports`
2. `PUT /api/imports/<id>/mapping`
3. `POST /api/imports/<id>/execute`
4. `GET /api/graphs/<id>?view=device|interface`
5. `GET /api/exports/<id>?format=json|drawio|csv`

関連エンドポイント:

- `GET /api/imports/<id>`
- `POST /api/results/<id>/drawio-layout`
- `POST /api/reconcile-runs`
- `POST /api/reconcile-runs/<id>/execute`（`?async=true` 対応）
- `GET /api/reconcile-runs/<id>`
- `POST /api/reconcile/compare`
- `GET /api/reconcile/ssh-vendors`
- `GET /api/openapi.yaml`

### 画面・操作

- `GET /`: 初期画面（保存済み結果一覧）
- `GET /result/<id>`: 保存済み結果の再表示
- `GET /files/<id>/csv|graph|drawio`: 生成物ダウンロード

UI 操作（主要）:

- Labels / Search + Hop / Clear / Reset View
- Save Layout / Load Layout
- Download SVG / Download drawio (Current Layout)
- Cable Media 凡例 / Node Types 凡例のトグル
- 接続一覧テーブルの列フィルタと双方向ハイライト
