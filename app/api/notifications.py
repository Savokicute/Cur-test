# coding=utf-8
"""通知管理 API 路由

RESTful 端点：
  POST   /api/notifications/subscriptions        # 创建订阅
  GET    /api/notifications/subscriptions        # 列表
  GET    /api/notifications/subscriptions/{id}   # 详情
  PUT    /api/notifications/subscriptions/{id}   # 更新
  DELETE /api/notifications/subscriptions/{id}   # 删除
  POST   /api/notifications/subscriptions/{id}/trigger  # 手动触发
  POST   /api/notifications/subscriptions/{id}/test     # 测试发送
  GET    /api/notifications/logs                 # 日志列表
  GET    /api/notifications/stats                # 统计信息
  GET    /api/notifications/templates            # 通知模板
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, validator

from app.services.notification_service import get_notification_service

logger = logging.getLogger(__name__)

router = APIRouter()


# ========== Pydantic 模型（请求/响应）==========

class FilterConfigModel(BaseModel):
    """过滤条件模型"""
    include_keywords: Optional[List[str]] = Field(None, description="包含关键词列表")
    exclude_keywords: Optional[List[str]] = Field(None, description="排除关键词列表")
    platforms: Optional[List[str]] = Field(None, description="平台过滤列表")
    min_hot_score: Optional[int] = Field(0, ge=0, le=100000, description="最低热度分数")
    max_items: Optional[int] = Field(50, ge=1, le=500, description="最大推送条目数")


class TargetConfigModel(BaseModel):
    """目标配置模型（Webhook认证等）"""
    auth_type: Optional[str] = Field("none", description="认证类型: none/bearer/basic")
    token: Optional[str] = Field(None, description="Bearer Token")
    username: Optional[str] = Field(None, description="Basic Auth 用户名")
    password: Optional[str] = Field(None, description="Basic Auth 密码")
    headers: Optional[dict] = Field(None, description="自定义请求头")
    msg_type: Optional[str] = Field("text", description="消息类型 (钉钉/企微): text/markdown")
    at_all: Optional[bool] = Field(False, description="@所有人 (钉钉)")
    channel: Optional[str] = Field("#general", description="Slack 频道")
    username: Optional[str] = Field(None, description="Slack 用户名")
    feed_title: Optional[str] = Field(None, description="RSS Feed 标题")
    feed_description: Optional[str] = Field(None, description="RSS Feed 描述")
    feed_link: Optional[str] = Field(None, description="RSS Feed 链接")
    max_items: Optional[int] = Field(50, description="RSS 最大条目数")


class CreateSubscriptionRequest(BaseModel):
    """创建订阅请求"""
    name: str = Field(..., min_length=1, max_length=256, description="订阅名称")
    description: Optional[str] = Field(None, description="订阅描述")
    subscription_type: str = Field(
        "webhook",
        description="订阅类型: rss/webhook/email/dingtalk/wechat_work/slack"
    )
    target_url: Optional[str] = Field(None, description="目标地址")
    target_config: Optional[TargetConfigModel] = Field(None, description="目标配置")
    filter_config: Optional[FilterConfigModel] = Field(None, description="过滤条件")
    format_template: Optional[str] = Field(None, description="格式模板")
    schedule_cron: Optional[str] = Field(None, description="Cron表达式")
    trigger_mode: Optional[str] = Field("manual", description="触发模式: manual/scheduled/event")
    is_active: Optional[bool] = Field(True, description="是否启用")

    @validator('subscription_type')
    def validate_type(cls, v):
        allowed = ["rss", "webhook", "email", "dingtalk", "wechat_work", "slack"]
        if v not in allowed:
            raise ValueError(f'不支持的订阅类型，允许值: {allowed}')
        return v


class UpdateSubscriptionRequest(BaseModel):
    """更新订阅请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=256)
    description: Optional[str] = None
    subscription_type: Optional[str] = None
    target_url: Optional[str] = None
    target_config: Optional[TargetConfigModel] = None
    filter_config: Optional[FilterConfigModel] = None
    format_template: Optional[str] = None
    schedule_cron: Optional[str] = None
    trigger_mode: Optional[str] = None
    is_active: Optional[bool] = None


