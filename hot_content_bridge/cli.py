# coding=utf-8
"""Click CLI for hot list sync and article crawling."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import click

import hot_content_bridge._crawl4ai_path  # noqa: F401  — must run before crawl4ai imports

from hot_content_bridge.config import BridgeConfig
from hot_content_bridge.daemon import PipelineDaemon, install_signal_handlers
from hot_content_bridge.pipeline_runner import run_crawl_step, run_hotlist_step, run_pipeline_once
from hot_content_bridge.storage import ensure_article_tables

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


@click.group()
@click.option(
    "--config",
    "config_path",
    type=click.Path(path_type=Path, exists=True),
    default=None,
    help="Path to hot_content_bridge/config.yaml",
)
@click.option(
    "--trendradar-config",
    type=click.Path(path_type=Path, exists=True),
    default=None,
    help="Override path to trendRadar config.yaml",
)
@click.pass_context
def main(ctx: click.Context, config_path: Path | None, trendradar_config: Path | None) -> None:
    ctx.ensure_object(dict)
    ctx.obj["cfg"] = BridgeConfig.load(path=config_path, trendradar_config=trendradar_config)


@main.command("fetch-hotlist-only")
@click.option(
    "--platform",
    "target_platform",
    default=None,
    help="仅抓取指定平台（ID），不传则抓取所有启用平台",
)
@click.pass_context
def fetch_hotlist_only_cmd(ctx: click.Context, target_platform: str | None) -> None:
    """仅抓取热榜并写入 SQLite（跳过完整趋势雷达主流程与 AI）。"""
    run_hotlist_step(ctx.obj["cfg"], full_sync=False, target_platform=target_platform)


@main.command("sync-hotlist")
@click.option(
    "--platform",
    "target_platform",
    default=None,
    help="仅同步指定平台（ID），不传则同步所有启用平台",
)
@click.pass_context
def sync_hotlist(ctx: click.Context, target_platform: str | None) -> None:
    """Run trendRadar once (same as `python -m trendradar` in trendRadar root)."""
    run_hotlist_step(ctx.obj["cfg"], full_sync=True, target_platform=target_platform)


@main.command("crawl-articles")
@click.option(
    "--limit",
    type=int,
    default=0,
    help="最多爬取条数（0=不限制，沿用 config max_urls_per_run）",
)
@click.pass_context
def crawl_articles(ctx: click.Context, limit: int) -> None:
    """Crawl article bodies for URLs from the latest hot-list batch."""
    run_crawl_step(ctx.obj["cfg"], limit=limit)


@main.command("run-pipeline")
@click.option("--skip-hotlist", is_flag=True, help="Do not run trendRadar crawl first")
@click.option(
    "--quick-hotlist",
    is_flag=True,
    help="仅热榜 API + SQLite（推荐）；否则执行完整 python -m trendradar（含 AI/调度等）",
)
@click.option(
    "--limit",
    type=int,
    default=0,
    help="正文爬取最多条数（0=不限制）",
)
@click.pass_context
def run_pipeline(ctx: click.Context, skip_hotlist: bool, quick_hotlist: bool, limit: int) -> None:
    """Optional hotlist sync, then article crawl."""
    cfg: BridgeConfig = ctx.obj["cfg"]
    result = run_pipeline_once(
        cfg,
        skip_hotlist=skip_hotlist,
        full_trendradar_sync=not quick_hotlist and not skip_hotlist,
        crawl_after_hotlist=True,
        crawl_limit=limit,
    )
    if result.hotlist_error or result.crawl_error:
        raise click.ClickException(
            f"Pipeline failed: hotlist={result.hotlist_error!r} crawl={result.crawl_error!r}"
        )


@main.command("daemon")
@click.option(
    "--interval",
    type=int,
    default=None,
    help="热榜刷新间隔（分钟），覆盖 config pipeline_daemon.hotlist_interval_minutes",
)
@click.option("--once", is_flag=True, help="只执行一轮后退出（等同 run-pipeline --quick-hotlist）")
@click.option(
    "--full-sync",
    is_flag=True,
    help="使用完整 trendradar 同步（含 AI 分析/筛选/推送），而非快速热榜 API",
)
@click.pass_context
def daemon_cmd(ctx: click.Context, interval: int | None, once: bool, full_sync: bool) -> None:
    """
    后台调度：启动时立即拉取当日热榜，并按间隔同步触发正文爬取。

    推荐通过 ``uv run python scripts/start_platform.py`` 与 we-mp-rss 一并启动。
    """
    cfg: BridgeConfig = ctx.obj["cfg"]
    settings = cfg.pipeline_daemon

    if once:
        result = run_pipeline_once(
            cfg,
            full_trendradar_sync=full_sync or settings.full_trendradar_sync,
            crawl_after_hotlist=settings.crawl_after_hotlist,
            crawl_limit=settings.crawl_limit_per_run,
        )
        if result.hotlist_error or result.crawl_error:
            raise click.ClickException(
                f"Pipeline failed: hotlist={result.hotlist_error!r} crawl={result.crawl_error!r}"
            )
        return

    if interval is not None:
        settings.hotlist_interval_minutes = interval

    # --full-sync 覆盖配置文件中的默认值
    if full_sync:
        settings.full_trendradar_sync = True

    if not settings.enabled:
        logger.warning("pipeline_daemon.enabled=false in config; exiting.")
        return

    logger.info(
        "Pipeline daemon: interval=%dm startup=%s full_sync=%s crawl_after=%s",
        settings.hotlist_interval_minutes,
        settings.run_on_startup,
        settings.full_trendradar_sync,
        settings.crawl_after_hotlist,
    )
    d = PipelineDaemon(cfg, settings)
    install_signal_handlers(d)
    d.run_forever()


@main.command("list-platform-rules")
@click.pass_context
def list_platform_rules_cmd(ctx: click.Context) -> None:
    """列出 platform_rules/ 下已加载的平台过滤规则。"""
    from hot_content_bridge.platform_rules_loader import get_registry

    reg = get_registry()
    click.echo(f"规则目录: {reg._dir}")
    click.echo(f"默认规则: {reg.default_rule.platform_id}")
    for rule in reg.all_rules():
        hosts = ", ".join(rule.hosts) if rule.hosts else "(无 hosts，仅按 platform_id 匹配)"
        te = rule.use_target_elements
        click.echo(
            f"  {rule.platform_id:24}  {rule.display_name:12}  enabled={rule.enabled}  "
            f"hosts={hosts}  target_elements={te}"
        )


@main.command("serve-web")
@click.option("--host", default="127.0.0.1", show_default=True)
@click.option("--port", default=8765, show_default=True)
@click.pass_context
def serve_web(ctx: click.Context, host: str, port: int) -> None:
    """Browse latest hot-list batch and crawled article bodies in the browser."""
    from hot_content_bridge.web_server import run_server

    cfg: BridgeConfig = ctx.obj["cfg"]
    ensure_article_tables(cfg)
    run_server(cfg, host, int(port))


if __name__ == "__main__":
    main()
