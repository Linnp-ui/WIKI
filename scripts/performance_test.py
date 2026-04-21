#!/usr/bin/env python3
"""
Performance test script for backend API

性能测试脚本，用于测试后端API的性能指标：
- 并发请求处理能力
- 响应延迟统计
- 状态码分布
"""

import time
import requests
import concurrent.futures

BASE_URL = "http://localhost:3000/api"

# 测试端点列表
ENDPOINTS = [
    "/wiki/pages",
    "/system/status",
    "/system/config"
]

# 测试参数
NUM_REQUESTS = 100  # 总请求数
CONCURRENT_REQUESTS = 10  # 并发连接数

def test_endpoint(endpoint):
    """
    测试单个API端点
    
    参数:
        endpoint: API端点路径
    
    返回:
        Tuple[str, int, float]: (端点, 状态码, 延迟毫秒)
    """
    url = BASE_URL + endpoint
    start_time = time.time()
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        status_code = response.status_code
        latency = (time.time() - start_time) * 1000  # 转换为毫秒
        return endpoint, status_code, latency
    except Exception as e:
        return endpoint, 500, (time.time() - start_time) * 1000

def main():
    """
    主函数：运行性能测试
    
    对每个端点执行并发请求，收集并展示：
        - 状态码分布
        - 平均、最小、最大延迟
    """
    print(f"Running performance test with {NUM_REQUESTS} requests and {CONCURRENT_REQUESTS} concurrent connections")
    print("=" * 80)
    
    for endpoint in ENDPOINTS:
        print(f"Testing endpoint: {endpoint}")
        latencies = []
        status_codes = {}
        
        # Run concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENT_REQUESTS) as executor:
            futures = []
            for _ in range(NUM_REQUESTS):
                futures.append(executor.submit(test_endpoint, endpoint))
            
            for future in concurrent.futures.as_completed(futures):
                ep, status, latency = future.result()
                latencies.append(latency)
                status_codes[status] = status_codes.get(status, 0) + 1
        
        # Calculate statistics
        if latencies:
            avg_latency = sum(latencies) / len(latencies)
            min_latency = min(latencies)
            max_latency = max(latencies)
            
            print(f"  Status codes: {status_codes}")
            print(f"  Average latency: {avg_latency:.2f} ms")
            print(f"  Min latency: {min_latency:.2f} ms")
            print(f"  Max latency: {max_latency:.2f} ms")
        print("-" * 80)

if __name__ == "__main__":
    main()
