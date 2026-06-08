# coding=utf-8
"""优化后的数据库模型定义 - 包含索引、约束和验证"""

import logging
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any

from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Text, ForeignKey, JSON, Float,
    create_engine, Index, UniqueConstraint, CheckConstraint, Enum as SAEnum
)
from sqlalchemy.orm import DeclarativeBase, relationship, sessionmaker, validates
from sqlalchemy.ext.hybrid import hybrid_property

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """基类"""
    pass


# ========== 枚举类型定义 ==========

class SubscriptionType(str, Enum):
    """订阅类型枚举"""
    RSS = "rss"
    WEBHOOK = "webhook"
    EMAIL = "email"
    DINGTALK = "dingtalk"
    WECHAT_WORK = "wechat_work"
    SLACK = "slack"


class NotificationStatus(str, Enum):
    """通知状态枚举"""
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class TaskPriority(int, Enum):
    """任务优先级枚举"""
    LOW = 0
    NORMAL = 5
    HIGH = 10
    URGENT = 20


class TaskType(str, Enum):
    """任务类型枚举"""
    ARTICLE_FETCH = "article_fetch"
    MEDIA_DOWNLOAD = "media_download"
    AI_ANALYSIS = "ai_analysis"
    NOTIFICATION = "notification"
    CLEANUP = "cleanup"


# ========== 浏览器配置 ==========

class BrowserProfile(Base):
    """浏览器配置文件"""
    __tablename__ = "browser_profiles"

    id = Column(String(64), primary_key=True)
    name = Column(String(128), nullable=False, comment="配置名称")
    config = Column(JSON, default=dict, comment="浏览器配置（代理、UA等）")
    enabled = Column(Boolean, default=True, comment="是否启用")
    is_global_default = Column(Boolean, default=False, comment="是否全局默认")
    size = Column(String(32), default="0MB", comment="配置大小")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    # 关联关系
    hotspot_sources = relationship("HotspotSource", back_populates="browser_profile", lazy="dynamic")
    website_sources = relationship("WebsiteSource", back_populates="browser_profile", lazy="dynamic")
    wechat_feeds = relationship("WeChatFeed", back_populates="browser_profile", lazy="dynamic")

    @validates('name')
    def validate_name(self, key, name):
        if not name or len(name.strip()) == 0:
            raise ValueError("名称不能为空")
        if len(name) > 128:
            raise ValueError("名称长度不能超过128个字符")
        return name.strip()


# ========== 热榜源配置 ==========

class HotspotSource(Base):
    """热榜源配置 - 优化版"""
    __tablename__ = "hotspot_sources"

    id = Column(String(64), primary_key=True, comment="平台ID（如 baidu、weibo）")
    name = Column(String(128), nullable=False, comment="平台名称")
    enabled = Column(Boolean, default=True, comment="是否启用")
    weight = Column(Integer, default=10, comment="权重（1-100）")
    browser_profile_id = Column(
        String(64),
        ForeignKey("browser_profiles.id"),
        nullable=True,
        comment="关联的浏览器配置文件ID"
    )
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    # 关联关系
    browser_profile = relationship("BrowserProfile", back_populates="hotspot_sources")

    # 约束
    __table_args__ = (
        CheckConstraint('weight >= 1 AND weight <= 100', name='ck_hotspot_source_weight'),
    )

    @validates('id')
    def validate_id(self, key, value):
        if not value or len(value.strip()) == 0:
            raise ValueError("平台ID不能为空")
        if len(value) > 64:
            raise ValueError("平台ID长度不能超过64个字符")
        return value.strip().lower()

    @validates('weight')
    def validate_weight(self, key, weight):
        if not 1 <= weight <= 100:
            raise ValueError("权重必须在1-100之间")
        return weight


# ========== 网站源配置 ==========

class WebsiteSource(Base):
    """网站源配置（RSS/自定义）"""
    __tablename__ = "website_sources"

    id = Column(String(64), primary_key=True)
    name = Column(String(256), nullable=False, comment="源名称")
    url = Column(Text, nullable=False, comment="URL或RSS地址")
    url_template = Column(Text, nullable=True, comment="URL模板（用于动态生成）")
    css_selector = Column(Text, nullable=True, comment="CSS选择器（用于内容提取）")
    enabled = Column(Boolean, default=True, comment="是否启用")
    max_age_days = Column(Integer, nullable=True, comment="最大保留天数")
    weight = Column(Integer, default=5, comment="权重（1-100）")
    source_type = Column(String(32), default="rss", comment="类型：rss/custom/api")
    browser_profile_id = Column(
        String(64),
        ForeignKey("browser_profiles.id"),
        nullable=True,
        comment="关联的浏览器配置文件ID"
    )
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    # 关联关系
    browser_profile = relationship("BrowserProfile", back_populates="website_sources")

    __table_args__ = (
        CheckConstraint('weight >= 1 AND weight <= 100', name='ck_website_source_weight'),
        CheckConstraint("source_type IN ('rss', 'custom', 'api')", name='ck_website_source_type'),
    )


# ========== 微信公众号 ==========

class WeChatFeed(Base):
    """公众号订阅（WeChatFeed）"""
    __tablename__ = "wechat_feeds"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="订阅ID")
    name = Column(String(256), nullable=False, comment="公众号名称")
    account_id = Column(String(128), nullable=True, comment="微信号")
    avatar_url = Column(Text, nullable=True, comment="头像URL")
    feed_url = Column(Text, nullable=True, comment="RSS链接")
    status = Column(String(32), default="active", comment="状态：active/inactive")
    crawl_interval = Column(Integer, default=3600, comment="抓取间隔（秒）")
    last_fetch_time = Column(DateTime, nullable=True, comment="最后抓取时间")
    filter_rules = Column(JSON, default=list, comment="内容过滤规则")
    browser_profile_id = Column(
        String(64),
        ForeignKey("browser_profiles.id"),
        nullable=True,
        comment="关联的浏览器配置文件ID"
    )
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    # 关联关系
    browser_profile = relationship("BrowserProfile", back_populates="wechat_feeds")
    articles = relationship("WeChatArticle", back_populates="feed", lazy="dynamic",
                           cascade="all, delete-orphan")


