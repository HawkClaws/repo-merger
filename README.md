# Repo Merger & Code Collector Toolkit

[![PyPI version](https://badge.fury.io/py/repo-merger-cli.svg)](https://badge.fury.io/py/repo-merger-cli)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

LLM（大規模言語モデル）との対話を効率化するために設計された、2つの強力なCLIツールキットです。

1.  **`repo-merge`**: リポジトリ全体のテキストファイルをインテリジェントにフィルタリングし、単一のプロンプト用テキストにマージします。
2.  **`code-collector`**: 指定した単一の関数から始まり、その依存関係をコードレベルで追跡し、関連する部分だけをピンポイントで収集します。

プロジェクト全体のコンテキストを渡したい時は`repo-merge`を、特定の機能やバグについて質問したい時は`code-collector`を使うことで、LLMとの対話の質と効率を劇的に向上させます。

## ✨ 主な機能

-   **デュアルツール**: プロジェクト全体のマージと、関数単位の依存関係収集の2つのモードを提供。
-   **複数言語対応**: `code-collector`はPython（.py, .pyw）とTypeScript/JavaScript（.ts, .tsx, .js, .jsx）の静的コード解析をサポート。
-   **スマートフィルタリング**: `.gitignore`ルールを尊重し、バイナリファイルや不要なディレクトリ（`.git`, `node_modules`など）を自動で除外。
-   **クリップボード優先**: 結果はデフォルトでクリップボードにコピーされ、すぐにLLMに貼り付け可能。
-   **カスタマイズ可能**: `repo-merge`では、独自の除外ルールを柔軟に追加できます。
-   **簡単なインストール**: pipでインストールすれば、すぐに2つのコマンドが利用可能になります。

## 📥 インストール

このツールキットは`pip`を使ってインストールできます。

```bash
# PyPIからインストール（今後リリース予定）
pip install repo-merger-cli

# GitHubリポジトリから直接インストール
pip install git+https://github.com/HawkClaws/repo-merger.git
```

**要件:**
- Python 3.9 以上
- `code-collector`のTypeScript解析機能を利用する場合は、Node.jsとnpmがインストールされている必要があります。

ツールのインストール時に、必要なNode.jsパッケージ(typescript)も自動でインストールされます。

## 🚀 使い方

インストールが完了すると、`repo-merge`と`code-collector`の2つのコマンドが利用可能になります。

### 🎯 New! インタラクティブモード (推奨)

**最も簡単な方法**: ファイル名や関数名を覚える必要がありません！

```bash
# プロジェクトディレクトリで実行
cd your-project
code-collector -i
```

**特徴:**
- 🔍 **検索機能**: 関数名やファイル名で検索
- 📋 **一覧表示**: プロジェクト内の全関数をページネーション表示
- 🎨 **言語対応**: Python、TypeScript、JavaScript、React自動判別
- 💾 **結果選択**: クリップボード、ファイル保存、プレビューから選択

**使用例:**
```
👉 Enter your choice: process_data
✅ Found exact match: main.py::process_data

👉 Enter your choice: f:service
🔍 Found 8 functions in files matching 'service'

👉 Enter your choice: list
📋 Functions (Page 1/3):
  1. main.py::main
  2. utils.py::helper_function
  ...
```

詳細は [INTERACTIVE_GUIDE.md](INTERACTIVE_GUIDE.md) を参照してください。

### repo-merge コマンド

リポジトリ全体をスキャンし、1つのテキストファイルにマージします。

#### 基本的な使い方

プロジェクトのルートディレクトリでコマンドを実行すると、結果がクリップボードにコピーされます。

```bash
# カレントディレクトリをスキャン
repo-merge

# 特定のディレクトリをスキャン
repo-merge /path/to/your/project

# 詳細な出力を表示
repo-merge -v
```

#### ファイルへの保存

`-o`または`--output`フラグで、結果をファイルに出力します。

```bash
repo-merge -o merged_output.md
repo-merge /path/to/project -o output.txt
```

#### 除外ルールのカスタマイズ

- `-xd`, `--exclude-dir`: ディレクトリを除外 (例: `-xd docs`)
- `-xe`, `--exclude-ext`: 拡張子を除外 (例: `-xe .md`)  
- `-xf`, `--exclude-file`: ファイル名で除外 (例: `-xf config.dev.json`)
- `--no-gitignore`: .gitignoreファイルを無視

```bash
# docsディレクトリと.mdファイルを除外
repo-merge -xd docs -xe .md

# 複数の除外ルールを適用
repo-merge -xd tests -xd __pycache__ -xe .pyc -xf README.md

# .gitignoreを無視してすべてのファイルをスキャン
repo-merge --no-gitignore
```

### code-collector コマンド

指定した関数を開始点として、その定義や呼び出し先のコードを収集します。

#### 基本的な使い方

プロジェクトのルート、起点となるファイル、関数名を指定します。結果はクリップボードにコピーされます。

```bash
# TypeScriptの関数を収集
code-collector -f src/services/api.ts -func fetchUserData

# Pythonの関数を収集
code-collector -f my_app/utils.py -func calculate_total

# プロジェクトパスを明示的に指定
code-collector /path/to/project -f src/main.py -func run_app
```

#### ファイルへの保存

`-o`または`--output`フラグで、結果をファイルに出力します。

```bash
code-collector -f src/main.py -func run_app -o app_context.md
```

#### ヘルプ

各コマンドの詳細なオプションは`--help`で確認できます。

```bash
repo-merge --help
code-collector --help
```

## 🛠️ 動作の仕組み

### `repo-merge`
指定されたディレクトリを再帰的にスキャンし、以下のルールでファイルをフィルタリングします：
1.  **強制除外**: 組み込みのバイナリ拡張子リスト（画像、動画、実行ファイルなど）と`.git`などを常に除外。
2.  **`.gitignore`**: プロジェクトの`.gitignore`ルールを適用。見つからない場合は組み込みのデフォルトルールを使用。
3.  **カスタムルール**: ユーザーがコマンドラインで指定した除外ルールを適用。

出力形式は以下のようにMarkdown形式のコードブロックとしてファイル内容をマージします：

````
```path/to/file.py
ファイルの内容
```

```path/to/another/file.js
別のファイルの内容
```
````

### `code-collector`
静的コード解析を用いて、以下のように依存関係を追跡します：
1.  **解析 (Parse)**: 対象ファイルをAST（抽象構文木）に変換し、コードの構造を把握します。
2.  **収集 (Collect)**: 指定された関数のソースコードを収集します。
3.  **追跡 (Trace)**: 関数内で呼び出されている他の関数を特定し、インポート文をたどって追跡対象を広げます。
4.  **繰り返し**: 新たに見つかった関数についても、キューが空になるまでこのプロセスを繰り返します。

#### サポートされている言語
- **Python**: `.py`, `.pyw`ファイル（ASTベースの解析）
- **TypeScript/JavaScript**: `.ts`, `.tsx`, `.js`, `.jsx`ファイル（TypeScript compilerを使用）

## 💡 使用例

### 例1: プロジェクト全体をLLMに送信
```bash
# プロジェクト全体をマージしてクリップボードにコピー
repo-merge

# テストファイルとドキュメントを除外
repo-merge -xd tests -xd docs -xe .md
```

### 例2: バグのある関数とその依存関係を調査
```bash
# 問題のある関数と関連コードのみを収集
code-collector -f src/payment/processor.py -func process_payment
```

### 例3: 特定の機能の実装を理解
```bash
# フロントエンドのAPI呼び出し部分を追跡
code-collector -f src/components/UserProfile.tsx -func fetchUserData
```

## ⚠️ 制限事項

- `code-collector`の依存関係追跡は静的解析に基づいているため、動的な関数呼び出し（`getattr`、`eval`など）は検出されません。
- TypeScript解析機能を使用するには、Node.js 16以上とnpmが必要です。
- 非常に大きなプロジェクトでは、出力が制限を超える場合があります。除外ルールを活用してください。

## 📜 ライセンス

このプロジェクトは Apache License 2.0 の下でライセンスされています。詳細は `LICENSE` ファイルをご覧ください。

## 🤝 コントリビューション

コントリビューション、Issue、機能リクエストを歓迎します！お気軽にIssuesページをご確認ください。

### 開発者向け情報

```bash
# 開発モードでインストール
pip install -e .

# 仮想環境を使用する場合
python3 -m venv venv
source venv/bin/activate  # Windowsの場合: venv\\Scripts\\activate
pip install -e .
```