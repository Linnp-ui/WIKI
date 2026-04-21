#!/usr/bin/env python3
"""
Test script for MarkItDown integration
"""

import sys
import os
import yaml

# Add the scripts directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'scripts'))

from ingest import read_file_content, load_config

def test_markitdown():
    """Test MarkItDown integration"""
    print("Testing MarkItDown integration...")
    
    # Test with markdown file
    test_file = "test_document.md"
    if os.path.exists(test_file):
        try:
            content = read_file_content(test_file)
            print(f"\nSuccessfully read {test_file}:")
            print("=" * 50)
            print(content)
            print("=" * 50)
            print("Test passed!")
        except Exception as e:
            print(f"Error reading file: {e}")
    else:
        print(f"Test file {test_file} not found")

if __name__ == "__main__":
    test_markitdown()