class WeChatArticle(Base):
    """公众号文章（WeChatArticle）- 优化版"""
    __tablename__ = "wechat_articles"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="文章ID")
    feed_id = Column(Integer, ForeignKey("wechat_feeds.id"), nullable=False, comment="所属订阅ID")
    title = Column(String(512), nullable=False, comment="标题")
    url = Column(Text, nullable=False, unique=True, comment="文章链接")
    author = Column(String(256), nullable=True, comment="作者")
    digest = Column(Text, nullable=True, comment="摘要")
    cover = Column(Text, nullable=True, comment="封面图URL")
    content = Column(Text, nullable=True, comment="文章内容（Markdown）")
    content_html = Column(Text, nullable=True, comment="HTML原文")
    publish_time = Column(DateTime, nullable=True, comment="发布时间")
    read_count = Column(Integer, default=0, comment="阅读数")
    like_count = Column(Integer, default=0, comment="点赞数")
    status = Column(String(32), default="pending", comment="状态：pending/success/failed")
    error_msg = Column(Text, nullable=True, comment="错误信息")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    # 关联关系
    feed = relationship("WeChatFeed", back_populates="articles")

    # 优化后的索引
    __table_args__ = (
        Index("idx_wechat_articles_feed_id", "feed_id"),
        Index("idx_wechat_articles_publish_time", "publish_time"),
        Index("idx_wechat_articles_status", "status"),
        Index("idx_wechat_articles_feed_status", "feed_id", "status"),  # 复合索引
    )

    @validates('title')
    def validate_title(self, key, title):
        if not title or len(title.strip()) == 0:
            raise ValueError("标题不能为空")
        if len(title) > 512:
            raise ValueError("标题长度不能超过512个字符")
        return title.strip()


# ========== 媒体文件 - 优化版 ==========

class MediaItem(Base):
    """媒体文件（图片/视频封面）- 优化版"""
    __tablename__ = "media_items"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="媒体ID")
    article_id = Column(Integer, nullable=True, comment="关联的文章ID（可为空，如热榜项）")
    original_url = Column(Text, nullable=False, comment="原始URL")
    stored_path = Column(String(512), nullable=True, comment="存储后的本地路径")
    media_type = Column(String(16), default="image", comment="类型：image/video")
    is_video_cover = Column(Boolean, default=False, comment="是否为视频封面")
    file_size = Column(Integer, default=0, comment="文件大小（字节）")
    width = Column(Integer, nullable=True, comment="宽度(px)")
    height = Column(Integer, nullable=True, comment="高度(px)")
    format = Column(String(16), nullable=True, comment="文件格式：jpg/png/gif/webp/mp4")
    status = Column(String(32), default="pending", comment="状态：pending/success/failed")
    error_msg = Column(Text, nullable=True, comment="错误信息")
    hash_value = Column(String(64), nullable=True, comment="文件SHA256哈希值")
    source_platform = Column(String(64), nullable=True, comment="来源平台")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    # 优化后的索引 - 添加复合索引
    __table_args__ = (
        Index("idx_media_items_article_id", "article_id"),
        Index("idx_media_items_article_type", "article_id", "media_type"),  # 新增复合索引
        Index("idx_media_items_type", "media_type"),
        Index("idx_media_items_status", "status"),
        Index("idx_media_items_hash", "hash_value"),
        Index("idx_media_items_platform", "source_platform"),
        CheckConstraint("media_type IN ('image', 'video')", name='ck_media_type'),
    )


# ========== AI 分析相关模型 ==========

class AIAnalysisConfig(Base):
    """AI分析配置表 - 优化版"""
    __tablename__ = "ai_analysis_configs"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="配置ID")
    name = Column(String(256), nullable=False, comment="配置名称")
    description = Column(Text, nullable=True, comment="配置描述")
    prompt_template = Column(Text, nullable=False, comment="提示词模板")
    model_name = Column(String(128), default="gpt-4", comment="使用的模型名称")
    temperature = Column(Float, default=0.7, comment="温度参数 (0-1)")
    max_tokens = Column(Integer, default=4096, comment="最大生成token数")
    trigger_type = Column(String(32), default="manual", comment="触发类型: manual/scheduled/event")
    schedule_cron = Column(String(128), nullable=True, comment="定时任务cron表达式")
    is_active = Column(Boolean, default=True, comment="是否启用")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    # 关联关系
    reports = relationship("AIAnalysisReport", back_populates="config", lazy="dynamic",
                           cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_ai_configs_trigger_type", "trigger_type"),
        Index("idx_ai_configs_active", "is_active"),
        CheckConstraint("temperature >= 0 AND temperature <= 1", name='ck_temperature'),
        CheckConstraint("max_tokens > 0", name='ck_max_tokens'),
    )


