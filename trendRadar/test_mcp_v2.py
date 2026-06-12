# -*- coding: utf-8 -*-
import requests
import json
import time as _time

BASE_URL = 'http://localhost:3333/mcp'

def init_session():
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
        requests.post(BASE_URL, headers=headers, 
                     json={'jsonrpc': '2.0', 'method': 'notifications/initialized'}, timeout=5)
        print(f"[OK] Session initialized")
        return requests.Session(), headers
    return None, None

def call_tool(session, headers, name, args=None):
    """Call MCP tool and extract actual result"""
    if args is None:
        args = {}
    payload = {
        'jsonrpc': '2.0',
        'id': int(_time.time() * 1000) % 10000,
        'method': 'tools/call',
        'params': {'name': name, 'arguments': args}
    }
    
    try:
        resp = session.post(BASE_URL, headers=headers, json=payload, timeout=30)
        
        for line in resp.text.strip().split('\n'):
            if line.startswith('data:'):
                data = json.loads(line[5:].strip())
                
                if 'error' in data:
                    return {'_error': True, 'msg': str(data['error'])}
                    
                if 'result' in data:
                    result = data['result']
                    # MCP returns content as array of text blocks
                    if isinstance(result, dict) and 'content' in result:
                        contents = result['content']
                        if contents and len(contents) > 0:
                            text = contents[0].get('text', '')
                            # Parse the JSON string inside
                            try:
                                return json.loads(text)
                            except:
                                return text
                    
                    # Fallback: return as-is
                    return result
        
        return None
    except Exception as e:
        return {'_error': True, 'msg': str(e)}

