# coding=utf-8
import tempfile
from pathlib import Path
from unittest.mock import patch

from trendradar.storage.base import NewsData, NewsItem

from hot_content_bridge.config import ArticleCrawlSettings, BridgeConfig, TrendRadarPaths
from hot_content_bridge.hotlist_reader import load_pending_from_latest_crawl
from hot_content_bridge.models import CrawlOutcome, PendingArticle
from hot_content_bridge.storage import (
    content_sha256,
    ensure_article_tables,
    filter_pending_for_crawl,
    upsert_crawl_result,
)


def test_content_sha256_stable():
    assert len(content_sha256("hello")) == 64


def test_filter_pending_respects_success():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "output" / "news").mkdir(parents=True)
        cfg = BridgeConfig(
            trendradar=TrendRadarPaths(root=root, config_yaml=root / "cfg.yaml"),
            article_crawl=ArticleCrawlSettings(recrawl_success=False),
            _raw_tr_config={"app": {"timezone": "UTC"}, "storage": {"local": {"data_dir": "output"}}},
        )
        ensure_article_tables(cfg)

        out = CrawlOutcome(
            url_norm="https://example.com/a",
            news_item_id=1,
            platform_id="t1",
            title_snapshot="t",
            status="success",
            http_status=200,
            markdown="# hi",
            extracted_title="",
            error="",
            content_sha256=content_sha256("# hi"),
        )
        upsert_crawl_result(cfg, out)

        pending = [
            PendingArticle(1, "https://example.com/a", "https://example.com/a", "t1", "t", 1),
            PendingArticle(2, "https://example.com/b", "https://example.com/b", "t1", "t2", 2),
        ]
        filt = filter_pending_for_crawl(cfg, pending)
        assert len(filt) == 1
        assert filt[0].url_norm.endswith("/b")


@patch("hot_content_bridge.hotlist_reader.get_storage_manager")
def test_load_pending_dedupe(mock_sm):
    item_a = NewsItem(
        title="A",
        source_id="p1",
        source_name="P1",
        rank=1,
        url="https://example.com/x",
        mobile_url="",
        news_item_db_id=10,
        raw_extra={"desc": "这是热搜摘要"},
    )
    item_b = NewsItem(
        title="B",
        source_id="p1",
        source_name="P1",
        rank=2,
        url="https://example.com/x",
        mobile_url="",
        news_item_db_id=11,
    )
    nd = NewsData(
        date="2026-01-01",
        crawl_time="2026-01-01 12:00:00",
        items={"p1": [item_a, item_b]},
        id_to_name={"p1": "P1"},
        failed_ids=[],
    )
    mock_sm.return_value.get_latest_crawl_data.return_value = nd

    cfg = BridgeConfig(
        trendradar=TrendRadarPaths(),
        article_crawl=ArticleCrawlSettings(),
        _raw_tr_config={"app": {"timezone": "Asia/Shanghai"}},
    )
    pending, _names = load_pending_from_latest_crawl(cfg)
    assert len(pending) == 1
    assert pending[0].news_item_id == 10
    assert pending[0].hot_summary == "这是热搜摘要"
