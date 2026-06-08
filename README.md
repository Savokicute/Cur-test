# Hot content bridge

Integrates [trendRadar](trendRadar/) (hot-list fetch + SQLite) with [crawl4ai](crawl4ai/) (Playwright + Markdown extraction).

CLI entry point: `hot-content-bridge` (after `uv sync`).

Monorepo note: an import shim ([`hot_content_bridge/_crawl4ai_path.py`](hot_content_bridge/_crawl4ai_path.py)) corrects editable `crawl4ai` resolution when the repo root folder shadows the inner package.

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md), [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md), and [docs/TEST_REPORT.md](docs/TEST_REPORT.md).

### Start the full stack (hot list + article crawl + we-mp-rss)

```bash
uv sync
uv run playwright install chromium
uv run python scripts/start_platform.py
```

This runs **`hot-content-bridge daemon`** (TrendRadar hot list every N minutes + crawl4ai article bodies) and **we-mp-rss** with scheduled jobs.