class AIAnalysisReport(Base):
    """分析报告表 - 优化版"""
    __tablename__ = "ai_analysis_reports"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="报告ID")
    config_id = Column(
        Integer,
        ForeignKey("ai_analysis_configs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="关联的配置ID"
    )
    title = Column(String(512), nullable=False, comment="报告标题")
    summary = Column(Text, nullable=True, comment="报告摘要")
    content = Column(Text, nullable=True, comment="报告内容（Markdown格式）")
    status = Column(
        String(32),
        default="pending",
        comment="状态: pending/running/completed/failed"
    )
    input_params = Column(JSON, default=dict, comment="输入参数（JSON）")
    result_data = Column(JSON, nullable=True, comment="结果数据（JSON）")
    error_message = Column(Text, nullable=True, comment="错误信息")
    started_at = Column(DateTime, nullable=True, comment="开始时间")
    completed_at = Column(DateTime, nullable=True, comment="完成时间")
    total_items = Column(Integer, default=0, comment="处理的总条目数")
    relevant_count = Column(Integer, default=0, comment="相关条目数")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")

    # 关联关系
    config = relationship("AIAnalysisConfig", back_populates="reports")

    # 优化后的索引 - 添加复合索引
    __table_args__ = (
        Index("idx_ai_reports_config_id", "config_id"),
        Index("idx_ai_reports_config_status", "config_id", "status"),  # 新增复合索引
        Index("idx_ai_reports_status", "status"),
        Index("idx_ai_reports_created_at", "created_at"),
    )


class AIAnalysisTemplate(Base):
    """预设模板表"""
    __tablename__ = "ai_analysis_templates"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="模板ID")
    name = Column(String(256), nullable=False, comment="模板名称")
    category = Column(String(128), nullable=False, comment="模板分类")
    description = Column(Text, nullable=True, comment="模板描述")
    prompt_template = Column(Text, nullable=False, comment="提示词模板")
    default_params = Column(JSON, default=dict, comment="默认参数（JSON）")
    is_system = Column(Boolean, default=False, comment="是否为系统预设")
    usage_count = Column(Integer, default=0, comment="使用次数")
    sort_order = Column(Integer, default=0, comment="排序顺序")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")

    __table_args__ = (
        Index("idx_ai_templates_category", "category"),
        Index("idx_ai_templates_system", "is_system"),
    )


# ========== 订阅与通知相关模型（新增）==========

class Subscription(Base):
    """
    订阅表 - 支持多种通知渠道

    支持 RSS、Webhook、邮件、钉钉、企业微信、Slack 等多种通知方式
    """
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="订阅ID")
    name = Column(String(256), nullable=False, comment="订阅名称")
    description = Column(Text, nullable=True, comment="订阅描述")

    # 订阅类型和目标配置
    subscription_type = Column(
        String(32),
        nullable=False,
        default=SubscriptionType.WEBHOOK.value,
        comment="订阅类型: rss/webhook/email/dingtalk/wechat_work/slack"
    )
    target_url = Column(Text, nullable=True, comment="目标地址（Webhook URL、RSS输出路径等）")
    target_config = Column(JSON, nullable=True, comment="目标配置（认证信息、Headers等）")

    # 过滤条件
    filter_config = Column(JSON, default=dict, comment="过滤条件（关键词、平台、最低热度等）")

    # 内容格式化
    format_template = Column(Text, nullable=True, comment="输出格式模板")

    # 调度设置
    schedule_cron = Column(String(128), nullable=True, comment="推送计划（Cron表达式）")
    trigger_mode = Column(
        String(32),
        default="manual",
        comment="触发模式: manual/scheduled/event"
    )

    # 状态跟踪
    is_active = Column(Boolean, default=True, comment="是否启用")
    last_triggered_at = Column(DateTime, nullable=True, comment="最后触发时间")
    last_success_at = Column(DateTime, nullable=True, comment="最后成功发送时间")
    error_message = Column(Text, nullable=True, comment="最近一次错误信息")
    total_triggers = Column(Integer, default=0, comment="总触发次数")
    success_count = Column(Integer, default=0, comment="成功次数")
    failure_count = Column(Integer, default=0, comment="失败次数")

    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    # 关联关系
    notification_logs = relationship("NotificationLog", back_populates="subscription", lazy="dynamic",
                                     cascade="all, delete-orphan")

    # 索引和约束
    __table_args__ = (
        Index("idx_subscriptions_type", "subscription_type"),
        Index("idx_subscriptions_active", "is_active"),
        Index("idx_subscriptions_active_type", "is_active", "subscription_type"),  # 复合索引
        CheckConstraint(
            "subscription_type IN ('" + "','".join([t.value for t in SubscriptionType]) + "')",
            name='ck_subscription_type'
        ),
        CheckConstraint(
            "trigger_mode IN ('manual', 'scheduled', 'event')",
            name='ck_trigger_mode'
        ),
    )

    @validates('name')
    def validate_name(self, key, name):
        if not name or len(name.strip()) == 0:
            raise ValueError("订阅名称不能为空")
        if len(name) > 256:
            raise ValueError("订阅名称长度不能超过256个字符")
        return name.strip()

    @hybrid_property
    def success_rate(self) -> float:
        """计算成功率"""
        if self.total_triggers == 0:
            return 0.0
        return round(self.success_count / self.total_triggers * 100, 2)


