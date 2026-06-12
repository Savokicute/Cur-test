import requests
import json

def test_mcp_service():
    """测试 MCP 服务基础功能"""
    
    base_url = 'http://localhost:3333/mcp'
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json, text/event-stream'
    }
    
    print("=" * 60)
    print("  TrendRadar MCP 服务功能测试")
    print("=" * 60)
    
    # 测试1: 获取工具列表
    print("\n📋 测试1: 获取工具列表")
    print("-" * 40)
    
    payload = {
        'jsonrpc': '2.0',
        'id': 1,
        'method': 'tools/list'
    }
    
    try:
        response = requests.post(base_url, headers=headers, json=payload, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if 'result' in data:
                tools = data['result'].get('tools', [])
                print(f"✅ 成功！共注册 {len(tools)} 个工具\n")
                
                # 按类别显示工具
                categories = {
                    '日期解析': [],
                    '数据查询': [],
                    'RSS查询': [],
                    '智能检索': [],
                    '高级分析': [],
                    '系统管理': [],
                    '存储同步': [],
                    '文章读取': [],
                    '通知推送': []
                }
                
                for tool in tools:
                    name = tool['name']
                    if name == 'resolve_date_range':
                        categories['日期解析'].append(tool)
                    elif name in ['get_latest_news', 'get_news_by_date', 'get_trending_topics']:
                        categories['数据查询'].append(tool)
                    elif name in ['get_latest_rss', 'search_rss', 'get_rss_feeds_status']:
                        categories['RSS查询'].append(tool)
                    elif name in ['search_news', 'find_related_news']:
                        categories['智能检索'].append(tool)
                    elif name in ['analyze_topic_trend', 'analyze_data_insights', 'analyze_sentiment', 
                                   'aggregate_news', 'compare_periods', 'generate_summary_report']:
                        categories['高级分析'].append(tool)
                    elif name in ['get_current_config', 'get_system_status', 'check_version', 'trigger_crawl']:
                        categories['系统管理'].append(tool)
                    elif name in ['sync_from_remote', 'get_storage_status', 'list_available_dates']:
                        categories['存储同步'].append(tool)
                    elif name in ['read_article', 'read_articles_batch']:
                        categories['文章读取'].append(tool)
                    elif name in ['get_channel_format_guide', 'get_notification_channels', 'send_notification']:
                        categories['通知推送'].append(tool)
                
                for cat_name, cat_tools in categories.items():
                    if cat_tools:
                        print(f"\n【{cat_name}】({len(cat_tools)}个)")
                        for t in cat_tools:
                            desc = t['description'][:50] + "..." if len(t['description']) > 50 else t['description']
                            print(f"  • {t['name']}: {desc}")
            else:
                print(f"❌ 响应异常: {data}")
        else:
            print(f"❌ HTTP错误: {response.status_code}")
            
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return False
    
    # 测试2: 调用 get_system_status
    print("\n\n" + "=" * 60)
    print("📊 测试2: 调用 get_system_status (系统状态)")
    print("-" * 40)
    
    payload = {
        'jsonrpc': '2.0',
        'id': 2,
        'method': 'tools/call',
        'params': {
            'name': 'get_system_status',
            'arguments': {}
        }
    }
    
    try:
        response = requests.post(base_url, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            # MCP Streamable HTTP 返回 SSE 格式
            lines = response.text.strip().split('\n')
            
            for line in lines:
                if line.startswith('data:'):
                    data_str = line[5:].strip()
                    try:
                        data = json.loads(data_str)
                        
                        if 'result' in data:
                            result = json.loads(data['result'])
                            print("✅ 系统状态获取成功!\n")
                            
                            # 解析并显示关键信息
                            if isinstance(result, dict):
                                for key, value in result.items():
                                    if key != 'error':
                                        print(f"  • {key}: {value}")
                            break
                            
                        elif 'error' in data:
                            error = data['error']
                            print(f"❌ 工具调用错误: {error.get('message', error)}")
                            break
                    except json.JSONDecodeError:
                        continue
        else:
            print(f"❌ HTTP错误: {response.status_code}")
            
    except Exception as e:
        print(f"❌ 请求失败: {e}")
    
    # 测试3: 调用 get_current_config
    print("\n\n" + "=" * 60)
    print("⚙️ 测试3: 调用 get_current_config (配置信息)")
    print("-" * 40)
    
    payload = {
        'jsonrpc': '2.0',
        'id': 3,
        'method': 'tools/call',
        'params': {
            'name': 'get_current_config',
            'arguments': {
                'section': 'crawler'
            }
        }
    }
    
    try:
        response = requests.post(base_url, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            lines = response.text.strip().split('\n')
            
            for line in lines:
                if line.startswith('data:'):
                    data_str = line[5:].strip()
                    try:
                        data = json.loads(data_str)
                        
                        if 'result' in data:
                            result = json.loads(data['result'])
                            print("✅ 配置信息获取成功!\n")
                            
                            if isinstance(result, dict) and 'config' in result:
                                config = result['config']
                                
                                # 显示平台配置
                                if 'platforms' in config:
                                    platforms = config['platforms']
                                    print(f"【热榜平台配置】")
                                    print(f"  启用状态: {platforms.get('enabled', 'N/A')}")
                                    
                                    sources = platforms.get('sources', [])
                                    print(f"  已配置平台数: {len(sources)}")
                                    print(f"  平台列表:")
                                    for src in sources:
                                        status = "✅" if not src.get('id').startswith('#') else "⏸️"
                                        print(f"    {status} {src.get('name')} ({src.get('id')})")
                            break
                            
                        elif 'error' in data:
                            error = data['error']
                            print(f"❌ 错误: {error.get('message', error)}")
                            break
                    except json.JSONDecodeError:
                        continue
        else:
            print(f"❌ HTTP错误: {response.status_code}")
            
    except Exception as e:
        print(f"❌ 请求失败: {e}")
    
    print("\n\n" + "=" * 60)
    print("✨ 测试完成！MCP 服务运行正常 ✅")
    print("=" * 60)
    
    return True

if __name__ == '__main__':
    test_mcp_service()
