#!/usr/bin/env python3
"""
Debug script to check the issue with summaries pages not showing up
"""

import os
import sys
import json

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.main import get_wiki_pages

# Clear cache
import backend.main
backend.main.wiki_pages_cache = None
backend.main.cache_timestamp = 0

# Get all pages
pages = get_wiki_pages(force_refresh=True)

print(f"Total pages: {len(pages)}")

# Check summaries pages
summaries_pages = []
for page in pages:
    path = page['path']
    if 'summaries' in path:
        summaries_pages.append(page)
        print(f"Found summaries page: {path}")

print(f"\nSummaries pages found: {len(summaries_pages)}")

# Check all page paths
print("\nAll page paths (first 50):")
for page in pages[:50]:
    print(f"  - {page['path']}")

# Save all pages to a file
with open('debug_pages.json', 'w', encoding='utf-8') as f:
    json.dump(pages, f, ensure_ascii=False, indent=2)

print("\nAll pages saved to debug_pages.json")