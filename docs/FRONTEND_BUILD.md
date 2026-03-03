# Frontend Build (Vite + TypeScript)

## Source of Truth

- `frontend/src/app-main.ts`
- `frontend/src/diagram.ts`
- `frontend/src/import-workflow.ts`

## Commands

- Sync without Node toolchain:
  - `python3 scripts/sync_frontend.py`
- Install deps (Node required):
  - `npm install`
- Dev server:
  - `npm run frontend:dev`
- Production build:
  - `npm run frontend:build`

## Build Output

- Vite output path: `static/dist/`
- Runtime fallback path: `static/`

---

## 日本語訳

### 正本ソース

- `frontend/src/app-main.ts`
- `frontend/src/diagram.ts`
- `frontend/src/import-workflow.ts`

### コマンド

- Node ツールチェーンなしで同期:
  - `python3 scripts/sync_frontend.py`
- 依存関係インストール（Node 必須）:
  - `npm install`
- 開発サーバ:
  - `npm run frontend:dev`
- 本番ビルド:
  - `npm run frontend:build`

### ビルド出力

- Vite 出力先: `static/dist/`
- ランタイムのフォールバック先: `static/`
