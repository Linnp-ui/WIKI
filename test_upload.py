#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试文档上传功能
"""

import requests
import os

# API 端点
API_URL = "http://localhost:8000/api/system/ingest"

# 测试文件路径
TEST_FILE = "测试文档.md"

# 检查文件是否存在
if not os.path.exists(TEST_FILE):
    print(f"测试文件不存在: {TEST_FILE}")
    exit(1)

print(f"开始上传测试文档: {TEST_FILE}")
print(f"API 端点: {API_URL}")
print("=" * 50)

# 准备文件数据
files = {
    'file': (TEST_FILE, open(TEST_FILE, 'rb'), 'text/markdown')
}

try:
    # 发送请求
    response = requests.post(API_URL, files=files, timeout=60)
    
    # 打印响应
    print(f"响应状态码: {response.status_code}")
    print(f"响应内容: {response.text}")
    
    if response.status_code == 200:
        print("\n✅ 文档上传成功！")
    else:
        print("\n❌ 文档上传失败")
        
except Exception as e:
    print(f"\n❌ 上传过程中出错: {str(e)}")
finally:
    # 关闭文件
    if 'file' in locals() and hasattr(files['file'][1], 'close'):
        files['file'][1].close()

print("=" * 50)
print("测试完成")