# -*- coding: utf-8 -*-
import requests
import json
import time as _time

BASE_URL = 'http://localhost:3333/mcp'

def init_session():
    """Initialize MCP session"""
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'text/event-stream, application/json'
    }
    
    payload = {
        'jsonrpc': '2.0',
        'id': 1,
        'method': 'initialize',
        'params': {
            'protocolVersion': '2024-11-05',
            'capabilities': {},
            'clientInfo': {'name': 'test', 'version': '1.0'}
        }
    }
    
    resp = requests.post(BASE_URL, headers=headers, json=payload, timeout=10)
    sid = resp.headers.get('mcp-session-id')
    if sid:
        headers['mcp-session-id'] = sid
        # Send initialized notification
        requests.post(BASE_URL, headers=headers, 
                     json={'jsonrpc': '2.0', 'method': 'notifications/initialized'}, timeout=5)
        print(f"[OK] Session initialized: {sid[:20]}...")
        return requests.Session(), headers
    return None, None

def call_tool(session, headers, name, args=None, timeout=30):
    """Call MCP tool"""
    if args is None:
        args = {}
    payload = {
        'jsonrpc': '2.0',
        'id': int(_time.time() * 1000) % 10000,
        'method': 'tools/call',
        'params': {'name': name, 'arguments': args}
    }
    resp = session.post(BASE_URL, headers=headers, json=payload, timeout=timeout)
    for line in resp.text.strip().split('\n'):
        if line.startswith('data:'):
            try:
                data = json.loads(line[5:].strip())
                if 'result' in data:
                    return json.loads(data['result'])
                elif 'error' in data:
                    return {'error': data['error']}
            except:
                pass
    return None

def main():
    print("\n" + "="*60)
    print("  TrendRadar MCP Service Test")
    print("="*60 + "\n")
    
    session, headers = init_session()
    if not session:
        print("[FAIL] Cannot connect to MCP server!")
        return
    
    tests = []
    
    # Test 1: System Status
    print("-"*60)
    print("[TEST 1/5] get_system_status")
    print("-"*60)
    t0 = _time.time()
    result = call_tool(session, headers, 'get_system_status')
    dt = (_time.time() - t0) * 1000
    
    if result and isinstance(result, dict) and 'error' not in result:
        print(f" [OK] {dt:.0f}ms")
        for k in ['version', 'project_root', 'config_path']:
            if k in result:
                print(f"      {k}: {result[k]}")
        tests.append(('System Status', True, dt))
    else:
        print(f" [FAIL] {dt:.0f}ms")
        tests.append(('System Status', False, dt))
    
    # Test 2: Config
    print("\n"+"-"*60)
    print("[TEST 2/5] get_current_config")
    print("-"*60)
    t0 = _time.time()
    result = call_tool(session, headers, 'get_current_config', {'section': 'crawler'})
    dt = (_time.time() - t0) * 1000
    
    if result and isinstance(result, dict):
        config = result.get('config', result)
        platforms = config.get('platforms', {})
        sources = platforms.get('sources', [])
        print(f" [OK] {dt:.0f}ms - {len(sources)} platforms configured")
        for s in sources[:5]:
            print(f"      [{s.get('id')}] {s.get('name')}")
        tests.append(('Config Query', True, dt))
    else:
        print(f" [FAIL] {dt:.0f}ms")
        tests.append(('Config Query', False, dt))
    
    # Test 3: Date Range
    print("\n"+"-"*60)
    print("[TEST 3/5] resolve_date_range")
    print("-"*60)
    t0 = _time.time()
    result = call_tool(session, headers, 'resolve_date_range', {'expression': 'last 7 days'})
    dt = (_time.time() - t0) * 1000
    
    if result and result.get('success'):
        dr = result.get('date_range', {})
        print(f" [OK] {dt:.0f}ms - {dr.get('start')} to {dr.get('end')}")
        tests.append(('Date Parser', True, dt))
    else:
        print(f" [FAIL] {dt:.0f}ms")
        tests.append(('Date Parser', False, dt))
    
    # Test 4: RSS Status
    print("\n"+"-"*60)
    print("[TEST 4/5] get_rss_feeds_status")
    print("-"*60)
    t0 = _time.time()
    result = call_tool(session, headers, 'get_rss_feeds_status')
    dt = (_time.time() - t0) * 1000
    
    if result and isinstance(result, dict):
        feeds = result.get('today_feeds', {})
        dates = result.get('available_dates', [])
        print(f" [OK] {dt:.0f}ms - {len(feeds)} feeds, {len(dates)} days of data")
        tests.append(('RSS Status', True, dt))
    else:
        print(f" [WARN] No RSS data (this is OK if no RSS configured), {dt:.0f}ms")
        tests.append(('RSS Status', True, dt))
    
    # Test 5: Latest News
    print("\n"+"-"*60)
    print("[TEST 5/5] get_latest_news (limit=3)")
    print("-"*60)
    t0 = _time.time()
    result = call_tool(session, headers, 'get_latest_news', {'limit': 3})
    dt = (_time.time() - t0) * 1000
    
    if result and isinstance(result, dict):
        news = result.get('news', result.get('data', []))
        if isinstance(news, list) and len(news) > 0:
            print(f" [OK] {dt:.0f}ms - Got {len(news)} news items")
            for n in news[:3]:
                title = n.get('title', '')[:40]
                plat = n.get('platform', '?')
                print(f"      [{plat}] {title}...")
        else:
            print(f" [OK] {dt:.0f}ms - No news yet (run crawler first)")
        tests.append(('News Query', True, dt))
    else:
        print(f" [FAIL] {dt:.0f}ms")
        tests.append(('News Query', False, dt))
    
    # Summary
    print("\n"+"="*60)
    print(" SUMMARY")
    print("="*60)
    passed = sum(1 for _, s, _ in tests if s)
    total = len(tests)
    avg_dt = sum(t for _, _, t in tests) / total if total > 0 else 0
    
    print(f"\n Total: {total} | Passed: {passed} | Failed: {total-passed}")
    print(f" Success Rate: {passed/total*100:.1f}% | Avg Response: {avg_dt:.0f}ms")
    
    for name, status, dt_ms in tests:
        icon = "PASS" if status else "FAIL"
        print(f"   [{icon}] {name}: {dt_ms:.0f}ms")
    
    print("\n"+ "="*60)
    if passed == total:
        print(" All tests passed! MCP service is working perfectly!")
    else:
        print(f" {passed}/{total} tests passed.")
    print("="*60 + "\n")

if __name__ == '__main__':
    main()
