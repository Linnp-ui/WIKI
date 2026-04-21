#!/usr/bin/env python3
"""
Comprehensive test script for MarkItDown integration
"""

import sys
import os
import tempfile
import shutil

# Add the scripts directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'scripts'))

from ingest import read_file_content

def test_markdown():
    """Test MarkItDown with markdown file"""
    print("Testing Markdown file...")
    test_file = "test_document.md"
    if os.path.exists(test_file):
        try:
            content = read_file_content(test_file)
            print(f"✓ Successfully read {test_file}")
            print(f"  Content length: {len(content)} characters")
            return True
        except Exception as e:
            print(f"✗ Error reading {test_file}: {e}")
            return False
    else:
        print(f"✗ Test file {test_file} not found")
        return False

def test_text():
    """Test MarkItDown with text file"""
    print("\nTesting Text file...")
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("This is a test text file.\n\nLine 2.\nLine 3.")
        temp_file = f.name
    
    try:
        content = read_file_content(temp_file)
        print(f"✓ Successfully read text file")
        print(f"  Content: {content[:100]}...")
        return True
    except Exception as e:
        print(f"✗ Error reading text file: {e}")
        return False
    finally:
        if os.path.exists(temp_file):
            os.unlink(temp_file)

def test_invalid_file():
    """Test MarkItDown with invalid file"""
    print("\nTesting invalid file...")
    non_existent_file = "non_existent_file.txt"
    try:
        content = read_file_content(non_existent_file)
        print(f"✗ Should have raised an error for non-existent file")
        return False
    except ValueError as e:
        print(f"✓ Correctly raised error for non-existent file: {e}")
        return True
    except Exception as e:
        print(f"✗ Raised unexpected error: {e}")
        return False

def main():
    """Run all tests"""
    print("=== MarkItDown Integration Tests ===")
    print()
    
    tests = [
        test_markdown,
        test_text,
        test_invalid_file
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print(f"\n=== Test Results ===")
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("✓ All tests passed!")
        return 0
    else:
        print("✗ Some tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())