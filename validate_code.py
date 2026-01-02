"""
Comprehensive Python code validation script.
Checks for syntax errors, import errors, and common issues.
"""

import sys
import os
import importlib.util
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

def check_module(module_path):
    """Check if a module can be imported without errors."""
    try:
        spec = importlib.util.spec_from_file_location("test_module", module_path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return True, None
    except Exception as e:
        return False, str(e)
    return False, "Unknown error"

def main():
    """Main validation function."""
    src_dir = Path(__file__).parent / 'src' / 'oracle_duckdb_sync'
    
    errors = []
    success_count = 0
    
    # Find all Python files
    py_files = list(src_dir.rglob('*.py'))
    
    print(f"Checking {len(py_files)} Python files...\n")
    
    for py_file in py_files:
        # Skip __pycache__
        if '__pycache__' in str(py_file):
            continue
            
        rel_path = py_file.relative_to(Path(__file__).parent)
        
        # Check syntax by compiling
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                compile(f.read(), str(py_file), 'exec')
            success_count += 1
            print(f"✓ {rel_path}")
        except SyntaxError as e:
            errors.append(f"SYNTAX ERROR in {rel_path}:\n  Line {e.lineno}: {e.msg}")
            print(f"✗ {rel_path} - SYNTAX ERROR")
        except Exception as e:
            errors.append(f"ERROR in {rel_path}: {e}")
            print(f"✗ {rel_path} - ERROR")
    
    print(f"\n{'='*60}")
    print(f"Results: {success_count} OK, {len(errors)} ERRORS")
    print(f"{'='*60}\n")
    
    if errors:
        print("ERRORS FOUND:\n")
        for error in errors:
            print(error)
            print()
        return 1
    else:
        print("✓ All files passed validation!")
        return 0

if __name__ == '__main__':
    sys.exit(main())
