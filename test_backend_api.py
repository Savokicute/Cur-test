#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import os
import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_api():
    base_url = "http://localhost:8000"
    print("="*60)
    print("Testing FastAPI Backend Test")
    print("="*60)

    # Test root endpoint first
    try:
        resp = requests.get(f"{base_url}/")
        print(f"\n1. 根路径测试:")
        print(f"  Status: {resp.status_code}")
        print(f"  Response: {resp.json()}")
    except Exception as e:
        print(f"Error: {e}")

    # Test the hot sources endpoint
    try:
        resp = requests.get(f"{base_url}/api/sources/hot-sources")
        print(f"\n2. 热榜源 API 测试:")
        print(f"  URL: {base_url}/api/sources/hot-sources")
        print(f"  Status: {resp.status_code}")
        print(f"  响应内容:")
        import json
        print(json.dumps(resp.json(), indent=4, ensure_ascii=False))
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "="*60)

if __name__ == "__main__":
    test_api()
