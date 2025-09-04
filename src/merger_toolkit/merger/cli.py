# -*- coding: utf-8 -*-
import os
import sys
import argparse
import io
import pathspec
from importlib import resources

try:
    import pyperclip
    PYPERCLIP_AVAILABLE = True
except ImportError:
    PYPERCLIP_AVAILABLE = False

FORCE_EXCLUDE_EXTENSIONS = {
    '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.ico', '.svg', '.webp',
    '.mp4', '.avi', '.mov', '.wmv', '.flv', '.mkv', '.mp3', '.wav', '.ogg', '.flac', '.aac',
    '.zip', '.tar', '.gz', '.rar', '.7z', '.jar', '.war', '.ear', '.exe', '.dll', '.so',
    '.dylib', '.o', '.a', '.lib', '.class', '.app', '.msi', '.pdf', '.doc', '.docx',
    '.xls', '.xlsx', '.ppt', '.pptx', '.odt', '.ods', '.odp', '.sqlite', '.db', '.mdb',
    '.dbf', '.ttf', '.otf', '.woff', '.woff2', '.eot', '.pyc', '.pyd', '.dat', '.bin',
}
FORCE_EXCLUDE_DIRS = {'.git'}


def merge_repository_to_string(input_dir, base_gitignore_spec, final_exclude_dirs, final_exclude_ext, final_exclude_files, verbose=False):
    """
    Merge repository files into a single string, respecting hierarchical .gitignore files.
    
    Args:
        input_dir: Root directory to scan
        base_gitignore_spec: Root-level gitignore spec (can be None)
        final_exclude_dirs: Set of directory names to exclude
        final_exclude_ext: Set of file extensions to exclude  
        final_exclude_files: Set of file names to exclude
        verbose: Whether to print verbose output
    
    Returns:
        String containing merged content
    """
    string_io = io.StringIO()
    
    # Cache for gitignore specs at each directory level
    gitignore_cache = {}
    
    def get_combined_gitignore_spec(dir_path):
        """Get combined gitignore spec for a given directory, including all parent gitignores."""
        if dir_path in gitignore_cache:
            return gitignore_cache[dir_path]
            
        # Start with parent gitignore specs
        parent_dir = os.path.dirname(dir_path)
        if parent_dir != dir_path and parent_dir:  # Not root
            parent_spec = get_combined_gitignore_spec(parent_dir)
        else:
            parent_spec = base_gitignore_spec
            
        # Check for local .gitignore in current directory
        local_gitignore_path = os.path.join(dir_path, '.gitignore')
        local_spec = None
        
        if os.path.isfile(local_gitignore_path):
            try:
                with open(local_gitignore_path, 'r', encoding='utf-8') as f:
                    local_spec = pathspec.PathSpec.from_lines('gitwildmatch', f)
                if verbose:
                    rel_path = os.path.relpath(local_gitignore_path, input_dir)
                    print(f"Found .gitignore at: {rel_path}")
            except Exception as e:
                if verbose:
                    print(f"Warning: Could not read .gitignore at {local_gitignore_path}: {e}")
        
        # Combine parent and local specs
        combined_spec = None
        if parent_spec and local_spec:
            # Combine patterns from both specs
            combined_patterns = list(parent_spec.patterns) + list(local_spec.patterns)
            combined_spec = pathspec.PathSpec(combined_patterns)
        elif parent_spec:
            combined_spec = parent_spec
        elif local_spec:
            combined_spec = local_spec
            
        gitignore_cache[dir_path] = combined_spec
        return combined_spec
    
    for root, dirs, files in os.walk(input_dir, topdown=True):
        # Get the appropriate gitignore spec for this directory
        current_gitignore_spec = get_combined_gitignore_spec(root)
        
        # First, exclude directories by name
        dirs[:] = [d for d in dirs if d not in final_exclude_dirs]
        
        # Then, exclude directories by gitignore rules
        if current_gitignore_spec:
            # Convert directory paths to relative paths from input_dir for gitignore matching
            dir_paths_for_gitignore = []
            excluded_dirs = []
            
            for d in dirs:
                dir_full_path = os.path.join(root, d)
                relative_dir_path = os.path.relpath(dir_full_path, input_dir).replace("\\", "/")
                
                # Check both with and without trailing slash as different gitignore implementations vary
                if (current_gitignore_spec.match_file(relative_dir_path) or 
                    current_gitignore_spec.match_file(relative_dir_path + '/')):
                    excluded_dirs.append(d)
                    if verbose:
                        print(f"Skipping directory by .gitignore: {relative_dir_path}")
            
            dirs[:] = [d for d in dirs if d not in excluded_dirs]
        
        # Process files
        sorted_files = sorted(files)
        for filename in sorted_files:
            # Skip .gitignore files themselves in the output
            if filename == '.gitignore':
                continue
                
            file_path = os.path.join(root, filename)
            relative_path = os.path.relpath(file_path, input_dir).replace("\\", "/")
            _, ext = os.path.splitext(filename)
            
            # Check gitignore rules
            if current_gitignore_spec and current_gitignore_spec.match_file(relative_path):
                if verbose:
                    print(f"Skipping by .gitignore: {relative_path}")
                continue
                
            # Check file extension exclusions
            if ext.lower() in final_exclude_ext:
                if verbose:
                    print(f"Skipping file by extension: {relative_path}")
                continue
                
            # Check file name exclusions  
            if filename in final_exclude_files:
                if verbose:
                    print(f"Skipping file by name: {relative_path}")
                continue
                
            if verbose:
                print(f"Processing: {relative_path}")
                
            try:
                string_io.write(f"```{relative_path}\n")
                content = ""
                error_message = None
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as infile:
                        content = infile.read()
                except (UnicodeDecodeError, IOError):
                    try:
                        with open(file_path, 'r', encoding=None) as infile:
                            content = infile.read()
                        if verbose:
                            print(f"  Note: Read '{relative_path}' with system default encoding.")
                    except Exception as e:
                        error_message = f"# ERROR: Could not read file (tried UTF-8 and default): {e}\n"
                except Exception as e:
                    error_message = f"# ERROR: Unexpected error reading file: {e}\n"
                
                if error_message:
                    string_io.write(error_message)
                    if verbose:
                        print(f"  {error_message.strip()}")
                else:
                    if content and not content.endswith('\n'):
                        content += '\n'
                    string_io.write(content)
                    
                string_io.write(f"```\n\n")
                
            except Exception as e:
                print(f"Error processing block for file {relative_path}: {e}")
                string_io.write(f"``` Error Processing {relative_path}\n# ERROR: Unexpected error: {e}\n```\n\n")
    
    return string_io.getvalue()


