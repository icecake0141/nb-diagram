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

---

## 日本語訳

### 現在のバージョン

- API の基準バージョンは `v1`（現時点ではパスは `/api/...` のまま）。
- 契約仕様の正本は `docs/openapi.yaml`。

### 互換性ルール

- レスポンスへの追加フィールドは許可。
- `v1` では既存フィールドの意味を変更しない。
- フィールド削除やステータスコード挙動変更はバージョン更新が必要。

### 将来のバージョニング

破壊的変更が必要な場合:

1. `/api/v2/...` ルートを追加する。
2. 非推奨期間中は `/api/...` を v1 として維持する。
3. README とリリースノートに移行手順を記載する。