class SubscriptionResponse(BaseModel):
    """订阅响应"""
    id: int
    name: str
    description: Optional[str]
    subscription_type: str
    target_url: Optional[str]
    target_config: Optional[dict]
    filter_config: Optional[dict]
    format_template: Optional[str]
    schedule_cron: Optional[str]
    trigger_mode: str
    is_active: bool
    last_triggered_at: Optional[str]
    last_success_at: Optional[str]
    total_triggers: int
    success_count: int
    failure_count: int
    success_rate: float
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class NotificationLogResponse(BaseModel):
    """通知日志响应"""
    id: int
    subscription_id: int
    content_summary: Optional[str]
    status: str
    error_message: Optional[str]
    items_count: int
    retry_count: int
    created_at: str
    sent_at: Optional[str]

    class Config:
        from_attributes = True


# ========== 辅助函数 ==========

def _subscription_to_dict(subscription) -> dict:
    """将 Subscription 对象转换为字典"""
    return {
        "id": subscription.id,
        "name": subscription.name,
        "description": subscription.description,
        "subscription_type": subscription.subscription_type,
        "target_url": _mask_sensitive_url(subscription.target_url),
        "target_config": _mask_sensitive_config(subscription.target_config),
        "filter_config": subscription.filter_config,
        "format_template": subscription.format_template,
        "schedule_cron": subscription.schedule_cron,
        "trigger_mode": subscription.trigger_mode,
        "is_active": subscription.is_active,
        "last_triggered_at": subscription.last_triggered_at.isoformat() if subscription.last_triggered_at else None,
        "last_success_at": subscription.last_success_at.isoformat() if subscription.last_success_at else None,
        "total_triggers": subscription.total_triggers,
        "success_count": subscription.success_count,
        "failure_count": subscription.failure_count,
        "success_rate": subscription.success_rate,
        "created_at": subscription.created_at.isoformat() if subscription.created_at else None,
        "updated_at": subscription.updated_at.isoformat() if subscription.updated_at else None,
    }


def _mask_sensitive_url(url: Optional[str]) -> Optional[str]:
    """对URL进行脱敏处理（隐藏敏感信息）"""
    if not url:
        return url

    try:
        # 如果URL包含token或key参数，隐藏其值
        import re
        masked = re.sub(r'(token|key|secret|password)=([^&]+)', r'\1=***', url, flags=re.IGNORECASE)
        return masked
    except Exception:
        return url


def _mask_sensitive_config(config: Optional[dict]) -> Optional[dict]:
    """对配置中的敏感信息进行脱敏"""
    if not config:
        return config

    masked = config.copy()
    sensitive_fields = ["token", "password", "secret", "api_key"]

    for field in sensitive_fields:
        if field in masked and masked[field]:
            masked[field] = "***"

    return masked


def _log_to_dict(log) -> dict:
    """将 NotificationLog 对象转换为字典"""
    return {
        "id": log.id,
        "subscription_id": log.subscription_id,
        "content_summary": log.content_summary,
        "status": log.status,
        "error_message": log.error_message,
        "items_count": log.items_count,
        "retry_count": log.retry_count,
        "created_at": log.created_at.isoformat() if log.created_at else None,
        "sent_at": log.sent_at.isoformat() if log.sent_at else None,
    }


# ========== API 端点实现 ==========

