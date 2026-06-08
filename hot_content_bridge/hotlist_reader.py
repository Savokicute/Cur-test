# coding=utf-8
"""Read latest hot-list batch from trendRadar storage."""

from __future__ import annotations

from typing import Dict, List, Set, Tuple
from urllib.parse import urlparse

from trendradar.storage.manager import get_storage_manager
from trendradar.utils.url import normalize_url

from hot_content_bridge.config import BridgeConfig
from hot_content_bridge.hot_summary import extract_hot_summary
from hot_content_bridge.models import PendingArticle


def _storage(cfg: BridgeConfig):
    tz = cfg._raw_tr_config.get("app", {}).get("timezone", "Asia/Shanghai")
    return get_storage_manager(
        backend_type="local",
        data_dir=str(cfg.data_dir),
        enable_txt=False,
        enable_html=False,
        timezone=tz,
        force_new=True,
    )


def load_pending_from_latest_crawl(cfg: BridgeConfig) -> Tuple[List[PendingArticle], Dict[str, str]]:
    """
    Build de-duplicated pending article list from the latest crawl snapshot.

    Returns:
        (pending_articles, id_to_name)
    """
    sm = _storage(cfg)
    latest = sm.get_latest_crawl_data()
    if not latest or not latest.items:
        return [], latest.id_to_name if latest else {}

    id_to_name = latest.id_to_name or {}
    seen_url: Set[str] = set()
    out: List[PendingArticle] = []
    ac = cfg.article_crawl

    for platform_id, news_list in latest.items.items():
        for item in news_list:
            url = (item.url or "").strip() or (item.mobile_url or "").strip()
            if not url:
                continue
            if ac.top_rank_only and item.rank > ac.top_rank_only:
                continue
            url_norm = normalize_url(url, platform_id)
            if not url_norm:
                continue
            host = urlparse(url_norm).netloc.lower()
            if any(host == d.lower() or host.endswith("." + d.lower()) for d in ac.skip_domains):
                continue
            if url_norm in seen_url:
                continue
            seen_url.add(url_norm)
            nid = int(item.news_item_db_id or 0)
            summary = extract_hot_summary(item.raw_extra, title=item.title)
            out.append(
                PendingArticle(
                    news_item_id=nid,
                    url=url,
                    url_norm=url_norm,
                    platform_id=platform_id,
                    title=item.title,
                    rank=item.rank,
                    hot_summary=summary,
                )
            )

    if ac.max_urls_per_run and ac.max_urls_per_run > 0:
        return out[: ac.max_urls_per_run], id_to_name
    return out, id_to_name
