# -*- coding: utf-8 -*-
"""
シンプルなインタラクティブモード（TUIなし）
"""

import os
from typing import List, Tuple, Optional
from merger_toolkit.collector.core import CodeCollector


class SimpleInteractiveMode:
    """シンプルなコマンドラインインタラクティブモード"""
    
    def __init__(self, project_root: str, verbose: bool = False):
        self.project_root = project_root
        self.verbose = verbose
        self.functions: List[Tuple[str, str, str]] = []  # (file_path, function_name, display_name)
    
    def run(self) -> int:
        """インタラクティブモードを実行"""
        print("🔍 Code Collector - Interactive Mode")
        print("=" * 50)
        print(f"Project: {os.path.basename(self.project_root)}")
        print()
        
        # 関数一覧を読み込み
        print("Loading functions...")
        self.load_functions()
        
        if not self.functions:
            print("❌ No functions found in the project.")
            return 1
        
        print(f"✅ Found {len(self.functions)} functions")
        print()
        
        while True:
            try:
                selected = self.select_function()
                if selected is None:
                    print("👋 Goodbye!")
                    return 0
                
                file_path, function_name, _ = selected
                print(f"\n🔄 Collecting dependencies for {function_name}...")
                
                # 依存関係を収集
                collector = CodeCollector(self.project_root, verbose=self.verbose)
                result = collector.collect(file_path, function_name)
                
                if result:
                    self.handle_result(result, function_name)
                else:
                    print("❌ No code was collected.")
                
                # 継続するかどうか尋ねる
                if not self.ask_continue():
                    break
                    
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                return 0
            except Exception as e:
                print(f"❌ Error: {e}")
                if not self.ask_continue():
                    break
        
        return 0
    
    def load_functions(self) -> None:
        """プロジェクト内の関数を読み込み"""
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
                                display_name = f"{rel_path}::{func_name}"
                                self.functions.append((file_path, func_name, display_name))
                except Exception:
                    continue
                    
        except Exception as e:
            print(f"❌ Error loading functions: {e}")
    
    def select_function(self) -> Optional[Tuple[str, str, str]]:
        """関数を選択"""
        while True:
            print("Select a function:")
            print("  📁 Search by file name: 'f:filename'")
            print("  🔍 Search by function name: 'func_name' or just type part of name")
            print("  📋 List all: 'list' or 'l'")
            print("  ❌ Exit: 'quit' or 'q'")
            print()
            
            query = input("👉 Enter your choice: ").strip()
            
            if query.lower() in ['quit', 'q', 'exit']:
                return None
            
            if query.lower() in ['list', 'l']:
                return self.list_and_select_functions()
            
            # ファイル名検索
            if query.startswith('f:'):
                filename = query[2:].strip()
                return self.search_by_file(filename)
            
            # 関数名検索
            return self.search_by_function(query)
    
    def list_and_select_functions(self, functions: List[Tuple[str, str, str]] = None) -> Optional[Tuple[str, str, str]]:
        """関数一覧を表示して選択"""
        if functions is None:
            functions = self.functions
        
        if not functions:
            print("❌ No functions found.")
            return None
        
        # ページング
        page_size = 20
        total_pages = (len(functions) + page_size - 1) // page_size
        current_page = 0
        
        while True:
            start_idx = current_page * page_size
            end_idx = min(start_idx + page_size, len(functions))
            page_functions = functions[start_idx:end_idx]
            
            print(f"\n📋 Functions (Page {current_page + 1}/{total_pages}):")
            print("-" * 60)
            
            for i, (_, func_name, display_name) in enumerate(page_functions, start_idx + 1):
                print(f"  {i:2d}. {display_name}")
            
            print("-" * 60)
            print(f"Commands: [number] select, [n]ext page, [p]rev page, [s]earch, [q]uit")
            
            choice = input("👉 Your choice: ").strip().lower()
            
            if choice == 'q':
                return None
            elif choice == 'n' and current_page < total_pages - 1:
                current_page += 1
                continue
            elif choice == 'p' and current_page > 0:
                current_page -= 1
                continue
            elif choice == 's':
                return self.select_function()
            
            # 数字選択
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(functions):
                    selected = functions[idx]
                    print(f"✅ Selected: {selected[2]}")
                    return selected
                else:
                    print("❌ Invalid number. Try again.")
            except ValueError:
                print("❌ Invalid input. Try again.")
    
    def search_by_file(self, filename: str) -> Optional[Tuple[str, str, str]]:
        """ファイル名で検索"""
        matches = [
            func for func in self.functions
            if filename.lower() in os.path.basename(func[0]).lower()
        ]
        
        if not matches:
            print(f"❌ No functions found in files matching '{filename}'")
            return None
        
        print(f"🔍 Found {len(matches)} functions in files matching '{filename}':")
        return self.list_and_select_functions(matches)
    
    def search_by_function(self, func_name: str) -> Optional[Tuple[str, str, str]]:
        """関数名で検索"""
        matches = [
            func for func in self.functions
            if func_name.lower() in func[1].lower()
        ]
        
        if not matches:
            print(f"❌ No functions found matching '{func_name}'")
            return None
        
        if len(matches) == 1:
            selected = matches[0]
            print(f"✅ Found exact match: {selected[2]}")
            return selected
        
        print(f"🔍 Found {len(matches)} functions matching '{func_name}':")
        return self.list_and_select_functions(matches)
    
    def handle_result(self, result: str, function_name: str) -> None:
        """結果を処理"""
        # 統計情報を計算
        lines = result.split('\n')
        function_count = len([line for line in lines if line.strip().startswith('def ')])
        file_count = len([line for line in lines if line.startswith('```') and not line.endswith('```')])
        size_mb = len(result.encode('utf-8')) / (1024 * 1024)
        
        print(f"📊 Collection Results:")
        print(f"   Functions: {function_count}")
        print(f"   Files: {file_count}")
        print(f"   Size: {size_mb:.2f} MB")
        print()
        
        while True:
            print("What would you like to do with the result?")
            print("  📋 1. Copy to clipboard")
            print("  💾 2. Save to file")
            print("  👀 3. Preview (first 20 lines)")
            print("  ⏭️  4. Continue to next function")
            
            choice = input("👉 Choose (1-4): ").strip()
            
            if choice == '1':
                try:
                    import pyperclip
                    pyperclip.copy(result)
                    print("✅ Copied to clipboard!")
                    break
                except ImportError:
                    print("❌ pyperclip not available. Choose another option.")
                except Exception as e:
                    print(f"❌ Failed to copy to clipboard: {e}")
            
            elif choice == '2':
                self.save_to_file(result, function_name)
                break
            
            elif choice == '3':
                self.preview_result(result)
            
            elif choice == '4':
                break
            
            else:
                print("❌ Invalid choice. Try again.")
    
    def save_to_file(self, result: str, function_name: str) -> None:
        """ファイルに保存"""
        from datetime import datetime
        
        # デフォルトファイル名を提案
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"{function_name}_{timestamp}.md"
        
        filename = input(f"💾 Enter filename (default: {default_name}): ").strip()
        if not filename:
            filename = default_name
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(result)
            print(f"✅ Saved to '{filename}'")
        except Exception as e:
            print(f"❌ Failed to save file: {e}")
    
    def preview_result(self, result: str) -> None:
        """結果をプレビュー"""
        lines = result.split('\n')
        print("\n👀 Preview (first 20 lines):")
        print("-" * 60)
        
        for i, line in enumerate(lines[:20], 1):
            print(f"{i:2d}: {line}")
        
        if len(lines) > 20:
            print(f"... and {len(lines) - 20} more lines")
        
        print("-" * 60)
        input("Press Enter to continue...")
    
    def ask_continue(self) -> bool:
        """続行するかどうか尋ねる"""
        while True:
            choice = input("\n🔄 Would you like to collect another function? (y/n): ").strip().lower()
            if choice in ['y', 'yes']:
                return True
            elif choice in ['n', 'no']:
                return False
            else:
                print("❌ Please enter 'y' or 'n'")


def run_simple_interactive_mode(project_root: str, verbose: bool = False) -> int:
    """シンプルなインタラクティブモードを実行"""
    mode = SimpleInteractiveMode(project_root, verbose)
    return mode.run()
