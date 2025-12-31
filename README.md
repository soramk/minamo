# Minamo - Market Ripple Observer

AI（Gemini）を活用した市場観測ツール。主要企業のニュースを自動収集・分析し、100点満点のスコアで株価期待値を評価します。実際の株価変動と予測を比較し、AIの予測精度を可視化します。

## 主な機能

### 📊 AI分析

- **高度なニュース分析**: Gemini 2.0 Flash を使用し、Google News RSSから収集した最新ニュースを多角的に分析。
- **100点満点評価**: 株価上昇期待値を0-100点で評価。50点を基準に強気・弱気を判定。
- **投資判断の自動生成**: AIスコアと過去の的中率に基づき、「強気買い」「様子見」などの売買シグナルを自動提示。

### 📈 精度評価と統計

- **的中率の可視化**: 上昇予測時と下落予測時の的中率を個別に集計し、AIの得意・不得意を把握可能。
- **市場サマリー**: 全対象企業の平均スコア、上昇/下落銘柄数、最新のスキャン時刻を一覧表示。
- **株価リアルタイム比較**: Yahoo Financeのデータを使用し、AIスコアと実際の変動（前日比）を比較検証。

### 📅 履歴管理とグラフ

- **時系列グラフ**: 各企業ごとにスコアと的中率の推移を2軸グラフで表示（週・月・年単位）。
- **カレンダー検索**: 日付ピッカーまたは履歴ドロップダウンから過去の分析結果を即座に参照。
- **自動データ移行**: 旧形式のデータ（`history.json`など）を自動的に日付別ファイルへ移行・統合。

### 🔍 高度なUI/UX

- **直感的な検索**: 企業名や銘柄コードによる瞬時のフィルタリング。
- **業種別ナビ**: 登録企業を業種ごとに自動分類し、セクターごとの動向を把握。
- **プレミアムデザイン**: Outfitフォントとガラスモフィズムを取り入れた、モダンなダークテーマUI。

## セットアップ

### 必要な環境

- Python 3.11以上
- Google Gemini API キー（`gemini-2.0-flash-exp` 使用）

### インストール

1. リポジトリをクローン

```bash
git clone https://github.com/soramk/minamo.git
cd minamo
```

1. 依存関係をインストール

```bash
pip install -r requirements.txt
```

1. 環境変数を設定

```bash
# macOS/Linux
export GEMINI_API_KEY="your-api-key-here"

# Windows (PowerShell)
$env:GEMINI_API_KEY="your-api-key-here"
```

### 設定

`config.json` に監視したい企業を追加します。`sector` を指定するとWeb UIで自動分類されます。

```json
[
    {
        "name": "トヨタ自動車",
        "sector": "輸送用機器"
    }
]
```

## 使用方法

### 分析の実行

```bash
python analyzer.py
```

実行されるプロセス：

1. `config.json` に基づき最新ニュースを収集
2. Gemini AIによるスコアリングと理由の生成
3. `yfinance` による最新価格と騰落率の取得
4. `docs/data/current.json` および `docs/data/history/YYYY-MM-DD.json` への保存

### Web表示

GitHub Pagesで公開する場合、設定で `docs/` ディレクトリを公開対象に指定してください。

ローカルで確認する場合：

```bash
cd docs
python -m http.server 8000
```

ブラウザで `http://localhost:8000` にアクセス。

## ファイル構造

```
minamo/
├── analyzer.py              # メインの分析スクリプト
├── config.json              # 企業設定ファイル（業種指定可能）
├── requirements.txt         # Python依存関係
├── README.md                # 本ファイル
└── docs/                    # GitHub Pages公開ディレクトリ
    ├── index.html           # Web UIメイン
    ├── style.css            # スタイリング
    ├── minamo.png           # ロゴ
    └── data/                # 分析結果格納（自動生成）
        ├── current.json     # 最新の分析結果
        └── history/         # 日付別履歴データ
            ├── index.json   # 履歴インデックス
            └── YYYY-MM-DD.json
```

## GitHub Actions

`.github/workflows/analyze.yml` により、毎日 JST 08:00 に自動実行されます。

- スケジュール実行のほか、Actionsタブから手動で即時スキャンも可能です。

## ライセンス

MIT License

## 作者

[soramk](https://github.com/soramk)
