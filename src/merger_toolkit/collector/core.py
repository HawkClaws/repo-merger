# -*- coding: utf-8 -*-
import os
from collections import deque
from merger_toolkit.collector.python_analyzer import PythonAnalyzer
from merger_toolkit.collector.typescript_analyzer import TypeScriptAnalyzer # ★ 追加

class CodeCollector:
    """
    指定された関数から始まり、その依存関係を再帰的に追跡して
    関連するすべてのコードを収集する。
    """
    def __init__(self, project_root: str):
        self.project_root = project_root
        # ★ アナライザーを辞書で管理
        self.analyzers = {
            'python': PythonAnalyzer(project_root),
            'typescript': TypeScriptAnalyzer(project_root)
        }
        self.collected_code: dict[str, set[str]] = {}
        self.processed_items: set[tuple[str, str]] = set()

    def _get_analyzer_for_file(self, file_path: str): # ★ 追加
        """ファイル拡張子から適切なアナライザーを返す"""
        ext = os.path.splitext(file_path)[1].lower()
        if ext in ['.py', '.pyw']:
            return self.analyzers['python']
        elif ext in ['.ts', '.tsx', '.js', '.jsx']:
            return self.analyzers['typescript']
        return None

    def collect(self, start_file: str, start_function: str) -> str:
        queue = deque([(os.path.abspath(start_file), start_function)])

        while queue:
            current_file, current_function_name = queue.popleft()

            if (current_file, current_function_name) in self.processed_items:
                continue
            self.processed_items.add((current_file, current_function_name))

            print(f"Processing: {os.path.relpath(current_file)} -> {current_function_name}")
            
            analyzer = self._get_analyzer_for_file(current_file) # ★ アナライザーを取得
            if not analyzer:
                print(f"Warning: No analyzer found for file type: {current_file}")
                continue

            analysis_result = analyzer.analyze_file(current_file)
            if not analysis_result:
                continue
            
            # 目的の関数の定義を収集
            if current_function_name in analysis_result.get('functions', {}):
                code_snippet = analysis_result['functions'][current_function_name]
                self.collected_code.setdefault(current_file, set()).add(code_snippet)
                
                # その関数が呼び出す他の関数をキューに追加
                if current_function_name in analysis_result.get('function_calls', {}):
                    for called_func_name in analysis_result['function_calls'][current_function_name]:
                        # A. 同じファイル内で定義されているか？
                        if called_func_name in analysis_result.get('functions', {}):
                            queue.append((current_file, called_func_name))
                        # B. インポートされているか？
                        else:
                            for module, names in analysis_result.get('imports', {}).items():
                                original_name = next((o for o, a in names.items() if a == called_func_name), called_func_name)
                                if original_name in names:
                                    imported_file = analyzer.resolve_import_path(module, current_file)
                                    if imported_file:
                                        queue.append((imported_file, original_name))
                                        break
        return self._format_output()

    def _format_output(self) -> str:
        # (この関数は変更なし)
        output = []
        sorted_files = sorted(self.collected_code.keys())
        for file_path in sorted_files:
            relative_path = os.path.relpath(file_path, self.project_root).replace("\\", "/")
            output.append(f"```{relative_path}")
            sorted_snippets = sorted(list(self.collected_code[file_path]))
            output.append("\n\n".join(sorted_snippets))
            output.append("```\n")
        return "\n".join(output)