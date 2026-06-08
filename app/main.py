# coding=utf-8
"""FastAPI 主应用入口。"""

import logging
import threading

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import hotspots, articles, wechat, sources, media, test, keywords, config, assistant, ai_analysis, notifications, sso, users, auth
from hot_content_bridge.config import BridgeConfig
from hot_content_bridge.daemon import PipelineDaemon, install_signal_handlers

logger = logging.getLogger(__name__)

# 全局 daemon 引用（用于 shutdown 停止）
_daemon: PipelineDaemon | None = None
_daemon_thread: threading.Thread | None = None


def _start_pipeline_daemon():
    """启动后台爬取守护进程（非阻塞，在独立线程中运行）。"""
    global _daemon, _daemon_thread
    try:
        cfg = BridgeConfig.load()
        settings = cfg.pipeline_daemon
        if not settings.enabled:
            logger.info("管道调度已禁用 (pipeline_daemon.enabled=false)，跳过启动")
            return

        _daemon = PipelineDaemon(cfg, settings)
        _daemon_thread = threading.Thread(target=_daemon.run_forever, name="PipelineDaemon", daemon=True)
        _daemon_thread.start()
        logger.info(
            "管道调度已启动: startup=%s, interval=%dmin, delay=%ds",
            settings.run_on_startup,
            settings.hotlist_interval_minutes,
            settings.initial_delay_seconds,
        )
    except Exception as e:
        logger.error("管道调度启动失败: %s", exc_info=True)


def _stop_pipeline_daemon():
    """停止后台爬取守护进程。"""
    global _daemon
    if _daemon:
        _daemon.stop()
        logger.info("管道调度已发送停止信号")


app = FastAPI(
    title="热点发现平台 API",
    description="整合 TrendRadar、crawl4ai、we-mp-rss 的热点发现平台",
    version="1.0.0",
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该设置具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(hotspots.router, prefix="/api", tags=["hotspots"])
app.include_router(articles.router, prefix="/api", tags=["articles"])
app.include_router(wechat.router, prefix="/api", tags=["wechat"])
app.include_router(sources.router, prefix="/api/sources", tags=["sources"])
app.include_router(media.router, prefix="/api", tags=["media"])
app.include_router(test.router, prefix="/api", tags=["test"])
app.include_router(keywords.router, prefix="/api", tags=["keywords"])
app.include_router(config.router, prefix="/api", tags=["config"])
app.include_router(assistant.router, prefix="/api", tags=["assistant"])
app.include_router(ai_analysis.router, prefix="/api", tags=["ai-analysis"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["notifications"])
app.include_router(sso.router, prefix="/api", tags=["sso"])
app.include_router(users.router, prefix="/api", tags=["users"])
app.include_router(auth.router, prefix="/api", tags=["auth"])


# ========== 启动/关闭事件 ==========
@app.on_event("startup")
async def startup_event():
    """应用启动时自动爬取当日热榜数据。"""
    _start_pipeline_daemon()

    # 初始化 MCP 工具
    try:
        from app.services.mcp_tools import register_builtin_tools
        register_builtin_tools()
        logger.info("MCP 工具初始化完成")
    except Exception as e:
        logger.error("MCP 工具初始化失败: %s", exc_info=True)

    # 初始化 AI 分析模板
    try:
        from app.models import get_session_factory, init_default_analysis_templates
        session_factory = get_session_factory()
        db = session_factory()
        try:
            init_default_analysis_templates(db)
            logger.info("AI分析模板初始化完成")
        finally:
            db.close()
    except Exception as e:
        logger.error("AI分析模板初始化失败: %s", exc_info=True)

    # 初始化 RBAC 权限数据（角色 + 权限 + 映射）
    try:
        from app.models import get_session_factory, init_rbac_data
        session_factory = get_session_factory()
        db = session_factory()
        try:
            init_rbac_data(db)
            logger.info("RBAC权限数据初始化完成")
        finally:
            db.close()
    except Exception as e:
        logger.error("RBAC权限数据初始化失败: %s", exc_info=True)

    # 初始化独立用户体系（认证表 + 种子用户）
    try:
        from app.api.auth import init_auth_tables, init_seed_users
        from app.models import get_session_factory

        # 确保认证相关表已创建
        init_auth_tables()

        session_factory = get_session_factory()
        db = session_factory()
        try:
            init_seed_users(db)
            logger.info("独立用户体系初始化完成")
        finally:
            db.close()
    except Exception as e:
        logger.error("独立用户体系初始化失败: %s", exc_info=True)


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时停止后台爬取进程。"""
    _stop_pipeline_daemon()


@app.get("/")
async def root():
    """根路径 - API 信息。"""
    return {
        "name": "热点发现平台 API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc",
    }


@app.get("/api/status")
async def get_status():
    """获取系统状态。"""
    cfg = BridgeConfig.load()
    return {
        "status": "ok",
        "data_dir": str(cfg.data_dir),
        "pipeline_daemon": {
            "enabled": cfg.pipeline_daemon.enabled,
            "run_on_startup": cfg.pipeline_daemon.run_on_startup,
            "hotlist_interval_minutes": cfg.pipeline_daemon.hotlist_interval_minutes,
            "running": _daemon is not None and _daemon_thread is not None,
        },
    }


@app.post("/api/crawl/trigger")
async def trigger_crawl():
    """手动触发一次热榜数据爬取（非阻塞，后台执行）。"""
    global _daemon
    if _daemon is None:
        return {"success": False, "message": "管道调度未运行，请检查 pipeline_daemon.enabled 配置"}

    import threading as _threading

    def _run_in_background():
        try:
            _daemon.run_once()
            logger.info("手动触发的爬取任务已完成")
        except Exception as e:
            logger.error("手动触发的爬取任务失败: %s", exc_info=True)

    t = _threading.Thread(target=_run_in_background, name="ManualCrawl", daemon=True)
    t.start()
    return {"success": True, "message": "爬取任务已在后台启动"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
