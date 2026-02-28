# NetBox Cable Diagram Generator

## English

A Flask app that generates an aggregated topology diagram between devices from a NetBox `Cables` CSV.

### Table of Contents

- [Quick Start](#quick-start)
- [Key Features](#key-features)
- [Setup](#setup)
- [Compatibility / Breaking Changes](#compatibility--breaking-changes)
- [API Example](#api-example)
- [Directory Structure](#directory-structure)
- [Test / Lint / Format](#test--lint--format)
- [Troubleshooting](#troubleshooting)
- [Persistence Specification](#persistence-specification)
- [CSV Column Mapping](#csv-column-mapping)
- [Data Transformation Rules](#data-transformation-rules)
- [Diagram Operations](#diagram-operations)
- [Screens and Endpoints](#screens-and-endpoints)
- [API-first Workflow (v1)](#api-first-workflow-v1)
- [Frontend Modules](#frontend-modules)
- [Frontend Build](#frontend-build)
- [Release](#release)

### Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open `http://localhost:8000` and use the API workflow panel on the page.

### Key Features

- Upload a CSV and generate a topology diagram.
- Aggregated device-to-device graph display (edge width reflects link count).
- Draw racks as group nodes and place devices under each rack.
- Automatic role classification (`core` / `leaf` / `server` / `external` / `patch_panel` / `pdu`, etc.).
- Rack-level filter, component-level filter, and server visibility toggle.
- Node type filter (`role`-based: `core` / `leaf` / `server` / etc.).
- Per-rack server collapse display.
- Click the Cable Type legend to toggle media visibility.
- Node Types legend with toggle-by-role visibility.
- Device-name search with hop-based focus.
- Label detail level switching (`standard` / `minimal` / `detailed`).
- Layout save/load via browser `localStorage`.
- Download current diagram as SVG (with current layout).
- Export drawio with current on-screen layout.
- Return to automatic layout with `Reset View`.
- `Type / Color` legend, endpoint type legend, and connection table.
- Connection table column filters and graph<->table linked highlighting.
- Persist results and reopen/download CSV/JSON/drawio outputs later.

### Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Recommended: Python 3.11

After startup, open `http://localhost:8000` and upload a CSV.

### Compatibility / Breaking Changes

- `POST /upload` is deprecated and returns `410`.
- Existing saved result endpoints remain available:
  - `GET /result/<id>`
  - `GET /files/<id>/<kind>`
- New clients should use API-first workflow endpoints under `/api/...`.

### API Example

```bash
# 1) Create import run
curl -X POST -F "csv_file=@samples/netbox_cables.csv" http://127.0.0.1:8000/api/imports

# 2) Save mapping (use mapping_candidates returned above)
curl -X PUT -H "Content-Type: application/json" \
  -d '{"mapping":{"a_device":"Device A","a_port":"Termination A","b_device":"Device B","b_port":"Termination B"}}' \
  http://127.0.0.1:8000/api/imports/1/mapping

# 3) Execute
curl -X POST http://127.0.0.1:8000/api/imports/1/execute

# 4) Get graph
curl "http://127.0.0.1:8000/api/graphs/1?view=device"

# 5) Export drawio
curl -L "http://127.0.0.1:8000/api/exports/1?format=drawio" -o result.drawio
```

### Reconcile API Example

```bash
# One-shot compare (does not persist reconcile run)
curl -X POST -H "Content-Type: application/json" \
  -d '{
    "import_id": 1,
    "method": "payload",
    "params": {
      "neighbors": [
        {"local_device": "sw1", "local_interface": "xe-0/0/1", "remote_device": "sw2", "remote_interface": "xe-0/0/2"}
      ]
    }
  }' \
  http://127.0.0.1:8000/api/reconcile/compare

# Persisted run with SNMP (recommended: use environment reference)
curl -X POST -H "Content-Type: application/json" \
  -d '{
    "import_id": 1,
    "method": "snmp",
    "seed_device": "sw1",
    "params": {"host": "192.0.2.10", "community_env": "SNMP_COMMUNITY"}
  }' \
  http://127.0.0.1:8000/api/reconcile-runs

# Persisted run with SSH vendor profile (command auto-selected)
curl -X POST -H "Content-Type: application/json" \
  -d '{
    "import_id": 1,
    "method": "ssh",
    "seed_device": "sw1",
    "params": {"host": "192.0.2.20", "username": "netops", "vendor": "cisco_ios"}
  }' \
  http://127.0.0.1:8000/api/reconcile-runs

# Execute persisted run asynchronously and poll status
curl -X POST "http://127.0.0.1:8000/api/reconcile-runs/1/execute?async=true"
curl "http://127.0.0.1:8000/api/reconcile-runs/1"
```

### Directory Structure

```text
.
├── app.py                      # Flask app entrypoint and API routes
├── nbcart/                     # Core domain/parser/graph/export modules
├── templates/                  # Jinja2 templates
├── static/                     # Runtime frontend assets (fallback + dist)
├── frontend/src/               # Frontend source modules (TypeScript)
├── migrations/                 # SQL schema migrations
├── scripts/                    # Utility scripts (sync/check)
├── tests/                      # Test suite
├── docs/                       # Design/API/release documentation
├── data/                       # Runtime data (SQLite/uploads/results; gitignored)
└── import/                     # Local user import files (gitignored except .gitkeep)
```

### Test File for General Users

- Public sample: `samples/netbox_cables.csv`
- Local import target for your own files: `import/` (excluded by `.gitignore`)

To verify behavior quickly, upload `samples/netbox_cables.csv` from the UI.

### Test / Lint / Format

```bash
source .venv/bin/activate
pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
ruff check .
black --check .
```

To auto-format:

```bash
black .
ruff check . --fix
```

### Troubleshooting

- `black --check .` fails:
  - Run `black .` and commit formatting changes.
- `mypy . --ignore-missing-imports` fails:
  - Run mypy locally and fix optional/typed dict mismatches first.
- Frontend files are out of sync:
  - Run `python3 scripts/sync_frontend.py`
  - Verify with `python3 scripts/check_frontend_sync.py`
- Node toolchain is unavailable:
  - Use sync scripts above; runtime fallback from `static/dist` to `static/` is enabled.

### Persistence Specification

- Metadata: `data/results.db` (SQLite)
- Uploaded CSV files: `data/uploads/`
- Generated graph JSON / row-data JSON: `data/results/`
- drawio files are generated on demand at download time (not stored)
- Saved results can be reopened from `Saved Results` on the top page

### CSV Column Mapping

Column names are normalized and auto-detected (tolerant of symbol/case differences).
However, `Rack A/B` and `Location A/B` are fixed column names.

- Required: device and port columns for both A and B sides
  - Example: `Termination A Device`, `Termination A Name`, `Termination B Device`, `Termination B Name`
  - Example: `Termination A`, `Termination B` (auto-split from `device:port`)
- Optional:
  - `Termination A Type`, `Termination B Type`
  - `ID`, `Label`, `Type`, `Color`
  - `Rack A`, `Rack B` (fixed column names)
  - `Location A`, `Location B` (fixed column names)

If major columns are missing, the UI shows the undetected column list.

### Data Transformation Rules

- Auto-detect encoding from `utf-8-sig` / `utf-8` / `cp932` / `shift_jis`.
- If `Label` is empty, use `Cable-{ID}` (or the row number when `ID` is also missing).
- If `Type` is empty, use `Unknown`.
- If `Color` is in `#RRGGBB`, use it as-is.
- If `Color` is empty/invalid, derive a stable color hash from `Type`.
- If `Termination A/B` is `device:port`, split it automatically.
- Determine endpoint kind from termination type:
  - `front_port`, `rear_port`, `circuit_termination`, `power_port`, `power_outlet`, `power_feed`, `interface`
- Determine domain from endpoint kind:
  - `data` / `pass_through` / `circuit` / `power`
- Keep representative `cable_type` / `color` / `domain` on aggregated edges (used for legend filters).
- Organize aggregated nodes into rack-based parent-child structure (`rack::<name>` containing `dev::<name>`).

### Diagram Operations

- `Labels`: switch node/edge label detail level.
- `Search` + `Hop`: focus neighboring nodes around matching devices.
- `Clear`: clear focus conditions.
- `Reset View`: return to automatic hierarchical layout.
- `Save Layout` / `Load Layout`: save/restore node positions per result ID.
- `Download SVG`: export current rendered diagram as SVG.
- `Download drawio (Current Layout)`: export drawio using current node positions.
- `Cable Media` legend: click to toggle visibility per cable type.
- `Node Types` legend: click to toggle visibility per role.
- `Node Type` select filter: filter by inferred role.
- Connection table supports per-column text filters.
- Click a connection row to highlight matching links on the diagram.
- Click a link or node in the diagram to highlight related connection rows.
- When filters are applied, parent rack nodes for target devices stay visible automatically.
- Auto-layout uses wider minimum spacing per role band to reduce overlap in dense graphs.

### Screens and Endpoints

- `GET /`: initial page (saved result list)
- `POST /upload`: deprecated (returns 410; use API workflow)
- `GET /result/<id>`: reopen a saved result
- `GET /files/<id>/csv`: download original CSV
- `GET /files/<id>/graph`: download graph JSON
- `GET /files/<id>/drawio`: download drawio file (aggregated device diagram)

### API-first Workflow (v1)

- `POST /api/imports`
  - Upload CSV, create an import run, and receive mapping candidates.
- `PUT /api/imports/<id>/mapping`
  - Confirm/override mapping for deterministic parsing.
- `POST /api/imports/<id>/execute`
  - Execute normalization and graph generation.
- `GET /api/imports/<id>`
  - Check import status and metadata.
- `GET /api/graphs/<id>?view=device|interface`
  - Fetch graph elements for frontend rendering.
- `GET /api/exports/<id>?format=json|drawio|csv`
  - Download export artifacts from completed imports.
- `POST /api/results/<id>/drawio-layout`
  - Download drawio generated from current node positions sent by the UI.
- `POST /api/reconcile-runs`
  - Create a reconcile run using completed import data plus observed LLDP source.
- `POST /api/reconcile-runs/<id>/execute`
  - Execute topology reconciliation (`payload`, `snmp`, and `ssh` methods are available).
- `GET /api/reconcile-runs/<id>`
  - Check reconcile status and diff report (`missing/unexpected/mismatched`).
- `POST /api/reconcile/compare`
  - Run one-shot reconcile without persisting a reconcile run (useful for secret-safe checks).
- `GET /api/openapi.yaml`
  - Download the pinned OpenAPI contract.

### Frontend Modules

- Runtime boot: tries `static/dist/app-main.js`, then falls back to `static/app-main.js`
- Fallback runtime modules: `static/diagram.js`, `static/import-workflow.js`
- Source modules (Vite + TypeScript): `frontend/src/*.ts`

### Frontend Build

```bash
python3 scripts/sync_frontend.py
python3 scripts/check_frontend_sync.py
npm install
npm run frontend:build
```

Build config: `frontend/vite.config.ts`  
Build output target: `static/dist/`  
Fallback runtime target: `static/`

### Release

- GitHub release workflow runs on tag push (`v*`).
- Recommended next version after this redesign: `v0.2.0`.
- Suggested release notes draft: `docs/releases/v0.2.0.md`.

### Notes

- Backend: Flask 3.1
- Frontend rendering: Cytoscape.js / elkjs
- To add more column-name rules, update `choose_columns()` in `app.py`.

---

## 日本語訳

NetBox の `Cables` CSV から、デバイス間の集約トポロジ図を生成する Flask アプリです。

### 目次

- [主な機能](#主な機能)
- [セットアップ](#セットアップ)
- [ディレクトリ構成](#ディレクトリ構成)
- [テスト / Lint / Format](#テスト--lint--format)
- [保存仕様（永続化）](#保存仕様永続化)
- [CSV 列マッピング](#csv-列マッピング)
- [データ変換ルール](#データ変換ルール)
- [図操作](#図操作)
- [画面とエンドポイント](#画面とエンドポイント)
- [API-first ワークフロー（v1）](#api-first-ワークフローv1)
- [フロントエンドモジュール](#フロントエンドモジュール)
- [フロントエンドビルド](#フロントエンドビルド)
- [リリース](#リリース)

### 主な機能

- CSV をアップロードしてトポロジを生成
- デバイス間を集約したグラフ表示（リンク本数をエッジ幅に反映）
- ラックをグループノードとして描画し、配下にデバイスを配置
- 自動ロール分類（`core` / `leaf` / `server` / `external` / `patch_panel` / `pdu` など）
- ラック単位フィルタ、コンポーネント単位フィルタ、サーバ表示 ON/OFF
- ノードタイプ（自動ロール判定）単位のフィルタ
- サーバをラックごとに折りたたみ表示
- Cable Type 凡例をクリックしてメディア種別ごとに表示/非表示を切替
- Node Types 凡例をクリックしてロールごとに表示/非表示を切替
- デバイス名検索 + Hop 指定のフォーカス表示
- ラベル表示レベル切替（`standard` / `minimal` / `detailed`）
- レイアウトの保存/読込（ブラウザ `localStorage`）
- 現在レイアウトの SVG ダウンロード
- 現在レイアウトを反映した drawio ダウンロード
- `Reset View` で自動配置へ戻す
- `Type / Color` 凡例、Endpoint 種別凡例、接続一覧テーブル表示
- 接続一覧テーブルの列別フィルタ、図との双方向ハイライト連携
- 結果を永続化し、過去結果の再表示と CSV/JSON/drawio ダウンロード

### セットアップ

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

推奨: Python 3.11

起動後に `http://localhost:8000` を開いて CSV をアップロードします。

### ディレクトリ構成

```text
.
├── app.py                      # Flask アプリ本体と API ルート
├── nbcart/                     # ドメイン/CSV解析/グラフ生成/エクスポート
├── templates/                  # Jinja2 テンプレート
├── static/                     # 実行時フロントエンド資産（fallback + dist）
├── frontend/src/               # フロントエンドソース（TypeScript）
├── migrations/                 # SQL マイグレーション
├── scripts/                    # 同期・検証ユーティリティ
├── tests/                      # テストコード
├── docs/                       # 設計/API/リリース文書
├── data/                       # 実行データ（SQLite/アップロード/結果。Git管理外）
└── import/                     # ローカル投入ファイル（`.gitkeep` 以外はGit管理外）
```

### 一般ユーザ向けテストファイル

- 公開サンプル: `samples/netbox_cables.csv`
- ローカル作業用の投入先: `import/`（`.gitignore` で除外）

公開サンプルで動作確認したい場合は、画面から `samples/netbox_cables.csv` をそのままアップロードしてください。

### テスト / Lint / Format

```bash
source .venv/bin/activate
pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
ruff check .
black --check .
```

自動整形する場合:

```bash
black .
ruff check . --fix
```

### 保存仕様（永続化）

- メタデータ: `data/results.db` (SQLite)
- アップロード CSV: `data/uploads/`
- 生成グラフ JSON / 行データ JSON: `data/results/`
- drawio はダウンロード時にオンデマンド生成（保存はしません）
- 保存済み結果はトップ画面の `Saved Results` から再表示可能

### CSV 列マッピング

列名は正規化して自動検出します（記号・大文字小文字の揺らぎに対応）。
ただし `Rack A/B` と `Location A/B` は列名固定です。

- 必須: A/B 側の device と port に相当する列
  - 例: `Termination A Device`, `Termination A Name`, `Termination B Device`, `Termination B Name`
  - 例: `Termination A`, `Termination B`（`device:port` を自動分解）
- 任意:
  - `Termination A Type`, `Termination B Type`
  - `ID`, `Label`, `Type`, `Color`
  - `Rack A`, `Rack B`（列名固定）
  - `Location A`, `Location B`（列名固定）

主要列が検出できない場合、画面に未検出列一覧が表示されます。

### データ変換ルール

- 文字コードは `utf-8-sig` / `utf-8` / `cp932` / `shift_jis` を自動判定
- `Label` が空の場合は `Cable-{ID}`（`ID` もない場合は行番号）を採用
- `Type` が空の場合は `Unknown`
- `Color` が `#RRGGBB` 形式ならそのまま利用
- `Color` が空/不正なら `Type` から安定ハッシュで色を割り当て
- `Termination A/B` が `device:port` 形式なら自動分解
- 終端タイプから endpoint 種別を判定:
  - `front_port`, `rear_port`, `circuit_termination`, `power_port`, `power_outlet`, `power_feed`, `interface`
- endpoint 種別からドメインを判定:
  - `data` / `pass_through` / `circuit` / `power`
- 集約エッジには代表 `cable_type` / `color` / `domain` を保持（凡例フィルタに利用）
- 集約ノードはラック単位で親子構造化（`rack::<name>` 配下に `dev::<name>`）

### 図操作

- `Labels`: ノード/エッジラベルの表示粒度を切替
- `Search` + `Hop`: 一致デバイスを起点に近傍ノードへフォーカス
- `Clear`: フォーカス条件をクリア
- `Reset View`: 自動階層レイアウトに戻す
- `Save Layout` / `Load Layout`: 表示座標を結果 ID ごとに保存・復元
- `Download SVG`: 現在の表示レイアウトで SVG を出力
- `Download drawio (Current Layout)`: 現在のノード座標で drawio を出力
- `Cable Media` 凡例: クリックで当該 cable type をトグル表示
- `Node Types` 凡例: クリックで当該ロールをトグル表示
- `Node Type` フィルタ: 自動判定ロールで絞り込み
- 接続一覧テーブルは列ごとの文字列フィルタに対応
- 接続一覧行クリックで図上リンクを強調表示
- 図上のリンク/ノードクリックで関連する接続一覧行を強調表示
- フィルタ適用時は対象デバイスの親ラック枠も自動で表示維持
- 自動配置はロール帯ごとの最小間隔を広めに設定し、ノード密集時の重なりを抑制

### 画面とエンドポイント

- `GET /`: 初期画面（保存済み結果一覧）
- `POST /upload`: 非推奨（`410` を返却。API ワークフローを利用）
- `GET /result/<id>`: 保存済み結果の再表示
- `GET /files/<id>/csv`: 元 CSV ダウンロード
- `GET /files/<id>/graph`: グラフ JSON ダウンロード
- `GET /files/<id>/drawio`: drawio ファイル（集約デバイス図）ダウンロード

### API-first ワークフロー（v1）

- `POST /api/imports`
  - CSV をアップロードし、import run を作成。マッピング候補を取得
- `PUT /api/imports/<id>/mapping`
  - 列マッピングを確定/上書き
- `POST /api/imports/<id>/execute`
  - 正規化・グラフ生成を実行
- `GET /api/imports/<id>`
  - import 状態・メタデータを取得
- `GET /api/graphs/<id>?view=device|interface`
  - フロント描画用グラフ要素を取得
- `GET /api/exports/<id>?format=json|drawio|csv`
  - 完了済み import のエクスポートを取得
- `POST /api/results/<id>/drawio-layout`
  - UI から送信した現在ノード座標で drawio を生成して取得
- `POST /api/reconcile-runs`
  - 完了済み import データと観測 LLDP データを使って比較 run を作成
- `POST /api/reconcile-runs/<id>/execute`
  - トポロジー比較を実行（`payload`/`snmp`/`ssh` を利用可能）
- `GET /api/reconcile-runs/<id>`
  - 比較状態と差分レポート（`missing/unexpected/mismatched`）を取得
- `POST /api/reconcile/compare`
  - 比較 run を保存せずにワンショット比較を実行（機密情報を残したくない用途向け）
- `GET /api/openapi.yaml`
  - OpenAPI 契約を取得

### フロントエンドモジュール

- ランタイム起動: `static/dist/app-main.js` を優先し、失敗時は `static/app-main.js` へフォールバック
- フォールバック用モジュール: `static/diagram.js`, `static/import-workflow.js`
- ソース（Vite + TypeScript）: `frontend/src/*.ts`

### フロントエンドビルド

```bash
python3 scripts/sync_frontend.py
python3 scripts/check_frontend_sync.py
npm install
npm run frontend:build
```

ビルド設定: `frontend/vite.config.ts`  
出力先: `static/dist/`  
フォールバック先: `static/`

### リリース

- GitHub Release はタグ push（`v*`）で自動実行
- この再設計後の推奨バージョン: `v0.2.0`
- リリースノート草案: `docs/releases/v0.2.0.md`

### 補足

- バックエンド: Flask 3.1
- フロント描画: Cytoscape.js / elkjs
- 列名ルールを増やす場合は `app.py` の `choose_columns()` を更新してください
