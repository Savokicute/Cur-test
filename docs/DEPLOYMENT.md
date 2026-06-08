# Deployment guide — Hot Content Bridge

> **Canonical spec**: PRD v9.4 §4.6（项目环境与依赖规范）。本文档为运维摘要；冲突时以 PRD 为准。

## Prerequisites

- **Python 3.12+** (repo lockfile may use 3.13; 3.12 is the minimum declared by trendRadar).
  - 版本标识: `.python-version` (用于 pyenv 等工具)
- **uv** (required for this monorepo; do not use a separate `web/backend` pip venv).
- **Node.js 20 LTS** (for `web/frontend` only; use `npm ci`).
  - 版本标识: `.nvmrc` (用于 nvm 等工具)
- **Playwright browsers** after install:

```bash
uv sync --group dev
uv run playwright install chromium
uv run python scripts/verify_environment.py   # 环境自检,验证所有配置
```

## Install

```bash
uv sync --group dev
# Production / CI: uv sync --frozen --no-dev
```

### 依赖冻结流程

**开发环境添加新依赖:**
```bash
# 添加生产依赖
uv add <package-name>

# 添加开发依赖
uv add --group dev <package-name>

# 提交更新后的 uv.lock
git add uv.lock
git commit -m "Update dependencies"
```

**冻结依赖用于生产/CI:**
```bash
# 使用 --frozen 确保依赖版本与 uv.lock 完全一致
uv sync --frozen --group dev  # 开发环境
uv sync --frozen --no-dev      # 生产环境
```

**注意事项:**
- 全仓仅使用根目录的 `uv sync`,禁止 `web/backend` 独立 venv
- `trendRadar` 和 `crawl4ai` 作为 editable 包安装,修改后直接生效
- 提交代码时必须同时提交 `uv.lock` 的变更

Editable packages: `trendRadar/`, `crawl4ai/`, and the root `hot-content-bridge` meta-package.

## Configuration

1. **trendRadar** — configure platforms and schedules under [`trendRadar/config/config.yaml`](../trendRadar/config/config.yaml) as usual (`storage.local.data_dir` defaults to `output` under the trendRadar project root).

2. **Bridge** — edit [`hot_content_bridge/config.yaml`](../hot_content_bridge/config.yaml):
   - `trendradar.root`: path to the `trendRadar` folder (default `trendRadar`).
   - `trendradar.config_yaml`: path to trendRadar’s main config (used for timezone + `data_dir`).
   - `article_crawl.*`: limits, concurrency, delays, `skip_domains`, `recrawl_success`.

Override config paths:

```bash
uv run hot-content-bridge --config path\to\bridge.yaml crawl-articles
uv run hot-content-bridge --trendradar-config path\to\config.yaml crawl-articles
```

## Operations

- **Fetch hot list only** (runs trendRadar main module; working directory = trendRadar root):

  ```bash
  uv run hot-content-bridge sync-hotlist
  ```

- **Crawl article bodies** for URLs in the **latest** hot-list batch (skips URLs that already have `status=success` unless `recrawl_success: true`):

  ```bash
  uv run hot-content-bridge crawl-articles
  ```

- **仅热榜入库（推荐日常流水线，跳过完整 `trendRadar` 主程序与 AI）**：

  ```bash
  uv run hot-content-bridge fetch-hotlist-only
  ```

- **完整 trendRadar 一次运行**（含调度、AI 筛选、报告等，可能较慢）：

  ```bash
  uv run hot-content-bridge sync-hotlist
  ```

- **Pipeline** (hot list then articles):

  ```bash
  uv run hot-content-bridge run-pipeline --quick-hotlist --limit 10
  uv run hot-content-bridge run-pipeline --skip-hotlist   # only crawl step
  uv run hot-content-bridge run-pipeline                    # 完整 trendRadar + 正文
  ```

- **Web 展示**（最新一批热榜 + 正文抓取状态，默认 <http://127.0.0.1:8765/>）：

  ```bash
  uv run hot-content-bridge serve-web
  uv run hot-content-bridge serve-web --host 0.0.0.0 --port 8080
  ```

## Real-time pipeline (recommended)

TrendRadar’s full CLI (`python -m trendradar`) uses **schedule/timeline** and may **skip** hot-list collection outside configured windows. For always-fresh data, use the bridge daemon ( **`fetch-hotlist-only`** + automatic article crawl):

```bash
# One command: hot-list daemon + we-mp-rss (jobs enabled)
uv run python scripts/start_platform.py

# Bridge daemon only
uv run hot-content-bridge daemon

# Single cycle (manual)
uv run hot-content-bridge run-pipeline --quick-hotlist
uv run python scripts/start_platform.py --once
```

### we-mp-rss 集成说明

**重要**: we-mp-rss 由 `start_platform.py` 启动,使用根目录的 Python 环境(通过 `sys.executable`),不需要单独为 we-mp-rss 创建 venv。

- we-mp-rss 可以直接导入根环境已安装的依赖(trendradar、crawl4ai、fastapi 等)
- 不要在 we-mp-rss 目录下单独运行 `pip install`
- 配置文件: `we-mp-rss/config.yaml` 中的 `server.enable_job: true` 会启用定时任务
- 使用 `--no-wemp` 参数可以跳过 we-mp-rss 启动

Tune intervals in [`hot_content_bridge/config.yaml`](../hot_content_bridge/config.yaml) → `pipeline_daemon`:

| Key | Default | Meaning |
|-----|---------|---------|
| `run_on_startup` | `true` | Fetch hot list + crawl bodies immediately on start |
| `hotlist_interval_minutes` | `30` | Repeat interval |
| `full_trendradar_sync` | `false` | `false` = always collect hot list; `true` = full trendradar (schedule-aware) |
| `crawl_after_hotlist` | `true` | Run crawl4ai via bridge after each hot-list run |

**we-mp-rss**: started by `start_platform.py` with `-job True` when `server.enable_job` is true in `we-mp-rss/config.yaml`.

## Scheduling (alternative)

- **Windows Task Scheduler**: `uv run hot-content-bridge run-pipeline --quick-hotlist` on an interval.
- **Linux cron**: same command from repo root.
- **Docker** (outline): `CMD ["uv","run","hot-content-bridge","daemon"]`.

## Dependencies note

Both **litellm** (trendRadar) and **unclecode-litellm** (crawl4ai) may be installed. The bridge does not require crawl4ai LLM extraction strategies by default; if import errors appear, keep crawl4ai usage limited to `AsyncWebCrawler` + Markdown as in `article_crawler.py`.

## Legal / ethics

Respect target sites’ terms of service and robots rules; keep `article_crawl` delays conservative in production.
