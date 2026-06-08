# coding=utf-8
"""Render stored Markdown as safe HTML for the web viewer."""

from __future__ import annotations

import html
import re
from functools import lru_cache

_IMG_MD = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")


def _fallback_markdown_to_html(md: str) -> str:
    """Minimal renderer when the `markdown` package is unavailable."""
    blocks: list[str] = []
    para: list[str] = []
    for line in md.splitlines():
        s = line.strip()
        if not s:
            if para:
                blocks.append("<p>" + "<br/>".join(html.escape(x) for x in para) + "</p>")
                para = []
            continue
        if s.startswith("### "):
            if para:
                blocks.append("<p>" + "<br/>".join(html.escape(x) for x in para) + "</p>")
                para = []
            blocks.append(f"<h3>{html.escape(s[4:])}</h3>")
            continue
        if s.startswith("## "):
            if para:
                blocks.append("<p>" + "<br/>".join(html.escape(x) for x in para) + "</p>")
                para = []
            blocks.append(f"<h2>{html.escape(s[3:])}</h2>")
            continue
        if s.startswith("# "):
            if para:
                blocks.append("<p>" + "<br/>".join(html.escape(x) for x in para) + "</p>")
                para = []
            blocks.append(f"<h1>{html.escape(s[2:])}</h1>")
            continue
        img = _IMG_MD.fullmatch(s)
        if img:
            if para:
                blocks.append("<p>" + "<br/>".join(html.escape(x) for x in para) + "</p>")
                para = []
            alt, url = img.group(1), img.group(2)
            blocks.append(
                f'<figure class="article-figure">'
                f'<img src="{html.escape(url, quote=True)}" alt="{html.escape(alt)}" loading="lazy"/>'
                f"</figure>"
            )
            continue
        para.append(line.rstrip())
    if para:
        blocks.append("<p>" + "<br/>".join(html.escape(x) for x in para) + "</p>")
    return "\n".join(blocks)


@lru_cache(maxsize=1)
def _markdown_lib():
    try:
        import markdown  # type: ignore

        return markdown
    except ImportError:
        return None


def markdown_to_html(md: str) -> str:
    if not md or not md.strip():
        return "<p class='muted'>（无正文内容）</p>"
    lib = _markdown_lib()
    if lib is None:
        return _fallback_markdown_to_html(md)
    return lib.markdown(
        md,
        extensions=["extra", "nl2br", "sane_lists"],
        output_format="html5",
    )
