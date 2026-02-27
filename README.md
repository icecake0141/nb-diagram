# NetBox Cable Diagram Generator

## English

A Flask app that generates an aggregated topology diagram between devices from a NetBox `Cables` CSV.

### Key Features

- Upload a CSV and generate a topology diagram.
- Aggregated device-to-device graph display (edge width reflects link count).
- Draw racks as group nodes and place devices under each rack.
- Automatic role classification (`core` / `leaf` / `server` / `external` / `patch_panel` / `pdu`, etc.).
- Rack-level filter, component-level filter, and server visibility toggle.
- Per-rack server collapse display.
- Click the Cable Type legend to toggle media visibility.
- Device-name search with hop-based focus.
- Label detail level switching (`standard` / `minimal` / `detailed`).
- Layout save/load via browser `localStorage`.
- Return to automatic layout with `Reset View`.
- `Type / Color` legend, endpoint type legend, and connection table.
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
- `Cable Media` legend: click to toggle visibility per cable type.
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

### 主な機能

- CSV をアップロードしてトポロジを生成
- デバイス間を集約したグラフ表示（リンク本数をエッジ幅に反映）
- ラックをグループノードとして描画し、配下にデバイスを配置
- 自動ロール分類（`core` / `leaf` / `server` / `external` / `patch_panel` / `pdu` など）
- ラック単位フィルタ、コンポーネント単位フィルタ、サーバ表示 ON/OFF
- サーバをラックごとに折りたたみ表示
- Cable Type 凡例をクリックしてメディア種別ごとに表示/非表示を切替
- デバイス名検索 + Hop 指定のフォーカス表示
- ラベル表示レベル切替（`standard` / `minimal` / `detailed`）
- レイアウトの保存/読込（ブラウザ `localStorage`）
- `Reset View` で自動配置へ戻す
- `Type / Color` 凡例、Endpoint 種別凡例、接続一覧テーブル表示
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
- `Cable Media` 凡例: クリックで当該 cable type をトグル表示
- フィルタ適用時は対象デバイスの親ラック枠も自動で表示維持
- 自動配置はロール帯ごとの最小間隔を広めに設定し、ノード密集時の重なりを抑制

### 画面とエンドポイント

- `GET /`: 初期画面（保存済み結果一覧）
- `POST /upload`: CSV 解析、グラフ生成、保存
- `GET /result/<id>`: 保存済み結果の再表示
- `GET /files/<id>/csv`: 元 CSV ダウンロード
- `GET /files/<id>/graph`: グラフ JSON ダウンロード
- `GET /files/<id>/drawio`: drawio ファイル（集約デバイス図）ダウンロード

### 補足

- バックエンド: Flask 3.1
- フロント描画: Cytoscape.js / elkjs
- 列名ルールを増やす場合は `app.py` の `choose_columns()` を更新してください
