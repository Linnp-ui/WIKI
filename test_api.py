#!/usr/bin/env python3
"""
Test script for API chat endpoint
"""

import requests
import json

def test_chat_endpoint():
    """Test the /api/chat endpoint"""
    url = "http://localhost:8005/api/chat"
    headers = {"Content-Type": "application/json"}
    data = {"message": "什么是AI大模型"}
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        print(f"Status code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")
        return response.status_code
    except Exception as e:
        print(f"Error: {e}")
        return None

def test_system_status():
    """Test the system status endpoint"""
    url = "http://localhost:8005/api/system/status"
    
    try:
        response = requests.get(url, timeout=10)
        print(f"Status code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")
        return response.status_code
    except Exception as e:
        print(f"Error: {e}")
        return None

if __name__ == "__main__":
    print("Testing system status...")
    test_system_status()
    print("\nTesting chat endpoint...")
    test_chat_endpoint()