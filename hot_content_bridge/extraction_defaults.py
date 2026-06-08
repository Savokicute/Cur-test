# coding=utf-8
"""Default HTML exclusions for main-body extraction (lxml/cssselect)."""

# Remove structural chrome before markdown conversion
DEFAULT_EXCLUDED_TAGS: tuple[str, ...] = (
    "nav",
    "header",
    "footer",
    "aside",
    "form",
    "iframe",
    "noscript",
    "dialog",
    "menu",
    "template",
    "address",
)

# Extra subtree removals (common CN/news portals + comments + modals)
DEFAULT_EXCLUDED_SELECTOR: str = (
    "[role='navigation'],[role='banner'],[role='contentinfo'],[role='complementary'],[role='dialog'],"
    "[class*='comment'],[id*='comment'],[class*='Comment'],[id*='Comment'],"
    "[class*='reply'],[id*='reply'],[class*='sidebar'],[id*='sidebar'],"
    "[class*='side-bar'],[id*='side-bar'],[class*='related-news'],[class*='recommend'],"
    "[class*='login'],[id*='login'],[class*='popup'],[id*='popup'],[class*='modal'],[id*='modal'],"
    "[class*='footer'],[id*='footer'],[class*='toolbar'],[id*='toolbar'],"
    "[class*='download-app'],[id*='download-app'],[class*='qrcode'],[id*='qrcode'],"
    "[class*='wuzhangai'],[class*='accessibility'],[class*='channel-nav'],[class*='top-nav']"
)

# If page has one of these, markdown is built only from their union (empty → fallback in caller)
DEFAULT_TARGET_ELEMENTS: tuple[str, ...] = (
    "article",
    "main",
    "[role='main']",
    ".article-content",
    ".article__content",
    ".article-body",
    ".post-content",
    "#artibody",
    ".TRS_Editor",
    ".content_main",
    ".main-content",
    ".index_cententWrap",
    ".newscontent",
    ".news_txt",
)
