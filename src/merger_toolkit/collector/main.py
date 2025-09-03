# -*- coding: utf-8 -*-
import os
import sys
import argparse
from merger_toolkit.collector.core import CodeCollector

# --- クリップボード機能のためのインポート ---
try:
    import pyperclip
    PYPERCLIP_AVAILABLE = True
except ImportError:
    PYPERCLIP_AVAILABLE = False

def main():
    parser = argparse.ArgumentParser(
        description="Collect a specific function and its dependencies from a Python repository.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("input_dir", nargs='?', default='.', help="Path to the project's root directory (default: current directory).")
    parser.add_argument("-f", "--file", required=True, help="Path to the file containing the starting function.")
    parser.add_argument("-func", "--function", required=True, help="Name of the starting function to trace.")
    parser.add_argument("-o", "--output", metavar="OUTPUT_FILE", default=None, help="Path to the output file. If not specified, content is copied to the clipboard.")
    
    args = parser.parse_args()

    # --- 入力値の検証 ---
    if not args.output and not PYPERCLIP_AVAILABLE:
        print("\nError: To copy to clipboard, 'pyperclip' library is required.", file=sys.stderr)
        print("Please install it ('pip install pyperclip') or use the -o/--output option.", file=sys.stderr)
        return 1
    if not os.path.isdir(args.input_dir):
        print(f"Error: Input directory '{args.input_dir}' not found.", file=sys.stderr)
        return 1
    if not os.path.isfile(args.file):
        print(f"Error: Starting file '{args.file}' not found.", file=sys.stderr)
        return 1

    try:
        # --- コアロジックの実行 ---
        collector = CodeCollector(project_root=args.input_dir)
        collected_content = collector.collect(start_file=args.file, start_function=args.function)

        if not collected_content.strip():
            print("\nWarning: No code was collected. Check if the function and file names are correct.")
            return 0

        # --- 出力処理 ---
        if args.output:
            output_path = os.path.abspath(args.output)
            try:
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(collected_content)
                print(f"\nCollected code successfully saved to '{output_path}'.")
            except IOError as e:
                print(f"\nError writing to file '{output_path}': {e}", file=sys.stderr)
                return 1
        else:
            try:
                pyperclip.copy(collected_content)
                content_size_mb = len(collected_content.encode('utf-8')) / (1024 * 1024)
                print(f"\nCollected code ({content_size_mb:.2f} MB) copied to clipboard successfully.")
            except pyperclip.PyperclipException as e:
                print(f"\nError copying to clipboard: {e}", file=sys.stderr)
                return 1
                
    except KeyboardInterrupt:
        print("\nProcess interrupted by user.", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}", file=sys.stderr)
        # デバッグ用にスタックトレースを表示
        import traceback
        traceback.print_exc()
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())