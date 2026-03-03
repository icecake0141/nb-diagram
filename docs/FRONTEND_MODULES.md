# Frontend Modules

## Source of Truth

- Primary source files are under `frontend/src/`:
  - `app-main.ts`
  - `diagram.ts`
  - `import-workflow.ts`

## Runtime Entrypoint

Template boot script:

1. tries `static/dist/app-main.js`
2. falls back to `static/app-main.js`

## Sync Strategy

Because Node toolchain may be unavailable in some environments:

- run `python3 scripts/sync_frontend.py`
- this copies `frontend/src/*.ts` to both:
  - `static/*.js`
  - `static/dist/*.js`

## Build Strategy

When Node is available, use Vite build from `frontend/src` and output to `static/dist/`.

---

## 日本語訳

### 正本ソース

- 主なソースファイルは `frontend/src/` 配下:
  - `app-main.ts`
  - `diagram.ts`
  - `import-workflow.ts`

### ランタイムのエントリポイント

テンプレートの起動スクリプトは:

1. `static/dist/app-main.js` を先に試す
2. 失敗時に `static/app-main.js` へフォールバックする

### 同期戦略

一部環境では Node ツールチェーンが利用できないため:

- `python3 scripts/sync_frontend.py` を実行
- `frontend/src/*.ts` を次の両方へコピーする:
  - `static/*.js`
  - `static/dist/*.js`

### ビルド戦略

Node が利用できる環境では、`frontend/src` を Vite でビルドし、`static/dist/` に出力します。
