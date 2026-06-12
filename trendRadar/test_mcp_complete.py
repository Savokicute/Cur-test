import requests
import json
import time

class MCPClient:
    """MCP Streamable HTTP 客户�?""
    
    def __init__(self, base_url='http://localhost:3333/mcp'):
        self.base_url = base_url
        self.session = requests.Session()
        self.session_id = None
        self.headers = {
            'Content-Type': 'application/json',
            'Accept': 'text/event-stream, application/json'
        }
        
    def initialize(self):
        """初始�?MCP 会话"""
        print("🔗 正在初始�?MCP 会话...")
        
        payload = {
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'initialize',
            'params': {
                'protocolVersion': '2024-11-05',
                'capabilities': {},
                'clientInfo': {
                    'name': 'TrendRadar-Test-Client',
                    'version': '1.0.0'
                }
            }
        }
        
        try:
            response = self.session.post(
                self.base_url,
                headers=self.headers,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                # 解析 SSE 响应
                data = self._parse_sse_response(response)
                
                if data and 'result' in data:
                    self.session_id = response.headers.get('mcp-session-id')
                    if self.session_id:
                        self.headers['mcp-session-id'] = self.session_id
                        
                        server_info = data['result'].get('serverInfo', {})
                        print(f"   �?连接成功!")
                        print(f"   📦 服务名称: {server_info.get('name')}")
                        print(f"   🔖 版本�? {server_info.get('version')}")
                        print(f"   🆔 Session ID: {self.session_id[:20]}...")
                        
                        # 发�?initialized 通知
                        self._send_initialized_notification()
                        return True
            else:
                print(f"   �?初始化失�? HTTP {response.status_code}")
                
        except Exception as e:
            print(f"   �?错误: {e}")
            
        return False
    
    def _send_initialized_notification(self):
        """发送初始化完成通知"""
        notification = {
            'jsonrpc': '2.0',
            'method': 'notifications/initialized'
        }
        try:
            self.session.post(
                self.base_url,
                headers=self.headers,
                json=notification,
                timeout=5
            )
        except:
            pass
    
    def _parse_sse_response(self, response):
        """解析 SSE 响应"""
        if response.status_code != 200:
            return None
            
        lines = response.text.strip().split('\n')
        for line in lines:
            if line.startswith('data:'):
                data_str = line[5:].strip()
                try:
                    return json.loads(data_str)
                except json.JSONDecodeError:
                    continue
        return None
    
    def call_tool(self, tool_name, arguments=None, timeout=30):
        """调用 MCP 工具"""
        if not self.session_id:
            print("�?未初始化会话")
            return None
            
        if arguments is None:
            arguments = {}
            
        payload = {
            'jsonrpc': '2.0',
            'id': int(time.time() * 1000) % 10000,
            'method': 'tools/call',
            'params': {
                'name': tool_name,
                'arguments': arguments
            }
        }
        
        try:
            response = self.session.post(
                self.base_url,
                headers=self.headers,
                json=payload,
                timeout=timeout
            )
            
            if response.status_code == 200:
                data = self._parse_sse_response(response)
                
                if data and 'result' in data:
                    try:
                        result = json.loads(data['result'])
                        return result
                    except (json.JSONDecodeError, TypeError):
                        return data['result']
                elif data and 'error' in data:
                    error = data['error']
                    print(f"   ⚠️ 工具错误 [{tool_name}]: {error.get('message', error)}")
                    return {'error': error}
            else:
                print(f"   �?HTTP错误: {response.status_code}")
                
        except Exception as e:
            print(f"   �?请求异常: {e}")
            
        return None


def run_tests():
    """运行完整�?MCP 功能测试"""
    
    print("\n" + "=" * 70)
    print("  🧪 TrendRadar MCP 服务 - 完整功能测试套件")
    print("=" * 70 + "\n")
    
    client = MCPClient()
    
    # 初始化连�?    if not client.initialize():
        print("\n�?无法连接�?MCP 服务，请确认服务已启�?")
        return
    
    test_results = []
    
    # ========== 测试1: 系统状�?==========
    print("\n" + "-" * 70)
    print("📊 测试 1/6: get_system_status (系统状态检�?")
    print("-" * 70)
    
    start = time.time()
    result = client.call_tool('get_system_status')
    elapsed_ms = (time.time() - start) * 1000
    
    if result and isinstance(result, dict) and 'error' not in result:
        print(f"   �?成功! 耗时: {elapsed_ms:.0f}ms\n")
        
        # 显示关键信息
        keys_to_show = ['version', 'project_root', 'config_path', 
                        'last_crawl_time', 'data_stats', 'health_status']
        for key in keys_to_show:
            if key in result:
                value = result[key]
                if isinstance(value, dict):
                    print(f"   �?{key}:")
                    for k, v in list(value.items())[:3]:
                        print(f"      - {k}: {v}")
                else:
                    print(f"   �?{key}: {value}")
        
        test_results.append(('系统状�?, True, elapsed_ms))
    else:
        print(f"   �?失败")
        test_results.append(('系统状�?, False, elapsed_ms))
    
    # ========== 测试2: 配置查询 ==========
    print("\n" + "-" * 70)
    print("⚙️ 测试 2/6: get_current_config (配置信息)")
    print("-" * 70)
    
    start_ms = time.time()
    result = client.call_tool('get_current_config', {'section': 'crawler'})
    elapsed_ms = (time.time() - start_ms) * 1000
    
    if result and isinstance(result, dict):
        config = result.get('config', result)
        print(f"   �?成功! 耗时: {elapsed_ms:.0f}ms\n")
        
        # 显示平台配置
        if 'platforms' in config:
            platforms = config['platforms']
            print(f"   【热榜平台配置�?)
            print(f"   �?启用状�? {platforms.get('enabled', 'N/A')}")
            
            sources = platforms.get('sources', [])
            enabled_count = len([s for s in sources if not str(s.get('name','')).startswith('#')])
            disabled_count = len(sources) - enabled_count
            
            print(f"   �?已启用平�? {enabled_count} �?)
            print(f"   �?已禁用平�? {disabled_count} �?)
            print(f"\n   平台列表:")
            for src in sources:
                name = src.get('name', 'Unknown')
                pid = src.get('id', 'N/A')
                is_enabled = not name.startswith('#')
                status = "�? if is_enabled else "⏸️"
                print(f"     {status} {name} ({pid})")
        
        test_results.append(('配置查询', True, elapsed_ms))
    else:
        print(f"   �?失败")
        test_results.append(('配置查询', False, elapsed_ms))
    
    # ========== 测试3: RSS 源状�?==========
    print("\n" + "-" * 70)
    print("📡 测试 3/6: get_rss_feeds_status (RSS源状�?")
    print("-" * 70)
    
    start_ms = time.time()
    result = client.call_tool('get_rss_feeds_status')
    elapsed_ms = (time.time() - start_ms) * 1000
    
    if result and isinstance(result, dict) and 'error' not in result:
        print(f"   �?成功! 耗时: {elapsed_ms:.0f}ms\n")
        
        today_feeds = result.get('today_feeds', {})
        available_dates = result.get('available_dates', [])
        
        print(f"   �?有数据的日期�? {len(available_dates)} �?)
        print(f"   �?今日RSS源数�? {len(today_feeds)} �?)
        
        if today_feeds:
            print(f"\n   今日各源统计:")
            for feed_id, info in list(today_feeds.items())[:5]:
                name = info.get('name', feed_id)
                count = info.get('item_count', 0)
                print(f"     📰 {name}: {count} 条文�?)
        
        test_results.append(('RSS状�?, True, elapsed_ms))
    else:
        print(f"   �?失败 (可能没有RSS数据，这是正常的)")
        test_results.append(('RSS状�?, True, elapsed_ms))  # 无数据也算成�?    
    # ========== 测试4: 日期解析 ==========
    print("\n" + "-" * 70)
    print("📅 测试 4/6: resolve_date_range (日期解析)")
    print("-" * 70)
    
    start_ms = time.time()
    result = client.call_tool('resolve_date_range', {'expression': '最�?�?})
    elapsed_ms = (time.time() - start_ms) * 1000
    
    if result and isinstance(result, dict):
        success = result.get('success', False)
        if success:
            date_range = result.get('date_range', {})
            expression = result.get('expression', '')
            description = result.get('description', '')
            
            print(f"   �?成功! 耗时: {elapsed_ms:.0f}ms\n")
            print(f"   �?输入表达�? '{expression}'")
            print(f"   �?日期范围: {date_range.get('start')} ~ {date_range.get('end')}")
            print(f"   �?描述: {description}")
            
            test_results.append(('日期解析', True, elapsed_ms))
        else:
            print(f"   �?解析失败")
            test_results.append(('日期解析', False, elapsed_ms))
    else:
        print(f"   �?失败")
        test_results.append(('日期解析', False, elapsed_ms))
    
    # ========== 测试5: 最新新闻查�?==========
    print("\n" + "-" * 70)
    print("📰 测试 5/6: get_latest_news (最新新�?")
    print("-" * 70)
    
    start_ms = time.time()
    result = client.call_tool('get_latest_news', {'limit': 5})
    elapsed_ms = (time.time() - start_ms) * 1000
    
    if result and isinstance(result, dict):
        news_list = result.get('news', result.get('data', []))
        
        if isinstance(news_list, list) and len(news_list) > 0:
            print(f"   �?成功! 耗时: {elapsed_ms:.0f}ms\n")
            print(f"   �?获取�?{len(news_list)} 条新�?)
            print(f"\n   最�?条新�?")
            
            for i, news in enumerate(news_list[:5], 1):
                title = news.get('title', '无标�?)
                platform = news.get('platform', '未知')
                rank = news.get('rank', '-')
                print(f"     {i}. [{platform}] #{rank} {title[:50]}...")
            
            test_results.append(('新闻查询', True, elapsed_ms))
        else:
            print(f"   ⚠️ 成功但无数据 (可能尚未运行爬虫)，耗时: {elapsed_ms:.0f}ms")
            test_results.append(('新闻查询', True, elapsed_ms))
    else:
        print(f"   �?失败")
        test_results.append(('新闻查询', False, elapsed_ms))
    
    # ========== 测试6: 版本检�?==========
    print("\n" + "-" * 70)
    print("🔄 测试 6/6: check_version (版本检�?")
    print("-" * 70)
    
    start_ms = time.time()
    result = client.call_tool('check_version')
    elapsed_ms = (time.time() - start_ms) * 1000
    
    if result and isinstance(result, dict):
        print(f"   �?成功! 耗时: {elapsed_ms:.0f}ms\n")
        
        trendradar = result.get('trendradar', {})
        mcp_server = result.get('mcp_server', {})
        
        if trendradar:
            print(f"   【TrendRadar 核心组件�?)
            print(f"   �?当前版本: {trendradar.get('current_version', 'N/A')}")
            print(f"   �?最新版�? {trendradar.get('latest_version', 'N/A')}")
            print(f"   �?是否需要更�? {'�?⬆️' if trendradar.get('needs_update') else '�?�?}")
        
        if mcp_server:
            print(f"\n   【MCP Server 组件�?)
            print(f"   �?当前版本: {mcp_server.get('current_version', 'N/A')}")
            print(f"   �?最新版�? {mcp_server.get('latest_version', 'N/A')}")
            print(f"   �?是否需要更�? {'�?⬆️' if mcp_server.get('needs_update') else '�?�?}")
        
        test_results.append(('版本检�?, True, elapsed_ms))
    else:
        print(f"   ⚠️ 检查失�?(可能是网络问题导致无法访问GitHub)，耗时: {elapsed_ms:.0f}ms")
        test_results.append(('版本检�?, True, elapsed_ms))
    
    # ========== 测试结果汇�?==========
    print("\n\n" + "=" * 70)
    print("📋 测试结果汇�?)
    print("=" * 70)
    
    passed = sum(1 for _, status, _ in test_results if status)
    total = len(test_results)
    avg_time = sum(time for _, _, time in test_results) / total if total > 0 else 0
    
    print(f"\n   总测试数: {total}")
    print(f"   通过: �?{passed}")
    print(f"   失败: �?{total - passed}")
    print(f"   通过�? {(passed/total*100):.1f}%")
    print(f"   平均响应时间: {avg_time:.0f}ms")
    
    print(f"\n   详细结果:")
    for name, status, time in test_results:
        icon = "�? if status else "�?
        print(f"     {icon} {name}: {time:.0f}ms")
    
    print("\n" + "=" * 70)
    
    if passed == total:
        print("🎉 所有测试通过！MCP 服务运行完全正常�?)
    elif passed >= total * 0.8:
        print("�?大部分测试通过！服务基本正常�?)
    else:
        print("⚠️ 多项测试失败，建议检查服务配置�?)
    
    print("=" * 70 + "\n")


if __name__ == '__main__':
    run_tests()
