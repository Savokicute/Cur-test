# coding=utf-8
"""Load bridge YAML config with defaults."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


@dataclass
class TrendRadarPaths:
    """Paths to trendRadar installation and its config."""

    root: Path = field(default_factory=lambda: Path("trendRadar"))
    # Relative to `root` (trendRadar project directory)
    config_yaml: Path = field(default_factory=lambda: Path("config/config.yaml"))


@dataclass
class PipelineDaemonSettings:
    """Background hot list + article crawl scheduler."""

    enabled: bool = True
    run_on_startup: bool = True
    hotlist_interval_minutes: int = 30
    initial_delay_seconds: int = 5
    # False = fetch-hotlist-only (always collects); True = full trendradar (may skip per schedule)
    full_trendradar_sync: bool = False
    crawl_after_hotlist: bool = True
    crawl_limit_per_run: int = 0

    @property
    def hotlist_interval_seconds(self) -> int:
        return int(self.hotlist_interval_minutes) * 60


@dataclass
class ArticleCrawlSettings:
    max_urls_per_run: int = 0
    concurrency: int = 2
    per_domain_min_delay_s: float = 1.5
    per_domain_max_delay_s: float = 3.5
    request_timeout_ms: int = 60000
    max_retries: int = 2
    top_rank_only: int = 0  # 0 = no filter; else only rank <= N
    skip_domains: List[str] = field(default_factory=list)
    user_agent: str = ""
    crawl_config_hash: str = "v2-main-content"
    recrawl_success: bool = False

    # --- Main content extraction (crawl4ai) ---
    # content_filter: "bm25" = relevance to hot-list title (recommended), "pruning" = density tree prune
    content_filter: str = "bm25"
    bm25_threshold: float = 0.48
    bm25_use_stemming: bool = False
    bm25_language: str = "english"
    pruning_threshold: float = 0.52

    word_count_threshold: int = 12
    delay_before_return_html: float = 0.35
    wait_until: str = "domcontentloaded"

    remove_forms: bool = True
    exclude_external_links: bool = True
    exclude_social_media_links: bool = True
    exclude_external_images: bool = False  # keep article body images in markdown

    markdown_ignore_links: bool = True
    post_strip_boilerplate: bool = True

    use_target_elements: bool = False

    excluded_tags: Optional[List[str]] = None
    excluded_selector: Optional[str] = None
    target_elements: Optional[List[str]] = None


@dataclass
class BridgeConfig:
    trendradar: TrendRadarPaths = field(default_factory=TrendRadarPaths)
    article_crawl: ArticleCrawlSettings = field(default_factory=ArticleCrawlSettings)
    pipeline_daemon: PipelineDaemonSettings = field(default_factory=PipelineDaemonSettings)

    @property
    def data_dir(self) -> Path:
        """Resolve trendRadar storage data_dir (local.output)."""
        cfg = self._raw_tr_config.get("storage", {}) or {}
        local = cfg.get("local", {}) or {}
        rel = local.get("data_dir", "output")
        root = self.trendradar.root.resolve()
        return (root / rel).resolve()

    _raw_tr_config: Dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def load(
        cls,
        path: Optional[Path] = None,
        trendradar_config: Optional[Path] = None,
    ) -> "BridgeConfig":
        p = path or Path(__file__).resolve().parent / "config.yaml"
        data: Dict[str, Any] = {}
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}

        tr = data.get("trendradar", {}) or {}
        root = Path(tr.get("root", "trendRadar"))
        cfg_yaml = Path(tr.get("config_yaml", "config/config.yaml"))
        if trendradar_config:
            cfg_yaml = Path(trendradar_config)

        raw_tr: Dict[str, Any] = {}
        cfg_abs = cfg_yaml if cfg_yaml.is_absolute() else (root / cfg_yaml).resolve()
        if cfg_abs.exists():
            with open(cfg_abs, "r", encoding="utf-8") as f:
                raw_tr = yaml.safe_load(f) or {}

        ac = data.get("article_crawl", {}) or {}
        cf_raw = (ac.get("content_filter") or "").strip().lower()
        if cf_raw in ("bm25", "pruning"):
            content_filter = cf_raw
        elif ac.get("use_pruning_filter") is True:
            content_filter = "pruning"
        elif ac.get("use_pruning_filter") is False:
            content_filter = "bm25"
        else:
            content_filter = "bm25"

        article = ArticleCrawlSettings(
            max_urls_per_run=int(ac.get("max_urls_per_run", 0)),
            concurrency=int(ac.get("concurrency", 2)),
            per_domain_min_delay_s=float(ac.get("per_domain_min_delay_s", 1.5)),
            per_domain_max_delay_s=float(ac.get("per_domain_max_delay_s", 3.5)),
            request_timeout_ms=int(ac.get("request_timeout_ms", 60000)),
            max_retries=int(ac.get("max_retries", 2)),
            top_rank_only=int(ac.get("top_rank_only", 0)),
            skip_domains=list(ac.get("skip_domains", []) or []),
            user_agent=str(ac.get("user_agent", "") or ""),
            crawl_config_hash=str(ac.get("crawl_config_hash", "v2-main-content")),
            recrawl_success=bool(ac.get("recrawl_success", False)),
            content_filter=content_filter,
            bm25_threshold=float(ac.get("bm25_threshold", 0.48)),
            bm25_use_stemming=bool(ac.get("bm25_use_stemming", False)),
            bm25_language=str(ac.get("bm25_language", "english")),
            pruning_threshold=float(ac.get("pruning_threshold", 0.52)),
            word_count_threshold=int(ac.get("word_count_threshold", 12)),
            delay_before_return_html=float(ac.get("delay_before_return_html", 0.35)),
            wait_until=str(ac.get("wait_until", "domcontentloaded")),
            remove_forms=bool(ac.get("remove_forms", True)),
            exclude_external_links=bool(ac.get("exclude_external_links", True)),
            exclude_social_media_links=bool(ac.get("exclude_social_media_links", True)),
            exclude_external_images=bool(ac.get("exclude_external_images", False)),
            markdown_ignore_links=bool(ac.get("markdown_ignore_links", True)),
            post_strip_boilerplate=bool(ac.get("post_strip_boilerplate", True)),
            use_target_elements=bool(ac.get("use_target_elements", False)),
            excluded_tags=ac.get("excluded_tags"),
            excluded_selector=ac.get("excluded_selector"),
            target_elements=ac.get("target_elements"),
        )

        pd = data.get("pipeline_daemon", {}) or {}
        pipeline_daemon = PipelineDaemonSettings(
            enabled=bool(pd.get("enabled", True)),
            run_on_startup=bool(pd.get("run_on_startup", True)),
            hotlist_interval_minutes=int(pd.get("hotlist_interval_minutes", 30)),
            initial_delay_seconds=int(pd.get("initial_delay_seconds", 5)),
            full_trendradar_sync=bool(pd.get("full_trendradar_sync", False)),
            crawl_after_hotlist=bool(pd.get("crawl_after_hotlist", True)),
            crawl_limit_per_run=int(pd.get("crawl_limit_per_run", 0)),
        )

        return cls(
            trendradar=TrendRadarPaths(root=root, config_yaml=cfg_abs),
            article_crawl=article,
            pipeline_daemon=pipeline_daemon,
            _raw_tr_config=raw_tr,
        )
