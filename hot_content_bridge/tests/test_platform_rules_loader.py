# coding=utf-8
from hot_content_bridge.markdown_post import strip_boilerplate_markdown
from hot_content_bridge.platform_rules_loader import (
    get_registry,
    rule_for_article,
)


def test_registry_loads_thepaper():
    reg = get_registry()
    rule = reg.get("thepaper")
    assert rule is not None
    assert rule.enabled
    assert "thepaper.cn" in rule.hosts
    assert rule.primary_target
    assert rule.content_filter == "none"
    assert "要闻" in rule.nav_labels


def test_wallstreetcn_dedupe_flag():
    rule = get_registry().get("wallstreetcn-hot")
    assert rule is not None
    assert rule.dedupe_paragraphs
    assert rule.primary_target == ".article__content"


def test_rule_for_article_prefers_platform_id():
    rule = rule_for_article("thepaper", "https://example.com/other")
    assert rule.platform_id == "thepaper"


def test_strip_with_platform_id():
    text = """* _要闻_
* _深度_

正文保留。
"""
    out = strip_boilerplate_markdown(text, platform_id="thepaper")
    assert "正文保留" in out
    assert "* _深度_" not in out
