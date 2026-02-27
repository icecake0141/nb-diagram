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
