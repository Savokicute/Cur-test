# coding=utf-8
"""Post-process extracted Markdown: drop nav/footer/license noise; keep article images."""

from __future__ import annotations

import re
from typing import List, Optional, Set

from hot_content_bridge.platform_rules_loader import get_rule

# Line-level noise (Chinese portals + generic junk)
_BOILERPLATE_LINE = re.compile(
    r"(互联网新闻信息服务许可证|增值电信业务|经营许可证[:：]?|"
    r"报业有限公司|东方报业|"
    r"ICP备|ICP证|京ICP|沪ICP|粤ICP|苏ICP|浙ICP|"
    r"网安备|网信|违法和不良信息|举报邮箱|"
    r"Copyright\s*\(?[cC]|^版权所有\s*$|^免责声明\s*$|^隐私政策\s*$|^用户协议\s*$|"
    r"Cookie\s*政策|扫码关注|微信扫一扫|"
    r"更多精彩|^相关阅读|^推荐阅读|^热评|^评论区|^发表评论|"
    r"^上一篇|^下一篇|^返回首页|^网站地图|^关于我们|^联系我们|"
    r"^订阅\s*$|^推送\s*$|下载客户端|打开APP|"
    r"^\s*分享到\s*$|^\s*点赞\s*\(\d+\)|^\s*收藏\s*$|^反馈\s*$|无障碍)",
    re.I | re.M,
)

# Markdown list nav: * _要闻_  /  - _深度_  /  * 直播
_NAV_BULLET = re.compile(
    r"^\s*[\*\-\+]\s+(_([^_\n]{1,20})_|([^_\n\*]{1,20}))\s*$"
)

# Standalone short nav labels (no bullet)
_NAV_PLAIN = re.compile(
    r"^(_)?(要闻|深度|直播|视频|时事|更多|首页|财经|体育|科技|思想|生活|问吧|澎湃|24小时|World|China)(_)?$"
)

# Image-only line
_IMG_LINE = re.compile(r"^!\[([^\]]*)\]\(([^)]+)\)\s*$")

# Decorative / chrome images (drop line only, not inline)
_DECOR_IMG_URL = re.compile(
    r"(wuzhangai|无障碍|logo|icon|avatar|qrcode|qrcode|sprite|/ads/|/ad/|"
    r"placeholder|blank\.gif|1x1|spacer|favicon)",
    re.I,
)

_JUNK_SHORT = re.compile(r"^[\s\-_|·•◆◇►▶\d\.]{0,12}$")

# © footer lines
_COPYRIGHT_LINE = re.compile(r"^©\s*\d{4}", re.I)

# 财联社/媒体导语、要点 bullets — 勿因含媒体名被 drop_line_patterns 误删
_ARTICLE_LEAD = re.compile(r"讯[（(].*[)）]|^[①②③④⑤⑥⑦⑧⑨⑩]")
_BULLET_PREFIX = re.compile(r"^[①②③④⑤⑥⑦⑧⑨⑩]")


def _nav_label_from_bullet(line: str) -> str:
    m = _NAV_BULLET.match(line.strip())
    if not m:
        return ""
    inner = (m.group(2) or m.group(3) or "").strip()
    return inner


def _extra_nav_labels(platform_id: Optional[str]) -> Set[str]:
    if not platform_id:
        return set()
    rule = get_rule(platform_id)
    if not rule:
        return set()
    return set(rule.nav_labels)


def _extra_drop_re(platform_id: Optional[str]):
    if not platform_id:
        return None
    rule = get_rule(platform_id)
    if not rule or not rule.drop_line_patterns:
        return None
    from hot_content_bridge.platform_rules_loader import compile_drop_line_pattern

    return compile_drop_line_pattern(rule.drop_line_patterns)


def _is_nav_line(s: str, extra_labels: Optional[Set[str]] = None) -> bool:
    t = s.strip()
    if not t:
        return False
    if extra_labels:
        inner = _nav_label_from_bullet(t)
        bare = t.strip("_")
        if bare in extra_labels or (inner and inner in extra_labels):
            return True
    if _NAV_PLAIN.match(t):
        return True
    label = _nav_label_from_bullet(t)
    if label and len(label) <= 8:
        return True
    return False


def _should_drop_line_pattern(line: str, extra_drop: Optional[re.Pattern[str]]) -> bool:
    """Platform drop_line_patterns: only remove footer/chrome, keep article leads."""
    if extra_drop is None:
        return False
    s = line.strip()
    if not s or len(s) > 400:
        return False
    if not extra_drop.search(s):
        return False
    if _ARTICLE_LEAD.search(s) or _BULLET_PREFIX.search(s):
        return False
    if len(s) >= 28 and ("讯（" in s or "讯(" in s):
        return False
    # 长段落多为正文，仅含品牌名不删
    if len(s) > 160:
        return False
    return True


def _is_decorative_image(url: str, alt: str) -> bool:
    if _DECOR_IMG_URL.search(url):
        return True
    if alt and _DECOR_IMG_URL.search(alt):
        return True
    return False


def strip_boilerplate_markdown(text: str, platform_id: Optional[str] = None) -> str:
    """
    Remove nav bullets, licenses, chrome images, and footer lines.
    Keeps substantive paragraphs and article images.

    platform_id: load extra nav_labels / drop_line_patterns from platform_rules/{id}.yaml
    """
    if not text or not text.strip():
        return text

    extra_nav = _extra_nav_labels(platform_id)
    extra_drop = _extra_drop_re(platform_id)

    lines: List[str] = text.splitlines()
    out: List[str] = []

    # Drop leading runs of nav bullets (site chrome before article)
    start = 0
    while start < len(lines):
        s = lines[start].strip()
        if not s:
            start += 1
            continue
        if _is_nav_line(s, extra_nav):
            start += 1
            continue
        break

    for line in lines[start:]:
        s = line.strip()
        if not s:
            out.append("")
            continue
        if _is_nav_line(s, extra_nav):
            continue
        if _COPYRIGHT_LINE.match(s):
            continue
        if _should_drop_line_pattern(s, extra_drop):
            continue
        if len(s) <= 200 and _BOILERPLATE_LINE.search(s):
            continue
        img_m = _IMG_LINE.match(s)
        if img_m:
            alt, url = img_m.group(1), img_m.group(2)
            if _is_decorative_image(url, alt):
                continue
            out.append(line)
            continue
        if len(s) <= 12 and _JUNK_SHORT.match(s):
            continue
        out.append(line)

    collapsed: List[str] = []
    blank_run = 0
    for line in out:
        if not line.strip():
            blank_run += 1
            if blank_run <= 2:
                collapsed.append("")
        else:
            blank_run = 0
            collapsed.append(line)

    return "\n".join(collapsed).strip()
