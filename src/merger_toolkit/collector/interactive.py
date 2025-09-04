# -*- coding: utf-8 -*-
"""
インタラクティブモード用のTUIアプリケーション
"""

import os
from typing import Dict, List, Tuple, Optional
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import (
    Header, Footer, Input, Button, DataTable, Static, 
    ProgressBar, TextArea, Label, Tree
)
from textual.binding import Binding
from textual.screen import Screen
from textual.message import Message
from rich.text import Text
from rich.syntax import Syntax

from merger_toolkit.collector.core import CodeCollector


class FunctionInfo:
    """関数情報を格納するクラス"""
    def __init__(self, file_path: str, function_name: str, display_name: str = None):
        self.file_path = file_path
        self.function_name = function_name
        self.display_name = display_name or function_name
        
    def __repr__(self):
        return f"FunctionInfo({self.file_path}, {self.function_name})"


class FunctionSelectorScreen(Screen):
    """関数選択画面"""
    
    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("enter", "select", "Select", show=False),
        Binding("ctrl+c", "quit", "Quit"),
    ]
    
    def __init__(self, project_root: str):
        super().__init__()
        self.project_root = project_root
        self.functions: List[FunctionInfo] = []
        self.filtered_functions: List[FunctionInfo] = []
        self.selected_function: Optional[FunctionInfo] = None
        
    def compose(self) -> ComposeResult:
        """UI構成を定義"""
        yield Header(show_clock=True)
        
        with Container(id="main"):
            yield Label("🔍 Code Collector - Interactive Mode", id="title")
            yield Label(f"Project: {os.path.basename(self.project_root)}", id="project")
            
            with Horizontal():
                with Vertical(id="left-panel"):
                    yield Label("Search Functions:")
                    yield Input(placeholder="Type to search functions...", id="search")
                    yield DataTable(id="functions-table")
                    
                    with Horizontal(id="buttons"):
                        yield Button("Select Function", variant="primary", id="select-btn")
                        yield Button("Cancel", variant="error", id="cancel-btn")
                
                with Vertical(id="right-panel"):
                    yield Label("Function Preview:")
                    yield TextArea("", id="preview", read_only=True)
        
        yield Footer()
    
    def on_mount(self) -> None:
        """画面がマウントされたときの処理"""
        self.load_functions()
        self.update_table()
        self.query_one("#search", Input).focus()
    
    def load_functions(self) -> None:
        """プロジェクト内の全関数を読み込み"""
        self.query_one("#main").loading = True
        
        try:
            collector = CodeCollector(self.project_root, verbose=False)
            source_files = collector._find_all_source_files()
            
            for file_path in source_files:
                try:
                    analyzer = collector._get_analyzer_for_file(file_path)
                    if analyzer:
                        analysis = analyzer.analyze_file(file_path)
                        if analysis and 'functions' in analysis:
                            rel_path = os.path.relpath(file_path, self.project_root)
                            for func_name in analysis['functions']:
                                # 表示用の名前を生成
                                display_name = f"{rel_path}::{func_name}"
                                func_info = FunctionInfo(file_path, func_name, display_name)
                                self.functions.append(func_info)
                except Exception as e:
                    # エラーがあってもスキップして続行
                    continue
                    
        except Exception as e:
            self.notify(f"Error loading functions: {e}", severity="error")
        finally:
            self.query_one("#main").loading = False
            
        self.filtered_functions = self.functions.copy()
        self.notify(f"Loaded {len(self.functions)} functions")
    
    def update_table(self) -> None:
        """関数テーブルを更新"""
        table = self.query_one("#functions-table", DataTable)
        table.clear(columns=True)
        
        # カラムを設定
        table.add_column("File", width=30)
        table.add_column("Function", width=25)
        table.add_column("Type", width=15)
        
        # 行を追加
        for func_info in self.filtered_functions:
            rel_path = os.path.relpath(func_info.file_path, self.project_root)
            func_type = self._get_function_type(func_info)
            table.add_row(rel_path, func_info.function_name, func_type, key=func_info)
    
    def _get_function_type(self, func_info: FunctionInfo) -> str:
        """関数の種類を判定"""
        if "." in func_info.function_name:
            return "Method"
        elif func_info.file_path.endswith(('.tsx', '.jsx')):
            return "Component"
        elif func_info.file_path.endswith(('.ts', '.js')):
            return "Function"
        else:
            return "Function"
    
    def on_input_changed(self, message: Input.Changed) -> None:
        """検索入力が変更されたときの処理"""
        if message.input.id == "search":
            search_term = message.value.lower()
            self.filter_functions(search_term)
    
    def filter_functions(self, search_term: str) -> None:
        """関数をフィルタリング"""
        if not search_term:
            self.filtered_functions = self.functions.copy()
        else:
            self.filtered_functions = [
                func for func in self.functions
                if (search_term in func.function_name.lower() or 
                    search_term in os.path.basename(func.file_path).lower())
            ]
        self.update_table()
    
    def on_data_table_row_selected(self, message: DataTable.RowSelected) -> None:
        """テーブルの行が選択されたときの処理"""
        if message.data_table.id == "functions-table":
            func_info = message.row_key
            self.selected_function = func_info
            self.show_function_preview(func_info)
    
    def show_function_preview(self, func_info: FunctionInfo) -> None:
        """関数のプレビューを表示"""
        try:
            collector = CodeCollector(self.project_root, verbose=False)
            analyzer = collector._get_analyzer_for_file(func_info.file_path)
            if analyzer:
                analysis = analyzer.analyze_file(func_info.file_path)
                if analysis and 'functions' in analysis and func_info.function_name in analysis['functions']:
                    code = analysis['functions'][func_info.function_name]
                    
                    # シンタックスハイライト
                    ext = os.path.splitext(func_info.file_path)[1]
                    if ext in ['.py', '.pyw']:
                        language = "python"
                    elif ext in ['.ts', '.tsx']:
                        language = "typescript"
                    elif ext in ['.js', '.jsx']:
                        language = "javascript"
                    else:
                        language = "text"
                    
                    preview = self.query_one("#preview", TextArea)
                    preview.text = code
                    
        except Exception as e:
            preview = self.query_one("#preview", TextArea)
            preview.text = f"Error loading preview: {e}"
    
    def on_button_pressed(self, message: Button.Pressed) -> None:
        """ボタンが押されたときの処理"""
        if message.button.id == "select-btn":
            self.action_select()
        elif message.button.id == "cancel-btn":
            self.action_cancel()
    
    def action_select(self) -> None:
        """関数を選択して実行"""
        if self.selected_function:
            self.dismiss(self.selected_function)
        else:
            self.notify("Please select a function first", severity="warning")
    
    def action_cancel(self) -> None:
        """キャンセル"""
        self.dismiss(None)


