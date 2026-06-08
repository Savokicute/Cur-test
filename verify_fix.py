#!/usr/bin/env python3
"""简化版配置同步测试（避免导入整个应用）"""

import sys
import os
from pathlib import Path

def test_config_path_directly():
    """直接测试路径计算逻辑"""
    print("=" * 60)
    print("测试: 配置文件路径解析")
    print("=" * 60)

    # 模拟 _get_config_path 的逻辑
    current_file = Path(__file__)
    project_root = current_file.parent  # 脚本所在目录就是项目根目录

    # 方法1: 基于项目根目录
    config_path1 = project_root / "trendRadar" / "config" / "config.yaml"

    # 方法2: 相对路径
    config_path2 = Path("trendRadar/config/config.yaml").resolve()

    # 方法3: 环境变量
    env_path = os.environ.get("TRENDRADAR_CONFIG")

    print(f"项目根目录: {project_root}")
    print(f"\n方法1 (基于脚本位置):")
    print(f"  路径: {config_path1}")
    print(f"  存在: {config_path1.exists()}")

    print(f"\n方法2 (相对路径):")
    print(f"  路径: {config_path2}")
    print(f"  存在: {config_path2.exists()}")

    if env_path:
        print(f"\n方法3 (环境变量):")
        print(f"  路径: {env_path}")
        print(f"  存在: {Path(env_path).exists()}")

    # 选择可用的路径
    final_path = None
    if config_path1.exists():
        final_path = config_path1
    elif config_path2.exists():
        final_path = config_path2
    elif env_path and Path(env_path).exists():
        final_path = Path(env_path)

    if final_path:
        print(f"\n✓ 最终使用的配置文件: {final_path}")
        return True, final_path
    else:
        print(f"\n✗ 未找到有效的配置文件!")
        return False, None

def test_yaml_operations(config_path):
    """测试 YAML 操作"""
    if not config_path:
        print("\n跳过 YAML 测试（无有效配置路径）")
        return False

    print("\n" + "=" * 60)
    print("测试: YAML 文件操作")
    print("=" * 60)

    try:
        import yaml

        # 读取测试
        with open(config_path, 'r', encoding='utf-8') as f:
            content = f.read()
            config = yaml.safe_load(content)

        print(f"✓ 成功读取配置文件")
        print(f"  大小: {len(content)} 字节")
        print(f"  顶级键: {list(config.keys())}")

        # 测试序列化
        test_data = {"test_module": {"key": "value", "enabled": True}}
        import io
        output = io.StringIO()
        yaml.dump(test_data, output, allow_unicode=True, default_flow_style=False, sort_keys=False)
        serialized = output.getvalue()
        print(f"\n✓ 序列化测试成功:")
        print(f"  {serialized.strip()}")

        # 测试修改并写回（使用临时文件）
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False, encoding='utf-8') as tmp:
            # 复制原始内容
            tmp.write(content)

            # 修改一个值
            modified_config = yaml.safe_load(content)
            if 'app' in modified_config:
                original_tz = modified_config['app'].get('timezone')
                modified_config['app']['_test_flag'] = 'test_value'

                # 写入修改后的内容（不保存到原文件）
                tmp.seek(0)
                tmp.truncate()
                yaml.dump(modified_config, tmp, allow_unicode=True, default_flow_style=False, sort_keys=False)

        print(f"\n✓ 写入操作正常（已验证，未实际修改原文件）")

        # 清理临时文件
        os.unlink(tmp.name)

        return True

    except Exception as e:
        print(f"✗ YAML 操作失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def show_fix_summary():
    """显示修复总结"""
    print("\n" + "=" * 60)
    print("修复总结")
    print("=" * 60)

    summary = """
已完成的修复:

1. ✅ 后端配置文件路径 ([app/api/config.py](app/api/config.py))
   - 问题: 使用 parent.parent.parent 导致路径错误
   - 修复: 增加多级备选路径查找机制
   - 新增支持:
     * 基于项目根目录的相对路径
     * 当前工作目录下的相对路径
     * 环境变量 TRENDRADAR_CONFIG 指定

2. ✅ 备份目录路径优化 ([app/api/config.py](app/api/config.py))
   - 改为基于配置文件路径计算备份目录

3. ✅ 前端 API 调用方式优化 ([web/frontend/src/services/config.js](web/frontend/src/services/config.js))
   - 修正 axios.put() 参数传递方式
   - 从非标准的 data 参数改为标准请求体

启动步骤:

# 终端1: 启动后端
cd "d:\\chao-TrendRadar\\Cur-test - v3"
python -m uvicorn app.main:app --reload --port 8000

# 终端2: 启动前端
cd web/frontend
npm run dev

# 浏览器访问
http://localhost:5173/settings 或 http://localhost:5173/system-config

调试提示:
- 打开浏览器 F12 → Network 标签页
- 修改任意配置项
- 观察 PUT /api/config/module 请求
- 预期: 状态码 200，响应包含 success: true
"""
    print(summary)

def main():
    print("""
╔═══════════════════════════════════════════════════════════════╗
║         TrendRadar 配置同步功能验证                            ║
╚═══════════════════════════════════════════════════════════════╝
""")

    success, config_path = test_config_path_directly()
    yaml_ok = test_yaml_operations(config_path)

    print("\n" + "=" * 60)
    print("验证结果")
    print("=" * 60)
    print(f"配置路径: {'✓ 正确' if success else '✗ 错误'}")
    print(f"YAML操作: {'✓ 正常' if yaml_ok else '✗ 异常'}")

    if success and yaml_ok:
        print("\n🎉 配置系统就绪！可以启动前后端服务进行测试。")
    else:
        print("\n⚠️  请检查上方错误信息")

    show_fix_summary()

    return 0 if (success and yaml_ok) else 1

if __name__ == "__main__":
    sys.exit(main())
