# coding=utf-8
"""
智能助手功能测试脚本

用于验证 MCP 工具集成和对话服务是否正常工作。
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


async def test_mcp_tools():
    """测试 MCP 工具注册和调用"""
    print("\n" + "=" * 60)
    print("1. 测试 MCP 工具注册")
    print("=" * 60)

    try:
        from app.services.mcp_tools import registry, register_builtin_tools

        # 注册内置工具
        register_builtin_tools()

        # 列出所有工具
        tools = registry.list_tools()
        stats = registry.get_stats()

        print(f"\n✅ 成功注册 {stats['total_tools']} 个工具:")
        for tool in tools:
            print(f"   - {tool['name']}: {tool['description'][:50]}...")

        print(f"\n📊 工具统计: {stats}")

        return True

    except Exception as e:
        print(f"\n❌ MCP 工具测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_tool_invocation():
    """测试工具调用"""
    print("\n" + "=" * 60)
    print("2. 测试工具调用")
    print("=" * 60)

    try:
        from app.services.mcp_tools import registry, register_builtin_tools

        # 确保工具已注册
        if not registry._tools:
            register_builtin_tools()

        # 测试搜索热榜工具（带参数限制，避免返回过多数据）
        print("\n🔍 调用 search_hotspots 工具 (limit=3)...")
        result = await registry.invoke_tool(
            name="search_hotspots",
            arguments={"limit": 3},
        )

        if result["success"]:
            data = result["result"]
            print(f"✅ 工具调用成功!")
            print(f"   - 总数: {data.get('total', 0)} 条")
            print(f"   - 返回条目: {len(data.get('items', []))} 条")

            if data.get("items"):
                for item in data["items"][:2]:
                    print(f"     • [{item.get('platform')}] {item.get('title', 'N/A')[:40]}...")
        else:
            print(f"⚠️ 工具调用返回: {result.get('error')}")

        # 测试获取平台统计工具
        print("\n📊 调用 get_platform_stats 工具...")
        result = await registry.invoke_tool(
            name="get_platform_stats",
            arguments={},
        )

        if result["success"]:
            data = result["result"]
            print(f"✅ 统计数据获取成功!")
            print(f"   - 总热点数: {data.get('total_items', 0)}")
            print(f"   - 覆盖天数: {data.get('total_dates', 0)}")
            platforms = data.get("platforms", {})
            if platforms:
                top_platforms = list(platforms.items())[:3]
                for platform, count in top_platforms:
                    print(f"     • {platform}: {count} 条")
        else:
            print(f"⚠️ 统计工具返回: {result.get('error')}")

        return True

    except Exception as e:
        print(f"\n❌ 工具调用测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_assistant_service():
    """测试对话服务"""
    print("\n" + "=" * 60)
    print("3. 测试对话服务")
    print("=" * 60)

    try:
        from app.services.assistant_service import AssistantService

        service = AssistantService()

        # 测试普通对话
        print("\n💬 发送消息: '你好'")
        response = await service.chat(message="你好")

        print(f"✅ 对话响应生成成功!")
        print(f"   - 内容长度: {len(response.content)} 字符")
        print(f"   - 预览: {response.content[:100]}...")

        # 测试带工具调用的对话
        print("\n💬 发送消息: '今天最热的5条新闻' (将触发工具调用)")
        response = await service.chat(
            message="今天最热的5条新闻",
            allowed_tools=["search_hotspots"],
        )

        print(f"✅ 带工具调用的对话响应生成成功!")
        print(f"   - 内容长度: {len(response.content)} 字符")
        print(f"   - 工具调用次数: {response.metadata.get('tool_calls_count', 0)}")
        print(f"   - 预览: {response.content[:150]}...")

        # 获取历史记录
        print("\n📜 获取历史记录...")
        history = await service.get_history(limit=5)
        print(f"✅ 历史记录获取成功!")
        print(f"   - 总消息数: {history['total']}")
        print(f"   - 返回条目: {len(history['items'])}")

        return True

    except Exception as e:
        print(f"\n❌ 对话服务测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """主测试函数"""
    print("=" * 60)
    print("智能助手与MCP集成功能测试")
    print("=" * 60)

    results = []

    # 运行各项测试
    results.append(("MCP工具注册", await test_mcp_tools()))
    results.append(("工具调用", await test_tool_invocation()))
    results.append(("对话服务", await test_assistant_service()))

    # 输出测试总结
    print("\n" + "=" * 60)
    print("测试结果总结")
    print("=" * 60)

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for name, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"{status}: {name}")

    print(f"\n总计: {passed}/{total} 项测试通过")

    if passed == total:
        print("\n🎉 所有测试通过！智能助手功能已就绪。")
        return 0
    else:
        print(f"\n⚠️ 有 {total - passed} 项测试失败，请检查错误信息。")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
