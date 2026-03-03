# Troubleshooting

## English

### `pytest -q` fails with `ModuleNotFoundError`

Run tests with an explicit module path:

```bash
PYTHONPATH=. pytest -q
```

### Frontend files look out of sync

Sync and verify runtime files:

```bash
python3 scripts/sync_frontend.py
python3 scripts/check_frontend_sync.py
```

### API smoke test fails because server is not running

Start the app first:

```bash
python app.py
```

Then open `http://127.0.0.1:8000` and retry API calls.

---

## 日本語訳

### `pytest -q` が `ModuleNotFoundError` で失敗する

モジュールパスを明示して実行します:

```bash
PYTHONPATH=. pytest -q
```

### フロントエンドファイルの同期が崩れている

ランタイム用ファイルを同期・検証します:

```bash
python3 scripts/sync_frontend.py
python3 scripts/check_frontend_sync.py
```

### API スモークテスト時にサーバ未起動で失敗する

先にアプリを起動します:

```bash
python app.py
```

その後 `http://127.0.0.1:8000` を開き、API 呼び出しを再実行してください。
