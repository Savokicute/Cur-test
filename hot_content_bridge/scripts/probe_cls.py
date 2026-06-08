# coding=utf-8
import asyncio
import os

os.environ["PYTHONUTF8"] = "1"
import hot_content_bridge._crawl4ai_path  # noqa: F401

from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

URL = "https://www.cls.cn/detail/2373905"
SELECTORS = [
    ".detail-content-wrap",
    ".detail-wrap",
    ".detail-container",
    ".detail",
    ".l-main",
    ".telegraph-detail",
    ".article-detail-content",
    ".detail-content-box",
    ".detail-body",
    ".content-wrapper",
    ".detail-content",
    ".detail-main-content",
    ".main-left",
    ".detail-brief",
    ".brief",
]


async def one(sel: str) -> tuple[int, bool]:
    bcfg = BrowserConfig(headless=True, verbose=False)
    cfg = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        markdown_generator=DefaultMarkdownGenerator(content_filter=None),
        page_timeout=90000,
        wait_until="load",
        delay_before_return_html=1.2,
        word_count_threshold=5,
        verbose=False,
        css_selector=sel,
        target_elements=[sel],
    )
    async with AsyncWebCrawler(config=bcfg, verbose=False) as c:
        r = await c.arun(url=URL, config=cfg)
    md = str(r.markdown or "")
    full = all(k in md for k in ["①", "财联社5月18日", "787.5"])
    return len(md), full


async def main() -> None:
    for sel in SELECTORS:
        n, full = await one(sel)
        if n > 500:
            print(sel, "len", n, "full", full)


if __name__ == "__main__":
    asyncio.run(main())
