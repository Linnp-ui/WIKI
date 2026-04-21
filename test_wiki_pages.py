#!/usr/bin/env python3
"""
Test script to debug get_wiki_pages function
"""

import os
import sys
import time
from typing import List, Dict, Any

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.ingest import load_config

# Load configuration
config = load_config()

# Base directory
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
WIKI_DIR = os.path.join(BASE_DIR, config["wiki_dir"])

print(f"BASE_DIR: {BASE_DIR}")
print(f"WIKI_DIR: {WIKI_DIR}")
print(f"WIKI_DIR exists: {os.path.exists(WIKI_DIR)}")

if os.path.exists(WIKI_DIR):
    print(f"Contents of WIKI_DIR: {os.listdir(WIKI_DIR)}")
    
    # Test os.walk
    print("\nTesting os.walk:")
    for root, dirs, files in os.walk(WIKI_DIR):
        print(f"\nDirectory: {root}")
        print(f"Subdirectories: {dirs}")
        print(f"Files: {files}")
        
        # Count .md files
        md_files = [f for f in files if f.endswith('.md')]
        print(f"MD files: {md_files}")

# Test the actual get_wiki_pages function
print("\n" + "="*50)
print("Testing get_wiki_pages function:")
print("="*50)

# Import the function
from backend.main import get_wiki_pages

# Clear cache
import backend.main
backend.main.wiki_pages_cache = None
backend.main.cache_timestamp = 0

# Get pages
pages = get_wiki_pages(force_refresh=True)
print(f"\nTotal pages found: {len(pages)}")

# Check summaries pages
summaries_pages = [p for p in pages if p['path'].startswith('summaries/')]
print(f"Summaries pages found: {len(summaries_pages)}")
print("Summaries page paths:")
for page in summaries_pages:
    print(f"  - {page['path']}")

# Check all page paths
print("\nAll page paths (first 20):")
for page in pages[:20]:
    print(f"  - {page['path']}")