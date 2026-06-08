# coding=utf-8
"""Backward-compatible re-exports; rules live in platform_rules/*.yaml."""

from __future__ import annotations

from hot_content_bridge.platform_rules_loader import (
    PlatformRule,
    SiteProfile,
    profile_for_platform,
    profile_for_url,
    rule_for_article,
    rule_for_host,
)

__all__ = [
    "PlatformRule",
    "SiteProfile",
    "profile_for_platform",
    "profile_for_url",
    "rule_for_article",
    "rule_for_host",
]
