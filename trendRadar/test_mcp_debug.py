import requests
import json

def test_mcp_debug():
    """调试 MCP 服务连接"""
    
    base_url = 'http://localhost:3333/mcp'
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json, text/event-stream'
    }
    
    print("🔍 调试 MCP 服务连接...")
    print("=" * 60)
    
    # 测试基本连通性
    print("\n1️⃣ 测试基本连通性 (GET 请求)")
    try:
        response = requests.get(base_url, timeout=5)
        print(f"   状态码: {response.status_code}")
        print(f"   响应头: {dict(response.headers)}")
        print(f"   响应内容(前200字符): {response.text[:200]}")
    except Exception as e:
        print(f"   ❌ 错误: {e}")
    
    # 测试 POST 请求
    print("\n2️⃣ 测试 POST 请求 (tools/list)")
    payload = {
        'jsonrpc': '2.0',
        'id': 1,
        'method': 'tools/list'
    }
    
    try:
        response = requests.post(base_url, headers=headers, json=payload, timeout=10)
        print(f"   状态码: {response.status_code}")
        print(f"   Content-Type: {response.headers.get('Content-Type')}")
        print(f"   响应内容:\n{response.text[:500]}")
        
        if response.status_code == 400:
            print("\n   💡 可能的原因:")
            print("   - MCP Streamable HTTP 需要特定的请求格式")
            print("   - 可能需要 Session ID 或其他头部信息")
            
    except Exception as e:
        print(f"   ❌ 错误: {e}")
    
    # 尝试使用正确的 MCP 协议
    print("\n3️⃣ 尝试 MCP Streamable HTTP 协议 (initialize)")
    
    # Step 1: initialize
    init_payload = {
        'jsonrpc': '2.0',
        'id': 1,
        'method': 'initialize',
        'params': {
            'protocolVersion': '2024-11-05',
            'capabilities': {},
            'clientInfo': {
                'name': 'test-client',
                'version': '1.0.0'
            }
        }
    }
    
    try:
        session = requests.Session()
        response = session.post(base_url, headers=headers, json=init_payload, timeout=10)
        print(f"   状态码: {response.status_code}")
        print(f"   响应:\n{response.text[:500]}")
        
        # 检查是否有 session 相关的 header
        mcp_session_id = response.headers.get('mcp-session-id')
        if mcp_session_id:
            print(f"\n   🎉 获取到 Session ID: {mcp_session_id}")
            
            # 使用 session ID 继续请求
            headers['mcp-session-id'] = mcp_session_id
            
            print("\n4️⃣ 使用 Session ID 获取工具列表")
            tools_payload = {
                'jsonrpc': '2.0',
                'id': 2,
                'method': 'tools/list'
            }
            
            response = session.post(base_url, headers=headers, json=tools_payload, timeout=10)
            print(f"   状态码: {response.status_code}")
            
            if response.status_code == 200:
                print("   ✅ 成功获取工具列表!")
                
                # 解析 SSE 响应
                lines = response.text.strip().split('\n')
                for line in lines:
                    if line.startswith('data:'):
                        data_str = line[5:].strip()
                        try:
                            data = json.loads(data_str)
                            if 'result' in data:
                                tools = data['result'].get('tools', [])
                                print(f"\n   📊 共 {len(tools)} 个工具已注册:")
                                for i, tool in enumerate(tools[:10], 1):
                                    print(f"      {i}. {tool['name']}")
                                if len(tools) > 10:
                                    print(f"      ... 还有 {len(tools)-10} 个工具")
                        except:
                            pass
            else:
                print(f"   响应: {response.text[:300]}")
                
    except Exception as e:
        print(f"   ❌ 错误: {e}")

if __name__ == '__main__':
    test_mcp_debug()
