# coding=utf-8
"""HTML viewer for latest hot-list + article_contents (stdlib + markdown render)."""

from __future__ import annotations

import html
import sqlite3
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List, Optional, Tuple

from hot_content_bridge.config import BridgeConfig
from hot_content_bridge.article_markdown import finalize_article_markdown
from hot_content_bridge.markdown_render import markdown_to_html
from hot_content_bridge.storage import _news_db_path, ensure_article_tables

_ARTICLE_CSS = """
    .article-wrap { max-width: 820px; margin: 0 auto; }
    .article-body { line-height: 1.75; font-size: 1.05rem; }
    .article-body h1, .article-body h2, .article-body h3 { margin: 1.2em 0 0.6em; line-height: 1.35; }
    .article-body p { margin: 0.75em 0; }
    .article-body img, .article-body figure img {
      max-width: 100%; height: auto; display: block; margin: 1rem auto;
      border-radius: 6px; background: #0d1117;
    }
    .article-body figure { margin: 1rem 0; }
    .article-body ul, .article-body ol { padding-left: 1.4em; }
    .article-body blockquote {
      border-left: 3px solid #30363d; margin: 1em 0; padding-left: 1em; color: #8b949e;
    }
    .article-body a { color: #58a6ff; word-break: break-all; }
    .article-body pre { display: none; }
"""


def _connect(cfg: BridgeConfig) -> sqlite3.Connection:
    path = _news_db_path(cfg)
    if not path.exists():
        raise FileNotFoundError(f"数据库不存在: {path}（请先运行热榜同步）")
    ensure_article_tables(cfg)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


def fetch_latest_rows(cfg: BridgeConfig) -> Tuple[Optional[str], List[Dict[str, Any]]]:
    """Return (latest_crawl_time, rows) for the most recent hot-list batch."""
    conn = _connect(cfg)
    try:
        cur = conn.cursor()
        cur.execute("SELECT crawl_time FROM crawl_records ORDER BY crawl_time DESC LIMIT 1")
        row = cur.fetchone()
        if not row:
            return None, []
        latest_t = row[0]
        cur.execute(
            """
            SELECT n.id AS news_id, n.title, n.platform_id,
                   COALESCE(p.name, n.platform_id) AS platform_name,
                   n.rank, n.url AS url_norm,
                   a.status AS article_status, a.fetched_at, a.error,
                   CASE WHEN a.markdown IS NOT NULL AND a.markdown != ''
                        THEN length(a.markdown) ELSE 0 END AS md_chars
            FROM news_items n
            LEFT JOIN platforms p ON n.platform_id = p.id
            LEFT JOIN article_contents a ON a.url_norm = n.url
            WHERE n.last_crawl_time = ?
            ORDER BY n.platform_id, n.rank
            """,
            (latest_t,),
        )
        rows = [dict(r) for r in cur.fetchall()]
        return latest_t, rows
    finally:
        conn.close()


def fetch_article(cfg: BridgeConfig, url_norm: str) -> Optional[Dict[str, Any]]:
    conn = _connect(cfg)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT url_norm, platform_id, title_snapshot, status, http_status,
                   markdown, extracted_title, error, fetched_at
            FROM article_contents
            WHERE url_norm = ?
            """,
            (url_norm,),
        )
        r = cur.fetchone()
        return dict(r) if r else None
    finally:
        conn.close()


def _page_shell(title: str, body: str, extra_css: str = "") -> bytes:
    doc = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>{html.escape(title)}</title>
  <style>
    body {{ font-family: system-ui, "Segoe UI", "PingFang SC", sans-serif; margin: 1rem 1.5rem;
           background: #0f1419; color: #e6edf3; }}
    a {{ color: #58a6ff; }}
    table {{ border-collapse: collapse; width: 100%; max-width: 1200px; }}
    th, td {{ border: 1px solid #30363d; padding: 0.45rem 0.6rem; text-align: left; vertical-align: top; }}
    th {{ background: #161b22; }}
    tr:nth-child(even) {{ background: #11161d; }}
    .muted {{ color: #8b949e; font-size: 0.9rem; }}
    .badge {{ display: inline-block; padding: 0.15rem 0.45rem; border-radius: 4px; font-size: 0.8rem; }}
    .ok {{ background: #238636; color: #fff; }}
    .fail {{ background: #da3633; color: #fff; }}
    .pending {{ background: #6e7681; color: #fff; }}
    {extra_css}
  </style>
</head>
<body>
{body}
</body>
</html>"""
    return doc.encode("utf-8")


