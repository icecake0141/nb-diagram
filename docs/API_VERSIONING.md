# API Versioning Policy

## Current Version

- API baseline: `v1` (path remains `/api/...` for now).
- Contract source of truth: `docs/openapi.yaml`.

## Compatibility Rules

- Additive fields are allowed in responses.
- Existing fields must not change semantics in `v1`.
- Removing fields or changing status-code behavior requires a version bump.

## Future Versioning

When a breaking change is needed:

1. Introduce `/api/v2/...` routes.
2. Keep `/api/...` as v1 during deprecation window.
3. Publish migration notes in README and release notes.