class CollectionResultScreen(Screen):
    """収集結果表示画面"""
    
    BINDINGS = [
        Binding("escape", "close", "Close"),
        Binding("ctrl+c", "quit", "Quit"),
        Binding("ctrl+s", "save", "Save to File"),
    ]
    
    def __init__(self, result: str, stats: dict):
        super().__init__()
        self.result = result
        self.stats = stats
    
    def compose(self) -> ComposeResult:
        """UI構成を定義"""
        yield Header(show_clock=True)
        
        with Container(id="result-container"):
            yield Label("📋 Collection Result", id="result-title")
            
            # 統計情報
            stats_text = f"Functions: {self.stats.get('function_count', 0)} | Files: {self.stats.get('file_count', 0)} | Size: {self.stats.get('size_mb', 0):.2f}MB"
            yield Label(stats_text, id="stats")
            
            # 結果表示
            yield TextArea(self.result, id="result-text", read_only=True)
            
            # ボタン
            with Horizontal(id="result-buttons"):
                yield Button("Save to File", variant="primary", id="save-btn")
                yield Button("Close", variant="default", id="close-btn")
        
        yield Footer()
    
    def on_button_pressed(self, message: Button.Pressed) -> None:
        """ボタンが押されたときの処理"""
        if message.button.id == "save-btn":
            self.action_save()
        elif message.button.id == "close-btn":
            self.action_close()
    
    def action_save(self) -> None:
        """ファイルに保存"""
        # 簡易実装：現在の日時でファイル名を生成
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"collected_code_{timestamp}.md"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(self.result)
            self.notify(f"Saved to {filename}", severity="information")
        except Exception as e:
            self.notify(f"Error saving file: {e}", severity="error")
    
    def action_close(self) -> None:
        """画面を閉じる"""
        self.dismiss()


