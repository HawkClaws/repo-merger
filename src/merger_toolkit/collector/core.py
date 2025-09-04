# -*- coding: utf-8 -*-
import os
from collections import deque
from merger_toolkit.collector.python_analyzer import PythonAnalyzer
from merger_toolkit.collector.typescript_analyzer import TypeScriptAnalyzer
import re

class CodeCollector:
    def __init__(self, project_root: str, verbose: bool = False):
        self.project_root = os.path.abspath(project_root)
        self.verbose = verbose
        self.analyzers = {
            'python': PythonAnalyzer(self.project_root, self.verbose),
            'typescript': TypeScriptAnalyzer(self.project_root)
        }
        self.collected_code: dict[str, set[str]] = {}
        self.processed_items: set[tuple[str, str]] = set()

    def _get_analyzer_for_file(self, file_path: str):
        ext = os.path.splitext(file_path)[1].lower()
        if ext in ['.py', '.pyw']:
            return self.analyzers['python']
        elif ext in ['.ts', '.tsx', '.js', '.jsx']:
            return self.analyzers['typescript']
        return None

    def _find_all_source_files(self) -> list[str]:
        source_files = []
        excluded_dirs = {'.git', 'node_modules', '__pycache__', '.venv', 'venv', 'env'}
        for root, dirs, files in os.walk(self.project_root, topdown=True):
            dirs[:] = [d for d in dirs if d not in excluded_dirs]
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in ['.py', '.pyw', '.ts', '.tsx', '.js', '.jsx']:
                    source_files.append(os.path.join(root, file))
        return source_files
    
    # ★ 変更点: 呼び出し元検索を、新しいアルゴリズムで完全に置き換え
    def _find_callers_and_contexts_recursive(self, target_function: str) -> tuple[set[tuple[str, str]], set[str]]:
        """
        再帰的に呼び出し元を検索する（循環参照を回避）
        
        Args:
            target_function: 検索対象の関数名
            
        Returns:
            tuple: (特定の呼び出し元のセット, モジュールレベル呼び出しファイルのセット)
        """
        if self.verbose: print("-" * 20 + "\n[Phase 1] Recursive Callers Search\n" + "-" * 20)
        
        all_specific_callers = set()
        all_context_files = set()
        processed_functions = set()  # 循環参照を防ぐ
        search_queue = [target_function]  # 検索キュー
        level = 0
        
        while search_queue and level < 50:  # 無限ループ防止（50レベル制限）
            level += 1
            current_targets = list(search_queue)
            search_queue.clear()
            
            if self.verbose: print(f"\n[Level {level}] Searching callers for: {current_targets}")
            
            for current_target in current_targets:
                if current_target in processed_functions:
                    if self.verbose: print(f"  [Skip] Already processed: {current_target}")
                    continue
                    
                processed_functions.add(current_target)
                
                # 現在のターゲットの呼び出し元を検索
                specific_callers, context_files = self._find_direct_callers(current_target)
                
                # 結果をマージ
                all_specific_callers.update(specific_callers)
                all_context_files.update(context_files)
                
                # 新しく見つかった呼び出し元を次のレベルの検索対象に追加
                for file_path, func_name in specific_callers:
                    if func_name not in processed_functions:
                        search_queue.append(func_name)
                        if self.verbose: print(f"  [Queue] Added for next level: {func_name}")
        
        if self.verbose: 
            print("\n[Summary] Recursive search completed:")
            print(f"  - Total levels searched: {level}")
            print(f"  - Total specific callers found: {len(all_specific_callers)}")
            print(f"  - Total context files found: {len(all_context_files)}")
        
        # 非verboseモードでは検索結果の簡潔な表示のみ
        if not self.verbose and (len(all_specific_callers) > 0 or len(all_context_files) > 0):
            caller_count = len(all_specific_callers)
            context_count = len(all_context_files)
            parts = []
            if caller_count > 0:
                parts.append(f"{caller_count} caller(s)")
            if context_count > 0:
                parts.append(f"{context_count} context file(s)")
            print(f"Found {', '.join(parts)}.")
        
        return all_specific_callers, all_context_files

    def _find_direct_callers(self, target_function: str) -> tuple[set[tuple[str, str]], set[str]]:
        """
        指定された関数の直接的な呼び出し元のみを検索（1レベル）
        
        Args:
            target_function: 検索対象の関数名
            
        Returns:
            tuple: (特定の呼び出し元のセット, モジュールレベル呼び出しファイルのセット)
        """
        specific_callers = set()
        context_files = set()
        source_files = self._find_all_source_files()
        
        search_pattern = re.compile(r'\b' + re.escape(target_function) + r'\b')
        def_pattern = re.compile(r'^\s*def\s+' + re.escape(target_function) + r'\b')

        for file_path in source_files:
            try:
                call_locations = []
                with open(file_path, 'r', encoding='utf-8') as f:
                    for i, line in enumerate(f, 1):
                        if search_pattern.search(line) and not def_pattern.match(line):
                            call_locations.append(i)
                
                if not call_locations:
                    continue

                if self.verbose: print(f"  [Scan] Found calls to '{target_function}' in '{os.path.relpath(file_path, self.project_root)}' at lines: {call_locations}")
                
                # ★ 修正: 適切なAnalyzerを使用
                analyzer = self._get_analyzer_for_file(file_path)
                if not analyzer:
                    continue
                
                analysis = analyzer.analyze_file(file_path)
                if not analysis or 'function_locations' not in analysis:
                    continue

                for line_num in call_locations:
                    found_in_function = False
                    for func_key, loc_info in analysis['function_locations'].items():
                        if loc_info['start'] <= line_num <= loc_info['end']:
                            if self.verbose:
                                class_prefix = f"{loc_info['class_name']}." if loc_info.get('class_name') else ""
                                display_name = f"{class_prefix}{loc_info['function_name']}"
                                print(f"    [+] Caller: Line {line_num} in function '{display_name}'")
                            specific_callers.add((os.path.abspath(file_path), func_key))
                            found_in_function = True
                            break
                    
                    if not found_in_function:
                        if self.verbose: print(f"    [+] Module-level call at line {line_num}")
                        context_files.add(os.path.abspath(file_path))

            except Exception as e:
                if self.verbose: print(f"    [Error] Failed to analyze {file_path}: {e}")
                continue
        
        return specific_callers, context_files

    def _find_definition_grep(self, target_function: str) -> list[tuple[str, str]]:
        locations = []
        source_files = self._find_all_source_files()
        pattern = re.compile(r'^\s*def\s+' + re.escape(target_function) + r'\b')
        for file_path in source_files:
            try:
                # ★ 修正: Pythonアナライザーを使ってより確実に関数を見つける
                analysis = self.analyzers['python'].analyze_file(file_path)
                if analysis and 'functions' in analysis:
                    for func_key in analysis['functions'].keys():
                        # 関数名が一致するかチェック（クラス名.メソッド名の場合も含む）
                        if func_key == target_function or func_key.endswith(f".{target_function}"):
                            if self.verbose: 
                                print(f"    [Resolve] Found definition of '{target_function}' as '{func_key}' in '{os.path.relpath(file_path, self.project_root)}'")
                            locations.append((os.path.abspath(file_path), func_key))
                
                # フォールバック: 従来の正規表現検索も併用
                with open(file_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        if pattern.match(line):
                            # 既に見つかっていない場合のみ追加
                            abs_path = os.path.abspath(file_path)
                            if not any(loc[0] == abs_path and loc[1] == target_function for loc in locations):
                                if self.verbose: print(f"    [Resolve] Found definition of '{target_function}' in '{os.path.relpath(file_path, self.project_root)}' (fallback)")
                                locations.append((abs_path, target_function))
                            break
            except Exception:
                continue
        return locations

    def collect(self, start_file: str, start_function: str) -> str:
        # ★ 変更点: collectメソッドのロジックを新しいアルゴリズムに置き換え
        start_file_abs = os.path.abspath(start_file)
        
        specific_callers, context_files = self._find_callers_and_contexts_recursive(start_function)
        
        queue = deque()
        
        # キューに追加するアイテムの重複を管理
        items_to_add = set()
        
        # 1. 開始関数を追加
        items_to_add.add((start_file_abs, start_function))

        # 2. 特定された呼び出し元関数を追加
        if specific_callers:
            if self.verbose: print(f"Found {len(specific_callers)} specific calling function(s).")
            items_to_add.update(specific_callers)
        
        # 3. モジュールレベルの呼び出しがあったファイルの全関数を追加
        if context_files:
            if self.verbose: print(f"Found {len(context_files)} file(s) with module-level calls.")
            for file_path in context_files:
                analysis = self.analyzers['python'].analyze_file(file_path)
                if analysis and 'functions' in analysis:
                    for func_key in analysis['functions'].keys():  # ★ 修正: func_keyを使用
                        items_to_add.add((file_path, func_key))

        # 開始関数が先頭に来るようにソートしてキューに追加
        sorted_items = sorted(list(items_to_add), key=lambda x: x != (start_file_abs, start_function))
        queue.extend(sorted_items)
        
        if not queue:
            if self.verbose: print("No functions to collect.")
            return ""

        if self.verbose: print(f"Starting collection with {len(queue)} initial function(s).")
        
        if self.verbose: print("\n" + "-" * 20 + "\n[Phase 2] Collecting Dependencies\n" + "-" * 20)
        while queue:
            current_file, current_function_name = queue.popleft()
            if (current_file, current_function_name) in self.processed_items:
                continue
            self.processed_items.add((current_file, current_function_name))

            if self.verbose: print(f"Processing: {os.path.relpath(current_file, self.project_root)} -> {current_function_name}")
            analyzer = self._get_analyzer_for_file(current_file)
            if not analyzer: continue
            analysis_result = analyzer.analyze_file(current_file) # ここをcurrent_fileに修正
            if not analysis_result: continue
            if current_function_name in analysis_result.get('functions', {}):
                code_snippet = analysis_result['functions'][current_function_name]
                self.collected_code.setdefault(current_file, set()).add(code_snippet)
                if self.verbose: print(f"  [Collect] Collected source for '{current_function_name}'")
                if current_function_name in analysis_result.get('function_calls', {}):
                    if self.verbose: print(f"  [Trace] Analyzing calls inside '{current_function_name}':")
                    for call in analysis_result['function_calls'][current_function_name]:
                        called_func_name = call['name']
                        if not called_func_name: continue
                        if self.verbose: print(f"    - Found call: {call['module'] or ''}.{called_func_name}")
                        # ★ 修正: 呼び出し関数名から実際のfunc_keyを検索
                        if call['module'] is None:
                            # まずは直接的な一致を試す
                            target_func_key = None
                            if called_func_name in analysis_result.get('functions', {}):
                                target_func_key = called_func_name
                            else:
                                # クラス名.メソッド名の形式も検索
                                for func_key in analysis_result.get('functions', {}):
                                    if func_key.endswith(f".{called_func_name}"):
                                        target_func_key = func_key
                                        break
                            
                            if target_func_key:
                                if self.verbose: print(f"      [Queue] Adding local function: '{target_func_key}'")
                                queue.append((current_file, target_func_key))
                        else:
                            definitions = self._find_definition_grep(called_func_name)
                            for def_file, def_func in definitions:
                                if (def_file, def_func) not in self.processed_items and (def_file, def_func) not in queue:
                                    if self.verbose: print(f"      [Queue] Adding found definition: '{def_func}' from '{os.path.relpath(def_file, self.project_root)}'")
                                    queue.append((def_file, def_func))
            else:
                 if self.verbose: print(f"  [Warn] Function '{current_function_name}' not found in analysis of {os.path.relpath(current_file, self.project_root)}")
        return self._format_output()

    def _format_output(self) -> str:
        output = []
        sorted_files = sorted(self.collected_code.keys())
        for file_path in sorted_files:
            relative_path = os.path.relpath(file_path, self.project_root).replace("\\", "/")
            output.append(f"```{relative_path}")
            
            # ★ 改善: クラス情報を含めて整理して出力
            snippets_with_context = []
            for snippet in self.collected_code[file_path]:
                snippets_with_context.append(snippet)
            
            sorted_snippets = sorted(list(snippets_with_context))
            output.append("\n\n".join(sorted_snippets))
            output.append("```\n")
        return "\n".join(output)