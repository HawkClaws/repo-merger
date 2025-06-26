# -*- coding: utf-8 -*-
import os
import sys
import argparse
import io
import pathspec
from importlib import resources # パッケージ内のリソースを読み込むためにインポート

# --- クリップボード機能のためのインポート ---
try:
    import pyperclip
    PYPERCLIP_AVAILABLE = True
except ImportError:
    PYPERCLIP_AVAILABLE = False

# --- 除外設定の再定義 ---

# レイヤー1: 強制除外リスト (常に適用)
# .gitignore の内容に関わらず、これらのバイナリファイル等は常に除外されます。
FORCE_EXCLUDE_EXTENSIONS = {
    # 画像ファイル
    '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.ico', '.svg', '.webp',
    # 動画・音声ファイル
    '.mp4', '.avi', '.mov', '.wmv', '.flv', '.mkv', '.mp3', '.wav', '.ogg', '.flac', '.aac',
    # 圧縮ファイル・バイナリなど
    '.zip', '.tar', '.gz', '.rar', '.7z', '.jar', '.war', '.ear', '.exe', '.dll', '.so',
    '.dylib', '.o', '.a', '.lib', '.class', '.app', '.msi', '.pdf', '.doc', '.docx',
    '.xls', '.xlsx', '.ppt', '.pptx', '.odt', '.ods', '.odp', '.sqlite', '.db', '.mdb',
    '.dbf', '.ttf', '.otf', '.woff', '.woff2', '.eot', '.pyc', '.pyd', '.dat', '.bin',
}
FORCE_EXCLUDE_DIRS = {
    '.git',  # .git ディレクトリはスキャン対象外
}
# --- 除外設定ここまで ---


def merge_repository_to_string(input_dir, gitignore_spec, final_exclude_dirs, final_exclude_ext, final_exclude_files, verbose=False):
    # (この関数の内容は変更なしのため、簡潔にするため省略します)
    # ... 前回の回答と同じロジック ...
    string_io = io.StringIO()
    for root, dirs, files in os.walk(input_dir, topdown=True):
        dirs[:] = [d for d in dirs if d not in final_exclude_dirs]
        if gitignore_spec:
            dir_paths_for_gitignore = {os.path.relpath(os.path.join(root, d), input_dir).replace("\\", "/") + '/' for d in dirs}
            excluded_by_gitignore = {os.path.basename(p.rstrip('/')) for p in gitignore_spec.match_files(dir_paths_for_gitignore)}
            if verbose and excluded_by_gitignore: print(f"Skipping directories in '{root}' by .gitignore: {', '.join(sorted(list(excluded_by_gitignore)))}")
            dirs[:] = [d for d in dirs if d not in excluded_by_gitignore]
        sorted_files = sorted(files)
        for filename in sorted_files:
            file_path = os.path.join(root, filename)
            relative_path = os.path.relpath(file_path, input_dir).replace("\\", "/")
            _, ext = os.path.splitext(filename)
            if gitignore_spec and gitignore_spec.match_file(relative_path):
                if verbose: print(f"Skipping by .gitignore: {relative_path}")
                continue
            if ext.lower() in final_exclude_ext:
                if verbose: print(f"Skipping file by extension: {relative_path}")
                continue
            if filename in final_exclude_files:
                if verbose: print(f"Skipping file by name: {relative_path}")
                continue
            if verbose: print(f"Processing: {relative_path}")
            try:
                string_io.write(f"```{relative_path}\n")
                content = ""
                error_message = None
                try:
                    with open(file_path, 'r', encoding='utf-8') as infile: content = infile.read()
                except (UnicodeDecodeError, IOError):
                    try:
                        with open(file_path, 'r', encoding=None) as infile: content = infile.read()
                        if verbose: print(f"  Note: Read '{relative_path}' with system default encoding.")
                    except Exception as e: error_message = f"# ERROR: Could not read file (tried UTF-8 and default): {e}\n"
                except Exception as e: error_message = f"# ERROR: Unexpected error reading file: {e}\n"
                if error_message:
                    string_io.write(error_message)
                    if verbose: print(f"  {error_message.strip()}")
                else:
                    if content and not content.endswith('\n'): content += '\n'
                    string_io.write(content)
                string_io.write(f"```\n\n")
            except Exception as e:
                print(f"Error processing block for file {relative_path}: {e}")
                string_io.write(f"``` Error Processing {relative_path}\n# ERROR: Unexpected error: {e}\n```\n\n")
    return string_io.getvalue()


