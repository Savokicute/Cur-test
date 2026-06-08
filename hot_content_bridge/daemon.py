# coding=utf-8
"""Background scheduler: periodic hot list + article crawl."""

from __future__ import annotations

import logging
import signal
import threading
import time
from datetime import datetime

from hot_content_bridge.config import BridgeConfig, PipelineDaemonSettings
from hot_content_bridge.pipeline_runner import run_pipeline_once

logger = logging.getLogger(__name__)


class PipelineDaemon:
    """Run ``run_pipeline_once`` on startup and on a fixed interval."""

    def __init__(self, cfg: BridgeConfig, settings: PipelineDaemonSettings):
        self.cfg = cfg
        self.settings = settings
        self._stop = threading.Event()

    def stop(self) -> None:
        self._stop.set()

    def run_once(self) -> None:
        logger.info(
            "Pipeline cycle start (%s)",
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )
        result = run_pipeline_once(
            self.cfg,
            skip_hotlist=False,
            full_trendradar_sync=self.settings.full_trendradar_sync,
            crawl_after_hotlist=self.settings.crawl_after_hotlist,
            crawl_limit=self.settings.crawl_limit_per_run,
        )
        if result.hotlist_error:
            logger.error("Hot list: FAILED — %s", result.hotlist_error)
        elif result.hotlist_ran:
            logger.info("Hot list: OK")
        if result.crawl_error:
            logger.error("Article crawl: FAILED — %s", result.crawl_error)
        else:
            logger.info(
                "Article crawl: crawled=%d skipped=%d",
                result.crawl_urls,
                result.crawl_skipped,
            )
        logger.info("Pipeline cycle end")

    def run_forever(self) -> None:
        """Block until :meth:`stop` or process signal."""
        interval = max(60, self.settings.hotlist_interval_seconds)

        if self.settings.initial_delay_seconds > 0:
            logger.info(
                "Waiting %ds before first cycle…",
                self.settings.initial_delay_seconds,
            )
            if self._stop.wait(self.settings.initial_delay_seconds):
                return

        if self.settings.run_on_startup:
            self.run_once()

        while not self._stop.is_set():
            if self._stop.wait(interval):
                break
            self.run_once()

        logger.info("Pipeline daemon stopped")


def install_signal_handlers(daemon: PipelineDaemon) -> None:
    def _handler(signum, frame):  # noqa: ARG001
        logger.info("Received signal %s, shutting down…", signum)
        daemon.stop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(sig, _handler)
        except (ValueError, OSError):
            pass
