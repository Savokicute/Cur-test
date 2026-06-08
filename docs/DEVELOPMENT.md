# Development documentation — Hot Content Bridge

## Purpose

This package connects **trendRadar** (hot-list fetch + SQLite in `output/news/{date}.db`) with **crawl4ai** (headless Chromium + Markdown extraction). It adds the `article_contents` table in the same SQLite file used by trendRadar.

## Layout

| Module | Role |
|--------|------|
| [`config.py`](../hot_content_bridge/config.py) | Loads [`config.yaml`](../hot_content_bridge/config.yaml) + trendRadar `config.yaml` for timezone and `storage.local.data_dir`. |
| [`hotlist_reader.py`](../hot_content_bridge/hotlist_reader.py) | Reads `StorageManager.get_latest_crawl_data()`, normalizes URLs, dedupes, applies `article_crawl` filters. |
| [`article_crawler.py`](../hot_content_bridge/article_crawler.py) | `AsyncWebCrawler` + `CrawlerRunConfig`（排除标签/CSS、表单/外链/社媒链接/外链图）、`BM25ContentFilter`（热榜标题作 query）或 `PruningContentFilter`、优先 `fit_markdown` + [`markdown_post.py`](../hot_content_bridge/markdown_post.py) 行级去噪。 |
| [`extraction_defaults.py`](../hot_content_bridge/extraction_defaults.py) | 默认 `excluded_tags` / `excluded_selector` / 可选 `target_elements` 列表。 |
| [`storage.py`](../hot_content_bridge/storage.py) | Ensures `article_contents` schema; `upsert_crawl_result`; skip list for successful URLs. |
| [`cli.py`](../hot_content_bridge/cli.py) | `sync-hotlist`, `crawl-articles`, `run-pipeline`, `list-platform-rules`, `serve-web`. |
| [`platform_rules/`](../hot_content_bridge/platform_rules/) | 每平台一个 YAML：爬取 CSS + Markdown 后处理规则。 |
| [`platform_rules_loader.py`](../hot_content_bridge/platform_rules_loader.py) | 加载并按 `platform_id` / URL 主机名解析规则。 |

## Monorepo / editable `crawl4ai`

If `import crawl4ai` resolves to a namespace package (no `AsyncWebCrawler`), ensure [`_crawl4ai_path.py`](../hot_content_bridge/_crawl4ai_path.py) is imported before any `crawl4ai` usage (the CLI and `article_crawler` already do this).

## trendRadar changes used by the bridge

- **`news_items.raw_extra`**: JSON text for extra API fields (heat, description, etc.). Migration runs on DB open via `SQLiteStorageMixin._migrate_news_items_raw_extra`.
- **`NewsItem.news_item_db_id`**: Populated when reading from SQLite so the bridge can link rows in `article_contents`.

## Main content extraction

- **HTML 阶段**：扩展 `excluded_tags`（`nav/header/footer/aside/form/dialog/...`）+ 宽但可覆盖常见门户的 `excluded_selector`（评论、侧栏、登录弹层、页脚等）；`remove_forms`、外链/社媒链接/外链图过滤；`word_count_threshold` 去掉极短块；`delay_before_return_html` 略等懒加载后再抽 DOM。
- **Markdown 阶段**：默认 **`BM25ContentFilter(user_query=热榜标题)`**，正文与标题语义对齐；可选 `content_filter: pruning` 走密度剪枝。
- **输出**：优先使用 crawl4ai 的 **`fit_markdown`**（内容过滤器输出）；若过短则回退 `raw_markdown`；最后 **`strip_boilerplate_markdown`** 去掉 ICP/版权/分享栏等典型单行噪声。
- **可选**：`use_target_elements: true` 时仅合并 `article`/`main`/常见正文容器（站点无这些结构时不要开）。

## 爬取全部热榜正文

```powershell
uv run hot-content-bridge fetch-hotlist-only
uv run hot-content-bridge crawl-articles --limit 0
```

确保 [`config.yaml`](../hot_content_bridge/config.yaml) 中 `article_crawl.max_urls_per_run: 0`。详见 [PLATFORM_RULES.md](PLATFORM_RULES.md)。

## Extending

- **Per-platform rules**: add or edit `hot_content_bridge/platform_rules/{platform_id}.yaml`; see [PLATFORM_RULES.md](PLATFORM_RULES.md).
- **Higher throughput**: tune `article_crawl.concurrency` and domain delays; consider running the browser pool in a separate process if Playwright stability is an issue.

## Code quality

Run tests from repo root:

```bash
uv sync --group dev
uv run pytest hot_content_bridge/tests -q
```
