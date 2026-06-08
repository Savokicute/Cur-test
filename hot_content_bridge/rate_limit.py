# coding=utf-8
"""Domain rate limiting using crawl4ai's RateLimiter."""

from __future__ import annotations

import hot_content_bridge._crawl4ai_path  # noqa: F401

from crawl4ai.async_dispatcher import RateLimiter

from hot_content_bridge.config import BridgeConfig


def build_rate_limiter(cfg: BridgeConfig) -> RateLimiter:
    ac = cfg.article_crawl
    return RateLimiter(
        base_delay=(ac.per_domain_min_delay_s, ac.per_domain_max_delay_s),
        max_delay=90.0,
        max_retries=max(3, ac.max_retries + 1),
        rate_limit_codes=[429, 503],
    )