class NotificationLog(Base):
    """
    通知日志表 - 记录每次通知发送的详细信息
    """
    __tablename__ = "notification_logs"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="日志ID")
    subscription_id = Column(
        Integer,
        ForeignKey("subscriptions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="关联的订阅ID"
    )

    # 内容信息
    content_summary = Column(Text, nullable=True, comment="内容摘要")
    sent_content = Column(Text, nullable=True, comment="实际发送的内容")
    items_count = Column(Integer, default=0, comment="推送的条目数量")

    # 发送状态
    status = Column(
        String(32),
        default=NotificationStatus.PENDING.value,
        comment="状态: pending/sent/failed"
    )
    error_message = Column(Text, nullable=True, comment="错误信息")
    response_code = Column(Integer, nullable=True, comment="HTTP响应码（Webhook类型）")
    retry_count = Column(Integer, default=0, comment="重试次数")

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    sent_at = Column(DateTime, nullable=True, comment="实际发送时间")
    completed_at = Column(DateTime, nullable=True, comment="完成时间")

    # 关联关系
    subscription = relationship("Subscription", back_populates="notification_logs")

    # 索引
    __table_args__ = (
        Index("idx_notification_logs_subscription_id", "subscription_id"),
        Index("idx_notification_logs_status", "status"),
        Index("idx_notification_logs_subscription_status", "subscription_id", "status"),  # 复合索引
        Index("idx_notification_logs_created_at", "created_at"),
        CheckConstraint(
            "status IN ('" + "','".join([s.value for s in NotificationStatus]) + "')",
            name='ck_notification_status'
        ),
    )


# ========== 任务队列相关模型（新增）==========

class Task(Base):
    """
    任务表 - 用于异步任务队列的任务持久化

    支持多种任务类型：文章抓取、媒体下载、AI分析、通知发送、清理任务
    """
    __tablename__ = "tasks"

    id = Column(String(36), primary_key=True, comment="任务ID（UUID格式）")

    # 任务基本信息
    task_type = Column(
        String(32),
        nullable=False,
        comment="任务类型: article_fetch/media_download/ai_analysis/notification/cleanup"
    )
    priority = Column(Integer, default=TaskPriority.NORMAL.value, comment="优先级（0-20，数值越高越优先）")
    params = Column(JSON, default=dict, comment="任务参数（JSON）")

    # 任务状态
    status = Column(
        String(32),
        default=TaskStatus.PENDING.value,
        comment="状态: pending/running/completed/failed/cancelled/retrying"
    )
    progress = Column(Float, default=0.0, comment="进度（0.0-1.0）")
    result = Column(JSON, nullable=True, comment="执行结果（JSON）")
    error_message = Column(Text, nullable=True, comment="错误信息")

    # 重试机制
    retry_count = Column(Integer, default=0, comment="已重试次数")
    max_retries = Column(Integer, default=3, comment="最大重试次数")
    next_retry_at = Column(DateTime, nullable=True, comment="下次重试时间")

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    started_at = Column(DateTime, nullable=True, comment="开始执行时间")
    completed_at = Column(DateTime, nullable=True, comment="完成时间")

    # 索引和约束
    __table_args__ = (
        Index("idx_tasks_type", "task_type"),
        Index("idx_tasks_status", "status"),
        Index("idx_tasks_type_status", "task_type", "status"),  # 复合索引
        Index("idx_tasks_priority_status", "priority", "status"),  # 用于优先级队列
        Index("idx_tasks_created_at", "created_at"),
        Index("idx_tasks_next_retry", "next_retry_at"),  # 用于重试调度
        CheckConstraint("task_type IN ('" + "','".join([t.value for t in TaskType]) + "')",
                       name='ck_task_type'),
        CheckConstraint("status IN ('" + "','".join([s.value for s in TaskStatus]) + "')",
                       name='ck_task_status'),
        CheckConstraint('priority >= 0 AND priority <= 20', name='ck_task_priority'),
        CheckConstraint('progress >= 0 AND progress <= 1', name='ck_task_progress'),
        CheckConstraint('retry_count >= 0', name='ck_retry_count'),
    )

    @hybrid_property
    def duration_seconds(self) -> Optional[float]:
        """计算任务执行时长（秒）"""
        if self.started_at and self.completed_at:
            delta = self.completed_at - self.started_at
            return delta.total_seconds()
        return None


# ========== 数据库连接管理函数 ==========

def get_database_url() -> str:
    """获取数据库 URL"""
    from hot_content_bridge.config import BridgeConfig
    cfg = BridgeConfig.load()
    db_path = cfg.data_dir / "hotspot_platform.db"
    return f"sqlite:///{db_path}"


_engine = None
_session_factory = None


def get_engine():
    """获取数据库引擎"""
    global _engine
    if _engine is None:
        from app.core.database import get_engine as _get_engine_with_pool
        _engine = _get_engine_with_pool()
        # 创建所有表
        Base.metadata.create_all(_engine)
    return _engine


def get_session_factory():
    """获取 Session 工厂"""
    global _session_factory
    if _session_factory is None:
        engine = get_engine()
        _session_factory = sessionmaker(bind=engine)
    return _session_factory


def get_db():
    """获取数据库会话（用于 FastAPI 依赖注入）"""
    from app.core.database import get_db as _get_db_with_context
    yield from _get_db_with_context()


def init_db():
    """初始化数据库（创建所有表）"""
    engine = get_engine()
    Base.metadata.create_all(engine)
    logger.info("数据库初始化完成，所有表已创建")


# 预设数据初始化函数

def init_default_hotspot_sources(db):
    """初始化默认的热榜源配置"""
    default_sources = [
        {"id": "toutiao", "name": "今日头条", "enabled": True, "weight": 10},
        {"id": "baidu", "name": "百度热搜", "enabled": True, "weight": 10},
        {"id": "weibo", "name": "微博", "enabled": True, "weight": 9},
        {"id": "zhihu", "name": "知乎", "enabled": True, "weight": 8},
        {"id": "zhihu-hot", "name": "知乎热榜", "enabled": True, "weight": 8},
        {"id": "bilibili-hot-search", "name": "Bilibili 热搜", "enabled": True, "weight": 7},
        {"id": "tieba", "name": "贴吧", "enabled": False, "weight": 6},
        {"id": "douyin", "name": "抖音", "enabled": True, "weight": 8},
        {"id": "wallstreetcn-hot", "name": "华尔街见闻", "enabled": False, "weight": 6},
        {"id": "thepaper", "name": "澎湃新闻", "enabled": True, "weight": 7},
        {"id": "cls-hot", "name": "财联社热门", "enabled": False, "weight": 6},
        {"id": "ifeng", "name": "凤凰网", "enabled": False, "weight": 6},
    ]

    for source_data in default_sources:
        existing = db.query(HotspotSource).filter_by(id=source_data["id"]).first()
        if not existing:
            source = HotspotSource(**source_data)
            db.add(source)

    db.commit()


def init_default_analysis_templates(db):
    """初始化系统预设的AI分析模板"""
    default_templates = [
        {
            "name": "每日热点总结",
            "category": "daily_summary",
            "description": "总结当天最热的20条新闻，提炼关键信息和趋势",
            "prompt_template": """请对以下热榜数据进行全面分析，生成一份专业的每日热点总结报告。

## 数据范围
- 日期：{{date}}
- 平台：{{platforms}}
- 热点数量：{{top_n}} 条

## 分析要求
1. **热点概览**：按热度排序列出前20条热点
2. **趋势分析**：识别3-5个主要趋势方向
3. **关键事件**：重点解读影响力最大的3条热点
4. **平台对比**：不同平台的热点差异
5. **预测展望**：基于当前热度预测未来可能的发展方向

## 输出格式
请使用Markdown格式输出，包含清晰的标题层级和表格。

## 原始数据
{{hotspots_data}}""",
            "default_params": {
                "top_n": 20,
                "platforms": ["baidu", "weibo", "zhihu"],
                "date": "{{today}}"
            },
            "is_system": True,
            "sort_order": 1,
        },
        {
            "name": "科技趋势分析",
            "category": "tech_analysis",
            "description": "聚焦科技领域热点趋势，识别技术创新和产业发展方向",
            "prompt_template": """请针对科技领域的热榜数据进行深度分析。

## 分析目标
识别科技创新、产业变革、政策影响等维度的关键信息

## 数据筛选条件
- 关键词过滤：科技、AI、芯片、互联网、5G、新能源、元宇宙、区块链等
- 时间范围：{{date_range}}
- 相关性阈值：{{min_relevance}}

## 分析维度
1. **技术突破**：识别重大技术进展和突破性创新
2. **产业动态**：分析产业链变化和市场竞争格局
3. **资本动向**：投融资事件和估值变化
4. **政策影响**：相关政策对行业的影响评估
5. **国际比较**：国内外技术发展水平对比

## 输出要求
- 使用专业术语但保持可读性
- 提供数据支撑和来源引用
- 给出趋势判断和投资建议

## 原始数据
{{filtered_tech_data}}""",
            "default_params": {
                "keywords": ["科技", "AI", "芯片", "互联网", "新能源"],
                "min_relevance": 0.7,
                "date_range": "7days"
            },
            "is_system": True,
            "sort_order": 2,
        },
        {
            "name": "舆情监测报告",
            "category": "sentiment",
            "description": "监控负面/正面舆情分布，识别潜在风险和机会",
            "prompt_template": """请对以下热榜数据进行舆情分析和情感倾向监测。

## 监测目标
识别正面、负面、中性舆情的分布情况及变化趋势

## 分析参数
- 监测时间：{{monitor_period}}
- 情感词典：使用标准中文情感分析词典
- 阈值设置：
  - 高度负面阈值：{{negative_threshold}}
  - 高度正面阈值：{{positive_threshold}}

## 分析框架
1. **情感分布统计**
   - 正面/负面/中性占比
   - 情感强度分布图描述

2. **负面舆情预警**
   - 识别高风险话题（超过负面阈值的）
   - 分析传播路径和影响范围
   - 给出应对建议

3. **正面舆情挖掘**
   - 发现品牌/产品正面评价
   - 识别口碑传播机会

4. **趋势预测**
   - 舆情走向预判
   - 关键节点提醒

## 输出格式
包含统计图表说明、风险等级标识、行动建议的完整报告

## 原始数据
{{sentiment_data}}""",
            "default_params": {
                "monitor_period": "24h",
                "negative_threshold": 0.7,
                "positive_threshold": 0.8
            },
            "is_system": True,
            "sort_order": 3,
        },
        {
            "name": "个性化推荐",
            "category": "recommendation",
            "description": "基于用户兴趣标签的个性化内容推荐分析",
            "prompt_template": """请根据用户兴趣偏好，从热榜数据中筛选并推荐最相关的内容。

## 用户画像
- 兴趣标签：{{user_interests}}
- 历史偏好：{{history_preferences}}
- 排除关键词：{{exclude_keywords}}

## 推荐策略
1. **精准匹配**：与用户兴趣高度相关的内容（相关性 > 0.8）
2. **拓展发现**：可能感兴趣的新领域内容（相关性 0.5-0.8）
3. **多样性保证**：覆盖不同主题和来源平台
4. **时效性优先**：最新发布的热点优先展示

## 推荐结果格式
对于每条推荐内容，提供：
- 标题和简要摘要
- 相关性评分和匹配理由
- 来源平台和时间
- 推荐理由（一句话）

## 分类汇总
- 🔥 必读推荐（Top 10）
- 📚 深度阅读（长文/分析类）
- ⚡ 快讯速览（短平快资讯）
- 💡 拓展视野（跨领域发现）

## 原始数据
{{all_hotspots}}""",
            "default_params": {
                "user_interests": ["科技", "财经", "社会热点"],
                "history_preferences": {},
                "exclude_keywords": ["广告", "推广"]
            },
            "is_system": True,
            "sort_order": 4,
        },
        {
            "name": "周报自动生成",
            "category": "weekly_report",
            "description": "自动生成周度趋势报告，适合定期汇报使用",
            "prompt_template": """请生成一份完整的周度热点趋势报告。

## 报告周期
- 开始日期：{{week_start}}
- 结束日期：{{week_end}}
- 报告生成时间：{{report_time}}

## 报告结构

### 一、本周概览（Executive Summary）
- 本周热点总数及环比变化
- 最受关注的5大主题
- 与上周对比的关键变化

### 二、热点排行榜（Top 30）
| 排名 | 标题 | 热度指数 | 平台 | 趋势 |
|------|------|----------|------|------|
... （自动填充）

### 三、专题深度分析
选择3个最具影响力的事件进行深入分析：
1. 事件背景和起因
2. 发展脉络和时间线
3. 各方反应和观点
4. 影响评估和后续展望

### 四、平台对比分析
各平台热点特征的差异化分析

### 五、下周展望
基于本周趋势预测下周可能的热点方向

### 六、附录
- 数据来源说明
- 统计方法说明
- 术语表

## 输出要求
- 专业、客观、数据驱动
- 图表用文字描述呈现
- 总字数控制在3000-5000字

## 原始数据
{{weekly_data}}""",
            "default_params": {
                "week_start": "{{last_monday}}",
                "week_end": "{{last_sunday}}",
                "report_time": "{{now}}"
            },
            "is_system": True,
            "sort_order": 5,
        },
    ]

    for template_data in default_templates:
        existing = db.query(AIAnalysisTemplate).filter_by(
            name=template_data["name"]
        ).first()
        if not existing:
            template = AIAnalysisTemplate(**template_data)
            db.add(template)

    db.commit()
    logger.info(f"已初始化 {len(default_templates)} 个系统预设模板")


# 初始化默认通知模板
def init_default_notification_templates(db):
    """初始化默认的通知模板"""
    default_templates = [
        {
            "name": "简洁列表",
            "description": "以简洁列表形式展示热点信息",
            "content": """🔥 {{date}} 热点速递

{% for item in items %}
{{loop.index}}. {{item.title}}
   🔗 {{item.url}}
   📊 热度: {{item.hot_score}}
   📍 {{item.platform}}
{% endfor %}

---
由 TrendRadar 自动生成""",
        },
        {
            "name": "详细卡片",
            "description": "以卡片形式展示详细信息",
            "content": """<h2>🔥 {{date}} 热点报告</h2>

{% for item in items %}
<div style="margin-bottom: 15px; padding: 10px; border: 1px solid #ddd; border-radius: 5px;">
  <h3>{{loop.index}}. {{item.title}}</h3>
  <p><strong>热度:</strong> {{item.hot_score}}</p>
  <p><strong>来源:</strong> {{item.platform}}</p>
  <p><a href="{{item.url}}">查看详情</a></p>
</div>
{% endfor %}

<p><em>由 TrendRadar 自动生成于 {{generated_at}}</em></p>""",
        },
        {
            "name": "Markdown 格式",
            "description": "标准的 Markdown 格式，适合技术团队",
            "content": """# 🔥 {{date}} 热点速递

## 统计概览
- 总条目数: {{items|length}}
- 最高热度: {% if items %}{{items[0].hot_score}}{% endif %}

## 热点列表

{% for item in items %}
### {{loop.index}}. {{item.title}}

- **热度**: {{item.hot_score}}
- **平台**: {{item.platform}}
- **链接**: [查看详情]({{item.url}})
{% endfor %}

---

*由 TrendRadar 自动生成 | {{generated_at}}*""",
        },
    ]

    logger.info(f"已准备 {len(default_templates)} 个默认通知模板")
    return default_templates


# ========== 独立用户体系模型 ==========
import re

class User(Base):
    """本地用户表 - 独立用户体系"""
    __tablename__ = "users"

    username = Column(String(50), primary_key=True, comment="用户名")
    password_hash = Column(Text, nullable=False, comment="bcrypt 密码哈希")
    nickname = Column(String(100), nullable=True, comment="昵称")
    email = Column(String(255), unique=True, nullable=True, comment="邮箱")
    avatar = Column(String(500), nullable=True, comment="头像 URL")
    role = Column(String(32), nullable=False, default='user', comment="角色: super_admin / user")
    is_active = Column(Boolean, nullable=False, default=True, comment="是否启用")
    force_change_password = Column(Boolean, nullable=False, default=False, comment="强制改密标记")
    login_count = Column(Integer, default=0, comment="登录次数")
    last_login_at = Column(DateTime, nullable=True, comment="最后登录时间")
    last_login_ip = Column(String(45), nullable=True, comment="最后登录 IP")
    failed_attempts = Column(Integer, default=0, comment="连续失败次数")
    locked_until = Column(DateTime, nullable=True, comment="锁定截止时间")
    remark = Column(Text, nullable=True, comment="管理员备注")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    @validates('username')
    def validate_username(self, key, username):
        if not re.match(r'^[a-zA-Z0-9_]{3,20}$', username):
            raise ValueError("用户名必须为 3-20 位字母、数字或下划线")
        return username

    @validates('email')
    def validate_email(self, key, email):
        if email and not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
            raise ValueError("邮箱格式不合法")
        return email


class LoginLog(Base):
    """登录日志表"""
    __tablename__ = "login_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), nullable=False, index=True, comment="用户名")
    ip_address = Column(String(45), nullable=True, comment="IP 地址")
    user_agent = Column(Text, nullable=True, comment="浏览器 UA")
    success = Column(Boolean, nullable=False, comment="是否成功")
    failure_reason = Column(String(100), nullable=True, comment="失败原因")
    created_at = Column(DateTime, default=datetime.utcnow, index=True, comment="创建时间")


# ========== 用户管理与权限控制（RBAC）相关模型 ==========

class Role(Base):
    """角色定义表"""
    __tablename__ = "roles"

    id = Column(String(32), primary_key=True, comment="角色标识: super_admin / user")
    name = Column(String(50), nullable=False, unique=True, comment="角色显示名称")
    description = Column(Text, nullable=True, comment="角色描述")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")

    # 关联关系
    permissions = relationship("RolePermission", back_populates="role", lazy="dynamic",
                               cascade="all, delete-orphan")
    users = relationship("UserRole", back_populates="role", lazy="dynamic",
                         cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("id IN ('super_admin', 'user')", name='ck_role_id'),
    )


class Permission(Base):
    """权限定义表"""
    __tablename__ = "permissions"

    id = Column(String(64), primary_key=True, comment="权限标识: user:list, source:manage ...")
    name = Column(String(100), nullable=False, comment="权限名称")
    category = Column(String(32), nullable=False, comment="分类: user_manage / system_config / content_access")
    description = Column(Text, nullable=True, comment="权限描述")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")

    # 关联关系
    roles = relationship("RolePermission", back_populates="permission", lazy="dynamic",
                         cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_permissions_category", "category"),
        CheckConstraint(
            "category IN ('user_manage', 'system_config', 'content_access')",
            name='ck_permission_category'
        ),
    )


class RolePermission(Base):
    """角色-权限关联表"""
    __tablename__ = "role_permissions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    role_id = Column(String(32), ForeignKey("roles.id", ondelete="CASCADE"), nullable=False,
                     comment="角色ID")
    permission_id = Column(String(64), ForeignKey("permissions.id", ondelete="CASCADE"),
                           nullable=False, comment="权限ID")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")

    # 关联关系
    role = relationship("Role", back_populates="permissions")
    permission = relationship("Permission", back_populates="roles")

    __table_args__ = (
        UniqueConstraint("role_id", "permission_id", name="uq_role_permission"),
        Index("idx_rp_role_id", "role_id"),
        Index("idx_rp_permission_id", "permission_id"),
    )


