# coding=utf-8
"""Shared datatypes for the pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class PendingArticle:
    news_item_id: int
    url: str
    url_norm: str
    platform_id: str
    title: str
    rank: int
    hot_summary: str = ""


@dataclass
class CrawlOutcome:
    url_norm: str
    news_item_id: int
    platform_id: str
    title_snapshot: str
    status: str  # success | failed
    http_status: Optional[int]
    markdown: str
    extracted_title: str
    error: str
    content_sha256: str
