# Minamo - Market Ripple Observer

AI（Gemini）を活用した市場観測ツール。主要企業のニュースを自動収集・分析し、100点満点のスコアで株価上昇期待値を評価します。実際の株価変動と予測を比較し、AIの予測精度を可視化します。

## 主な機能

### 📊 AI分析
- **ニュース自動収集**: Google News RSSから主要企業の最新ニュースを自動収集
- **100点満点評価**: Gemini AIが各企業のニュースを分析し、株価上昇期待値を0-100点で評価
- **記事ごとのスコア**: 各ニュース記事についても個別にスコアと理由を提示

### 📈 株価情報と精度評価
- **株価データ取得**: Yahoo Financeから前日比の株価情報を取得
- **予測精度評価**: AIスコアと実際の株価変動を比較し、予測精度を評価
- **評価結果表示**: 「的中」「部分的的中」「外れ」で結果を表示

### 📅 履歴管理
- **無期限保存**: すべての履歴データを日付ごとに分割して保存
- **カレンダー選択**: 日付ピッカーで過去のデータを選択して表示
- **履歴ドロップダウン**: タイムスタンプから履歴を選択

### 📉 グラフ表示
- **企業ごとのグラフ**: 各企業カードにスコアと精度の推移グラフを表示
- **2軸表示**: 左軸にスコア、右軸に精度を表示
- **期間選択**: 週・月・年の期間を選択して表示範囲を変更

## セットアップ

### 必要な環境
- Python 3.11以上
- Google Gemini API キー

### インストール

1. リポジトリをクローン
```bash
git clone https://github.com/soramk/minamo.git
cd minamo
```

2. 依存関係をインストール
```bash
pip install -r requirements.txt
```

3. 環境変数を設定
```bash
export GEMINI_API_KEY="your-api-key-here"
```

Windowsの場合:
```powershell
$env:GEMINI_API_KEY="your-api-key-here"
```

### 設定

`config.json`に監視したい企業を追加します：

```json
[
    {
        "name": "トヨタ自動車",
        "query": "トヨタ自動車 株価 ニュース"
    }
]
```

## 使用方法

### 分析の実行

```bash
python analyzer.py
```

このコマンドで以下が実行されます：
1. 各企業のニュースを収集
2. Gemini AIで分析・スコアリング
3. 株価情報を取得
4. スコアと株価変動を比較
5. `data/current.json`に最新データを保存
6. `data/history/YYYY-MM-DD.json`に履歴を保存

### Web表示

GitHub Pagesで公開する場合：
1. `docs/`ディレクトリにWebファイルを配置
2. GitHubリポジトリの設定で`docs/`を公開ディレクトリに設定

ローカルで確認する場合：
```bash
# 簡易HTTPサーバーを起動
cd docs
python -m http.server 8000
```

ブラウザで `http://localhost:8000` にアクセス

## ファイル構造

```
minamo/
├── analyzer.py              # メインの分析スクリプト
├── config.json              # 企業設定ファイル
├── requirements.txt         # Python依存関係
├── data/                    # データディレクトリ
│   ├── current.json        # 最新の分析結果
│   └── history/            # 履歴データ（日付ごとに分割）
│       ├── index.json      # 履歴インデックス
│       ├── YYYY-MM-DD.json # 日付ごとの履歴
│       └── ...
└── docs/                    # GitHub Pages用（Webファイル）
    ├── index.html
    ├── style.css
    ├── minamo.png
    └── data/                # データファイル（コピー）
```

## GitHub Actions

### 日次自動実行

`.github/workflows/analyze.yml`で毎日自動実行されます：
- スケジュール: UTC 23:00（JST 08:00）
- 手動実行: GitHub Actionsのワークフローから実行可能

### キャッシュ機能

依存関係のインストール時間を短縮するため、pipのキャッシュを利用しています。

## データ形式

### 最新データ (`data/current.json`)

```json
{
  "metadata": {
    "updated_at": "2025-12-24 16:11",
    "token_usage": {
      "total_tokens": 31178
    }
  },
  "companies": [
    {
      "company": "トヨタ自動車",
      "average_score": 78,
      "updated_at": "2025-12-24 16:11",
      "stock_info": {
        "ticker": "7203.T",
        "current_price": 3353.0,
        "price_change_percent": -1.82
      },
      "score_evaluation": {
        "accuracy": 40.9,
        "prediction": "上昇予測 (強い)",
        "actual": "-1.82%",
        "status": "外れ"
      },
      "news": [...]
    }
  ]
}
```

### 履歴データ (`data/history/YYYY-MM-DD.json`)

日付ごとに分割された履歴データ。各エントリにはタイムスタンプと完全なデータが含まれます。

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。

## 作者

soramk
