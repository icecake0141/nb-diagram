# NetBox Cable Diagram Generator

## English

A Flask app that generates an aggregated topology diagram from a NetBox `Cables` CSV.

### Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:8000` after startup.

### Documents

- [Specification](docs/SPEC.md)
- [Testing / Lint / Format](docs/TESTING.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)
- [API Versioning](docs/API_VERSIONING.md)
- [OpenAPI Guide](docs/OPENAPI.md)
- [OpenAPI YAML](docs/openapi.yaml)
- [Frontend Build](docs/FRONTEND_BUILD.md)
- [Frontend Modules](docs/FRONTEND_MODULES.md)
- [Build Status](docs/BUILD_STATUS.md)
- [Migrations](docs/MIGRATIONS.md)
- [Redesign Plan](docs/REDESIGN_PLAN.md)
- [Release Notes (v0.2.0)](docs/releases/v0.2.0.md)

---

## 日本語訳

NetBox の `Cables` CSV から、デバイス間の集約トポロジ図を生成する Flask アプリです。

### インストール

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

起動後に `http://127.0.0.1:8000` を開いて利用します。

### ドキュメント

- [仕様](docs/SPEC.md)
- [テスト / Lint / Format](docs/TESTING.md)
- [トラブルシューティング](docs/TROUBLESHOOTING.md)
- [API バージョニング](docs/API_VERSIONING.md)
- [OpenAPI ガイド](docs/OPENAPI.md)
- [OpenAPI YAML](docs/openapi.yaml)
- [フロントエンドビルド](docs/FRONTEND_BUILD.md)
- [フロントエンドモジュール](docs/FRONTEND_MODULES.md)
- [ビルド状況](docs/BUILD_STATUS.md)
- [マイグレーション](docs/MIGRATIONS.md)
- [再設計計画](docs/REDESIGN_PLAN.md)
- [リリースノート (v0.2.0)](docs/releases/v0.2.0.md)
