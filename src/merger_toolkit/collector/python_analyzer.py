# -*- coding: utf-8 -*-
import ast
import os
import sys
from typing import Set, Dict, List, Any, Optional

class CodeVisitor(ast.NodeVisitor):
    def __init__(self):
        self.imports: Dict[str, str] = {}
        self.from_imports: Dict[str, Dict[str, Optional[str]]] = {}
        # ★ 変更点: 関数の詳細情報を保存する辞書に変更
        self.function_details: Dict[str, Dict[str, Any]] = {}
        self.class_defs: Dict[str, ast.ClassDef] = {}
        self.function_calls: Dict[str, List[Dict[str, Optional[str]]]] = {}
        self._current_function_name: Optional[str] = None
        self._current_class_name: Optional[str] = None  # ★ 追加: 現在のクラス名を追跡

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            self.imports[alias.asname or alias.name] = alias.name
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        module_path = "." * node.level + (node.module or "")
        self.from_imports.setdefault(module_path, {})
        for alias in node.names:
            self.from_imports[module_path][alias.name] = alias.asname

    def visit_FunctionDef(self, node: ast.FunctionDef):
        # ★ 変更点: 開始行と終了行、クラス情報を保存
        function_key = node.name
        if self._current_class_name:
            function_key = f"{self._current_class_name}.{node.name}"
        
        self.function_details[function_key] = {
            'node': node,
            'start_line': node.lineno,
            'end_line': node.end_lineno,
            'class_name': self._current_class_name,
            'function_name': node.name
        }
        
        original_function_name = self._current_function_name
        self._current_function_name = function_key  # ★ 変更: フルネームを使用
        self.function_calls.setdefault(function_key, [])
        self.generic_visit(node)
        self._current_function_name = original_function_name

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        """async関数の処理"""
        # ★ 追加: AsyncFunctionDefもFunctionDefと同様に処理
        function_key = node.name
        if self._current_class_name:
            function_key = f"{self._current_class_name}.{node.name}"
        
        self.function_details[function_key] = {
            'node': node,
            'start_line': node.lineno,
            'end_line': node.end_lineno,
            'class_name': self._current_class_name,
            'function_name': node.name
        }
        
        original_function_name = self._current_function_name
        self._current_function_name = function_key
        self.function_calls.setdefault(function_key, [])
        self.generic_visit(node)
        self._current_function_name = original_function_name

    def visit_ClassDef(self, node: ast.ClassDef):
        self.class_defs[node.name] = node
        original_class_name = self._current_class_name
        self._current_class_name = node.name  # ★ 変更: クラス名を設定
        self.generic_visit(node)
        self._current_class_name = original_class_name  # ★ 変更: クラス名を復元

    def visit_Call(self, node: ast.Call):
        if self._current_function_name:
            call_info = {'name': None, 'module': None}
            if isinstance(node.func, ast.Name):
                call_info['name'] = node.func.id
            elif isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
                call_info['name'] = node.func.attr
                call_info['module'] = node.func.value.id
            if call_info['name']:
                self.function_calls[self._current_function_name].append(call_info)
        self.generic_visit(node)


class PythonAnalyzer:
    def __init__(self, project_root: str, verbose: bool = False):
        self.project_root = os.path.abspath(project_root)
        self._cache: Dict[str, Any] = {}
        self.verbose = verbose

    def analyze_file(self, file_path: str) -> Dict[str, Any]:
        abs_path = os.path.abspath(file_path)
        if abs_path in self._cache:
            return self._cache[abs_path]
        try:
            with open(abs_path, "r", encoding="utf-8") as f:
                content = f.read()
            if sys.version_info >= (3, 12):
                tree = ast.parse(content, feature_version=(3, 11))
            else:
                tree = ast.parse(content)
            visitor = CodeVisitor()
            visitor.visit(tree)
            
            # ★ 変更点: 新しいデータ構造を返す（クラス情報も含む）
            functions_with_source = {
                name: self.get_node_source(details['node'], content)
                for name, details in visitor.function_details.items()
            }
            function_locations = {
                name: {
                    'start': details['start_line'], 
                    'end': details['end_line'],
                    'class_name': details['class_name'],
                    'function_name': details['function_name']
                }
                for name, details in visitor.function_details.items()
            }

            result = {
                'functions': functions_with_source,
                'function_locations': function_locations, # 行番号情報を追加
                'imports': visitor.from_imports,
                'full_imports': visitor.imports,
                'function_calls': visitor.function_calls
            }
            self._cache[abs_path] = result
            return result
        except Exception:
            # エラー時は空の辞書を返す
            return {}

    @staticmethod
    def get_node_source(node: ast.AST, full_source: str) -> str:
        try:
            return ast.get_source_segment(full_source, node)
        except (AttributeError, TypeError):
            lines = full_source.splitlines()
            start = node.lineno - 1
            end = node.end_lineno if hasattr(node, 'end_lineno') and node.end_lineno is not None else start + 1
            return "\n".join(lines[start:end])