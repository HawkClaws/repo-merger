# Repo Merger (リポジトリ・マージャー)

[![PyPI version](https://badge.fury.io/py/repo-merger-cli.svg)](https://badge.fury.io/py/repo-merger-cli)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

リポジトリ内のテキストファイルを、LLM（大規模言語モデル）のプロンプト用に、単一の文字列へとマージするためのCLIツールです。`.gitignore`やバイナリファイルの除外ルールを賢く尊重します。

`repo-merge`は指定されたディレクトリをスキャンし、関連するすべてのテキストファイルをMarkdownのコードブロック形式で一つの出力にまとめ、クリップボードにコピーします。GPT-4やClaudeのようなLLMに、あなたのコードベース全体の文脈を簡単に提供できるよう設計されています。

## ✨ 主な機能

-   **クリップボード優先**: マージされたコンテンツは、デフォルトでクリップボードにコピーされ、すぐに貼り付けられます。
-   **`.gitignore`対応**: `.gitignore`ファイルに記述された除外ルールを自動的に尊重します。
-   **スマートなフィルタリング**: バイナリファイル（画像、動画、実行ファイルなど）や、不要なファイル・ディレクトリ（`node_modules`、`.git`など）をインテリジェントに除外します。
-   **カスタマイズ可能**: ファイル、ディレクトリ、拡張子単位で独自の除外ルールを追加できます。
-   **シンプルなCLI**: 使いやすく、直感的なデフォルト設定を備えています。

## 📥 インストール

`repo-merge`は`pip`を使ってインストールできます。

```bash
pip install git+https://github.com/HawkClaws/repo-merger.git
```

このツールは Python 3.8 以上が必要です。

## 🚀 使い方

`repo-merge`の使い方は簡単です。プロジェクトのルートディレクトリに移動して、コマンドを実行するだけです。

### 基本的な使い方

カレントディレクトリをスキャンし、マージした結果をクリップボードにコピーします。

```bash
repo-merge
```

特定のディレクトリをスキャンする場合：

```bash
repo-merge /path/to/your/project
```

### ファイルへの保存

クリップボードへのコピーではなく、結果をファイルに保存したい場合は、`-o`または`--output`フラグを使用します。

```bash
repo-merge -o merged_output.txt
```

### 除外ルールのカスタマイズ

デフォルト設定や`.gitignore`に加えて、独自の除外ルールを追加できます。

#### ディレクトリを除外: `-xd` または `--exclude-dir`

```bash
# 'docs' ディレクトリを除外する
repo-merge -xd docs
```

#### 拡張子を除外: `-xe` または `--exclude-ext`

```bash
# すべてのマークダウンファイルを除外する
repo-merge -xe .md
```

#### 特定のファイルを除外: `-xf` または `--exclude-file`

```bash
# 特定の設定ファイルを除外する
repo-merge -xf config.dev.json
```

これらのフラグは複数回指定できます。

### その他のオプション

#### 詳細モード (Verbose Mode)
どのファイルが処理され、どのファイルがスキップされたかを確認するには、`-v`または`--verbose`フラグを使用します。

```bash
repo-merge -v
```

#### .gitignoreを無視
`.gitignore`を無効にし、組み込みルールとカスタムルールのみを使用するには、`--no-gitignore`フラグを使用します。

```bash
repo-merge --no-gitignore
```

### コマンドラインヘルプ

すべてのコマンドとオプションの一覧は、`--help`フラグで確認できます。

```bash
repo-merge --help
```

## 🛠️ 動作の仕組み

このツールは指定されたディレクトリを再帰的にスキャンし、以下の3層の除外ロジックを適用します。

1.  **強制除外**: 組み込みのバイナリファイルの拡張子（`.png`, `.mp4`, `.exe`など）と、重要なディレクトリ（`.git`など）は常に除外されます。

2.  **`.gitignore` ルール**: `.gitignore`ファイルが存在する場合、そのルールが適用されます。これがプロジェクト固有の除外ルールの基本となります。

3.  **デフォルト/ユーザー指定の除外**:
    -   `.gitignore`が見つからない場合、一般的な開発ディレクトリ（`node_modules`, `venv`など）を含むデフォルトのリストがフォールバックとして使用されます。
    -   コマンドラインで指定されたルール（`-xd`, `-xe`, `-xf`）は常に適用されます。

処理対象となった各ファイルの内容は、ファイルパスを情報文字列に持つMarkdownのコードブロックでラップされます。

```markdown
```src/main.py
print("Hello, World!")
```

```utils/helpers.py
def helper_function():
    return True
```


この整形された出力が、クリップボードにコピーされるか、ファイルに保存されます。

## 📜 ライセンス

このプロジェクトは Apache License 2.0 の下でライセンスされています。詳細は `LICENSE` ファイルをご覧ください。

## 🤝 コントリビューション

コントリビューション、Issue、機能リクエストを歓迎します！お気軽にIssuesページをご確認ください。
