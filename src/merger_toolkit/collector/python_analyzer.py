# -*- coding: utf-8 -*-
import ast
import os
from typing import Set, Dict, List, Any, Optional

class CodeVisitor(ast.NodeVisitor):
    """
    ASTを走査して、コードの構造（関数、クラス、インポート、呼び出し）を収集する。
    """
    def __init__(self):
        self.imports: Dict[str, List[str]] = {}  # { 'module_name': ['func1', 'func2'] }
        self.from_imports: Dict[str, Dict[str, Optional[str]]] = {} # { 'module_path': {'original_name': 'alias_name'} }
        self.function_defs: Dict[str, ast.FunctionDef] = {}
        self.class_defs: Dict[str, ast.ClassDef] = {}
        self.function_calls: Dict[str, Set[str]] = {} # { 'caller_func': {'called_func1', ...} }
        self._current_function_name: Optional[str] = None

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            self.imports.setdefault(alias.name, []).append(alias.asname or alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        module_path = "." * node.level + (node.module or "")
        self.from_imports.setdefault(module_path, {})
        for alias in node.names:
            self.from_imports[module_path][alias.name] = alias.asname

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self.function_defs[node.name] = node
        # 関数内の呼び出しを記録するために現在の関数名を保存
        original_function_name = self._current_function_name
        self._current_function_name = node.name
        self.function_calls[node.name] = set()
        self.generic_visit(node)
        self._current_function_name = original_function_name

    def visit_ClassDef(self, node: ast.ClassDef):
        self.class_defs[node.name] = node
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        if self._current_function_name:
            if isinstance(node.func, ast.Name):
                # 例: my_function()
                self.function_calls[self._current_function_name].add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                # 例: self.my_method(), other_obj.method()
                # ここでは簡易的に属性名のみを記録
                 if isinstance(node.func.ctx, ast.Load):
                    self.function_calls[self._current_function_name].add(node.func.attr)
        self.generic_visit(node)


class PythonAnalyzer:
    """
    Pythonファイルの解析を行い、依存関係の解決をサポートする。
    """
    def __init__(self, project_root: str):
        self.project_root = os.path.abspath(project_root)
        self._cache: Dict[str, CodeVisitor] = {}

    def analyze_file(self, file_path: str) -> Dict[str, Any]: # ★ 返り値の型ヒントを更新
        """指定されたファイルを解析し、結果をキャッシュして辞書形式で返す。"""
        abs_path = os.path.abspath(file_path)
        if abs_path in self._cache:
            return self._cache[abs_path]

        try:
            with open(abs_path, "r", encoding="utf-8") as f:
                content = f.read()
            tree = ast.parse(content)
            visitor = CodeVisitor()
            visitor.visit(tree)
            
            # ★ CodeVisitorの結果を汎用的な辞書に変換
            result = {
                'functions': {name: self.get_node_source(node, content) for name, node in visitor.function_defs.items()},
                'classes': {name: self.get_node_source(node, content) for name, node in visitor.class_defs.items()},
                'imports': visitor.from_imports, # 形式が似ているのでそのまま利用
                'function_calls': {caller: list(callees) for caller, callees in visitor.function_calls.items()}
            }
            self._cache[abs_path] = result
            return result
            
        except (FileNotFoundError, SyntaxError, UnicodeDecodeError) as e:
            print(f"Warning: Could not analyze file {file_path}: {e}")
            return {}

    def resolve_import_path(self, module_path: str, current_file: str) -> Optional[str]:
        """
        'from . import ...' のような相対インポートパスを絶対ファイルパスに変換する。
        """
        current_dir = os.path.dirname(os.path.abspath(current_file))
        
        # 相対パスの解決
        if module_path.startswith('.'):
            rel_parts = module_path.split('.')
            level = len(rel_parts) - 1
            up_dirs = "../" * (level -1)
            module_name = rel_parts[-1]
            
            base_dir = os.path.dirname(current_file)
            for _ in range(level-1):
                base_dir = os.path.dirname(base_dir)

            potential_path_py = os.path.join(base_dir, module_name + ".py")
            potential_path_init = os.path.join(base_dir, module_name, "__init__.py")
        else: # 絶対パスインポート
            parts = module_path.split('.')
            potential_path_py = os.path.join(self.project_root, *parts) + ".py"
            potential_path_init = os.path.join(self.project_root, *parts, "__init__.py")

        if os.path.isfile(potential_path_py):
            return potential_path_py
        if os.path.isfile(potential_path_init):
            return potential_path_init
        
        # sys.pathなどを含むより複雑な解決はここでは省略
        return None

    @staticmethod
    def get_node_source(node: ast.AST, full_source: str) -> str:
        """ASTノードから元のソースコードを取得する (Python 3.9+)"""
        # ast.get_source_segmentはPython 3.9以降で利用可能です
        # それ以前のバージョンでは、行番号(lineno)を元に手動で抽出する必要があります。
        try:
            return ast.get_source_segment(full_source, node)
        except AttributeError:
            # フォールバック (簡易版)
            lines = full_source.splitlines()
            start = node.lineno - 1
            end = node.end_lineno if hasattr(node, 'end_lineno') else start + 1
            return "\n".join(lines[start:end])