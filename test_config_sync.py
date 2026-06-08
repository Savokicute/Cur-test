#!/usr/bin/env python3
"""测试配置同步功能"""

import sys
import json
from pathlib import Path

def test_config_path():
    """测试配置文件路径解析"""
    print("=" * 60)
    print("测试1: 配置文件路径解析")
    print("=" * 60)

    # 导入修复后的模块
    sys.path.insert(0, str(Path(__file__).parent))
    from app.api.config import _get_config_path, _get_backup_dir

    config_path = _get_config_path()
    backup_dir = _get_backup_dir()

    print(f"配置文件路径: {config_path}")
    print(f"配置文件存在: {config_path.exists()}")
    print(f"备份目录: {backup_dir}")
    print(f"备份目录存在: {backup_dir.exists()}")

    if config_path.exists():
        print("✓ 配置文件路径正确")
        return True
    else:
        print("✗ 配置文件路径错误")
        return False

def test_yaml_read_write():
    """测试 YAML 读写"""
    print("\n" + "=" * 60)
    print("测试2: YAML 文件读写")
    print("=" * 60)

    try:
        import yaml
        from app.api.config import _get_config_path

        config_path = _get_config_path()

        # 读取
        with open(config_path, 'r', encoding='utf-8') as f:
            content = f.read()
            config = yaml.safe_load(content)

        print(f"✓ 成功读取配置文件")
        print(f"  模块数量: {len(config.keys())}")
        print(f"  模块列表: {list(config.keys())[:5]}...")

        # 测试修改一个值（不实际保存）
        test_value = {"test": "value", "timestamp": "2024-01-01T00:00:00"}
        import io
        output = io.StringIO()
        yaml.dump(test_value, output, allow_unicode=True, default_flow_style=False)
        result = output.getvalue()

        print(f"✓ YAML 序列化正常")
        print(f"  示例输出: {result[:100]}...")

        return True
    except Exception as e:
        print(f"✗ YAML 读写失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_api_endpoint():
    """测试 API 端点定义"""
    print("\n" + "=" * 60)
    print("测试3: API 端点检查")
    print("=" * 60)

    try:
        from app.api.config import router

        print(f"✓ Config 路由器加载成功")
        print(f"  路由前缀: {router.prefix}")

        routes = []
        for route in router.routes:
            if hasattr(route, 'methods'):
                methods = ','.join(route.methods) if route.methods else ''
                routes.append(f"{methods} {route.path}")

        print(f"  注册的路由:")
        for route in routes[:5]:
            print(f"    - {route}")
        if len(routes) > 5:
            print(f"    ... 还有 {len(routes) - 5} 个路由")

        return True
    except Exception as e:
        print(f"✗ API 端点检查失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("""
╔═══════════════════════════════════════════════════════════════╗
║         TrendRadar 配置同步功能测试                            ║
╚═══════════════════════════════════════════════════════════════╝
    """)

    results = {
        "路径解析": test_config_path(),
        "YAML读写": test_yaml_read_write(),
        "API端点": test_api_endpoint(),
    }

    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    for name, passed in results.items():
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"{name}: {status}")

    all_passed = all(results.values())
    if all_passed:
        print("\n🎉 所有测试通过！前端配置应该可以正常同步到后端了。")
        print("\n下一步操作:")
        print("1. 启动后端服务: python -m uvicorn app.main:app --reload --port 8000")
        print("2. 启动前端服务: cd web/frontend && npm run dev")
        print("3. 打开浏览器访问 http://localhost:5173/settings")
        print("4. 修改任意配置项，观察是否成功保存")
    else:
        print("\n❌ 部分测试失败，请查看上方错误信息")

    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