@router.post("/subscriptions", response_model=dict)
async def create_subscription(request: CreateSubscriptionRequest):
    """
    创建新的通知订阅

    支持多种类型：RSS、Webhook、邮件、钉钉、企业微信、Slack
    """
    service = get_notification_service()

    try:
        data = request.dict(exclude_unset=True)

        # 转换嵌套模型为字典
        if isinstance(data.get("target_config"), TargetConfigModel):
            data["target_config"] = data["target_config"].dict(exclude_none=True)
        if isinstance(data.get("filter_config"), FilterConfigModel):
            data["filter_config"] = data["filter_config"].dict(exclude_none=True)

        subscription = await service.create_subscription(data)

        return {
            "success": True,
            "data": _subscription_to_dict(subscription),
            "message": "订阅创建成功",
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"创建订阅失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"创建订阅失败: {str(e)}")


@router.get("/subscriptions", response_model=dict)
async def list_subscriptions(
    is_active: Optional[bool] = Query(None, description="是否仅返回活跃的"),
    subscription_type: Optional[str] = Query(None, description="按类型过滤"),
    limit: int = Query(50, ge=1, le=200, description="每页数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
):
    """获取订阅列表"""
    service = get_notification_service()

    try:
        subscriptions, total = await service.list_subscriptions(
            is_active=is_active,
            subscription_type=subscription_type,
            limit=limit,
            offset=offset,
        )

        return {
            "success": True,
            "data": [_subscription_to_dict(s) for s in subscriptions],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    except Exception as e:
        logger.error(f"获取订阅列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/subscriptions/{subscription_id}", response_model=dict)
async def get_subscription(subscription_id: int):
    """获取单个订阅详情"""
    service = get_notification_service()

    try:
        subscription = await service.get_subscription(subscription_id)
        if not subscription:
            raise HTTPException(status_code=404, detail="订阅不存在")

        return {
            "success": True,
            "data": _subscription_to_dict(subscription),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取订阅详情失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/subscriptions/{subscription_id}", response_model=dict)
async def update_subscription(subscription_id: int, request: UpdateSubscriptionRequest):
    """更新订阅配置"""
    service = get_notification_service()

    try:
        data = request.dict(exclude_unset=True)

        # 转换嵌套模型
        if isinstance(data.get("target_config"), TargetConfigModel):
            data["target_config"] = data["target_config"].dict(exclude_none=True)
        if isinstance(data.get("filter_config"), FilterConfigModel):
            data["filter_config"] = data["filter_config"].dict(exclude_none=True)

        subscription = await service.update_subscription(subscription_id, data)
        if not subscription:
            raise HTTPException(status_code=404, detail="订阅不存在")

        return {
            "success": True,
            "data": _subscription_to_dict(subscription),
            "message": "订阅更新成功",
        }

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"更新订阅失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/subscriptions/{subscription_id}", response_model=dict)
async def delete_subscription(subscription_id: int):
    """删除订阅"""
    service = get_notification_service()

    try:
        success = await service.delete_subscription(subscription_id)
        if not success:
            raise HTTPException(status_code=404, detail="订阅不存在")

        return {
            "success": True,
            "message": "订阅已删除",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除订阅失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/subscriptions/{subscription_id}/trigger", response_model=dict)
async def trigger_subscription(subscription_id: int):
    """手动触发订阅（发送通知）"""
    service = get_notification_service()

    try:
        log = await service.trigger_subscription(subscription_id)

        return {
            "success": log.status == "sent",
            "data": _log_to_dict(log),
            "message": "通知已发送" if log.status == "sent" else f"通知发送失败: {log.error_message}",
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"触发订阅失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/subscriptions/{subscription_id}/test", response_model=dict)
async def test_subscription(subscription_id: int):
    """测试订阅发送（使用模拟数据）"""
    service = get_notification_service()

    try:
        result = await service.test_subscription(subscription_id)

        return {
            **result,
            "message": "测试发送完成",
        }

    except Exception as e:
        logger.error(f"测试订阅失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/logs", response_model=dict)
async def get_notification_logs(
    subscription_id: Optional[int] = Query(None, description="按订阅ID过滤"),
    status: Optional[str] = Query(None, description="按状态过滤: pending/sent/failed"),
    limit: int = Query(50, ge=1, le=200, description="每页数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
):
    """获取通知日志列表"""
    service = get_notification_service()

    try:
        logs, total = await service.get_notification_logs(
            subscription_id=subscription_id,
            status=status,
            limit=limit,
            offset=offset,
        )

        return {
            "success": True,
            "data": [_log_to_dict(l) for l in logs],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    except Exception as e:
        logger.error(f"获取通知日志失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=dict)
async def get_notification_stats():
    """获取通知服务统计信息"""
    service = get_notification_service()

    try:
        stats = await service.get_stats()
        return {
            "success": True,
            "data": stats,
        }

    except Exception as e:
        logger.error(f"获取通知统计失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/templates", response_model=dict)
async def get_notification_templates():
    """获取可用的通知模板列表"""
    service = get_notification_service()

    try:
        templates = await service.get_templates()
        return {
            "success": True,
            "data": templates,
        }

    except Exception as e:
        logger.error(f"获取通知模板失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
