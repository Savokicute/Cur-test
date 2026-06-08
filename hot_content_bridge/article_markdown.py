# coding=utf-8
"""Finalize crawled article markdown (strip, dedupe, normalize, hot summary)."""

from __future__ import annotations

from typing import Optional

from hot_content_bridge.config import BridgeConfig
from hot_content_bridge.markdown_normalize import (
    dedupe_paragraphs,
    normalize_markdown,
    prepend_hot_summary,
)
from hot_content_bridge.markdown_post import strip_boilerplate_markdown
from hot_content_bridge.platform_rules_loader import PlatformRule, get_rule


def finalize_article_markdown(
    text: str,
    *,
    platform_id: Optional[str] = None,
    hot_summary: str = "",
    title: str = "",
    cfg: Optional[BridgeConfig] = None,
    rule: Optional[PlatformRule] = None,
) -> str:
    rule = rule or (get_rule(platform_id or "") if platform_id else None)
    base = text or ""

    if cfg is None or cfg.article_crawl.post_strip_boilerplate:
        base = strip_boilerplate_markdown(base, platform_id=platform_id)

    if rule and rule.dedupe_paragraphs:
        base = dedupe_paragraphs(base)

    do_norm = True
    if rule is not None and rule.normalize_markdown is not None:
        do_norm = rule.normalize_markdown
    if do_norm:
        base = normalize_markdown(base, title=title or None)

    do_prepend = True
    if rule is not None and rule.prepend_hot_summary is not None:
        do_prepend = rule.prepend_hot_summary
    if do_prepend and hot_summary:
        base = prepend_hot_summary(base, hot_summary, title=title)

    return base.strip()
