# ファイル構造

## ディレクトリ構成

```
minamo/
├── analyzer.py              # メインの分析スクリプト
├── config.json              # 企業設定ファイル
├── requirements.txt         # Python依存関係
├── README.md                # プロジェクト説明
├── data/                    # データディレクトリ
│   ├── current.json        # 最新の分析結果
│   └── history/            # 履歴データ（日付ごとに分割）
│       ├── index.json      # 履歴インデックス
│       ├── 2025-12-24.json
│       ├── 2025-12-23.json
│       └── ...
└── docs/                    # GitHub Pages用（Webファイル）
    ├── index.html
    ├── style.css
    ├── minamo.png
    └── data/                # シンボリックリンクまたはコピー
        ├── current.json
        └── history/
```

## 変更点

### 履歴管理の改善
- **日付ごとに分割**: `history.json`の代わりに`data/history/YYYY-MM-DD.json`として保存
- **自動クリーンアップ**: 90日以上前の履歴を自動削除
- **インデックスファイル**: `data/history/index.json`で利用可能な日付を管理

### ファイル構造の整理
- **データファイル**: `data/`ディレクトリに集約
- **Webファイル**: `docs/`ディレクトリに移動（GitHub Pages用）

## 移行手順

1. `docs/`ディレクトリを作成
2. `index.html`, `style.css`, `minamo.png`を`docs/`に移動
3. 既存の`history.json`を`data/history/`に分割（オプション）
4. GitHub Pagesの設定で`docs/`を公開ディレクトリに設定

