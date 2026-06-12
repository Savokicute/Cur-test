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
        return requests.Session(), headers
    return None, None

def call_tool_raw(session, headers, name, args=None):
    """Call MCP tool and return raw result"""
    if args is None:
        args = {}
    payload = {
        'jsonrpc': '2.0',
        'id': int(_time.time() * 1000) % 10000,
        'method': 'tools/call',
        'params': {'name': name, 'arguments': args}
    }
    resp = session.post(BASE_URL, headers=headers, json=payload, timeout=30)
    print(f"   HTTP Status: {resp.status_code}")
    print(f"   Response (first 500 chars):")
    print(f"   {resp.text[:500]}")
    print()
    
    for line in resp.text.strip().split('\n'):
        if line.startswith('data:'):
            try:
                data = json.loads(line[5:].strip())
                if 'result' in data:
                    try:
                        parsed = json.loads(data['result'])
                        return parsed
                    except:
                        return data['result']
                elif 'error' in data:
                    return data['error']
            except:
                pass
    return None

def main():
    print("\n" + "="*60)
    print("  TrendRadar MCP Service - Debug Test")
    print("="*60 + "\n")
    
    session, headers = init_session()
    if not session:
        print("[FAIL] Cannot connect!")
        return
    
    # Test System Status
    print("-"*60)
    print("[TEST] get_system_status")
    print("-"*60)
    result = call_tool_raw(session, headers, 'get_system_status')
    if result:
        print(f"   Result type: {type(result)}")
        print(f"   Keys: {list(result.keys()) if isinstance(result, dict) else 'N/A'}")

if __name__ == '__main__':
    main()
