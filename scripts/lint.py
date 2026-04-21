#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lint script for LLM Wiki.
Checks for orphan pages, broken links, and quality issues.

此脚本执行知识库质量检查，包括：
1. 孤儿页面检测（没有入链的页面）
2. 断链检测（指向不存在页面的链接）
3. 逻辑矛盾检测
4. 高频未建立术语发现
5. 源文件缺失页面检测
"""

import sys
import os
import re
from collections import defaultdict

# Set default encoding to UTF-8
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')


def find_wiki_links(content):
    """
    查找内容中的所有Wiki链接
    
    参数:
        content: 页面内容
    
    返回:
        List[str]: Wiki链接目标页面名称列表
    """
    return re.findall(r"\[\[([^\]]+)\]\]", content)


def get_all_wiki_pages(wiki_dir):
    """
    获取wiki目录中的所有页面
    
    参数:
        wiki_dir: wiki根目录
    
    返回:
        List[str]: 页面名称列表
    """
    pages = []
    for root, _, files in os.walk(wiki_dir):
        for file in files:
            if file.endswith('.md'):
                # 将文件路径转换为页面名称（去除.md扩展名）
                page_path = os.path.join(root, file)
                relative_path = os.path.relpath(page_path, wiki_dir)
                page_name = os.path.splitext(relative_path.replace(os.path.sep, '/'))[0]
                pages.append(page_name)
    return pages


def build_link_graph(wiki_dir):
    """
    构建页面之间的链接图谱
    
    参数:
        wiki_dir: wiki根目录
    
    返回:
        Tuple[Dict, Dict, Dict]: 
            - outgoing_links: 页面到其出链的映射
            - incoming_links: 页面到其入链的映射
            - mentioned_terms: 链接中提到的术语及其出现次数
    """
    # Map from page to its outgoing links
    outgoing_links = defaultdict(list)
    # Map from page to its incoming links
    incoming_links = defaultdict(list)
    # All terms mentioned in links
    mentioned_terms = defaultdict(int)
    
    for root, _, files in os.walk(wiki_dir):
        for file in files:
            if file.endswith('.md'):
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, wiki_dir)
                current_page = os.path.splitext(relative_path.replace(os.path.sep, '/'))[0]
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        links = find_wiki_links(content)
                        outgoing_links[current_page] = links
                        
                        for link in links:
                            mentioned_terms[link] += 1
                            incoming_links[link].append(current_page)
                except Exception as e:
                    print(f"Error reading {file_path}: {e}")
    
    return outgoing_links, incoming_links, mentioned_terms


def find_orphan_pages(wiki_dir):
    """
    查找孤儿页面（没有入链的页面）
    
    孤儿页面是知识库中的"孤岛"，没有任何页面链接到它们。
    这些页面可能需要被删除、合并或添加更多链接。
    
    参数:
        wiki_dir: wiki根目录
    
    返回:
        List[str]: 孤儿页面名称列表
    """
    _, incoming_links, _ = build_link_graph(wiki_dir)
    all_pages = get_all_wiki_pages(wiki_dir)
    
    orphans = []
    for page in all_pages:
        if page not in incoming_links or len(incoming_links[page]) == 0:
            orphans.append(page)
    
    return orphans


def find_broken_links(wiki_dir):
    """
    查找断链（指向不存在页面的链接）
    
    参数:
        wiki_dir: wiki根目录
    
    返回:
        List[Tuple[str, str]]: 断链列表，每项为(来源页面, 目标页面)
    """
    outgoing_links, _, _ = build_link_graph(wiki_dir)
    all_pages = get_all_wiki_pages(wiki_dir)
    page_set = set(all_pages)
    
    broken_links = []
    for page, links in outgoing_links.items():
        for link in links:
            if link not in page_set:
                broken_links.append((page, link))
    
    return broken_links


def find_logical_contradictions(wiki_dir):
    """
    检测页面中的逻辑矛盾
    
    通过检测矛盾短语模式来发现潜在的逻辑问题，如：
    - "is not" 与 "is" 同时出现
    - "true" 与 "false" 同时出现
    - "exists" 与 "does not exist" 同时出现
    
    参数:
        wiki_dir: wiki根目录
    
    返回:
        List[Tuple[str, str]]: 矛盾列表，每项为(页面名, 矛盾描述)
    """
    # This is a simple implementation that checks for contradictory phrases
    # in the same page
    contradictions = []
    
    # Common contradictory phrase patterns
    contradiction_patterns = [
        (r'(is not|cannot|never)', r'(is|can|always)'),
        (r'(true|correct|valid)', r'(false|incorrect|invalid)'),
        (r'(exists|present)', r'(does not exist|absent)'),
    ]
    
    for root, _, files in os.walk(wiki_dir):
        for file in files:
            if file.endswith('.md'):
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, wiki_dir)
                current_page = os.path.splitext(relative_path.replace(os.path.sep, '/'))[0]
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read().lower()
                        
                        for pattern1, pattern2 in contradiction_patterns:
                            if re.search(pattern1, content) and re.search(pattern2, content):
                                contradictions.append((current_page, f"Potential contradiction: contains both '{pattern1}' and '{pattern2}'"))
                                break
                except Exception as e:
                    print(f"Error reading {file_path}: {e}")
    
    return contradictions


def find_frequent_unestablished_terms(wiki_dir, min_count=3):
    """
    发现高频但尚未建立页面的术语
    
    这些术语在知识库中被多次提及，但没有对应的Wiki页面。
    建议为这些术语创建新页面以丰富知识图谱。
    
    参数:
        wiki_dir: wiki根目录
        min_count: 最小提及次数阈值（默认3）
    
    返回:
        List[Tuple[str, int]]: 术语列表，按出现次数降序排列
    """
    _, _, mentioned_terms = build_link_graph(wiki_dir)
    all_pages = get_all_wiki_pages(wiki_dir)
    page_set = set(all_pages)
    
    unestablished_terms = []
    for term, count in mentioned_terms.items():
        if term not in page_set and count >= min_count:
            unestablished_terms.append((term, count))
    
    # Sort by count descending
    unestablished_terms.sort(key=lambda x: x[1], reverse=True)
    
    return unestablished_terms


def find_source_missing_pages(wiki_dir, raw_sources_dir):
    """
    查找源文件已被删除的Wiki页面
    
    当原始资料被删除后，关联的Wiki页面会被标记为孤儿状态。
    系统会检查页面的source字段，验证源文件是否仍然存在。
    
    参数:
        wiki_dir: wiki根目录
        raw_sources_dir: 原始资料目录
    
    返回:
        List[Dict]: 缺失源文件的页面列表，每项包含:
            - page: 页面名称
            - path: 页面路径
            - is_orphan: 是否已被标记为孤儿
            - orphaned_at: 标记为孤儿的时间
            - missing_sources: 缺失的源文件列表
            - all_sources: 所有源文件列表
    """
    import time
    
    source_missing = []
    
    for root, _, files in os.walk(wiki_dir):
        for file in files:
            if not file.endswith('.md'):
                continue
            
            file_path = os.path.join(root, file)
            relative_path = os.path.relpath(file_path, wiki_dir)
            page_name = os.path.splitext(relative_path.replace(os.path.sep, '/'))[0]
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check if page is already marked as orphan
                is_orphan = False
                orphaned_at = None
                source_files = []
                
                if content.startswith('---'):
                    parts = content.split('---', 2)
                    if len(parts) >= 2:
                        frontmatter = parts[1]
                        for line in frontmatter.split('\n'):
                            if ':' in line:
                                key, value = line.split(':', 1)
                                key = key.strip()
                                value = value.strip()
                                if key == 'orphan':
                                    is_orphan = value.lower() == 'true'
                                elif key == 'orphaned_at':
                                    orphaned_at = value
                                elif key == 'source':
                                    source_files = [s.strip() for s in value.split(',') if s.strip()]
                
                # Check if any source file exists
                missing_sources = []
                for source in source_files:
                    source_path = os.path.join(raw_sources_dir, source)
                    if not os.path.exists(source_path):
                        missing_sources.append(source)
                
                if missing_sources or is_orphan:
                    source_missing.append({
                        'page': page_name,
                        'path': relative_path,
                        'is_orphan': is_orphan,
                        'orphaned_at': orphaned_at,
                        'missing_sources': missing_sources,
                        'all_sources': source_files
                    })
                    
            except Exception as e:
                print(f"Error reading {file_path}: {e}")
    
    # Sort by orphan status first (orphans first), then by name
    source_missing.sort(key=lambda x: (not x['is_orphan'], x['page']))
    
    return source_missing


def main():
    """
    主函数：执行所有lint检查
    
    检查项目:
        1. 孤儿页面检测
        2. 断链检测
        3. 逻辑矛盾检测
        4. 高频未建立术语发现
        5. 源文件缺失页面检测
    """
    import time
    
    print("Running Wiki lint checks...")
    
    wiki_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'wiki')
    raw_sources_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'raw_sources')
    
    # 1. Find orphan pages (no incoming links)
    print("\n1. Checking for orphan pages...")
    orphans = find_orphan_pages(wiki_dir)
    if orphans:
        print(f"Found {len(orphans)} orphan pages:")
        for orphan in orphans:
            print(f"  - {orphan}")
    else:
        print("No orphan pages found.")
    
    # 2. Find broken [[WikiLinks]]
    print("\n2. Checking for broken links...")
    broken_links = find_broken_links(wiki_dir)
    if broken_links:
        print(f"Found {len(broken_links)} broken links:")
        for page, link in broken_links:
            try:
                print(f"  - {page} -> {link}")
            except UnicodeEncodeError:
                # Handle Unicode encoding error by printing the page and link as repr
                print(f"  - {repr(page)} -> {repr(link)}")
    else:
        print("No broken links found.")
    
    # 3. Check for logical contradictions
    print("\n3. Checking for logical contradictions...")
    contradictions = find_logical_contradictions(wiki_dir)
    if contradictions:
        print(f"Found {len(contradictions)} potential contradictions:")
        for page, message in contradictions:
            print(f"  - {page}: {message}")
    else:
        print("No logical contradictions found.")
    
    # 4. Find frequent unestablished terms
    print("\n4. Checking for frequent unestablished terms...")
    unestablished_terms = find_frequent_unestablished_terms(wiki_dir)
    if unestablished_terms:
        print(f"Found {len(unestablished_terms)} frequently mentioned terms without pages:")
        for term, count in unestablished_terms:
            print(f"  - {term} (mentioned {count} times)")
    else:
        print("No frequent unestablished terms found.")
    
    # 5. Find pages with missing source files
    print("\n5. Checking for pages with missing source files...")
    source_missing_pages = find_source_missing_pages(wiki_dir, raw_sources_dir)
    if source_missing_pages:
        print(f"Found {len(source_missing_pages)} pages with missing source files:")
        for item in source_missing_pages:
            if item['is_orphan']:
                print(f"  - {item['page']} [ORPHAN, marked at {item['orphaned_at']}]")
            else:
                print(f"  - {item['page']} [missing: {', '.join(item['missing_sources'])}]")
    else:
        print("No pages with missing source files found.")
    
    print("\nLint checks completed.")


if __name__ == "__main__":
    main()