def main():
    parser = argparse.ArgumentParser(
        description="Merge repository files into a single output, respecting .gitignore and other rules.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    # ... (引数の定義は変更なし) ...
    parser.add_argument("input_dir", nargs='?', default='.', help="Path to the input directory to scan (default: current directory).")
    parser.add_argument("-o", "--output", metavar="OUTPUT_FILE", default=None, help="Path to the output file. If not specified, content is copied to the clipboard.")
    parser.add_argument("-xd", "--exclude-dir", action='append', default=[], metavar='DIR', help="Add a directory name to exclude.")
    parser.add_argument("-xe", "--exclude-ext", action='append', default=[], metavar='.ext', help="Add a file extension to exclude.")
    parser.add_argument("-xf", "--exclude-file", action='append', default=[], metavar='FILE', help="Add a file name to exclude.")
    parser.add_argument("--no-gitignore", action="store_true", help="Do not use .gitignore file for exclusions.")
    parser.add_argument("-v", "--verbose", action="store_true", help="Print verbose output.")
    args = parser.parse_args()

    # ... (クリップボードとディレクトリのチェックは変更なし) ...
    if not args.output and not PYPERCLIP_AVAILABLE:
        print("\nError: To copy to clipboard, 'pyperclip' library is required.", file=sys.stderr)
        print("Please install it ('pip install pyperclip') or use the -o/--output option.", file=sys.stderr)
        return 1
    if not os.path.isdir(args.input_dir):
        print(f"Error: Input directory '{args.input_dir}' not found.", file=sys.stderr)
        return 1
        
    # --- .gitignore の読み込みロジックを更新 ---
    gitignore_spec = None
    if not args.no_gitignore:
        gitignore_path = os.path.join(args.input_dir, '.gitignore')
        if os.path.isfile(gitignore_path):
            if args.verbose:
                print(f"Using local .gitignore from: {gitignore_path}")
            with open(gitignore_path, 'r', encoding='utf-8') as f:
                gitignore_spec = pathspec.PathSpec.from_lines('gitwildmatch', f)
        else:
            # ローカルに.gitignoreがない場合、パッケージ内のデフォルトを読み込む
            if args.verbose:
                print("No local .gitignore found. Attempting to use built-in default .gitignore.")
            try:
                # 'repo_merger.data' パッケージ内の 'default.gitignore' を読み込む
                default_gitignore_content = resources.files('repo_merger.data').joinpath('default.gitignore').read_text(encoding='utf-8')
                gitignore_spec = pathspec.PathSpec.from_lines('gitwildmatch', default_gitignore_content.splitlines())
            except (FileNotFoundError, ModuleNotFoundError):
                if args.verbose:
                    print("Warning: Built-in default .gitignore not found. Proceeding without gitignore rules.")

    # --- 最終的な除外リストの構築 ---
    # 強制除外とユーザー指定の除外のみを設定
    final_exclude_dirs = set(FORCE_EXCLUDE_DIRS)
    final_exclude_ext = {ext.lower() for ext in FORCE_EXCLUDE_EXTENSIONS}
    final_exclude_files = set() # 強制除外するファイル名は基本的にはない

    final_exclude_dirs.update(args.exclude_dir)
    final_exclude_ext.update({ext.lower() if ext.startswith('.') else '.' + ext.lower() for ext in args.exclude_ext})
    final_exclude_files.update(args.exclude_file)

    # .gitignoreが一切使われなかった場合のみ、最低限のフォールバックを追加
    if gitignore_spec is None:
        if args.verbose:
            print("No .gitignore rules applied. Using minimal fallback exclusions.")
        # ここに、どうしても除外したいものがあれば追加できますが、
        # 基本的にdefault.gitignoreに任せるため、空でも良いでしょう。
        # final_exclude_dirs.update({'node_modules', 'venv'}) # 例
    
    # ... (以降の処理は変更なし) ...
    try:
        merged_content = merge_repository_to_string(
            args.input_dir,
            gitignore_spec,
            final_exclude_dirs,
            final_exclude_ext,
            final_exclude_files,
            args.verbose
        )
        if not merged_content.strip():
            print("\nWarning: No files were found or processed based on the criteria.")
            return 0
        final_output = "差分はいらない。変更が必要なファイルのみを、各ファイルごとにコードブロックで出力してください。\nまた、必要最低限の変更にしてください。リファクタなどは不要です。\n\n" + merged_content.strip() + "\n"
        if args.output:
            # ... (ファイル出力) ...
            output_path = os.path.abspath(args.output)
            try:
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                with open(output_path, 'w', encoding='utf-8') as f: f.write(final_output)
                print(f"\nMerged content successfully saved to '{output_path}'.")
            except IOError as e:
                print(f"\nError writing to file '{output_path}': {e}", file=sys.stderr)
                return 1
        else:
            # ... (クリップボードコピー) ...
            try:
                pyperclip.copy(final_output)
                content_size_mb = len(final_output.encode('utf-8')) / (1024 * 1024)
                print(f"\nMerged content ({content_size_mb:.2f} MB) copied to clipboard successfully.")
                if content_size_mb > 5: print("Warning: Content is large. Pasting may be slow in some applications.")
            except pyperclip.PyperclipException as e:
                print(f"\nError copying to clipboard: {e}", file=sys.stderr)
                return 1
    except KeyboardInterrupt:
        print("\nProcess interrupted by user.", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}", file=sys.stderr)
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())