class InteractiveCollectorApp(App):
    """メインのインタラクティブアプリケーション"""
    
    CSS_PATH = None
    CSS = """
    #main {
        height: 100%;
        padding: 1;
    }
    
    #title {
        text-align: center;
        color: $accent;
        text-style: bold;
        margin-bottom: 1;
    }
    
    #project {
        text-align: center;
        color: $text-muted;
        margin-bottom: 1;
    }
    
    #left-panel {
        width: 60%;
        margin-right: 1;
    }
    
    #right-panel {
        width: 40%;
    }
    
    #functions-table {
        height: 70%;
        margin-bottom: 1;
    }
    
    #preview {
        height: 80%;
    }
    
    #buttons {
        height: auto;
        margin-top: 1;
    }
    
    #result-container {
        height: 100%;
        padding: 1;
    }
    
    #result-title {
        text-align: center;
        color: $accent;
        text-style: bold;
        margin-bottom: 1;
    }
    
    #stats {
        text-align: center;
        color: $text-muted;
        margin-bottom: 1;
    }
    
    #result-text {
        height: 80%;
        margin-bottom: 1;
    }
    
    #result-buttons {
        height: auto;
    }
    """
    
    def __init__(self, project_root: str, verbose: bool = False):
        super().__init__()
        self.project_root = project_root
        self.verbose = verbose
    
    def on_mount(self) -> None:
        """アプリケーション開始"""
        self.push_screen(FunctionSelectorScreen(self.project_root), self.on_function_selected)
    
    def on_function_selected(self, selected_function: Optional[FunctionInfo]) -> None:
        """関数が選択されたときの処理"""
        if selected_function:
            self.collect_dependencies(selected_function)
        else:
            self.exit()
    
    def collect_dependencies(self, func_info: FunctionInfo) -> None:
        """依存関係を収集"""
        try:
            collector = CodeCollector(self.project_root, verbose=self.verbose)
            
            # 収集実行
            result = collector.collect(func_info.file_path, func_info.function_name)
            
            # 統計情報を計算
            stats = self.calculate_stats(result)
            
            # 結果画面を表示
            self.push_screen(CollectionResultScreen(result, stats), self.on_result_closed)
            
        except Exception as e:
            self.notify(f"Error collecting dependencies: {e}", severity="error")
    
    def calculate_stats(self, result: str) -> dict:
        """結果の統計情報を計算"""
        lines = result.split('\n')
        function_count = len([line for line in lines if line.strip().startswith('def ')])
        file_count = len([line for line in lines if line.startswith('```') and not line.endswith('```')])
        size_mb = len(result.encode('utf-8')) / (1024 * 1024)
        
        return {
            'function_count': function_count,
            'file_count': file_count,
            'size_mb': size_mb
        }
    
    def on_result_closed(self) -> None:
        """結果画面が閉じられたときの処理"""
        # 新しい関数を選択するか終了するかを選択
        self.push_screen(FunctionSelectorScreen(self.project_root), self.on_function_selected)


def run_interactive_mode(project_root: str, verbose: bool = False):
    """インタラクティブモードを開始"""
    app = InteractiveCollectorApp(project_root, verbose)
    return app.run()
