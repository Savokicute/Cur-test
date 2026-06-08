# coding=utf-8
"""Single pipeline cycle: hot list fetch then article crawl."""

from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import sys
from dataclasses import dataclass

from hot_content_bridge.article_crawler import crawl_pending_batch
from hot_content_bridge.config import BridgeConfig
from hot_content_bridge.hotlist_reader import load_pending_from_latest_crawl
from hot_content_bridge.quick_hotlist import fetch_hotlist_only
from hot_content_bridge.rate_limit import build_rate_limiter
from hot_content_bridge.storage import ensure_article_tables, filter_pending_for_crawl

logger = logging.getLogger(__name__)


@dataclass
class PipelineRunResult:
    hotlist_ran: bool
    hotlist_error: str | None
    crawl_urls: int
    crawl_skipped: int
    crawl_error: str | None


def run_trendradar_full_sync(cfg: BridgeConfig) -> None:
    """Run full ``python -m trendradar`` (respects schedule; may skip collect)."""
    root = cfg.trendradar.root.resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"trendRadar root not found: {root}")
    env = {**__import__("os").environ, "PYTHONUTF8": "1"}
    cmd = [sys.executable, "-m", "trendradar"]
    logger.info("Running full trendradar: cwd=%s %s", root, " ".join(cmd))
    rc = subprocess.call(cmd, cwd=str(root), env=env)
    if rc != 0:
        raise RuntimeError(f"trendradar exited with code {rc}")


def run_hotlist_step(cfg: BridgeConfig, *, full_sync: bool = False, target_platform: str | None = None) -> None:
    """Fetch today's hot list into SQLite (always collects when using quick path)."""
    if target_platform:
        os.environ["HCB_TARGET_PLATFORM"] = target_platform
    elif "HCB_TARGET_PLATFORM" in os.environ:
        del os.environ["HCB_TARGET_PLATFORM"]

    if full_sync:
        run_trendradar_full_sync(cfg)
    else:
        fetch_hotlist_only(cfg)


def run_crawl_step(cfg: BridgeConfig, *, limit: int = 0) -> tuple[int, int]:
    """
    Crawl article bodies for the latest hot-list batch.

    Returns:
        (crawled_count, skipped_already_success)
    """
    ensure_article_tables(cfg)
    pending, _names = load_pending_from_latest_crawl(cfg)
    if not pending:
        logger.info("No pending URLs in latest hot-list batch")
        return 0, 0
    todo = filter_pending_for_crawl(cfg, pending)
    skipped = len(pending) - len(todo)
    if limit and limit > 0:
        todo = todo[:limit]
    if not todo:
        logger.info("All %d URLs already crawled successfully (skipped=%d)", len(pending), skipped)
        return 0, skipped
    logger.info("Crawling %d URLs (pending=%d, skipped=%d)", len(todo), len(pending), skipped)
    rate = build_rate_limiter(cfg)
    asyncio.run(crawl_pending_batch(cfg, todo, rate))
    return len(todo), skipped


def run_pipeline_once(
    cfg: BridgeConfig,
    *,
    skip_hotlist: bool = False,
    full_trendradar_sync: bool = False,
    crawl_after_hotlist: bool = True,
    crawl_limit: int = 0,
) -> PipelineRunResult:
    hotlist_ran = False
    hotlist_error: str | None = None
    crawl_urls = 0
    crawl_skipped = 0
    crawl_error: str | None = None

    if not skip_hotlist:
        try:
            run_hotlist_step(cfg, full_sync=full_trendradar_sync)
            hotlist_ran = True
        except Exception as exc:
            hotlist_error = str(exc)
            logger.exception("Hot list step failed: %s", exc)

    if crawl_after_hotlist and hotlist_error is None:
        try:
            crawl_urls, crawl_skipped = run_crawl_step(cfg, limit=crawl_limit)
        except Exception as exc:
            crawl_error = str(exc)
            logger.exception("Article crawl step failed: %s", exc)
    elif crawl_after_hotlist and hotlist_error:
        logger.warning("Skipping article crawl because hot list step failed")

    return PipelineRunResult(
        hotlist_ran=hotlist_ran,
        hotlist_error=hotlist_error,
        crawl_urls=crawl_urls,
        crawl_skipped=crawl_skipped,
        crawl_error=crawl_error,
    )
