# NetBox Cable Diagram Generator

NetBox の `Cables` CSV から、デバイス間の集約トポロジ図を生成する Flask アプリです。

## 主な機能

- CSV をアップロードしてトポロジを生成
- デバイス間を集約したグラフ表示（リンク本数をエッジ幅に反映）
- ラックをグループノードとして描画し、配下にデバイスを配置
- 自動ロール分類（`core` / `leaf` / `server` / `external` / `patch_panel` / `pdu` など）
- ラック単位フィルタ、コンポーネント単位フィルタ、サーバ表示ON/OFF
- サーバをラックごとに折りたたみ表示
- Cable Type 凡例をクリックしてメディア種別ごとに表示/非表示を切替
- デバイス名検索 + Hop 指定のフォーカス表示
- ラベル表示レベル切替（標準 / 最小 / 詳細）
- レイアウトの保存/読込（ブラウザ `localStorage`）
- Reset View で自動配置へ戻す
- `Type / Color` 凡例、Endpoint 種別凡例、接続一覧テーブル表示
- 結果を永続化し、過去結果の再表示と CSV/JSON/drawio ダウンロード

## セットアップ

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

推奨: Python 3.11

起動後に `http://localhost:8000` を開いて CSV をアップロードします。

## 一般ユーザ向けテストファイル

- 公開サンプル: `samples/netbox_cables.csv`
- ローカル作業用の投入先: `import/`（`.gitignore` で除外）

公開サンプルで動作確認したい場合は、画面から `samples/netbox_cables.csv` をそのままアップロードしてください。

## テスト / Lint / Format

```bash
source .venv/bin/activate
pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
ruff check .
black --check .
```

自動整形する場合:

```bash
black .
ruff check . --fix
```

## 保存仕様（永続化）

- メタデータ: `data/results.db` (SQLite)
- アップロード CSV: `data/uploads/`
- 生成グラフ JSON / 行データ JSON: `data/results/`
- drawio はダウンロード時にオンデマンド生成（保存はしません）
- 保存済み結果はトップ画面の「保存済み結果」から再表示可能

## CSV 列マッピング

列名は正規化して自動検出します（記号・大文字小文字の揺らぎに対応）。
ただし `Rack A/B` と `Location A/B` は列名固定です。

- 必須: A/B 側の device と port に相当する列
  - 例: `Termination A Device`, `Termination A Name`, `Termination B Device`, `Termination B Name`
  - 例: `Termination A`, `Termination B`（`device:port` を自動分解）
- 任意:
  - `Termination A Type`, `Termination B Type`
  - `ID`, `Label`, `Type`, `Color`
  - `Rack A`, `Rack B`（列名固定）
  - `Location A`, `Location B`（列名固定）

主要列が検出できない場合、画面に「推定できなかった列」が表示されます。

## データ変換ルール

- 文字コードは `utf-8-sig` / `utf-8` / `cp932` / `shift_jis` を自動判定
- `Label` が空の場合は `Cable-{ID}`（`ID` もない場合は行番号）を採用
- `Type` が空の場合は `Unknown`
- `Color` が `#RRGGBB` 形式ならそのまま利用
- `Color` が空/不正なら `Type` から安定ハッシュで色を割り当て
- `Termination A/B` が `device:port` 形式なら自動分解
- 終端タイプから endpoint 種別を判定:
  - `front_port`, `rear_port`, `circuit_termination`, `power_port`, `power_outlet`, `power_feed`, `interface`
- endpoint 種別からドメインを判定:
  - `data` / `pass_through` / `circuit` / `power`
- 集約エッジには代表 `cable_type` / `color` / `domain` を保持（凡例フィルタに利用）
- 集約ノードはラック単位で親子構造化（`rack::<name>` 配下に `dev::<name>`）

## 図操作

- `ラベル`: ノード/エッジラベルの表示粒度を切替
- `検索` + `Hop`: 一致デバイスを起点に近傍ノードへフォーカス
- `解除`: フォーカス条件をクリア
- `Reset View`: 自動階層レイアウトに戻す
- `レイアウト保存` / `レイアウト読込`: 表示座標を結果IDごとに保存・復元
- `Cable Media` 凡例: クリックで当該 cable type をトグル表示
- フィルタ適用時は対象デバイスの親ラック枠も自動で表示維持
- 自動配置はロール帯ごとの最小間隔を広めに設定し、ノード密集時の重なりを抑制

## 画面とエンドポイント

- `GET /`: 初期画面（保存済み結果一覧）
- `POST /upload`: CSV 解析、グラフ生成、保存
- `GET /result/<id>`: 保存済み結果の再表示
- `GET /files/<id>/csv`: 元 CSV ダウンロード
- `GET /files/<id>/graph`: グラフ JSON ダウンロード
- `GET /files/<id>/drawio`: drawio ファイル（集約デバイス図）ダウンロード

## 補足

- バックエンド: Flask 3.1
- フロント描画: Cytoscape.js / elkjs
- 列名ルールを増やす場合は `app.py` の `choose_columns()` を更新してください
