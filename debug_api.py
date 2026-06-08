#!/usr/bin/env python3
# coding=utf-8
"""调试API响应"""

import sys
import io
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import httpx
import json

response = httpx.get("http://localhost:8000/api/hotspots?group_by=none", timeout=10)
print(f"状态码: {response.status_code}")
data = response.json()
print(f"\n完整响应: {json.dumps(data, indent=2, ensure_ascii=False)}")

if data.get('success') and data.get('data', {}).get('items'):
    print(f"\n第一条数据:")
    print(json.dumps(data['data']['items'][0], indent=2, ensure_ascii=False))
    print(f"\n可用的键: {list(data['data']['items'][0].keys())}")
