# Test report — Hot Content Bridge

**Date:** 2026-05-15  
**Scope:** Unit tests for storage deduplication / filtering and hot-list reader dedupe (mocked storage).

## Environment

- OS: Windows  
- Python: 3.13 (uv-managed `.venv` in repo root)  
- Command: `python -m pytest hot_content_bridge/tests -q`

## Results

| Suite | Tests | Passed | Failed |
|-------|-------|--------|--------|
| `hot_content_bridge/tests/test_storage_and_reader.py` | 3 | 3 | 0 |

### Cases

1. **`test_content_sha256_stable`** — SHA-256 length sanity for stored content fingerprints.
2. **`test_filter_pending_respects_success`** — Creates a temporary `output/news/{today}.db`, inserts a successful `article_contents` row, verifies URLs already marked success are skipped on the next crawl batch.
3. **`test_load_pending_dedupe`** — Mocks `get_storage_manager().get_latest_crawl_data()` with two items sharing the same URL; asserts a single `PendingArticle` and stable `news_item_db_id` from the first item.

## Not covered (manual / future)

- **End-to-end Playwright crawl** against live sites (flaky in CI); run locally with `crawl-articles` after `sync-hotlist` on a machine with browsers installed.
- **Load / stress** — tune `concurrency` and measure CPU/RAM with real batches; record numbers here when available.

## Known limitations

- `sync-hotlist` invokes `python -m trendradar` with cwd set to `trendradar.root`; ensure that directory contains a valid `trendRadar` install and config.
- Remote-only trendRadar storage backends are not targeted; the bridge expects **local** SQLite paths resolved from trendRadar config.
