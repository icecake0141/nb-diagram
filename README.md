# NetBox Cable Diagram Generator

NetBox の `Cables` CSV から、デバイス間の集約トポロジ図を生成する Flask アプリです。

## 主な機能

- CSV をアップロードしてトポロジを生成
- デバイス間を集約したグラフ表示（リンク本数をエッジ幅に反映）
- 自動ロール分類（`core` / `leaf` / `server`）と読みやすい配置
- ラック単位フィルタ、コンポーネント単位フィルタ、サーバ表示ON/OFF
- サーバをラックごとに折りたたみ表示
- `Type / Color` 凡例、Endpoint 種別凡例、接続一覧テーブル表示
- 結果を永続化し、過去結果の再表示と CSV/JSON ダウンロード

## セットアップ

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

起動後に `http://localhost:8000` を開いて CSV をアップロードします。

## 保存仕様（永続化）

- メタデータ: `data/results.db` (SQLite)
- アップロード CSV: `data/uploads/`
- 生成グラフ JSON / 行データ JSON: `data/results/`
- 保存済み結果はトップ画面の「保存済み結果」から再表示可能

## CSV 列マッピング

列名は正規化して自動検出します（記号・大文字小文字の揺らぎに対応）。

- 必須: A/B 側の device と port に相当する列
  - 例: `Termination A Device`, `Termination A Name`, `Termination B Device`, `Termination B Name`
- 任意:
  - `Termination A Type`, `Termination B Type`
  - `ID`, `Label`, `Type`, `Color`
  - `Rack A`, `Rack B`
  - `Location A`, `Location B`

主要列が検出できない場合、画面に「推定できなかった列」が表示されます。

## データ変換ルール

- 文字コードは `utf-8-sig` / `utf-8` / `cp932` / `shift_jis` を自動判定
- `Label` が空の場合は `Cable-{ID}`（`ID` もない場合は行番号）を採用
- `Type` が空の場合は `Unknown`
- `Color` が `#RRGGBB` 形式ならそのまま利用
- `Color` が空/不正なら `Type` から安定ハッシュで色を割り当て
- 終端タイプから endpoint 種別を判定:
  - `front_port`, `rear_port`, `circuit_termination`, `power_port`, `power_outlet`, `power_feed`, `interface`
- endpoint 種別からドメインを判定:
  - `data` / `pass_through` / `circuit` / `power`

## 画面とエンドポイント

- `GET /`: 初期画面（保存済み結果一覧）
- `POST /upload`: CSV 解析、グラフ生成、保存
- `GET /result/<id>`: 保存済み結果の再表示
- `GET /files/<id>/csv`: 元 CSV ダウンロード
- `GET /files/<id>/graph`: グラフ JSON ダウンロード

## 補足

- バックエンド: Flask 3.1
- フロント描画: Cytoscape.js
- 列名ルールを増やす場合は `app.py` の `choose_columns()` を更新してください
