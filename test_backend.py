#!/usr/bin/env python3
# coding=utf-8
"""测试后端 API"""

import sys
import io
from pathlib import Path

# 设置输出编码为 UTF-8
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

import httpx
import json


def test_root():
    """测试根路径"""
    print("\n" + "=" * 60)
    print("测试 1: 根路径 /")
    print("=" * 60)
    try:
        response = httpx.get("http://localhost:8000/", timeout=10)
        print(f"状态码: {response.status_code}")
        print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        return response.status_code == 200
    except Exception as e:
        print(f"错误: {e}")
        return False


def test_status():
    """测试状态接口"""
    print("\n" + "=" * 60)
    print("测试 2: 状态接口 /api/status")
    print("=" * 60)
    try:
        response = httpx.get("http://localhost:8000/api/status", timeout=10)
        print(f"状态码: {response.status_code}")
        print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        return response.status_code == 200
    except Exception as e:
        print(f"错误: {e}")
        return False


def test_hotspots():
    """测试热榜接口"""
    print("\n" + "=" * 60)
    print("测试 3: 热榜接口 /api/hotspots")
    print("=" * 60)
    try:
        response = httpx.get("http://localhost:8000/api/hotspots", timeout=10)
        print(f"状态码: {response.status_code}")
        data = response.json()
        print(f"成功: {data.get('success')}")
        if data.get('success') and data.get('data'):
            print(f"最后采集时间: {data['data'].get('last_fetch_time')}")
            print(f"总条数: {data['data'].get('total_items')}")
            if data['data'].get('groups'):
                print(f"分组数: {len(data['data']['groups'])}")
                for i, (platform, items) in enumerate(data['data']['groups'].items()):
                    if i < 3:
                        print(f"  - {platform}: {len(items)} 条")
        return response.status_code == 200
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_hotspots_group_none():
    """测试热榜接口不分组"""
    print("\n" + "=" * 60)
    print("测试 4: 热榜接口 /api/hotspots?group_by=none")
    print("=" * 60)
    try:
        response = httpx.get("http://localhost:8000/api/hotspots?group_by=none", timeout=10)
        print(f"状态码: {response.status_code}")
        data = response.json()
        if data.get('success') and data.get('data', {}).get('items'):
            print(f"返回条数: {len(data['data']['items'])}")
            if len(data['data']['items']) > 0:
                first = data['data']['items'][0]
                print(f"第一条: {first.get('title')[:50]}...")
        return response.status_code == 200
    except Exception as e:
        print(f"错误: {e}")
        return False


def test_platforms():
    """测试平台接口"""
    print("\n" + "=" * 60)
    print("测试 5: 平台接口 /api/hotspots/platforms")
    print("=" * 60)
    try:
        response = httpx.get("http://localhost:8000/api/hotspots/platforms", timeout=10)
        print(f"状态码: {response.status_code}")
        data = response.json()
        if data.get('success') and data.get('data'):
            print(f"平台数: {len(data['data'])}")
            for p in data['data']:
                print(f"  - {p.get('name')} ({p.get('id')})")
        return response.status_code == 200
    except Exception as e:
        print(f"错误: {e}")
        return False


def get_first_hotspot_url():
    """获取第一条热榜的 URL，用于测试文章接口"""
    try:
        response = httpx.get("http://localhost:8000/api/hotspots?group_by=none", timeout=10)
        data = response.json()
        if data.get('success') and data.get('data', {}).get('items'):
            return data['data']['items'][0].get('url_norm')
    except Exception:
        pass
    return None


def test_article(url_norm):
    """测试文章接口"""
    print("\n" + "=" * 60)
    print(f"测试 6: 文章接口 /api/articles/{url_norm[:30]}...")
    print("=" * 60)
    try:
        # URL 编码
        from urllib.parse import quote
        encoded_url = quote(url_norm, safe='')
        response = httpx.get(f"http://localhost:8000/api/articles/{encoded_url}", timeout=10)
        print(f"状态码: {response.status_code}")
        data = response.json()
        print(f"成功: {data.get('success')}")
        if data.get('success') and data.get('data'):
            article = data['data']
            print(f"标题: {article.get('title_snapshot')[:50]}...")
            print(f"状态: {article.get('status')}")
            print(f"Markdown 长度: {len(article.get('markdown', ''))}")
        return response.status_code == 200
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("[*] 热点发现平台 - 后端 API 测试")
    print("=" * 60)

    # 检查后端是否运行
    print("\n[*] 请确保后端正在运行:")
    print("   uv run uvicorn app.main:app --reload\n")

    results = []

    # 运行测试
    results.append(("根路径", test_root()))
    results.append(("状态接口", test_status()))
    results.append(("热榜接口", test_hotspots()))
    results.append(("热榜接口(不分组)", test_hotspots_group_none()))
    results.append(("平台接口", test_platforms()))

    # 获取一个热榜 URL 测试文章接口
    url_norm = get_first_hotspot_url()
    if url_norm:
        results.append(("文章接口", test_article(url_norm)))
    else:
        print("\n[!] 无法获取热榜数据，跳过文章接口测试")

    # 汇总结果
    print("\n" + "=" * 60)
    print("[*] 测试结果汇总")
    print("=" * 60)
    all_passed = True
    for name, passed in results:
        status = "[OK]" if passed else "[FAIL]"
        print(f"{name}: {status}")
        if not passed:
            all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("[OK] 所有测试通过!")
        return 0
    else:
        print("[!] 部分测试失败，请检查")
        return 1


if __name__ == "__main__":
    sys.exit(main())