class UserRole(Base):
    """用户-角色关联表"""
    __tablename__ = "user_roles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(255), nullable=False, unique=True, comment="关联 we-mp-rss users.username")
    role_id = Column(String(32), ForeignKey("roles.id", ondelete="CASCADE"), nullable=False,
                     comment="角色ID")
    assigned_by = Column(String(255), nullable=True, comment="分配者用户名")
    assigned_at = Column(DateTime, default=datetime.utcnow, comment="分配时间")
    remark = Column(Text, nullable=True, comment="管理员备注")

    # 关联关系
    role = relationship("Role", back_populates="users")

    __table_args__ = (
        Index("idx_user_roles_username", "username"),
    )

    @validates('username')
    def validate_username(self, key, value):
        if not value or len(value.strip()) == 0:
            raise ValueError("用户名不能为空")
        return value.strip()


class UserOperationLog(Base):
    """用户操作日志表（append-only，不可删除/修改）"""
    __tablename__ = "user_operation_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    operator = Column(String(255), nullable=False, comment="操作人用户名")
    action = Column(String(32), nullable=False,
                    comment="操作类型: update_role / disable / enable / batch_update / update_info")
    target_user = Column(String(255), nullable=False, comment="目标用户名")
    detail = Column(Text, nullable=True, comment="变更详情 JSON")
    ip_address = Column(String(45), nullable=True, comment="操作 IP 地址")
    user_agent = Column(Text, nullable=True, comment="浏览器 User-Agent")
    created_at = Column(DateTime, default=datetime.utcnow, comment="操作时间")

    __table_args__ = (
        Index("idx_logs_operator", "operator"),
        Index("idx_logs_action", "action"),
        Index("idx_logs_target_user", "target_user"),
        Index("idx_logs_created_at", "created_at"),
        CheckConstraint(
            "action IN ('update_role', 'disable', 'enable', 'batch_update', 'update_info')",
            name='ck_log_action'
        ),
    )


