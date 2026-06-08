# coding=utf-8
"""Load per-platform crawl + markdown post rules from platform_rules/*.yaml."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

import yaml

logger = logging.getLogger(__name__)

_RULES_DIR = Path(__file__).resolve().parent / "platform_rules"


@dataclass(frozen=True)
class PlatformRule:
    platform_id: str
    display_name: str = ""
    enabled: bool = True
    hosts: Tuple[str, ...] = ()
    css_selector: Optional[str] = None
    target_elements: Optional[Tuple[str, ...]] = None
    primary_target: Optional[str] = None
    use_target_elements: Optional[bool] = None
    excluded_selector_extra: str = ""
    # none | bm25 | pruning — 覆盖全局 content_filter
    content_filter: Optional[str] = None
    prefer_raw_markdown: bool = False
    delay_before_return_html: Optional[float] = None
    wait_until: Optional[str] = None
    nav_labels: Tuple[str, ...] = ()
    drop_line_patterns: Tuple[str, ...] = ()
    dedupe_paragraphs: bool = False
    normalize_markdown: Optional[bool] = None
    prepend_hot_summary: Optional[bool] = None


def _norm_hosts(raw) -> Tuple[str, ...]:
    if not raw:
        return ()
    if isinstance(raw, str):
        raw = [raw]
    return tuple(h.lower().strip() for h in raw if h and str(h).strip())


def _norm_str_list(raw) -> Tuple[str, ...]:
    if not raw:
        return ()
    if isinstance(raw, str):
        raw = [raw]
    return tuple(str(x).strip() for x in raw if x and str(x).strip())


def _parse_rule(data: dict, stem: str) -> PlatformRule:
    crawl = data.get("crawl") or {}
    md = data.get("markdown_post") or {}
    te = crawl.get("target_elements")
    target_elements: Optional[Tuple[str, ...]] = None
    if te:
        target_elements = tuple(str(x) for x in te)
    pid = str(data.get("platform_id") or stem).strip()
    primary = (crawl.get("primary_target") or "").strip() or None
    if primary:
        target_elements = (primary,)
    md_post = data.get("markdown_post") or {}
    return PlatformRule(
        platform_id=pid,
        display_name=str(data.get("display_name") or pid),
        enabled=bool(data.get("enabled", True)),
        hosts=_norm_hosts(data.get("hosts")),
        css_selector=(crawl.get("css_selector") or None),
        target_elements=target_elements,
        primary_target=primary,
        use_target_elements=crawl.get("use_target_elements"),
        excluded_selector_extra=str(crawl.get("excluded_selector_extra") or "").strip(),
        content_filter=(crawl.get("content_filter") or None),
        prefer_raw_markdown=bool(crawl.get("prefer_raw_markdown", False)),
        delay_before_return_html=crawl.get("delay_before_return_html"),
        wait_until=(crawl.get("wait_until") or None),
        nav_labels=_norm_str_list(md_post.get("nav_labels")),
        drop_line_patterns=_norm_str_list(md_post.get("drop_line_patterns")),
        dedupe_paragraphs=bool(md_post.get("dedupe_paragraphs", False)),
        normalize_markdown=md_post.get("normalize_markdown"),
        prepend_hot_summary=md_post.get("prepend_hot_summary"),
    )


class PlatformRulesRegistry:
    def __init__(self, rules_dir: Path | None = None) -> None:
        self._dir = rules_dir or _RULES_DIR
        self._by_id: Dict[str, PlatformRule] = {}
        self._default: PlatformRule = PlatformRule(platform_id="_default")
        self._host_index: List[Tuple[str, PlatformRule]] = []
        self.reload()

    def reload(self) -> None:
        by_id: Dict[str, PlatformRule] = {}
        default = PlatformRule(platform_id="_default")
        if not self._dir.is_dir():
            logger.warning("platform_rules dir missing: %s", self._dir)
            self._by_id = by_id
            self._default = default
            self._host_index = []
            return

        for path in sorted(self._dir.glob("*.yaml")):
            stem = path.stem
            try:
                data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            except Exception as exc:
                logger.warning("skip rule file %s: %s", path.name, exc)
                continue
            rule = _parse_rule(data, stem)
            if stem == "_default" or rule.platform_id == "_default":
                default = rule
                continue
            if rule.platform_id in by_id:
                logger.warning("duplicate platform_id %s in %s", rule.platform_id, path.name)
            by_id[rule.platform_id] = rule

        host_index: List[Tuple[str, PlatformRule]] = []
        for rule in by_id.values():
            if not rule.enabled:
                continue
            for h in rule.hosts:
                host_index.append((h, rule))
        host_index.sort(key=lambda x: len(x[0]), reverse=True)

        self._by_id = by_id
        self._default = default
        self._host_index = host_index

    @property
    def default_rule(self) -> PlatformRule:
        return self._default

    def all_rules(self) -> List[PlatformRule]:
        return sorted(self._by_id.values(), key=lambda r: r.platform_id)

    def get(self, platform_id: str) -> Optional[PlatformRule]:
        if not platform_id:
            return None
        return self._by_id.get(platform_id)

    def rule_for_host(self, url: str) -> Optional[PlatformRule]:
        try:
            host = (urlparse(url).hostname or "").lower()
        except Exception:
            return None
        if not host:
            return None
        for key, rule in self._host_index:
            if host == key or host.endswith("." + key):
                return rule
        return None

    def rule_for_article(self, platform_id: str, url: str) -> PlatformRule:
        """Prefer platform_id rule; else host match; else _default."""
        if platform_id:
            rule = self.get(platform_id)
            if rule and rule.enabled:
                return rule
        host_rule = self.rule_for_host(url)
        if host_rule:
            return host_rule
        return self._default


_registry = PlatformRulesRegistry()


def get_registry() -> PlatformRulesRegistry:
    return _registry


def reload_rules() -> None:
    _registry.reload()


def list_platform_rules() -> List[PlatformRule]:
    return _registry.all_rules()


def get_rule(platform_id: str) -> Optional[PlatformRule]:
    return _registry.get(platform_id)


def rule_for_host(url: str) -> Optional[PlatformRule]:
    return _registry.rule_for_host(url)


def rule_for_article(platform_id: str, url: str) -> PlatformRule:
    return _registry.rule_for_article(platform_id, url)


def compile_drop_line_pattern(patterns: Tuple[str, ...]) -> Optional[re.Pattern[str]]:
    if not patterns:
        return None
    parts = [re.escape(p) for p in patterns if p]
    if not parts:
        return None
    return re.compile("|".join(parts), re.I | re.M)


# Backward-compatible alias for article_crawler / site_profiles consumers
SiteProfile = PlatformRule


def profile_for_url(url: str) -> Optional[PlatformRule]:
    return rule_for_host(url)


def profile_for_platform(platform_id: str, url: str) -> PlatformRule:
    return rule_for_article(platform_id, url)
