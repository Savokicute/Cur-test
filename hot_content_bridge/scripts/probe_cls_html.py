# coding=utf-8
import asyncio
import os
import re

os.environ["PYTHONUTF8"] = "1"
import hot_content_bridge._crawl4ai_path  # noqa: F401

from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig

URL = "https://www.cls.cn/detail/2373905"


async def main() -> None:
    bcfg = BrowserConfig(headless=True, verbose=False)
    cfg = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        page_timeout=90000,
        wait_until="load",
        delay_before_return_html=1.5,
        verbose=False,
    )
    async with AsyncWebCrawler(config=bcfg, verbose=False) as c:
        r = await c.arun(url=URL, config=cfg)
    html = r.html or ""
    idx = html.find("①")
    if idx < 0:
        print("no bullet in html")
        return
    snippet = html[max(0, idx - 400) : idx + 200]
    # class names near bullet
    classes = set(re.findall(r'class="([^"]*)"', snippet))
    print("classes near bullet:", classes)
    # parent chain - find id/class on enclosing divs
    for pat in [
        r'<([a-z]+)[^>]*class="([^"]*)"[^>]*>[^<]{0,80}①',
        r'id="([^"]+)"[^>]*>[\s\S]{0,200}?①',
    ]:
        m = re.search(pat, html[max(0, idx - 2000) : idx + 100], re.I)
        if m:
            print("match", pat[:30], m.groups())


if __name__ == "__main__":
    asyncio.run(main())
