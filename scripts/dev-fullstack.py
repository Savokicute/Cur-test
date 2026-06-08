#!/usr/bin/env python3
# coding=utf-8
"""
热点发现平台 - 全栈开发启动脚本
同时启动：
1. hot-content-bridge daemon (热榜采集)
2. FastAPI backend (API 服务)
3. Vite frontend (前端开发服务器)
"""

import argparse
import asyncio
import os
import signal
import sys
from pathlib import Path
from typing import List

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent


async def run_command(cmd: List[str], cwd: Path, name: str):
    """运行命令并实时输出。"""
    print(f"[{name}] 启动: {' '.join(cmd)}")
    process = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=str(cwd),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    
    async def read_output():
        while True:
            line = await process.stdout.readline()
            if not line:
                break
            print(f"[{name}] {line.decode('utf-8', errors='replace').rstrip()}")
    
    asyncio.create_task(read_output())
    return process


async def main():
    parser = argparse.ArgumentParser(description="热点发现平台 - 全栈开发启动脚本")
    parser.add_argument("--skip-daemon", action="store_true", help="跳过启动 hot-content-bridge daemon")
    parser.add_argument("--skip-backend", action="store_true", help="跳过启动 FastAPI backend")
    parser.add_argument("--skip-frontend", action="store_true", help="跳过启动 Vite frontend")
    args = parser.parse_args()

    print("🔥 热点发现平台 - 全栈启动")
    print("=" * 40)
    print()

    processes = []

    try:
        # 创建日志目录
        log_dir = PROJECT_ROOT / "logs"
        log_dir.mkdir(exist_ok=True)

        # 1. 启动 hot-content-bridge daemon
        if not args.skip_daemon:
            print("[1/3] 启动 hot-content-bridge daemon...")
            daemon_proc = await run_command(
                ["uv", "run", "hot-content-bridge", "daemon"],
                PROJECT_ROOT,
                "daemon"
            )
            processes.append(("daemon", daemon_proc))
            await asyncio.sleep(2)

        # 2. 启动 FastAPI backend
        if not args.skip_backend:
            print("[2/3] 启动 FastAPI backend...")
            backend_proc = await run_command(
                ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"],
                PROJECT_ROOT,
                "backend"
            )
            processes.append(("backend", backend_proc))
            await asyncio.sleep(2)

        # 3. 启动 Vite frontend
        if not args.skip_frontend:
            print("[3/3] 启动 Vite frontend...")
            frontend_dir = PROJECT_ROOT / "web" / "frontend"
            frontend_proc = await run_command(
                ["npm", "run", "dev"],
                frontend_dir,
                "frontend"
            )
            processes.append(("frontend", frontend_proc))

        print()
        print("✅ 所有服务已启动!")
        print()
        print("📋 访问地址:")
        if not args.skip_frontend:
            print("  前端: http://localhost:5173")
        if not args.skip_backend:
            print("  后端 API: http://localhost:8000")
            print("  API 文档: http://localhost:8000/docs")
        print()
        print("⏹️  按 Ctrl+C 停止所有服务")
        print()

        # 等待所有进程
        while True:
            all_running = True
            for name, proc in processes:
                if proc.returncode is not None:
                    print(f"⚠️  进程 {name} 已退出 (code: {proc.returncode})")
                    all_running = False
            if not all_running:
                break
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        print()
        print("⏹️  正在停止所有服务...")

    finally:
        # 停止所有进程
        for name, proc in processes:
            if proc.returncode is None:
                try:
                    proc.terminate()
                    await asyncio.wait_for(proc.wait(), timeout=5)
                    print(f"  ✓ {name} 已停止")
                except asyncio.TimeoutError:
                    proc.kill()
                    await proc.wait()
                    print(f"  ✓ {name} 已强制停止")
                except Exception as e:
                    print(f"  ✗ 停止 {name} 失败: {e}")

        print("👋 再见!")


if __name__ == "__main__":
    asyncio.run(main())