def make_handler(cfg: BridgeConfig):
    class H(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args) -> None:
            print("[web]", self.address_string(), fmt % args)

        def do_GET(self) -> None:
            path = self.path.split("?", 1)[0]
            if path in ("/", "/index"):
                self._index()
                return
            if path == "/article":
                qs = urllib.parse.urlparse(self.path).query
                q = urllib.parse.parse_qs(qs)
                u = (q.get("u") or [""])[0]
                if not u:
                    self._send(400, _page_shell("错误", "<p>缺少参数 <code>u</code>（url_norm）</p>"))
                    return
                url_norm = urllib.parse.unquote(u)
                self._article(url_norm)
                return
            self._send(404, _page_shell("404", "<p>未找到页面</p>"))

        def _send(self, code: int, body: bytes, ctype: str = "text/html; charset=utf-8") -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _index(self) -> None:
            try:
                latest_t, rows = fetch_latest_rows(cfg)
            except FileNotFoundError as e:
                self._send(200, _page_shell("热榜正文", f"<p class='muted'>{html.escape(str(e))}</p>"))
                return
            if not latest_t:
                body = "<p class='muted'>暂无抓取记录。</p>"
            else:
                lines = [
                    f"<p class='muted'>最新批次时间：<strong>{html.escape(latest_t)}</strong>，共 {len(rows)} 条</p>",
                    "<table><thead><tr><th>#</th><th>平台</th><th>标题</th><th>正文</th></tr></thead><tbody>",
                ]
                for r in rows:
                    st = r.get("article_status") or ""
                    md_c = int(r.get("md_chars") or 0)
                    if st == "success" and md_c > 0:
                        badge = f"<span class='badge ok'>已抓 {md_c} 字</span>"
                        uq = urllib.parse.quote(r["url_norm"], safe="")
                        link = f'<a href="/article?u={uq}">阅读正文</a>'
                    elif st == "failed":
                        err = html.escape((r.get("error") or "")[:120])
                        badge = f"<span class='badge fail'>失败</span> <span class='muted'>{err}</span>"
                        link = "—"
                    else:
                        badge = "<span class='badge pending'>未抓</span>"
                        link = "—"
                    title = html.escape(r.get("title") or "")
                    plat = html.escape(r.get("platform_name") or r.get("platform_id") or "")
                    rank = int(r.get("rank") or 0)
                    url = html.escape(r.get("url_norm") or "")
                    lines.append(
                        f"<tr><td>{rank}</td><td>{plat}</td><td>{title}<br/>"
                        f"<span class='muted'><a href='{url}' target='_blank' rel='noopener'>{url}</a></span></td>"
                        f"<td>{badge}<br/>{link}</td></tr>"
                    )
                lines.append("</tbody></table>")
                body = "\n".join(lines)
            self._send(200, _page_shell("热榜 + 正文状态", f"<h1>热榜与正文</h1>\n{body}"))

        def _article(self, url_norm: str) -> None:
            row = fetch_article(cfg, url_norm)
            if not row:
                self._send(
                    404,
                    _page_shell(
                        "未找到",
                        f"<p>尚无该 URL 的正文记录。</p><p><a href='/'>返回列表</a></p>",
                    ),
                )
                return
            title = html.escape(row.get("title_snapshot") or row.get("extracted_title") or "正文")
            st = row.get("status") or ""
            md = row.get("markdown") or ""
            err = row.get("error") or ""
            src = html.escape(url_norm)
            meta = (
                f"<p class='muted'>状态: {html.escape(st)} | HTTP {row.get('http_status')} | "
                f"{html.escape(row.get('fetched_at') or '')} | "
                f"<a href='{src}' target='_blank' rel='noopener'>原文链接</a></p>"
            )
            if st == "success" and md:
                md = finalize_article_markdown(
                    md,
                    platform_id=row.get("platform_id") or None,
                    title=row.get("title_snapshot") or row.get("extracted_title") or "",
                )
                body_html = markdown_to_html(md)
                content = (
                    f"<div class='article-wrap'>"
                    f"<h1>{title}</h1>{meta}"
                    f"<article class='article-body'>{body_html}</article>"
                    f"</div>"
                )
            else:
                content = f"<h1>{title}</h1>{meta}<p class='muted'>{html.escape(err)}</p>"
            content += "<p style='margin-top:2rem'><a href='/'>← 返回列表</a></p>"
            self._send(200, _page_shell(title, content, extra_css=_ARTICLE_CSS))

    return H


def run_server(cfg: BridgeConfig, host: str, port: int) -> None:
    H = make_handler(cfg)
    httpd = ThreadingHTTPServer((host, port), H)
    print(f"Web 展示: http://{host}:{port}/  （Ctrl+C 停止）", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("停止服务")
    finally:
        httpd.server_close()
