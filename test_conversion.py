#!/usr/bin/env python3
"""
Test script for MarkItDown conversion functionality
"""

import sys
import os
import tempfile

# Add the scripts directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'scripts'))

from ingest import read_file_content

def test_file_conversion(file_path, description):
    """Test conversion for a specific file"""
    print(f"\nTesting {description}...")
    print(f"File: {file_path}")
    
    if not os.path.exists(file_path):
        print(f"✗ File not found: {file_path}")
        return False
    
    try:
        content = read_file_content(file_path)
        print(f"✓ Successfully converted {description}")
        print(f"  Content length: {len(content)} characters")
        print(f"  First 200 characters: {content[:200]}...")
        return True
    except Exception as e:
        print(f"✗ Error converting {description}: {e}")
        return False

def create_test_files():
    """Create test files for different formats"""
    test_files = {}
    
    # Create markdown test file
    md_content = "# Test Markdown\n\nThis is a test\n\n## Section\n\n- Item 1\n- Item 2"
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write(md_content)
        test_files['markdown'] = (f.name, "Markdown file")
    
    # Create text test file
    txt_content = "This is a test text file.\n\nLine 2.\nLine 3."
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(txt_content)
        test_files['text'] = (f.name, "Text file")
    
    # Create CSV test file
    csv_content = "Name,Age,City\nJohn,30,New York\nJane,25,London"
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write(csv_content)
        test_files['csv'] = (f.name, "CSV file")
    
    # Create JSON test file
    json_content = '{"name": "John", "age": 30, "city": "New York"}'
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        f.write(json_content)
        test_files['json'] = (f.name, "JSON file")
    
    # Create XML test file
    xml_content = '<person><name>John</name><age>30</age><city>New York</city></person>'
    with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
        f.write(xml_content)
        test_files['xml'] = (f.name, "XML file")
    
    # Create HTML test file
    html_content = '<html><body><h1>Test</h1><p>This is a test</p></body></html>'
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
        f.write(html_content)
        test_files['html'] = (f.name, "HTML file")
    
    return test_files

def main():
    """Run conversion tests"""
    print("=== MarkItDown Conversion Tests ===")
    print()
    
    # Create test files
    test_files = create_test_files()
    
    # Test existing test document
    test_file = "test_document.md"
    if os.path.exists(test_file):
        test_file_conversion(test_file, "Existing test document")
    
    # Test created test files
    passed = 0
    total = len(test_files)
    
    for file_type, (file_path, description) in test_files.items():
        if test_file_conversion(file_path, description):
            passed += 1
    
    # Clean up test files
    for file_path, _ in test_files.values():
        if os.path.exists(file_path):
            os.unlink(file_path)
    
    print(f"\n=== Test Results ===")
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("✓ All conversion tests passed!")
        return 0
    else:
        print("✗ Some conversion tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())