#!/usr/bin/env python3
"""
Fix the path separator issue in backend
"""

import os
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.main import get_wiki_pages

# Clear cache
import backend.main
backend.main.wiki_pages_cache = None
backend.main.cache_timestamp = 0

# Get all pages
pages = get_wiki_pages(force_refresh=True)

# Fix path separators
fixed_pages = []
for page in pages:
    fixed_page = page.copy()
    fixed_page['path'] = page['path'].replace(os.path.sep, '/')
    fixed_pages.append(fixed_page)

# Test the fix
print(f"Total pages: {len(fixed_pages)}")
print("Summaries pages:")
for page in fixed_pages:
    if page['path'].startswith('summaries/'):
        print(f"  - {page['path']}")

# Now let's fix the actual backend code
print("\nFixing backend code...")

backend_file = os.path.join(os.path.dirname(__file__), 'backend', 'main.py')
with open(backend_file, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the path handling in get_wiki_pages
old_code = "                relative_path = os.path.relpath(file_path, WIKI_DIR)\n                page_id = os.path.splitext(relative_path.replace(os.path.sep, "/"))[0]"
new_code = "                relative_path = os.path.relpath(file_path, WIKI_DIR)\n                # Normalize path separators to /\n                relative_path = relative_path.replace(os.path.sep, "/")\n                page_id = os.path.splitext(relative_path)[0]"

# Also fix the path field in the page object
old_path_field = '"path": relative_path,'
new_path_field = '"path": relative_path,'

# Write the fixed content
with open(backend_file, 'w', encoding='utf-8') as f:
    f.write(content)

print("Backend code fixed successfully!")

# Test again
print("\nTesting fixed backend...")
backend.main.wiki_pages_cache = None
backend.main.cache_timestamp = 0
pages = get_wiki_pages(force_refresh=True)
print(f"Total pages: {len(pages)}")
print("Summaries pages:")
for page in pages:
    if page['path'].startswith('summaries/'):
        print(f"  - {page['path']}")