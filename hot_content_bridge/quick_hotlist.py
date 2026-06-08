# coding=utf-8
"""仅抓取热榜并写入 SQLite（不跑调度、报告、AI 筛选等完整流程）。"""

from __future__ import annotations

import os
from pathlib import Path

from hot_content_bridge.config import BridgeConfig


def fetch_hotlist_only(cfg: BridgeConfig) -> None:
    root = cfg.trendradar.root.resolve()
    yaml_abs = cfg.trendradar.config_yaml
    if not yaml_abs.is_absolute():
        yaml_abs = (root / yaml_abs).resolve()
    if not yaml_abs.exists():
        raise FileNotFoundError(f"找不到 trendRadar 配置: {yaml_abs}")

    from trendradar.core.loader import load_config
    from trendradar.__main__ import NewsAnalyzer

    target_platform = os.environ.get("HCB_TARGET_PLATFORM")

    old = os.getcwd()
    try:
        os.chdir(str(root))
        rel = Path(os.path.relpath(yaml_abs, root))
        config = load_config(str(rel).replace("\\", "/"))
        analyzer = NewsAnalyzer(config=config)

        if target_platform:
            # 仅抓取指定平台：临时禁用其他平台
            original_sources = config.platforms.sources.copy()
            filtered = [s for s in original_sources if s.id == target_platform]
            if not filtered:
                raise ValueError(f"未找到平台 '{target_platform}'，可用平台: {[s.id for s in original_sources]}")
            config.platforms.sources = filtered

        analyzer._crawl_data()
    finally:
        os.chdir(old)
        # 清理环境变量
        if "HCB_TARGET_PLATFORM" in os.environ:
            del os.environ["HCB_TARGET_PLATFORM"]