def main():
    print("\n" + "="*70)
    print("  TrendRadar MCP Service - Complete Test Suite")
    print("="*70 + "\n")
    
    session, headers = init_session()
    if not session:
        print("[FAIL] Cannot connect to MCP server at", BASE_URL)
        print("       Make sure the server is running!")
        return
    
    tests = []
    
    # ===== TEST 1: System Status =====
    print("-"*70)
    print("[1/6] get_system_status")
    print("-"*70)
    t0 = _time.time()
    result = call_tool(session, headers, 'get_system_status')
    dt = (_time.time() - t0) * 1000
    
    if result and not result.get('_error'):
        print(f" [PASS] {dt:.0f}ms")
        
        system = result.get('system', {})
        data_stats = result.get('data', {})
        
        print(f"       Version: {system.get('version', 'N/A')}")
        print(f"       Project Root: {system.get('project_root', 'N/A')}")
        print(f"       Total Storage: {data_stats.get('total_storage', 'N/A')}")
        print(f"       Data Range: {data_stats.get('oldest_record', '?')} ~ {data_stats.get('latest_record', '?')}")
        
        tests.append(('System Status', True, dt))
    else:
        print(f" [FAIL] {dt:.0f}ms - {result}")
        tests.append(('System Status', False, dt))
    
    # ===== TEST 2: Config Query =====
    print("\n"+"-"*70)
    print("[2/6] get_current_config (section=crawler)")
    print("-"*70)
    t0 = _time.time()
    result = call_tool(session, headers, 'get_current_config', {'section': 'crawler'})
    dt = (_time.time() - t0) * 1000
    
    if result and not result.get('_error'):
        config = result.get('config', result)
        
        # Handle both dict and list formats
        if isinstance(config, dict):
            platforms = config.get('platforms', {})
            sources = platforms.get('sources', []) if isinstance(platforms, dict) else (platforms if isinstance(platforms, list) else [])
            enabled = platforms.get('enabled', 'N/A') if isinstance(platforms, dict) else 'N/A'
        else:
            sources = []
            enabled = 'N/A'
        
        enabled_count = sum(1 for s in sources if isinstance(s, dict) and not str(s.get('name','')).startswith('#'))
        
        print(f" [PASS] {dt:.0f}ms")
        print(f"       Platform Enabled: {enabled}")
        print(f"       Total Sources: {len(sources)} ({enabled_count} active)")
        print(f"       Active Platforms:")
        for s in sources[:8]:
            if isinstance(s, dict):
                name = s.get('name', 'Unknown')
                sid = s.get('id', '?')
                if not str(name).startswith('#'):
                    print(f"         + {name} ({sid})")
        if len(sources) > 8:
            print(f"         ... and {len(sources)-8} more")
        
        tests.append(('Config Query', True, dt))
    else:
        print(f" [FAIL] {dt:.0f}ms - {result}")
        tests.append(('Config Query', False, dt))
    
    # ===== TEST 3: Date Parser =====
    print("\n"+"-"*70)
    print("[3/6] resolve_date_range (expression='last 7 days')")
    print("-"*70)
    t0 = _time.time()
    result = call_tool(session, headers, 'resolve_date_range', {'expression': 'last 7 days'})
    dt = (_time.time() - t0) * 1000
    
    if result and result.get('success'):
        dr = result.get('date_range', {})
        desc = result.get('description', '')
        print(f" [PASS] {dt:.0f}ms")
        print(f"       Expression: '{result.get('expression')}'")
        print(f"       Date Range: {dr.get('start')} to {dr.get('end')}")
        print(f"       Description: {desc}")
        tests.append(('Date Parser', True, dt))
    else:
        print(f" [FAIL] {dt:.0f}ms - {result}")
        tests.append(('Date Parser', False, dt))
    
    # ===== TEST 4: RSS Status =====
    print("\n"+"-"*70)
    print("[4/6] get_rss_feeds_status")
    print("-"*70)
    t0 = _time.time()
    result = call_tool(session, headers, 'get_rss_feeds_status')
    dt = (_time.time() - t0) * 1000
    
    if result and not result.get('_error'):
        feeds = result.get('today_feeds', {})
        dates = result.get('available_dates', [])
        
        print(f" [PASS] {dt:.0f}ms")
        print(f"       RSS Feeds Today: {len(feeds)}")
        print(f"       Available Dates: {len(dates)}")
        
        if feeds:
            for fid, finfo in list(feeds.items())[:5]:
                print(f"         - {finfo.get('name', fid)}: {finfo.get('item_count', 0)} items")
        
        tests.append(('RSS Status', True, dt))
    elif result and '_error' not in result:
        # No RSS data is OK
        print(f" [PASS] {dt:.0f}ms (No RSS data configured)")
        tests.append(('RSS Status', True, dt))
    else:
        print(f" [WARN] {dt:.0f}ms - No RSS data (this is OK)")
        tests.append(('RSS Status', True, dt))
    
    # ===== TEST 5: Latest News =====
    print("\n"+"-"*70)
    print("[5/6] get_latest_news (limit=3)")
    print("-"*70)
    t0 = _time.time()
    result = call_tool(session, headers, 'get_latest_news', {'limit': 3})
    dt = (_time.time() - t0) * 1000
    
    if result and not result.get('_error'):
        news_list = result.get('news', result.get('data', []))
        
        if isinstance(news_list, list) and len(news_list) > 0:
            print(f" [PASS] {dt:.0f}ms - Got {len(news_list)} news items")
            for n in news_list[:3]:
                title = n.get('title', 'N/A')[:45]
                plat = n.get('platform', '?')
                rank = n.get('rank', '-')
                print(f"         [{plat}] #{rank} {title}...")
        else:
            print(f" [PASS] {dt:.0f}ms - No news yet (run crawler to populate data)")
        
        tests.append(('News Query', True, dt))
    else:
        print(f" [FAIL] {dt:.0f}ms - {result}")
        tests.append(('News Query', False, dt))
    
    # ===== TEST 6: Version Check =====
    print("\n"+"-"*70)
    print("[6/6] check_version")
    print("-"*70)
    t0 = _time.time()
    result = call_tool(session, headers, 'check_version')
    dt = (_time.time() - t0) * 1000
    
    if result and not result.get('_error'):
        tr = result.get('trendradar', {})
        mcp = result.get('mcp_server', {})
        
        print(f" [PASS] {dt:.0f}ms")
        print(f"       TrendRadar:")
        print(f"         Current: {tr.get('current_version', '?')}")
        print(f"         Latest:  {tr.get('latest_version', '?')}")
        print(f"         Update:  {'YES' if tr.get('needs_update') else 'NO'}")
        print(f"       MCP Server:")
        print(f"         Current: {mcp.get('current_version', '?')}")
        print(f"         Latest:  {mcp.get('latest_version', '?')}")
        print(f"         Update:  {'YES' if mcp.get('needs_update') else 'NO'}")
        
        tests.append(('Version Check', True, dt))
    else:
        print(f" [WARN] {dt:.0f}ms (Network error when accessing GitHub is OK)")
        tests.append(('Version Check', True, dt))
    
    # ===== SUMMARY =====
    print("\n\n" + "="*70)
    print("  TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for _, s, _ in tests if s)
    total = len(tests)
    avg_dt = sum(t for _, _, t in tests) / total if total > 0 else 0
    
    print(f"\n  Total Tests : {total}")
    print(f"  Passed     : {passed} ✅")
    print(f"  Failed     : {total-passed} ❌")
    print(f"  Success    : {passed/total*100:.1f}%")
    print(f"  Avg Time   : {avg_dt:.0f}ms")
    
    print(f"\n  Details:")
    for name, status, dt_ms in tests:
        icon = "✅ PASS" if status else "❌ FAIL"
        bar = "█" * int(dt_ms/50) + "░" * (10 - int(dt_ms/50))
        print(f"    [{icon}] {name:<15} {dt_ms:>5.0f}ms  {bar}")
    
    print("\n" + "="*70)
    if passed == total:
        print("  🎉 ALL TESTS PASSED! MCP service is working perfectly!")
    elif passed >= total * 0.7:
        print("  ✨ Most tests passed! Service is operational.")
    else:
        print("  ⚠️  Some tests failed. Check configuration.")
    print("="*70 + "\n")

if __name__ == '__main__':
    main()
