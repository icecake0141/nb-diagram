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
