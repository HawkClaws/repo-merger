# -*- coding: utf-8 -*-
import os
import sys
import argparse
from merger_toolkit.collector.core import CodeCollector

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
    parser.add_argument("-f", "--file", help="Path to the file containing the starting function.")
    parser.add_argument("-func", "--function", help="Name of the starting function to trace.")
    parser.add_argument("-o", "--output", metavar="OUTPUT_FILE", default=None, help="Path to the output file. If not specified, content is copied to the clipboard.")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable detailed logging for debugging.")
    parser.add_argument("-i", "--interactive", action="store_true", help="Launch interactive mode for easy function selection.")
    
    args = parser.parse_args()

    # ★ 新機能: インタラクティブモード
    if args.interactive:
        try:
            # まずTUI版を試す
            from merger_toolkit.collector.interactive import run_interactive_mode
            return run_interactive_mode(args.input_dir, args.verbose)
        except ImportError:
            # TUI版が使えない場合はシンプル版にフォールバック
            try:
                from merger_toolkit.collector.simple_interactive import run_simple_interactive_mode
                print("🔄 Falling back to simple interactive mode (TUI not available)")
                return run_simple_interactive_mode(args.input_dir, args.verbose)
            except Exception as e:
                print(f"\nError in simple interactive mode: {e}", file=sys.stderr)
                return 1
        except Exception as e:
            # TUI版でエラーが発生した場合もシンプル版にフォールバック
            try:
                from merger_toolkit.collector.simple_interactive import run_simple_interactive_mode
                print(f"🔄 TUI error ({e}), falling back to simple mode")
                return run_simple_interactive_mode(args.input_dir, args.verbose)
            except Exception as e2:
                print(f"\nError in interactive mode: {e2}", file=sys.stderr)
                return 1

    # 従来のコマンドラインモード
    if not args.file or not args.function:
        print("\nError: Both --file and --function are required in command-line mode.", file=sys.stderr)
        print("Use --interactive (-i) for interactive selection, or provide both arguments.", file=sys.stderr)
        return 1

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
        collector = CodeCollector(
            project_root=args.input_dir,
            verbose=args.verbose
        )
        collected_content = collector.collect(start_file=args.file, start_function=args.function)

        if not collected_content.strip():
            print("\nWarning: No code was collected. Check if the function and file names are correct.")
            return 0

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
        import traceback
        traceback.print_exc()
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())