class UserStats(Base):
    """用户统计表（可选，也可从 we-mp-rss 同步）"""
    __tablename__ = "user_stats"

    username = Column(String(255), primary_key=True, comment="用户名（关联 we-mp-rss）")
    login_count = Column(Integer, default=0, comment="登录次数")
    last_login_at = Column(DateTime, nullable=True, comment="最后登录时间")
    last_login_ip = Column(String(45), nullable=True, comment="最后登录 IP")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")


# ========== RBAC 预设数据初始化函数 ==========

def init_rbac_data(db):
    """
    初始化 RBAC 预设数据：2 个角色 + 16 个权限 + 角色权限映射

    Args:
        db: SQLAlchemy Session
    """
    from sqlalchemy import text

    # ---- 1. 初始化角色 ----
    roles_data = [
        {"id": "super_admin", "name": "超级管理员", "description": "拥有所有权限，可管理用户、配置系统、查看所有数据"},
        {"id": "user", "name": "普通用户", "description": "平台基础功能使用者：热点查看、AI 分析、公众号内容、媒体文件"},
    ]

    for r in roles_data:
        existing = db.query(Role).filter_by(id=r["id"]).first()
        if not existing:
            db.add(Role(**r))

    # ---- 2. 初始化权限 ----
    permissions_data = [
        # 用户管理 (user_manage)
        ("user:list", "查看用户列表", "user_manage", "查看用户列表及详情"),
        ("user:edit", "编辑用户信息", "user_manage", "修改用户昵称、邮箱等"),
        ("user:disable", "禁用/启用账号", "user_manage", "更改用户账号启用状态"),
        ("user:batch", "批量操作", "user_manage", "批量修改角色或状态"),

        # 系统配置 (system_config)
        ("source:manage", "管理信息源", "system_config", "管理热榜源/网站源/公众号"),
        ("config:crawler", "配置爬虫规则", "system_config", "设置爬取参数和过滤规则"),
        ("config:schedule", "设置定时任务", "system_config", "配置调度策略"),
        ("config:notification", "管理通知渠道", "system_config", "配置订阅和推送"),

        # 内容/数据访问 (content_access)
        ("hotspot:view", "查看热点数据", "content_access", "浏览热榜和热点信息"),
        ("hotspot:export", "导出热点数据", "content_access", "导出热点数据为文件"),
        ("ai:analysis", "使用 AI 分析", "content_access", "发起 AI 分析任务"),
        ("ai:template_manage", "管理 AI 模板", "content_access", "创建/编辑/删除分析模板"),
        ("wechat:view", "查看公众号内容", "content_access", "浏览公众号文章"),
        ("media:view", "查看媒体文件", "content_access", "浏览图片和视频"),
    ]

    for perm in permissions_data:
        existing = db.query(Permission).filter_by(id=perm[0]).first()
        if not existing:
            db.add(Permission(
                id=perm[0], name=perm[1], category=perm[2], description=perm[3]
            ))

    db.flush()

    # ---- 3. 初始化角色-权限映射 ----
    # 超级管理员：拥有全部权限
    super_admin_role = db.query(Role).filter_by(id="super_admin").first()
    if super_admin_role:
        all_perms = db.query(Permission).all()
        for perm in all_perms:
            exists = db.query(RolePermission).filter_by(
                role_id=super_admin_role.id, permission_id=perm.id
            ).first()
            if not exists:
                db.add(RolePermission(role_id=super_admin_role.id, permission_id=perm.id))

    # 普通用户：仅内容访问类非管理权限
    user_role = db.query(Role).filter_by(id="user").first()
    if user_role:
        user_permissions = [
            "hotspot:view", "ai:analysis", "wechat:view", "media:view"
        ]
        for perm_id in user_permissions:
            exists = db.query(RolePermission).filter_by(
                role_id=user_role.id, permission_id=perm_id
            ).first()
            if not exists:
                db.add(RolePermission(role_id=user_role.id, permission_id=perm_id))

    db.commit()

    role_count = db.query(Role).count()
    perm_count = db.query(Permission).count()
    rp_count = db.query(RolePermission).count()

    logger.info(f"RBAC 数据初始化完成: {role_count} 个角色, {perm_count} 个权限, {rp_count} 条映射")

    # 确保至少存在一个超级管理员
    ensure_admin_exists(db)


