# coding=utf-8
"""SQLite helpers for article_contents (same DB as trendRadar)."""

from __future__ import annotations

import hashlib
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Set

from hot_content_bridge.config import BridgeConfig
from hot_content_bridge.models import CrawlOutcome, PendingArticle


def _news_db_path(cfg: BridgeConfig, date: Optional[str] = None) -> Path:
    from trendradar.utils.time import format_date_folder

    tz = cfg._raw_tr_config.get("app", {}).get("timezone", "Asia/Shanghai")
    date_str = format_date_folder(date, tz)
    return cfg.data_dir / "news" / f"{date_str}.db"


def _schema_sql() -> str:
    return (Path(__file__).resolve().parent / "article_schema.sql").read_text(encoding="utf-8")


def ensure_article_tables(cfg: BridgeConfig, date: Optional[str] = None) -> Path:
    """Create article_contents tables if missing. Returns DB path."""
    db_path = _news_db_path(cfg, date)
    if not db_path.parent.exists():
        db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    try:
        conn.executescript(_schema_sql())
        conn.commit()
    finally:
        conn.close()
    return db_path


def already_crawled_url_norms(cfg: BridgeConfig, date: Optional[str] = None) -> Set[str]:
    """URL norms that already have a successful crawl (skipped unless recrawl_success)."""
    db_path = _news_db_path(cfg, date)
    if not db_path.exists():
        return set()
    ensure_article_tables(cfg, date)
    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT url_norm FROM article_contents WHERE status = 'success'"
        )
        return {row[0] for row in cur.fetchall()}
    finally:
        conn.close()


def upsert_crawl_result(cfg: BridgeConfig, outcome: CrawlOutcome, date: Optional[str] = None) -> None:
    db_path = ensure_article_tables(cfg, date)
    conn = sqlite3.connect(str(db_path))
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO article_contents (
                news_item_id, url_norm, platform_id, title_snapshot,
                status, http_status, markdown, extracted_title, error,
                content_sha256, fetched_at, crawl_config_hash, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(url_norm) DO UPDATE SET
                news_item_id = excluded.news_item_id,
                platform_id = excluded.platform_id,
                title_snapshot = excluded.title_snapshot,
                status = excluded.status,
                http_status = excluded.http_status,
                markdown = excluded.markdown,
                extracted_title = excluded.extracted_title,
                error = excluded.error,
                content_sha256 = excluded.content_sha256,
                fetched_at = excluded.fetched_at,
                crawl_config_hash = excluded.crawl_config_hash,
                updated_at = excluded.updated_at
            """,
            (
                outcome.news_item_id or None,
                outcome.url_norm,
                outcome.platform_id,
                outcome.title_snapshot,
                outcome.status,
                outcome.http_status,
                outcome.markdown,
                outcome.extracted_title,
                outcome.error,
                outcome.content_sha256,
                now,
                cfg.article_crawl.crawl_config_hash,
                now,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def content_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def filter_pending_for_crawl(cfg: BridgeConfig, pending: List[PendingArticle]) -> List[PendingArticle]:
    if cfg.article_crawl.recrawl_success:
        return pending
    done = already_crawled_url_norms(cfg)
    return [p for p in pending if p.url_norm not in done]
