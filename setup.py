import subprocess
import os
import sys
from setuptools import setup, find_packages
from setuptools.command.build_py import build_py

# --- npm install を実行するカスタムコマンド ---
def npm_install(path):
    """指定されたパスで npm install を実行する"""
    # 変更点: package.jsonのある正しいパスを指定
    collector_path = os.path.join(path, 'src', 'merger_toolkit', 'collector')
    if not os.path.exists(os.path.join(collector_path, 'package.json')):
        print(f"package.json not found in {collector_path}", file=sys.stderr)
        return

    print(f"Running 'npm install' in {collector_path}")
    try:
        subprocess.check_call(['npm', 'install'], cwd=collector_path, shell=os.name == 'nt')
        print("'npm install' completed successfully.")
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"Error during 'npm install': {e}", file=sys.stderr)
        print("Please ensure Node.js and npm are installed and in your PATH.", file=sys.stderr)
        raise

# --- 標準のビルドプロセスにnpm installを組み込む ---
class CustomBuildPyCommand(build_py):
    def run(self):
        npm_install(os.path.dirname(os.path.realpath(__file__)))
        build_py.run(self)

# --- パッケージのセットアップ ---
setup(
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    
    # 変更点: データファイルのパスを 'merger_toolkit' に合わせる
    package_data={
        'merger_toolkit.merger': ['data/default.gitignore'],
        'merger_toolkit.collector': ['*.js', 'package.json'],
    },
    
    # 変更点: コマンドのエントリーポイントを 'merger_toolkit' と 'main.py' に合わせる
    entry_points={
        'console_scripts': [
            'repo-merge = merger_toolkit.merger.cli:main',
            'code-collector = merger_toolkit.collector.main:main', # collector.py -> main.py
        ],
    },
    
    cmdclass={
        'build_py': CustomBuildPyCommand,
    },
    include_package_data=True,
)