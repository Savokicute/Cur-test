# coding=utf-8
from hot_content_bridge.markdown_post import strip_boilerplate_markdown


def test_strip_thepaper_nav_bullets():
    text = """* _要闻_
* _深度_
* _直播_
* _视频_
* _时事_
* _更多_

这是正文第一段，应保留。

第二段内容。
"""
    out = strip_boilerplate_markdown(text, platform_id="thepaper")
    assert "要闻" not in out or "这是正文" in out
    assert "这是正文第一段" in out
    assert "第二段" in out
    assert "* _深度_" not in out


def test_strip_icp_and_footer():
    text = """# 标题

正文段落一。

互联网新闻信息服务许可证：31120170006
增值电信业务经营许可证：沪B2-2017116
© 2014-2026 上海东方报业有限公司
![](https://www.thepaper.cn/_next/static/media/wuzhangai.a66118af.png)
反馈
"""
    out = strip_boilerplate_markdown(text)
    assert "正文段落" in out
    assert "互联网新闻" not in out
    assert "增值电信" not in out
    assert "东方报业" not in out
    assert "wuzhangai" not in out
    assert "反馈" not in out or out.strip().endswith("反馈") is False


def test_keeps_article_image():
    md = "正文\n\n![配图](https://img.thepaper.cn/article/photo.jpg)\n\n结尾"
    out = strip_boilerplate_markdown(md)
    assert "photo.jpg" in out
    assert "正文" in out
