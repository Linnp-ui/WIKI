#!/usr/bin/env python3
"""
Run API server in background and test it
"""

import subprocess
import time
import requests
import sys

def main():
    # Start the server in background
    print("Starting API server...")
    proc = subprocess.Popen(
        [sys.executable, "-c", "import uvicorn; from main import app; uvicorn.run(app, host='0.0.0.0', port=8006)"],
        cwd=r"d:\code\project\WIKI\backend",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )

    # Wait for server to start
    print("Waiting for server to start...")
    time.sleep(5)

    # Test the server
    try:
        print("\nTesting system status...")
        response = requests.get("http://127.0.0.1:8006/", timeout=5)
        print(f"Status code: {response.status_code}")
        print(f"Response: {response.json()}")

        print("\nTesting chat endpoint...")
        response = requests.post(
            "http://127.0.0.1:8006/api/chat",
            headers={"Content-Type": "application/json"},
            json={"message": "什么是AI大模型"},
            timeout=30
        )
        print(f"Status code: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Error: {e}")

    # Terminate the server
    print("\nTerminating server...")
    proc.terminate()
    proc.wait()

if __name__ == "__main__":
    main()