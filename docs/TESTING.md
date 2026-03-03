# テスト / Lint / Format

## 開発依存のインストール

```bash
source .venv/bin/activate
pip install -r requirements-dev.txt
```

## テスト

```bash
pytest -q
```

## Lint

```bash
ruff check .
```

## Format

```bash
ruff format .
```

## API スモークテスト

```bash
# 1) import run を作成
curl -X POST -F "csv_file=@samples/netbox_cables.csv" http://127.0.0.1:8000/api/imports

# 2) 実行
curl -X POST http://127.0.0.1:8000/api/imports/<id>/execute

# 3) グラフ取得
curl "http://127.0.0.1:8000/api/graphs/<id>?view=device"
```

## テスト用ファイル

- 公開サンプル: `samples/netbox_cables.csv`
- ローカル投入先: `import/`（`.gitignore` で除外）
