# coding=utf-8
"""crawl4ai wrapper: single-URL crawl with retries and persistence hooks."""

from __future__ import annotations

import hot_content_bridge._crawl4ai_path  # noqa: F401

import asyncio
import logging
import sys
from typing import List

if sys.platform == "win32":
    for _stream in (sys.stdout, sys.stderr):
        if hasattr(_stream, "reconfigure"):
            try:
                _stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig
from crawl4ai.async_dispatcher import RateLimiter
from crawl4ai.content_filter_strategy import BM25ContentFilter, PruningContentFilter
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

from hot_content_bridge.config import BridgeConfig
from hot_content_bridge.extraction_defaults import (
    DEFAULT_EXCLUDED_SELECTOR,
    DEFAULT_EXCLUDED_TAGS,
    DEFAULT_TARGET_ELEMENTS,
)
from hot_content_bridge.article_markdown import finalize_article_markdown
from hot_content_bridge.platform_rules_loader import PlatformRule, rule_for_article
from hot_content_bridge.models import CrawlOutcome, PendingArticle
from hot_content_bridge.storage import content_sha256, upsert_crawl_result

logger = logging.getLogger(__name__)


def _content_filter(cfg: BridgeConfig, title: str, rule: PlatformRule):
    ac = cfg.article_crawl
    mode = (rule.content_filter or ac.content_filter or "bm25").strip().lower()
    if mode in ("none", "off", "false", "raw"):
        return None
    if mode == "pruning":
        return PruningContentFilter(threshold=ac.pruning_threshold)
    q = (title or "").strip()
    return BM25ContentFilter(
        user_query=q or None,
        bm25_threshold=ac.bm25_threshold,
        language=ac.bm25_language,
        use_stemming=ac.bm25_use_stemming,
    )


def _uses_scoped_extraction(rule: PlatformRule, ac) -> bool:
    if rule.primary_target or rule.target_elements:
        return True
    if rule.use_target_elements is True:
        return True
    if rule.use_target_elements is None and ac.use_target_elements:
        return True
    return False


def _run_config(
    cfg: BridgeConfig,
    pending: PendingArticle,
    *,
    rule: PlatformRule | None = None,
    scopeless_fallback: bool = False,
) -> CrawlerRunConfig:
    ac = cfg.article_crawl
    rule = rule or rule_for_article(pending.platform_id, pending.url)
    filt = _content_filter(cfg, pending.title, rule)
    md_opts: dict = {"ignore_images": False}
    if ac.markdown_ignore_links:
        md_opts["ignore_links"] = True
    md_gen = DefaultMarkdownGenerator(
        content_filter=filt,
        options=md_opts,
    )

    excluded_tags = list(ac.excluded_tags) if ac.excluded_tags else list(DEFAULT_EXCLUDED_TAGS)
    excluded_selector = (ac.excluded_selector or "").strip() or DEFAULT_EXCLUDED_SELECTOR
    if rule.excluded_selector_extra:
        excluded_selector = f"{excluded_selector},{rule.excluded_selector_extra}"

    use_te = (
        rule.use_target_elements
        if rule.use_target_elements is not None
        else ac.use_target_elements
    )

    delay = (
        float(rule.delay_before_return_html)
        if rule.delay_before_return_html is not None
        else ac.delay_before_return_html
    )
    wait_until = rule.wait_until or ac.wait_until

    kwargs = dict(
        cache_mode=CacheMode.BYPASS,
        markdown_generator=md_gen,
        page_timeout=ac.request_timeout_ms,
        wait_until=wait_until,
        delay_before_return_html=delay,
        word_count_threshold=ac.word_count_threshold,
        excluded_tags=excluded_tags,
        excluded_selector=excluded_selector,
        remove_forms=ac.remove_forms,
        exclude_external_links=ac.exclude_external_links,
        exclude_social_media_links=ac.exclude_social_media_links,
        exclude_external_images=ac.exclude_external_images,
    )
    if not scopeless_fallback:
        if rule.primary_target:
            kwargs["css_selector"] = rule.primary_target
            kwargs["target_elements"] = [rule.primary_target]
        elif rule.css_selector:
            kwargs["css_selector"] = rule.css_selector
        if rule.target_elements and not rule.primary_target:
            kwargs["target_elements"] = list(rule.target_elements)
        elif use_te:
            te = list(ac.target_elements) if ac.target_elements else list(DEFAULT_TARGET_ELEMENTS)
            kwargs["target_elements"] = te

    return CrawlerRunConfig(**kwargs)


def _run_config_fallback(cfg: BridgeConfig, pending: PendingArticle, rule: PlatformRule) -> CrawlerRunConfig:
    """Retry without target_elements when scoped extraction yields empty markdown."""
    return _run_config(cfg, pending, rule=rule, scopeless_fallback=True)


def _markdown_from_result(
    result,
    cfg: BridgeConfig,
    pending: PendingArticle,
    rule: PlatformRule,
) -> str:
    """Prefer fit_markdown or raw per platform rule; then post-process pipeline."""
    m = result.markdown
    if m is None:
        return ""
    fit = (getattr(m, "fit_markdown", None) or "").strip()
    raw = str(m).strip()
    if rule.prefer_raw_markdown and raw:
        base = raw
    elif fit and (
        len(fit) >= 120
        or (len(fit) >= 60 and len(fit) >= 0.12 * max(len(raw), 1))
    ):
        base = fit
    else:
        base = raw
    processed = finalize_article_markdown(
        base,
        platform_id=pending.platform_id,
        hot_summary=pending.hot_summary,
        title=pending.title,
        cfg=cfg,
        rule=rule,
    )
    if not processed.strip() and base.strip():
        logger.warning(
            "post-process emptied markdown for %s; using stripped raw",
            pending.url_norm,
        )
        from hot_content_bridge.markdown_post import strip_boilerplate_markdown

        processed = strip_boilerplate_markdown(base, platform_id=pending.platform_id)
    return processed


