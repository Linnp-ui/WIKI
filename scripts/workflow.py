#!/usr/bin/env python3
"""
Workflow script for LLM Wiki.
Implements the Ingest-Query-Lint closed loop workflow.

This script coordinates the three core operations:
1. Ingest: Process raw source files into Wiki pages
2. Query: Search Wiki and generate answers
3. Lint: Check Wiki quality and fix issues
"""

import os
import sys
import subprocess
import yaml
from datetime import datetime


def load_config() -> dict:
    """Load configuration from config.yaml"""
    config_path = os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")), "config.yaml")
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def run_ingest(source_file: str) -> bool:
    """Run ingestion process"""
    ingest_script = os.path.join(os.path.dirname(__file__), "ingest.py")
    
    # Set UTF-8 encoding for subprocess on Windows
    env = os.environ.copy()
    env['PYTHONIOENCODING'] = 'utf-8'
    
    result = subprocess.run([sys.executable, ingest_script, source_file], 
                         capture_output=True, text=True,
                         encoding='utf-8', errors='replace',
                         env=env)
    print("=== INGEST OUTPUT ===")
    print(result.stdout)
    if result.stderr:
        print("=== INGEST ERRORS ===")
        print(result.stderr)
    return result.returncode == 0


def run_query(query: str) -> str:
    """Run query process"""
    query_script = os.path.join(os.path.dirname(__file__), "query.py")
    result = subprocess.run([sys.executable, query_script, query], 
                         capture_output=True, text=True)
    print("=== QUERY OUTPUT ===")
    print(result.stdout)
    if result.stderr:
        print("=== QUERY ERRORS ===")
        print(result.stderr)
    return result.stdout


def run_lint() -> bool:
    """Run lint process"""
    lint_script = os.path.join(os.path.dirname(__file__), "lint.py")
    
    # Set UTF-8 encoding for subprocess on Windows
    env = os.environ.copy()
    env['PYTHONIOENCODING'] = 'utf-8'
    
    result = subprocess.run([sys.executable, lint_script], 
                         capture_output=True, text=True,
                         encoding='utf-8', errors='replace',
                         env=env)
    print("=== LINT OUTPUT ===")
    print(result.stdout)
    if result.stderr:
        print("=== LINT ERRORS ===")
        print(result.stderr)
    return result.returncode == 0


def update_index() -> bool:
    """Update wiki index.md"""
    update_script = os.path.join(os.path.dirname(__file__), "update_index.py")
    if os.path.exists(update_script):
        # Set UTF-8 encoding for subprocess on Windows
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        
        result = subprocess.run([sys.executable, update_script], 
                             capture_output=True, text=True,
                             encoding='utf-8', errors='replace',
                             env=env)
        print("=== INDEX UPDATE OUTPUT ===")
        print(result.stdout)
        if result.stderr:
            print("=== INDEX UPDATE ERRORS ===")
            print(result.stderr)
        return result.returncode == 0
    return False


def main():
    """Main workflow function"""
    print(f"=== LLM Wiki Workflow started at {datetime.now().isoformat()} ===")
    
    config = load_config()
    
    # Get base directory (parent of scripts directory)
    base_dir = os.path.dirname(os.path.dirname(__file__))
    
    # Check if we have source files to ingest
    raw_sources_dir = config.get("raw_sources_dir", "raw_sources")
    # Convert to absolute path if relative
    if not os.path.isabs(raw_sources_dir):
        raw_sources_dir = os.path.join(base_dir, raw_sources_dir)
    
    print(f"Looking for raw sources in: {raw_sources_dir}")
    
    if os.path.exists(raw_sources_dir):
        source_files = [f for f in os.listdir(raw_sources_dir) 
                      if os.path.isfile(os.path.join(raw_sources_dir, f))]
        
        if source_files:
            print(f"Found {len(source_files)} source files to ingest")
            for source_file in source_files:
                full_path = os.path.join(raw_sources_dir, source_file)
                print(f"\nProcessing: {source_file}")
                success = run_ingest(full_path)
                if success:
                    print(f"[OK] Successfully ingested: {source_file}")
                else:
                    print(f"[FAIL] Failed to ingest: {source_file}")
        else:
            print("No source files found in raw_sources directory")
    else:
        print(f"Raw sources directory not found: {raw_sources_dir}")
    
    # Update index
    print("\n=== Updating Wiki index ===")
    update_index()
    
    # Run lint to check quality
    print("\n=== Running Wiki quality checks ===")
    run_lint()
    
    print(f"\n=== LLM Wiki Workflow completed at {datetime.now().isoformat()} ===")


if __name__ == "__main__":
    main()