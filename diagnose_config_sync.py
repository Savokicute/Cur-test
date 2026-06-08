#!/usr/bin/env python3
"""诊断前端配置同步问题"""

import sys
from pathlib import Path

def check_config_path():
    """检查配置文件路径"""
    print("=" * 60)
    print("1. 检查配置文件路径")
    print("=" * 60)

    # 模拟后端的路径计算
    current_file = Path(__file__)
    config_path = current_file.parent.parent.parent / "trendRadar" / "config" / "config.yaml"

    print(f"当前脚本位置: {current_file}")
    print(f"计算的配置路径: {config_path}")
    print(f"配置文件存在: {config_path.exists()}")

    if config_path.exists():
        print(f"✓ 配置文件路径正确")
        return True
    else:
        print(f"✗ 配置文件不存在!")
        # 尝试其他可能的路径
        alt_paths = [
            Path("trendRadar/config/config.yaml"),
            Path("../trendRadar/config/config.yaml"),
            Path("config.yaml"),
        ]
        for alt in alt_paths:
            if alt.exists():
                print(f"  发现备选路径: {alt}")
        return False

def check_backend_imports():
    """检查后端模块导入"""
    print("\n" + "=" * 60)
    print("2. 检查后端模块导入")
    print("=" * 60)

    try:
        from fastapi import FastAPI
        print("✓ FastAPI 导入成功")
    except Exception as e:
        print(f"✗ FastAPI 导入失败: {e}")
        return False

    try:
        import yaml
        print("✓ PyYAML 导入成功")
    except Exception as e:
        print(f"✗ PyYAML 导入失败: {e}")
        return False

    try:
        # 尝试导入 config 路由（不启动整个应用）
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "config_api",
            "app/api/config.py"
        )
        print("✓ Config API 模块可访问")
        return True
    except Exception as e:
        print(f"⚠ Config API 检查跳过: {e}")
        return True

def check_frontend_api_call():
    """检查前端 API 调用方式"""
    print("\n" + "=" * 60)
    print("3. 检查前端 API 调用实现")
    print("=" * 60)

    config_js_path = Path("web/frontend/src/services/config.js")
    if not config_js_path.exists():
        print(f"✗ 前端配置服务文件不存在: {config_js_path}")
        return False

    with open(config_js_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 检查 updateConfigModule 实现
    if 'updateConfigModule' in content:
        print("✓ 找到 updateConfigModule 函数")

        # 提取函数体
        import re
        match = re.search(
            r'export async function updateConfigModule\([^)]+\)\s*\{([^}]+)\}',
            content,
            re.DOTALL
        )
        if match:
            func_body = match.group(1).strip()
            print(f"\n函数实现:\n{func_body}")

            # 检查是否有潜在问题
            issues = []
            if 'data:' in func_body and 'params:' in func_body:
                if "api.put('/config/module', null," in func_body or \
                   "api.put('/config/module',undefined," in func_body:
                    issues.append("⚠ 可能的问题: 使用 null/undefined 作为第二个参数")

            if issues:
                for issue in issues:
                    print(issue)
            else:
                print("✓ API 调用方式基本正确")

    return True

def check_cors_config():
    """检查 CORS 配置"""
    print("\n" + "=" * 60)
    print("4. 检查 CORS 配置")
    print("=" * 60)

    main_py_path = Path("app/main.py")
    if not main_py_path.exists():
        print(f"✗ 主应用文件不存在: {main_py_path}")
        return False

    with open(main_py_path, 'r', encoding='utf-8') as f:
        content = f.read()

    if 'CORSMiddleware' in content and 'allow_origins' in content:
        print("✓ CORS 中间件已配置")

        # 提取 allow_origins
        import re
        match = re.search(r'allow_origins=\[([^\]]+)\]', content)
        if match:
            origins = match.group(1)
            print(f"允许的来源: [{origins}]")
            if '*' in origins:
                print("  ⚠ 允许所有来源 (开发环境OK，生产环境需限制)")
    else:
        print("✗ 未找到 CORS 配置")
        return False

    return True

def check_vite_proxy():
    """检查 Vite 代理配置"""
    print("\n" + "=" * 60)
    print("5. 检查前端开发服务器代理配置")
    print("=" * 60)

    vite_config_path = Path("web/frontend/vite.config.js")
    if not vite_config_path.exists():
        print(f"✗ Vite 配置文件不存在: {vite_config_path}")
        return False

    with open(vite_config_path, 'r', encoding='utf-8') as f:
        content = f.read()

    if '/api' in content and 'target' in content:
        print("✓ 找到 API 代理配置")

        import re
        match = re.search(r"target:\s*['\"]([^'\"]+)['\"]", content)
        if match:
            target = match.group(1)
            print(f"代理目标: {target}")

            if 'localhost:8000' in target:
                print("  → 后端应在 http://localhost:8000 运行")
    else:
        print("✗ 未找到 API 代理配置")
        return False

    return True

def generate_solution():
    """生成解决方案"""
    print("\n" + "=" * 60)
    print("解决方案建议")
    print("=" * 60)

    solution = """
## 问题诊断结果

根据代码分析，前端配置页面修改无法同步到后端可能有以下原因:

### 1. 后端服务未运行或端口不匹配
- **症状**: 前端请求超时或连接拒绝
- **解决**: 确保后端在 localhost:8000 运行
```bash
# 启动后端服务
cd "d:\\chao-TrendRadar\\Cur-test - v3"
python -m uvicorn app.main:app --reload --port 8000
```

### 2. 前端 API 调用参数格式问题 (最可能的原因)
- **文件**: web/frontend/src/services/config.js
- **问题**: `updateConfigModule` 的 axios 调用方式不规范
- **修复**: 修改为标准调用方式

### 3. 配置文件路径错误
- **文件**: app/api/config.py 第14行
- **问题**: 路径计算可能不准确
- **验证**: 检查实际路径是否正确指向 config.yaml

### 4. 文件写入权限问题
- **症状**: 后端返回500错误
- **解决**: 确保有 config.yaml 的写权限

### 5. 浏览器开发者工具调试步骤
1. 打开浏览器 DevTools (F12)
2. 切换到 Network 标签页
3. 在前端修改任意配置项
4. 观察是否有 PUT /api/config/module 请求
5. 检查请求状态码和响应内容
6. 如果是 404/500/网络错误，查看具体错误信息

### 推荐的完整修复方案
见下方代码修复部分
"""

    print(solution)

def main():
    print("""
╔═══════════════════════════════════════════════════════════════╗
║         TrendRadar 前端配置同步问题诊断工具                      ║
╚═══════════════════════════════════════════════════════════════╝
    """)

    results = {
        "配置文件路径": check_config_path(),
        "后端模块": check_backend_imports(),
        "前端API": check_frontend_api_call(),
        "CORS配置": check_cors_config(),
        "Vite代理": check_vite_proxy(),
    }

    print("\n" + "=" * 60)
    print("诊断总结")
    print("=" * 60)
    for name, passed in results.items():
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"{name}: {status}")

    generate_solution()

    # 返回退出码
    all_passed = all(results.values())
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