def _browser_config(cfg: BridgeConfig) -> BrowserConfig:
    ua = (cfg.article_crawl.user_agent or "").strip()
    if ua:
        return BrowserConfig(headless=True, user_agent=ua, verbose=False)
    return BrowserConfig(headless=True, verbose=False)


async def _crawl_one_url(
    crawler: AsyncWebCrawler,
    pending: PendingArticle,
    run_cfg: CrawlerRunConfig,
    rate_limiter: RateLimiter,
    cfg: BridgeConfig,
) -> CrawlOutcome:
    await rate_limiter.wait_if_needed(pending.url)
    try:
        result = await crawler.arun(url=pending.url, config=run_cfg)
    except Exception as exc:  # pragma: no cover - network
        logger.warning("crawl exception %s: %s", pending.url, exc)
        rate_limiter.update_delay(pending.url, 503)
        return CrawlOutcome(
            url_norm=pending.url_norm,
            news_item_id=pending.news_item_id,
            platform_id=pending.platform_id,
            title_snapshot=pending.title,
            status="failed",
            http_status=None,
            markdown="",
            extracted_title="",
            error=str(exc)[:2000],
            content_sha256="",
        )

    code = result.status_code or (200 if result.success else None)
    rule = rule_for_article(pending.platform_id, pending.url)
    md = _markdown_from_result(result, cfg, pending, rule) if result.success else ""

    if result.success and not md and _uses_scoped_extraction(rule, cfg.article_crawl):
        logger.info("empty markdown after scoped extract, retry scopeless: %s", pending.url)
        try:
            fb_cfg = _run_config_fallback(cfg, pending, rule)
            fb_result = await crawler.arun(url=pending.url, config=fb_cfg)
            if fb_result.success:
                result = fb_result
                code = result.status_code or code
                md = _markdown_from_result(result, cfg, pending, rule)
        except Exception as exc:
            logger.warning("scopeless fallback failed %s: %s", pending.url, exc)

    if result.success and md:
        title = ""
        if getattr(result, "metadata", None) and isinstance(result.metadata, dict):
            title = str(result.metadata.get("title", "") or "")
        sha = content_sha256(md)
        rate_limiter.update_delay(pending.url, int(code or 200))
        return CrawlOutcome(
            url_norm=pending.url_norm,
            news_item_id=pending.news_item_id,
            platform_id=pending.platform_id,
            title_snapshot=pending.title,
            status="success",
            http_status=code,
            markdown=md,
            extracted_title=title,
            error="",
            content_sha256=sha,
        )

    raw_hint = ""
    if result.success and getattr(result, "markdown", None):
        raw_hint = str(result.markdown)[:120].replace("\n", " ")
    err = (result.error_message or "empty_markdown")[:2000]
    if raw_hint:
        err = f"{err} | raw_prefix={raw_hint}"
    rate_limiter.update_delay(pending.url, int(code or 599))
    return CrawlOutcome(
        url_norm=pending.url_norm,
        news_item_id=pending.news_item_id,
        platform_id=pending.platform_id,
        title_snapshot=pending.title,
        status="failed",
        http_status=code,
        markdown=str(result.markdown or "")[:50000],
        extracted_title="",
        error=err,
        content_sha256="",
    )


async def _crawl_with_retries(
    crawler: AsyncWebCrawler,
    pending: PendingArticle,
    rate_limiter: RateLimiter,
    cfg: BridgeConfig,
    max_retries: int,
) -> CrawlOutcome:
    last: CrawlOutcome | None = None
    attempts = max(1, max_retries + 1)
    for i in range(attempts):
        run_cfg = _run_config(cfg, pending)
        last = await _crawl_one_url(crawler, pending, run_cfg, rate_limiter, cfg)
        if last.status == "success":
            return last
        if i + 1 < attempts:
            await asyncio.sleep(min(8.0, 1.5 * (2**i)))
    assert last is not None
    return last


async def crawl_pending_batch(
    cfg: BridgeConfig,
    pending: List[PendingArticle],
    rate_limiter: RateLimiter,
) -> List[CrawlOutcome]:
    if not pending:
        return []

    bcfg = _browser_config(cfg)
    outcomes: List[CrawlOutcome] = []
    sem = asyncio.Semaphore(max(1, cfg.article_crawl.concurrency))
    retries = cfg.article_crawl.max_retries

    async with AsyncWebCrawler(config=bcfg, verbose=False) as crawler:

        async def one(p: PendingArticle) -> CrawlOutcome:
            async with sem:
                out = await _crawl_with_retries(crawler, p, rate_limiter, cfg, retries)
                upsert_crawl_result(cfg, out)
                return out

        tasks = [asyncio.create_task(one(p)) for p in pending]
        for coro in asyncio.as_completed(tasks):
            outcomes.append(await coro)

    return outcomes
