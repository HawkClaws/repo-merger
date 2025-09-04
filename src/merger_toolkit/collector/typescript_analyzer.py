# -*- coding: utf-8 -*-
import os
import sys
import json
import subprocess
from typing import Dict, Any, Optional

try:
    from importlib import resources
except ImportError:
    # Python < 3.9 compatibility
    import importlib_resources as resources

class TypeScriptAnalyzer:
    """
    Node.jsのパーサースクリプトを呼び出してTypeScriptファイルを解析し、
    依存関係の解決をサポートする。
    """
    def __init__(self, project_root: str):
        self.project_root = os.path.abspath(project_root)
        self._cache: Dict[str, Dict[str, Any]] = {}
        self.parser_script_path = str(resources.files('merger_toolkit.collector').joinpath('ts_parser.js'))

    def analyze_file(self, file_path: str) -> Dict[str, Any]:
        """指定されたファイルを解析し、結果をキャッシュする。"""
        abs_path = os.path.abspath(file_path)
        if abs_path in self._cache:
            return self._cache[abs_path]

        # Node.jsとパーサースクリプトの存在チェック
        if not os.path.isfile(self.parser_script_path):
            print(f"Error: TypeScript parser script not found at '{self.parser_script_path}'", file=sys.stderr)
            return {}

        command = ['node', self.parser_script_path, abs_path]
        
        try:
            # shell=Trueはセキュリティリスクがあるため、Windowsでもリスト形式で渡す
            # subprocess.CREATE_NO_WINDOW はWindowsでコンソールウィンドウが開くのを防ぐ
            startupinfo = None
            if sys.platform == "win32":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            process = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding='utf-8',
                check=True,
                startupinfo=startupinfo
            )
            
            raw_result = json.loads(process.stdout)
            if raw_result.get("error"):
                print(f"Warning: Error analyzing {file_path}: {raw_result['error']}", file=sys.stderr)
                return {}

            # ★ 修正: PythonAnalyzerの出力形式に合わせて変換
            result = {
                'functions': raw_result.get('functions', {}),
                'function_locations': self._extract_function_locations(raw_result, abs_path),
                'imports': raw_result.get('imports', {}),
                'full_imports': {},  # TypeScriptでは現状未対応
                'function_calls': self._convert_function_calls(raw_result.get('function_calls', {}))
            }

            self._cache[abs_path] = result
            return result
        except FileNotFoundError:
            print("Error: 'node' command not found. Please ensure Node.js is installed and in your PATH.", file=sys.stderr)
            return {}
        except subprocess.CalledProcessError as e:
            print(f"Error: TypeScript parser script failed for {file_path}", file=sys.stderr)
            print(e.stderr, file=sys.stderr)
            return {}
        except json.JSONDecodeError:
            print(f"Error: Could not decode JSON from TypeScript parser for {file_path}", file=sys.stderr)
            return {}
        except Exception as e:
            print(f"An unexpected error occurred in TypeScriptAnalyzer: {e}", file=sys.stderr)
            return {}

    def _extract_function_locations(self, raw_result: Dict[str, Any], file_path: str) -> Dict[str, Dict[str, Any]]:
        """
        TypeScriptパーサーから関数位置情報を抽出
        """
        # ★ 改善: TypeScriptパーサーが位置情報を提供するようになったので、それを使用
        return raw_result.get('function_locations', {})

    def _convert_function_calls(self, raw_function_calls: Dict[str, list]) -> Dict[str, list]:
        """
        TypeScriptパーサーの関数呼び出し形式をPythonAnalyzer形式に変換
        """
        # ★ 改善: TypeScriptパーサーが既に適切な形式を返すようになった
        return raw_function_calls

    def resolve_import_path(self, module_path: str, current_file: str) -> Optional[str]:
        """
        './utils' のようなインポートパスを実際のファイルパスに変換する。
        """
        # tsconfig.jsonのpathsエイリアスは未対応の簡易版
        base_dir = os.path.dirname(os.path.abspath(current_file))
        
        # 拡張子なしのインポートパスに対応
        potential_path = os.path.join(base_dir, module_path)
        extensions = ['.ts', '.tsx', '.js', '/index.ts', '/index.tsx', '/index.js']
        
        for ext in extensions:
            path_with_ext = potential_path + ext
            if os.path.isfile(path_with_ext):
                return path_with_ext
        
        return None