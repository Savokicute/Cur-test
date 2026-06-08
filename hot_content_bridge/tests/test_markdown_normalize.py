# coding=utf-8
from hot_content_bridge.hot_summary import extract_hot_summary
from hot_content_bridge.markdown_normalize import (
    dedupe_paragraphs,
    normalize_markdown,
    prepend_hot_summary,
)


def test_dedupe_repeated_paragraph():
    text = """第一段正文内容比较长，用于测试去重逻辑是否生效。

第一段正文内容比较长，用于测试去重逻辑是否生效。

第二段不同内容。
"""
    out = dedupe_paragraphs(text)
    assert out.count("第一段正文") == 1
    assert "第二段不同" in out


def test_normalize_heading_and_image():
    raw = """标题行

![ ](https://img.example.com/a.jpg)
段落一
硬换行续写
"""
    out = normalize_markdown(raw, title="标题行")
    assert "![配图]" in out or "![ ]" in out
    assert "\n\n" in out


def test_prepend_hot_summary():
    md = "正文开始。"
    out = prepend_hot_summary(md, "这是热搜摘要文字。", title="标题")
    assert "摘要" in out
    assert "这是热搜摘要" in out
    assert "正文开始" in out


def test_prepend_skips_if_already_present():
    md = "这是热搜摘要文字。正文。"
    out = prepend_hot_summary(md, "这是热搜摘要文字。", title="")
    assert out == md


def test_extract_hot_summary_from_raw_extra():
    extra = {"desc": "央行宣布降准0.5个百分点", "heat": "125万"}
    s = extract_hot_summary(extra, title="央行降准")
    assert "降准" in s
    assert "125万" not in s
