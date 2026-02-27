# AGENTS.md

## Purpose
A minimal guide for agents working in this repository.

## Workflow
- Keep changes small and focused.
- Identify the root cause first, then apply the minimal fix.
- Run tests for affected areas before finishing.

## Commands
- Test: `pytest -q`
- Format: `ruff format .`
- Lint: `ruff check .`
- App start: `python app.py` (open `http://127.0.0.1:8000`)
- API workflow (E2E-like smoke test):
  - `curl -X POST -F "csv_file=@samples/netbox_cables.csv" http://127.0.0.1:8000/api/imports`
  - `curl -X POST http://127.0.0.1:8000/api/imports/<id>/execute`
  - `curl "http://127.0.0.1:8000/api/graphs/<id>?view=device"`

## Notes
- Prefer existing architecture and naming conventions.
- Avoid unrelated refactoring.
