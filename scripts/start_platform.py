# coding=utf-8
"""
Start the hotspot platform stack:

  1. hot-content-bridge daemon  — TrendRadar hot list + crawl4ai article crawl
  2. we-mp-rss                  — WeChat official account RSS (optional)

调度由 timeline.yaml 唯一控制：
  - timeline.yaml  → 定义时间段（何时采集/分析/推送）
  - config.yaml    → 总开关、AI 模型、通知渠道
  - bridge daemon  → 每 5 分钟轮询触发，实际执行由 TrendRadar 按 timeline 判断

Usage (from repo root):
  uv run python scripts/start_platform.py                          # 守护进程（timeline 调度）
  uv run python scripts/start_platform.py --no-wemp               # 不含公众号
  uv run python scripts/start_platform.py --once                  # 单轮（快速热榜+正文）
  uv run python scripts/start_platform.py --once --full           # 单轮完整（含 AI 分析/推送/报告）
  uv run python scripts/start_platform.py --once --full --no-wemp # 单轮完整，不含公众号
"""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _popen(cmd: list[str], cwd: Path, env: dict | None = None) -> subprocess.Popen:
    print(f"[start] {' '.join(cmd)}  (cwd={cwd})")
    return subprocess.Popen(
        cmd,
        cwd=str(cwd),
        env=env,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Start hotspot platform services")
    parser.add_argument("--no-wemp", action="store_true", help="Do not start we-mp-rss")
    parser.add_argument("--once", action="store_true", help="Run one pipeline cycle and exit")
    parser.add_argument(
        "--full",
        action="store_true",
        help=(
            "Execute FULL TrendRadar pipeline including AI analysis, "
            "filtering, notification & report generation. "
            "Without this flag only fetches hot list via quick API (no AI)."
        ),
    )
    args = parser.parse_args()

    env = {**os.environ, "PYTHONUTF8": "1"}

    # ── 构建命令 ──
    children: list[subprocess.Popen] = []

    bridge_cmd = [sys.executable, "-m", "hot_content_bridge.cli"]
    if args.once:
        bridge_cmd.append("run-pipeline")
        if not args.full:
            bridge_cmd.append("--quick-hotlist")
        # --full: 不传 --quick-hotlist → 触发 python -m trendradar 全流程
        #         （热榜采集 → AI 筛选/分析 → 推送通知 → HTML 报告 → 正文爬取）
    else:
        bridge_cmd.append("daemon")
        # 默认 --full-sync: 让 TrendRadar 根据 timeline.yaml 决定采集/分析/推送
        # 不加此参数时仅热榜入库（绕过 timeline 调度）
        bridge_cmd.append("--full-sync")
    children.append(_popen(bridge_cmd, REPO_ROOT, env))

    if not args.no_wemp and not args.once:
        wemp_root = REPO_ROOT / "we-mp-rss"
        wemp_cmd = [sys.executable, "main.py", "-job", "True"]
        children.append(_popen(wemp_cmd, wemp_root, env))

    # ── 单轮模式：等待完成 ──
    if args.once:
        for p in children:
            rc = p.wait()
            if rc != 0:
                return rc
        return 0

    # ── 守护进程模式：保持运行 ──
    if not children:
        print("[start] Nothing to run.")
        return 0

    print("[start] Services running. Press Ctrl+C to stop all.")
    print("[start] 调度由 timeline.yaml 唯一控制:")
    print(f"[start]   daemon 每 5 分钟轮询 → TrendRadar 按 timeline 判断是否执行")
    print(f"[start]   不在时间段内 → 自动跳过（零开销）")

    def shutdown(signum=None, frame=None):  # noqa: ARG001
        print("\n[start] Stopping children…")
        for p in children:
            if p.poll() is None:
                p.terminate()
        deadline = time.time() + 15
        for p in children:
            while p.poll() is None and time.time() < deadline:
                time.sleep(0.2)
            if p.poll() is None:
                p.kill()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    try:
        while True:
            for p in children:
                rc = p.poll()
                if rc is not None:
                    print(f"[start] Process exited with code {rc}: {p.args}")
                    shutdown()
            time.sleep(1)
    except KeyboardInterrupt:
        shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
