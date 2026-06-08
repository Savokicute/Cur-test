# coding=utf-8
"""Extract hot-list summary / lead text from NewsNow API raw_extra fields."""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, Optional

# NewsNow / 各源常见字段（按优先级）
_SUMMARY_KEYS: tuple[str, ...] = (
    "desc",
    "description",
    "summary",
    "intro",
    "digest",
    "brief",
    "subtitle",
    "subTitle",
    "abstract",
    "lead",
    "content",
    "detail",
    "text",
    "remark",
    "tag",
)

_NOISE_VALUE = re.compile(
    r"^(true|false|null|none|\d+(\.\d+)?%?)$",
    re.I,
)


def _clean_text(val: Any) -> str:
    if val is None:
        return ""
    if isinstance(val, (int, float)):
        return str(val).strip()
    if isinstance(val, str):
        s = val.strip()
    elif isinstance(val, dict):
        for k in ("text", "content", "desc", "summary", "title"):
            inner = _clean_text(val.get(k))
            if inner:
                return inner
        return ""
    elif isinstance(val, (list, tuple)):
        parts = [_clean_text(x) for x in val]
        parts = [p for p in parts if p]
        return "；".join(parts[:3])
    else:
        s = str(val).strip()
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    if _NOISE_VALUE.match(s):
        return ""
    return s


def _iter_extra_values(extra: Dict[str, Any]) -> Iterable[tuple[str, str]]:
    for key, val in extra.items():
        text = _clean_text(val)
        if not text or len(text) < 4:
            continue
        yield str(key).lower(), text


def extract_hot_summary(
    raw_extra: Optional[Dict[str, Any]],
    title: str = "",
) -> str:
    """
  Pick the best summary-like string from API extra fields.
  Skips values that duplicate the title or look like pure heat metrics.
  """
    if not raw_extra:
        return ""
    title_n = re.sub(r"\s+", " ", (title or "").strip())
    candidates: list[tuple[int, int, str]] = []

    for key, text in _iter_extra_values(raw_extra):
        if title_n and text == title_n:
            continue
        if title_n and len(title_n) >= 6 and title_n in text and len(text) < len(title_n) + 8:
            continue
        # 纯数字热度
        if re.fullmatch(r"[\d.,]+[万亿kKwW]?", text):
            continue
        priority = _SUMMARY_KEYS.index(key) if key in _SUMMARY_KEYS else 100
        candidates.append((priority, -len(text), text))

    if not candidates:
        return ""

    candidates.sort(key=lambda x: (x[0], x[1]))
    best = candidates[0][2]
    # 过长字段多为正文而非摘要
    if len(best) > 600:
        best = best[:600].rstrip() + "…"
    return best
