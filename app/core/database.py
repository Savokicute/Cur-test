# coding=utf-8
"""数据库连接池与连接管理"""

import logging
import threading
from contextlib import contextmanager
from typing import Generator, Optional
from sqlalchemy import create_engine, event, pool, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import OperationalError

logger = logging.getLogger(__name__)

# 全局引擎和会话工厂
_engine = None
_session_factory = None
_lock = threading.Lock()


class DatabaseConfig:
    """数据库连接池配置"""
    # 连接池大小
    POOL_SIZE = 10
    MAX_OVERFLOW = 20
    # 连接超时设置
    POOL_TIMEOUT = 30  # 获取连接的超时时间（秒）
    POOL_RECYCLE = 3600  # 连接回收时间（秒），防止长时间使用的连接失效
    # 连接健康检查
    pool_pre_ping = True  # 每次从连接池取出连接时检查是否有效
    # Echo SQL（调试用）
    ECHO = False


def get_database_url() -> str:
    """获取数据库 URL"""
    from hot_content_bridge.config import BridgeConfig
    cfg = BridgeConfig.load()
    db_path = cfg.data_dir / "hotspot_platform.db"
    return f"sqlite:///{db_path}"


def get_engine():
    """
    获取数据库引擎（带连接池配置）。

    Returns:
        SQLAlchemy Engine 实例
    """
    global _engine
    if _engine is None:
        with _lock:
            if _engine is None:
                database_url = get_database_url()
                logger.info(f"初始化数据库引擎: {database_url}")

                _engine = create_engine(
                    database_url,
                    connect_args={
                        "check_same_thread": False,
                        "timeout": DatabaseConfig.POOL_TIMEOUT,
                    },
                    echo=DatabaseConfig.ECHO,
                    pool_size=DatabaseConfig.POOL_SIZE,
                    max_overflow=DatabaseConfig.MAX_OVERFLOW,
                    pool_timeout=DatabaseConfig.POOL_TIMEOUT,
                    pool_recycle=DatabaseConfig.POOL_RECYCLE,
                    pool_pre_ping=DatabaseConfig.pool_pre_ping,
                )

                # 注册事件监听器用于连接监控
                @event.listens_for(_engine, "connect")
                def set_sqlite_pragma(dbapi_connection, connection_record):
                    """SQLite 特定优化"""
                    cursor = dbapi_connection.cursor()
                    # 启用 WAL 模式以提高并发性能
                    cursor.execute("PRAGMA journal_mode=WAL")
                    # 设置更大的缓存大小（单位：KB）
                    cursor.execute("PRAGMA cache_size=-64000")  # 64MB
                    # 禁用同步以提升性能（注意：可能影响数据安全）
                    cursor.execute("PRAGMA synchronous=NORMAL")
                    # 外键约束
                    cursor.execute("PRAGMA foreign_keys=ON")
                    cursor.close()

                @event.listens_for(_engine, "checkout")
                def receive_checkout(dbapi_connection, connection_record, connection_proxy):
                    """连接取出时记录日志"""
                    logger.debug("数据库连接已从连接池取出")

                @event.listens_for(_engine, "checkin")
                def receive_checkin(dbapi_connection, connection_record):
                    """连接归还时记录日志"""
                    logger.debug("数据库连接已归还到连接池")

                logger.info(
                    f"数据库引擎创建成功 - "
                    f"pool_size={DatabaseConfig.POOL_SIZE}, "
                    f"max_overflow={DatabaseConfig.MAX_OVERFLOW}, "
                    f"pool_recycle={DatabaseConfig.POOL_RECYCLE}s"
                )
    return _engine


def get_session_factory() -> sessionmaker:
    """
    获取 Session 工厂。

    Returns:
        SQLAlchemy sessionmaker 实例
    """
    global _session_factory
    if _session_factory is None:
        with _lock:
            if _session_factory is None:
                engine = get_engine()
                _session_factory = sessionmaker(
                    bind=engine,
                    expire_on_commit=False,  # 避免访问已提交对象时报错
                )
    return _session_factory


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    获取数据库会话的上下文管理器。

    Yields:
        SQLAlchemy Session 实例

    Example:
        >>> with get_db_session() as db:
        ...     user = db.query(User).first()
    """
    session_factory = get_session_factory()
    db = session_factory()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"数据库操作失败，已回滚: {e}", exc_info=True)
        raise
    finally:
        db.close()


def get_db():
    """
    获取数据库会话（用于 FastAPI 依赖注入）。

    Yields:
        SQLAlchemy Session 实例
    """
    session_factory = get_session_factory()
    db = session_factory()
    try:
        yield db
    finally:
        db.close()


async def check_database_health() -> dict:
    """
    检查数据库健康状态。

    Returns:
        包含健康状态信息的字典
    """
    health_status = {
        "status": "healthy",
        "pool_size": DatabaseConfig.POOL_SIZE,
        "checked_in": 0,
        "checked_out": 0,
        "overflow": 0,
        "error": None,
    }

    try:
        engine = get_engine()
        pool = engine.pool

        health_status.update({
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
        })

        # 执行简单查询测试连接
        with get_db_session() as db:
            db.execute(text("SELECT 1"))

        logger.debug(f"数据库健康检查通过: {health_status}")
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["error"] = str(e)
        logger.error(f"数据库健康检查失败: {e}", exc_info=True)

    return health_status


def close_database_connections():
    """
    关闭所有数据库连接。
    在应用关闭时调用。
    """
    global _engine, _session_factory
    try:
        if _engine:
            _engine.dispose()
            logger.info("数据库引擎已关闭")
        _engine = None
        _session_factory = None
    except Exception as e:
        logger.error(f"关闭数据库连接失败: {e}", exc_info=True)
