# coding=utf-8
"""Normalize Markdown structure and remove duplicate paragraphs."""

from __future__ import annotations

import re
from typing import List, Optional

_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_LIST_BULLET = re.compile(r"^(\s*)([\*\-\+]|\d+\.)\s+")
_IMG = re.compile(r"^!\[([^\]]*)\]\(([^)]+)\)\s*$")
_LINK_ONLY = re.compile(r"^\[([^\]]+)\]\(([^)]+)\)\s*$")
_MULTI_BLANK = re.compile(r"\n{3,}")


def _norm_compare(text: str) -> str:
    t = re.sub(r"^#{1,6}\s+", "", text.strip())
    t = re.sub(r"[*_`]", "", t)
    t = re.sub(r"\s+", " ", t)
    return t.strip().lower()


def _is_duplicate_block(block: str, seen: List[str]) -> bool:
    n = _norm_compare(block)
    if not n or len(n) < 16:
        return False
    for prev in seen:
        if n == prev:
            return True
        if len(n) >= 40 and len(prev) >= 40:
            if n in prev or prev in n:
                return True
            # 高重叠：前 80 字相同
            if n[:80] == prev[:80]:
                return True
    return False


def dedupe_paragraphs(text: str) -> str:
    """Remove repeated paragraphs/blocks (e.g. nested DOM merged twice)."""
    if not text or not text.strip():
        return text

    blocks = re.split(r"\n\s*\n", text.strip())
    seen: List[str] = []
    out: List[str] = []

    for block in blocks:
        b = block.strip()
        if not b:
            continue
        if _is_duplicate_block(b, seen):
            continue
        n = _norm_compare(b)
        if len(n) >= 16:
            seen.append(n)
        out.append(b)

    # 连续完全相同行（华尔街见闻等）
    lines: List[str] = []
    prev_line_norm = ""
    for block in out:
        for line in block.splitlines():
            ln = _norm_compare(line)
            if ln and len(ln) >= 24 and ln == prev_line_norm:
                continue
            lines.append(line.rstrip())
            prev_line_norm = ln if len(ln) >= 24 else prev_line_norm
        lines.append("")

    while lines and not lines[-1].strip():
        lines.pop()

    return "\n".join(lines).strip()


def prepend_hot_summary(markdown: str, summary: str, title: str = "") -> str:
    """Prepend hot-list summary as blockquote when not already in body."""
    md = (markdown or "").strip()
    s = (summary or "").strip()
    if not s or len(s) < 6:
        return md
    title_n = re.sub(r"\s+", " ", (title or "").strip())
    if title_n and s == title_n:
        return md
    probe = md[: min(len(md), max(len(s) * 2, 500))]
    if s in probe or (len(s) >= 20 and s[:20] in probe):
        return md
    lead = f"> **摘要**：{s}\n\n---\n\n"
    return lead + md


def normalize_markdown(text: str, title: Optional[str] = None) -> str:
    """
    Standardize headings, paragraph breaks, lists, and images.
    """
    if not text or not text.strip():
        return text

    lines = text.replace("\r\n", "\n").split("\n")
    out: List[str] = []
    in_code = False
    first_heading_done = False
    code_buf: List[str] = []

    def _flush_code_buf() -> None:
        nonlocal code_buf
        if not code_buf:
            return
        body = "\n".join(l.strip() for l in code_buf if l.strip())
        code_buf = []
        if not body:
            return
        if out and out[-1] != "":
            out.append("")
        if re.search(r"^[①②③④⑤⑥⑦⑧⑨⑩]", body, re.M):
            for part in re.split(r"(?<=[；;])\s*", body):
                part = part.strip()
                if part:
                    out.append(f"- {part}")
        else:
            out.append(body)
        out.append("")

    for raw in lines:
        line = raw.rstrip()
        if line.strip().startswith("```"):
            if in_code:
                in_code = False
                _flush_code_buf()
            else:
                if out and out[-1] != "":
                    out.append("")
                in_code = True
            continue
        if in_code:
            code_buf.append(line)
            continue

        stripped = line.strip()
        if not stripped:
            if out and out[-1] != "":
                out.append("")
            continue

        hm = _HEADING.match(stripped)
        if hm:
            level = len(hm.group(1))
            body = hm.group(2).strip()
            if not first_heading_done and title:
                t_norm = re.sub(r"\s+", " ", title.strip())
                if body == t_norm or t_norm in body:
                    level = 1
                first_heading_done = True
            if level > 4:
                level = 4
            if out and out[-1] != "":
                out.append("")
            out.append("#" * level + " " + body)
            continue

        im = _IMG.match(stripped)
        if im:
            alt, url = im.group(1).strip() or "配图", im.group(2).strip()
            if out and out[-1] != "":
                out.append("")
            out.append(f"![{alt}]({url})")
            out.append("")
            continue

        lm = _LINK_ONLY.match(stripped)
        if lm and len(lm.group(1)) > 4:
            if out and out[-1] != "":
                out.append("")
            out.append(stripped)
            continue

        if _LIST_BULLET.match(line):
            if out and out[-1] != "" and not _LIST_BULLET.match(out[-1]):
                out.append("")
            out.append(line)
            continue

        # 普通段落：与上一行合并为同段（爬虫常输出硬换行）
        if (
            out
            and out[-1] != ""
            and not _HEADING.match(out[-1])
            and not _LIST_BULLET.match(out[-1])
            and not _IMG.match(out[-1])
            and not stripped.startswith(">")
            and not out[-1].startswith(">")
            and len(stripped) > 0
            and not stripped.endswith(("。", "！", "？", "；", "：", ".", "!", "?"))
            and len(out[-1]) < 200
        ):
            out[-1] = out[-1] + stripped
        else:
            if out and out[-1] != "" and not _LIST_BULLET.match(out[-1]):
                out.append("")
            out.append(stripped)

    result = "\n".join(out).strip()
    result = _MULTI_BLANK.sub("\n\n", result)
    return result