def ensure_admin_exists(db):
    """
    确保系统中至少存在一个超级管理员账号

    策略：
    1. 检查 user_roles 表中是否已有 super_admin
    2. 若无，尝试将 "admin" 用户设为超级管理员
    3. 若 "admin" 不存在，尝试从 we-mp-rss 获取第一个用户

    Args:
        db: SQLAlchemy Session
    """
    from sqlalchemy import text

    # 检查是否已有超级管理员
    existing_admin = db.query(UserRole).filter_by(role_id="super_admin").first()
    if existing_admin:
        logger.info(f"已存在超级管理员: {existing_admin.username}")
        return

    # 候选用户名列表（按优先级）
    candidates = ["admin"]

    # 尝试从 we-mp-rss 获取第一个可用用户
    try:
        from app.integrations import is_wemp_running, get_wemp_client
        if is_wemp_running():
            wemp = get_wemp_client()
            result = wemp.get("/api/v1/users", timeout=3)
            if result and isinstance(result, list) and len(result) > 0:
                first_user = result[0]
                uname = first_user.get("username")
                if uname and uname not in candidates:
                    candidates.append(uname)
    except Exception as e:
        logger.debug(f"从 we-mp-rss 获取用户列表失败（非致命）: {e}")

    # 逐个尝试候选用户
    for username in candidates:
        if not username:
            continue

        # 检查该用户在 user_roles 中是否存在
        existing = db.query(UserRole).filter_by(username=username).first()

        if existing:
            # 已有记录但不是管理员 → 升级
            old_role = existing.role_id
            existing.role_id = "super_admin"
            existing.assigned_by = "system"
            existing.assigned_at = datetime.utcnow()
            db.add(
                UserOperationLog(
                    operator="system",
                    action="update_role",
                    target_user=username,
                    detail='{"old_role":"' + old_role + '","new_role":"super_admin","reason":"初始种子数据"}',
                )
            )
            db.commit()
            logger.info(f"已将用户 {username} 从 {old_role} 升级为超级管理员（初始种子）")
            return

        else:
            # 无记录 → 新建 super_admin 角色
            try:
                new_admin = UserRole(
                    username=username,
                    role_id="super_admin",
                    assigned_by="system",
                    remark="系统自动分配的初始超级管理员",
                )
                db.add(new_admin)
                db.add(
                    UserOperationLog(
                        operator="system",
                        action="update_role",
                        target_user=username,
                        detail='{"role":"super_admin","reason":"初始种子数据"}',
                    )
                )
                db.commit()
                logger.info(f"已创建初始超级管理员: {username}")
                return
            except Exception as e:
                logger.warning(f"创建超级管理员 {username} 失败: {e}")
                continue

    logger.warning("未能自动创建超级管理员，请手动通过 API 分配角色")
