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
