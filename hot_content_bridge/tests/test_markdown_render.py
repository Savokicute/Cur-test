# coding=utf-8
from hot_content_bridge.markdown_render import markdown_to_html


def test_renders_image_tag():
    html_out = markdown_to_html("![图](https://example.com/a.jpg)\n\n段落文字。")
    assert "<img" in html_out
    assert "a.jpg" in html_out
    assert "段落" in html_out
