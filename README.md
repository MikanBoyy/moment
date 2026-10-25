# moment

TradingView Pine Script v6 indicator の開発リポジトリです。現在は実装を削除し、再実装に向けたパッケージ構成だけを保持しています。

## 構成

- `src/domain/`: domain層
- `src/application/`: ユースケースと状態の統合
- `src/presentation/`: 設定と描画
- `src/main.pine`: indicator の入口
- `scripts/`: ビルド
- `dist/`: 自動生成された貼り付け用 Pine Script（Git 管理外）

依存方向は `presentation -> application -> domain` とします。

## ビルド

Python 3.10 以降を使います。外部パッケージは不要です。

```powershell
python scripts/build.py
```

`dist/moment.pine` を TradingView の Pine Editor に貼り付けて確認します。すべての `.pine` ファイルは UTF-8（BOM なし）で保存してください。