def main():
    parser = argparse.ArgumentParser(description="Merge repository files into a single output, respecting .gitignore and other rules.", formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("input_dir", nargs='?', default='.', help="Path to the input directory to scan (default: current directory).")
    parser.add_argument("-o", "--output", metavar="OUTPUT_FILE", default=None, help="Path to the output file. If not specified, content is copied to the clipboard.")
    parser.add_argument("-xd", "--exclude-dir", action='append', default=[], metavar='DIR', help="Add a directory name to exclude.")
    parser.add_argument("-xe", "--exclude-ext", action='append', default=[], metavar='.ext', help="Add a file extension to exclude.")
    parser.add_argument("-xf", "--exclude-file", action='append', default=[], metavar='FILE', help="Add a file name to exclude.")
    parser.add_argument("--no-gitignore", action="store_true", help="Do not use .gitignore file for exclusions.")
    parser.add_argument("-v", "--verbose", action="store_true", help="Print verbose output.")
    args = parser.parse_args()

    if not args.output and not PYPERCLIP_AVAILABLE:
        print("\nError: To copy to clipboard, 'pyperclip' library is required.", file=sys.stderr)
        print("Please install it ('pip install pyperclip') or use the -o/--output option.", file=sys.stderr)
        return 1
    if not os.path.isdir(args.input_dir):
        print(f"Error: Input directory '{args.input_dir}' not found.", file=sys.stderr)
        return 1
        
    base_gitignore_spec = None
    if not args.no_gitignore:
        # Check for root-level .gitignore
        root_gitignore_path = os.path.join(args.input_dir, '.gitignore')
        if os.path.isfile(root_gitignore_path):
            if args.verbose: 
                print(f"Using root .gitignore from: {root_gitignore_path}")
            with open(root_gitignore_path, 'r', encoding='utf-8') as f:
                base_gitignore_spec = pathspec.PathSpec.from_lines('gitwildmatch', f)
        else:
            if args.verbose: 
                print("No root .gitignore found. Attempting to use built-in default .gitignore.")
            try:
                # Use built-in default gitignore as base
                default_gitignore_content = resources.files('merger_toolkit.merger.data').joinpath('default.gitignore').read_text(encoding='utf-8')
                base_gitignore_spec = pathspec.PathSpec.from_lines('gitwildmatch', default_gitignore_content.splitlines())
            except (FileNotFoundError, ModuleNotFoundError):
                if args.verbose: 
                    print("Warning: Built-in default .gitignore not found. Proceeding without base gitignore rules.")
        
        if args.verbose:
            print("Note: Will also check for .gitignore files in subdirectories during traversal.")

    final_exclude_dirs = set(FORCE_EXCLUDE_DIRS)
    final_exclude_ext = {ext.lower() for ext in FORCE_EXCLUDE_EXTENSIONS}
    final_exclude_files = set()
    final_exclude_dirs.update(args.exclude_dir)
    final_exclude_ext.update({ext.lower() if ext.startswith('.') else '.' + ext.lower() for ext in args.exclude_ext})
    final_exclude_files.update(args.exclude_file)
    
    try:
        merged_content = merge_repository_to_string(
            args.input_dir, base_gitignore_spec, final_exclude_dirs,
            final_exclude_ext, final_exclude_files, args.verbose
        )
        if not merged_content.strip():
            print("\nWarning: No files were found or processed based on the criteria.")
            return 0
        
        # This custom prefix can be removed if not needed.
        final_output = "差分はいらない。変更が必要なファイルのみを、各ファイルごとにコードブロックで出力してください。\nまた、必要最低限の変更にしてください。リファクタなどは不要です。\n\n" + merged_content.strip() + "\n"
        
        if args.output:
            output_path = os.path.abspath(args.output)
            try:
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                with open(output_path, 'w', encoding='utf-8') as f: f.write(final_output)
                print(f"\nMerged content successfully saved to '{output_path}'.")
            except IOError as e:
                print(f"\nError writing to file '{output_path}': {e}", file=sys.stderr)
                return 1
        else:
            try:
                pyperclip.copy(final_output)
                content_size_mb = len(final_output.encode('utf-8')) / (1024 * 1024)
                print(f"\nMerged content ({content_size_mb:.2f} MB) copied to clipboard successfully.")
                if content_size_mb > 5: print("Warning: Content is large. Pasting may be slow in some applications.")
            except pyperclip.PyperclipException as e:
                print(f"\nError copying to clipboard: {e}", file=sys.stderr)
                return 1
    except KeyboardInterrupt:
        print("\nProcess interrupted by user.", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}", file=sys.stderr)
        return 1

    return 0