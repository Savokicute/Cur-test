# coding=utf-8
"""通知服务 - 支持多种通知渠道

支持的渠道：
- RSS: 生成 RSS/Atom Feed
- Webhook: HTTP POST 推送
- Email: 邮件发送（预留）
- DingTalk: 钉钉机器人
- WeChatWork: 企业微信机器人
- Slack: Slack Webhook

功能：
1. 订阅管理 (CRUD)
2. 多种发送器实现
3. 内容格式化与模板渲染
4. 过滤条件处理
5. 发送日志记录
6. 测试发送功能
"""

import asyncio
import hashlib
import hmac
import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import httpx
from jinja2 import Template, TemplateSyntaxError

from app.core.database import get_db_session
from app.models import (
    Subscription,
    NotificationLog,
    SubscriptionType,
    NotificationStatus,
)
from app.services.cache_service import CacheService, CacheKey, get_cache_service

logger = logging.getLogger(__name__)


class NotificationService:
    """
    通知服务主类

    提供订阅管理、消息发送、日志记录等功能
    """

    def __init__(self):
        self.cache = get_cache_service()
        self._http_client: Optional[httpx.AsyncClient] = None

    async def _get_http_client(self) -> httpx.AsyncClient:
        """获取 HTTP 客户端（懒加载）"""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(
                timeout=30.0,
                follow_redirects=True,
            )
        return self._http_client

    async def close(self):
        """关闭 HTTP 客户端"""
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()

    # ========== 订阅管理 ==========

    async def create_subscription(self, data: Dict[str, Any]) -> Subscription:
        """
        创建新的订阅

        Args:
            data: 订阅数据字典，包含：
                  - name: 名称
                  - subscription_type: 类型
                  - target_url: 目标地址
                  - target_config: 配置
                  - filter_config: 过滤条件
                  - format_template: 格式模板
                  - schedule_cron: 调度表达式
                  - trigger_mode: 触发模式

        Returns:
            Subscription 对象
        """
        with get_db_session() as db:
            # 验证必需字段
            name = data.get("name", "").strip()
            if not name:
                raise ValueError("订阅名称不能为空")

            sub_type = data.get("subscription_type", SubscriptionType.WEBHOOK.value)

            subscription = Subscription(
                name=name,
                description=data.get("description"),
                subscription_type=sub_type,
                target_url=data.get("target_url"),
                target_config=data.get("target_config"),
                filter_config=data.get("filter_config", {}),
                format_template=data.get("format_template"),
                schedule_cron=data.get("schedule_cron"),
                trigger_mode=data.get("trigger_mode", "manual"),
                is_active=data.get("is_active", True),
            )

            db.add(subscription)
            db.flush()  # 获取ID
            db.refresh(subscription)

            logger.info(f"创建订阅成功: {subscription.id} - {name}")

            # 清除缓存
            await self.cache.invalidate_subscriptions()

            return subscription

    async def update_subscription(self, subscription_id: int, data: Dict[str, Any]) -> Optional[Subscription]:
        """更新订阅"""
        with get_db_session() as db:
            subscription = db.query(Subscription).filter_by(id=subscription_id).first()
            if not subscription:
                return None

            # 更新允许的字段
            updatable_fields = [
                "name", "description", "subscription_type", "target_url",
                "target_config", "filter_config", "format_template",
                "schedule_cron", "trigger_mode", "is_active"
            ]

            for field in updatable_fields:
                if field in data:
                    setattr(subscription, field, data[field])

            db.flush()
            db.refresh(subscription)

            # 清除缓存
            await self.cache.invalidate_subscriptions()

            logger.info(f"更新订阅成功: {subscription_id}")
            return subscription

    async def delete_subscription(self, subscription_id: int) -> bool:
        """删除订阅"""
        with get_db_session() as db:
            subscription = db.query(Subscription).filter_by(id=subscription_id).first()
            if not subscription:
                return False

            db.delete(subscription)

            # 清除缓存
            await self.cache.invalidate_subscriptions()

            logger.info(f"删除订阅成功: {subscription_id}")
            return True

    async def list_subscriptions(
        self,
        is_active: Optional[bool] = None,
        subscription_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> tuple[List[Subscription], int]:
        """
        列出订阅

        Returns:
            (订阅列表, 总数)
        """
        cache_key = CacheKey.subscription()

        # 尝试从缓存获取
        cached = await self.cache.get(cache_key)
        if cached and not is_active and not subscription_type:
            return cached[:offset+limit], len(cached)

        with get_db_session() as db:
            query = db.query(Subscription)

            if is_active is not None:
                query = query.filter(Subscription.is_active == is_active)
            if subscription_type:
                query = query.filter(Subscription.subscription_type == subscription_type)

            total = query.count()
            subscriptions = query.order_by(Subscription.created_at.desc()).offset(offset).limit(limit).all()

            result = list(subscriptions)

            # 缓存完整列表（仅无过滤条件时）
            if not is_active and not subscription_type:
                all_subs = db.query(Subscription).order_by(Subscription.created_at.desc()).all()
                await self.cache.set(cache_key, list(all_subs), ttl=300)

            return result, total

    async def get_subscription(self, subscription_id: int) -> Optional[Subscription]:
        """获取单个订阅详情"""
        cache_key = CacheKey.subscription(subscription_id)

        cached = await self.cache.get(cache_key)
        if cached:
            return cached

        with get_db_session() as db:
            subscription = db.query(Subscription).filter_by(id=subscription_id).first()
            if subscription:
                await self.cache.set(cache_key, subscription, ttl=300)
            return subscription

    # ========== 触发与测试 ==========

    async def trigger_subscription(self, subscription_id: int, items: List[Dict] = None) -> NotificationLog:
        """
        触发订阅（执行通知发送）

        Args:
            subscription_id: 订阅ID
            items: 要推送的数据条目（可选，如果不提供则自动获取）

        Returns:
            NotificationLog 日志对象
        """
        subscription = await self.get_subscription(subscription_id)
        if not subscription:
            raise ValueError(f"订阅不存在: {subscription_id}")

        if not subscription.is_active:
            raise ValueError(f"订阅已禁用: {subscription_id}")

        # 更新触发统计
        subscription.total_triggers += 1
        subscription.last_triggered_at = datetime.utcnow()

        # 创建日志记录
        log = NotificationLog(
            subscription_id=subscription_id,
            status=NotificationStatus.PENDING.value,
            created_at=datetime.utcnow(),
        )

        try:
            # 如果没有提供items，尝试获取最新热榜数据
            if items is None:
                items = await self._get_items_for_subscription(subscription)

            # 应用过滤条件
            filtered_items = await self._apply_filters(items, subscription.filter_config or {})

            # 格式化内容
            content = await self.format_content(filtered_items, subscription.format_template)

            log.content_summary = f"{len(filtered_items)} 条目" if filtered_items else "无匹配项"
            log.sent_content = content
            log.items_count = len(filtered_items)

            # 根据类型发送
            log.sent_at = datetime.utcnow()

            success = False
            if subscription.subscription_type == SubscriptionType.RSS.value:
                success = await self.send_rss_notification(subscription, filtered_items)
            elif subscription.subscription_type == SubscriptionType.WEBHOOK.value:
                success = await self.send_webhook_notification(subscription, {"items": filtered_items, "content": content})
            elif subscription.subscription_type == SubscriptionType.DINGTALK.value:
                success = await self.send_dingtalk_notification(subscription, content)
            elif subscription.subscription_type == SubscriptionType.WECHAT_WORK.value:
                success = await self.send_wechat_work_notification(subscription, content)
            elif subscription.subscription_type == SubscriptionType.SLACK.value:
                success = await self.send_slack_notification(subscription, content)
            elif subscription.subscription_type == SubscriptionType.EMAIL.value:
                success = await self.send_email_notification(subscription, content)
            else:
                raise ValueError(f"不支持的通知类型: {subscription.subscription_type}")

            if success:
                log.status = NotificationStatus.SENT.value
                subscription.success_count += 1
                subscription.last_success_at = datetime.utcnow()
                subscription.error_message = None
                logger.info(f"通知发送成功: 订阅={subscription_id}, 条目数={len(filtered_items)}")
            else:
                log.status = NotificationStatus.FAILED.value
                subscription.failure_count += 1
                subscription.error_message = "发送失败"
                logger.warning(f"通知发送失败: 订阅={subscription_id}")

        except Exception as e:
            log.status = NotificationStatus.FAILED.value
            log.error_message = str(e)
            subscription.failure_count += 1
            subscription.error_message = str(e)[:500]
            logger.error(f"通知触发异常: 订阅={subscription_id}, 错误={e}", exc_info=True)

        finally:
            log.completed_at = datetime.utcnow()

            # 保存日志
            with get_db_session() as db:
                db.add(log)
                # 更新订阅统计
                sub = db.query(Subscription).filter_by(id=subscription_id).first()
                if sub:
                    sub.total_triggers = subscription.total_triggers
                    sub.success_count = subscription.success_count
                    sub.failure_count = subscription.failure_count
                    sub.last_triggered_at = subscription.last_triggered_at
                    sub.last_success_at = subscription.last_success_at
                    sub.error_message = subscription.error_message

            # 清除缓存
            await self.cache.invalidate_notification_logs(subscription_id)

        return log

    async def test_subscription(self, subscription_id: int) -> Dict[str, Any]:
        """
        测试订阅发送（使用测试数据）

        Returns:
            测试结果字典
        """
        subscription = await self.get_subscription(subscription_id)
        if not subscription:
            return {"success": False, "error": "订阅不存在"}

        # 生成测试数据
        test_items = [
            {
                "title": "[测试] 这是一条测试热点",
                "url": "https://example.com/test",
                "hot_score": 9999,
                "platform": "test",
                "summary": "这是一条用于测试通知配置的模拟数据",
                "rank": 1,
            },
            {
                "title": "[测试] 另一条测试热点",
                "url": "https://example.com/test2",
                "hot_score": 8888,
                "platform": "test",
                "summary": "第二条测试数据",
                "rank": 2,
            },
        ]

        start_time = datetime.utcnow()

        try:
            log = await self.trigger_subscription(subscription_id, test_items)

            duration = (datetime.utcnow() - start_time).total_seconds()

            return {
                "success": log.status == NotificationStatus.SENT.value,
                "log_id": log.id,
                "status": log.status,
                "duration_seconds": round(duration, 2),
                "error": log.error_message,
                "sent_at": log.sent_at.isoformat() if log.sent_at else None,
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "duration_seconds": round((datetime.utcnow() - start_time).total_seconds(), 2),
            }

    # ========== 发送器实现 ==========

    async def send_rss_notification(self, subscription: Subscription, items: List[Dict]) -> bool:
        """RSS 通知：生成并保存 RSS 文件"""
        try:
            rss_content = await self.generate_rss_feed(items, subscription.target_config or {})

            output_path = subscription.target_url
            if output_path:
                import os
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(rss_content)
                logger.info(f"RSS文件已生成: {output_path}")
                return True
            else:
                logger.error("RSS输出路径未设置")
                return False

        except Exception as e:
            logger.error(f"RSS生成失败: {e}", exc_info=True)
            return False

    async def send_webhook_notification(self, subscription: Subscription, data: Dict) -> bool:
        """Webhook 通知：HTTP POST 推送"""
        try:
            url = subscription.target_url
            if not url:
                raise ValueError("Webhook URL 未设置")

            config = subscription.target_config or {}
            headers = {}

            # 认证处理
            auth_type = config.get("auth_type", "none")

            if auth_type == "bearer":
                token = config.get("token", "")
                headers["Authorization"] = f"Bearer {token}"
            elif auth_type == "basic":
                username = config.get("username", "")
                password = config.get("password", "")
                import base64
                credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
                headers["Authorization"] = f"Basic {credentials}"

            # 自定义Headers
            custom_headers = config.get("headers", {})
            headers.update(custom_headers)

            # 默认Content-Type
            if "Content-Type" not in headers:
                headers["Content-Type"] = "application/json"

            client = await self._get_http_client()
            response = await client.post(url, json=data, headers=headers, timeout=30.0)

            if response.status_code >= 200 and response.status_code < 300:
                logger.info(f"Webhook发送成功: {url}, status={response.status_code}")
                return True
            else:
                logger.warning(f"Webhook返回错误状态码: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Webhook发送失败: {e}", exc_info=True)
            return False

    async def send_dingtalk_notification(self, subscription: Subscription, content: str) -> bool:
        """钉钉机器人通知"""
        try:
            webhook_url = subscription.target_url
            if not webhook_url:
                raise ValueError("钉钉 Webhook URL 未设置")

            config = subscription.target_config or {}
            msg_type = config.get("msg_type", "text")
            at_all = config.get("at_all", False)

            payload = {
                "msgtype": msg_type,
            }

            if msg_type == "text":
                payload["text"] = {
                    "content": content
                }
                if at_all:
                    payload["at"] = {"isAtAll": True}
            elif msg_type == "markdown":
                payload["markdown"] = {
                    "title": "热点推送",
                    "text": content
                }

            client = await self._get_http_client()
            response = await client.post(webhook_url, json=payload, timeout=15.0)

            result = response.json()
            if result.get("errcode") == 0:
                logger.info("钉钉通知发送成功")
                return True
            else:
                logger.warning(f"钉钉返回错误: {result}")
                return False

        except Exception as e:
            logger.error(f"钉钉通知发送失败: {e}", exc_info=True)
            return False

    async def send_wechat_work_notification(self, subscription: Subscription, content: str) -> bool:
        """企业微信机器人通知"""
        try:
            webhook_url = subscription.target_url
            if not webhook_url:
                raise ValueError("企业微信 Webhook URL 未设置")

            config = subscription.target_config or {}
            msg_type = config.get("msg_type", "text")

            payload = {
                "msgtype": msg_type,
            }

            if msg_type == "text":
                payload["text"] = {"content": content}
            elif msg_type == "markdown":
                payload["markdown"] = {"content": content}

            client = await self._get_http_client()
            response = await client.post(webhook_url, json=payload, timeout=15.0)

            result = response.json()
            if result.get("errcode") == 0:
                logger.info("企业微信通知发送成功")
                return True
            else:
                logger.warning(f"企业微信返回错误: {result}")
                return False

        except Exception as e:
            logger.error(f"企业微信通知发送失败: {e}", exc_info=True)
            return False

    async def send_slack_notification(self, subscription: Subscription, content: str) -> bool:
        """Slack Webhook 通知"""
        try:
            webhook_url = subscription.target_url
            if not webhook_url:
                raise ValueError("Slack Webhook URL 未设置")

            config = subscription.target_config or {}
            channel = config.get("channel", "#general")
            username = config.get("username", "TrendRadar Bot")

            payload = {
                "channel": channel,
                "username": username,
                "text": content,
                "mrkdwn": True,
            }

            client = await self._get_http_client()
            response = await client.post(webhook_url, json=payload, timeout=15.0)

            if response.status_code == 200:
                logger.info("Slack通知发送成功")
                return True
            else:
                logger.warning(f"Slack返回错误: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Slack通知发送失败: {e}", exc_info=True)
            return False

    async def send_email_notification(self, subscription: Subscription, content: str) -> bool:
        """
        邮件通知（预留接口）

        需要安装 aiosmtplib 或类似库才能使用
        """
        logger.info("邮件通知功能暂未完全实现，请后续配置SMTP服务")
        # TODO: 实现邮件发送逻辑
        # 可以使用 aiosmtplib 或 sendgrid 等
        return True  # 暂时返回成功

    # ========== 内容格式化 ==========

    async def format_content(self, items: List[Dict], template_str: Optional[str] = None) -> str:
        """
        使用模板格式化内容

        支持的变量：
        - {{date}}: 当前日期
        - {{generated_at}}: 生成时间
        - {{items|length}}: 条目数量
        - 循环中的变量：
          - {{item.title}}: 标题
          - {{item.url}}: 链接
          - {{item.hot_score}}: 热度分数
          - {{item.platform}}: 平台
          - {{item.summary}}: 摘要
          - {{item.rank}}: 排名
          - {{loop.index}}: 序号
        """
        now = datetime.now()

        # 如果没有自定义模板，使用默认模板
        if not template_str:
            template_str = """🔥 {{date.strftime('%Y-%m-%d')}} 热点速递

{% for item in items %}
{{loop.index}}. **{{item.title}}**
   🔗 {{item.url}}
   📊 热度: {{item.hot_score}}
   📍 {{item.platform}}
{% endfor %}

---
由 TrendRadar 自动生成于 {{generated_at.strftime('%Y-%m-%d %H:%M:%S')}}
"""

        try:
            template = Template(template_str)
            rendered = template.render(
                date=now,
                generated_at=now,
                items=items or [],
            )
            return rendered

        except TemplateSyntaxError as e:
            logger.error(f"模板语法错误: {e}")
            return self._fallback_format(items)

    async def generate_rss_feed(self, items: List[Dict], config: Dict) -> str:
        """生成 RSS/Atom Feed"""
        now = datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0000")

        feed_title = config.get("feed_title", "TrendRadar 热点推送")
        feed_description = config.get("feed_description", "实时热点信息聚合")
        feed_link = config.get("feed_link", "https://example.com")
        max_items = config.get("max_items", 50)

        items = (items or [])[:max_items]

        item_xmls = []
        for item in items:
            pub_date = ""
            if item.get("publish_time") or item.get("_source_date"):
                pub_date = f"<pub_date>{item.get('publish_time') or item.get('_source_date')}</pub_date>"

            item_xml = f"""
            <item>
              <title><![CDATA[{self._escape_xml(item.get('title', ''))}]]></title>
              <link>{item.get('url', '')}</link>
              <description><![CDATA[{self._escape_xml(item.get('summary', item.get('title', '')))}]]></description>
              {pub_date}
              <guid isPermaLink="false">{item.get('news_id', item.get('url', ''))}</guid>
            </item>"""
            item_xmls.append(item_xml)

        rss_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>{self._escape_xml(feed_title)}</title>
    <link>{feed_link}</link>
    <description>{self._escape_xml(feed_description)}</description>
    <language>zh-CN</language>
    <lastBuildDate>{now}</lastBuildDate>
    <generator>TrendRadar</generator>
    {''.join(item_xmls)}
  </channel>
</rss>"""

        return rss_xml

    @staticmethod
    def _escape_xml(text: str) -> str:
        """转义XML特殊字符"""
        return (text
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;"))

    def _fallback_format(self, items: List[Dict]) -> str:
        """备用简单格式化"""
        lines = [f"🔥 热点速递 ({datetime.now().strftime('%Y-%m-%d %H:%M')})\n"]

        for i, item in enumerate((items or [])[:20], 1):
            lines.append(
                f"{i}. {item.get('title', 'N/A')}\n"
                f"   🔗 {item.get('url', 'N/A')}\n"
                f"   📊 热度: {item.get('hot_score', 'N/A')} | "
                f"📍 {item.get('platform', 'N/A')}\n"
            )

        lines.append("\n--- 由 TrendRadar 自动生成 ---")
        return "\n".join(lines)

    # ========== 辅助方法 ==========

    async def _get_items_for_subscription(self, subscription: Subscription) -> List[Dict]:
        """根据订阅配置获取数据项"""
        try:
            from app.integrations import TrendRadarReader
            reader = TrendRadarReader()

            # 获取最近的热榜数据
            hotspots_data = reader.read_hotspots(days=1)

            # 展平为列表
            items = []
            for platform, platform_hotspots in hotspots_data.items():
                for hotspot in platform_hotspots:
                    items.append({
                        **hotspot,
                        "platform_name": platform,
                    })

            return items

        except Exception as e:
            logger.error(f"获取订阅数据失败: {e}", exc_info=True)
            return []

    async def _apply_filters(self, items: List[Dict], filter_config: Dict) -> List[Dict]:
        """应用过滤条件"""
        if not items:
            return items

        filtered = items

        # 关键词过滤
        include_keywords = filter_config.get("include_keywords", [])
        exclude_keywords = filter_config.get("exclude_keywords", [])

        if include_keywords:
            filtered = [
                item for item in filtered
                if any(kw.lower() in (item.get("title") or "").lower() for kw in include_keywords)
            ]

        if exclude_keywords:
            filtered = [
                item for item in filtered
                if not any(kw.lower() in (item.get("title") or "").lower() for kw in exclude_keywords)
            ]

        # 平台过滤
        platforms = filter_config.get("platforms", [])
        if platforms:
            filtered = [
                item for item in filtered
                if item.get("platform_name") or item.get("platform_id") in platforms
            ]

        # 最低热度过滤
        min_hot_score = filter_config.get("min_hot_score", 0)
        if min_hot_score > 0:
            filtered = [
                item for item in filtered
                if (item.get("hot_score") or 0) >= min_hot_score
            ]

        # 最大条目数限制
        max_items = filter_config.get("max_items", 100)
        filtered = filtered[:max_items]

        return filtered

    # ========== 日志查询 ==========

    async def get_notification_logs(
        self,
        subscription_id: Optional[int] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> tuple[List[NotificationLog], int]:
        """
        查询通知日志

        Returns:
            (日志列表, 总数)
        """
        with get_db_session() as db:
            query = db.query(NotificationLog)

            if subscription_id:
                query = query.filter(NotificationLog.subscription_id == subscription_id)
            if status:
                query = query.filter(NotificationLog.status == status)

            total = query.count()
            logs = query.order_by(NotificationLog.created_at.desc()).offset(offset).limit(limit).all()

            return list(logs), total

    async def get_stats(self) -> Dict[str, Any]:
        """获取通知服务统计信息"""
        with get_db_session() as db:
            total_subs = db.query(Subscription).count()
            active_subs = db.query(Subscription).filter(Subscription.is_active == True).count()

            # 今日触发次数
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            today_logs = db.query(NotificationLog).filter(
                NotificationLog.created_at >= today_start
            )
            today_triggers = today_logs.count()
            today_sent = today_logs.filter(NotificationLog.status == NotificationStatus.SENT.value).count()
            today_failed = today_logs.filter(NotificationLog.status == NotificationStatus.FAILED.value).count()

            # 成功率
            success_rate = (today_sent / today_triggers * 100) if today_triggers > 0 else 0

            # 按类型统计
            type_stats = {}
            for sub_type in SubscriptionType:
                count = db.query(Subscription).filter(
                    Subscription.subscription_type == sub_type.value
                ).count()
                type_stats[sub_type.value] = count

            return {
                "total_subscriptions": total_subs,
                "active_subscriptions": active_subs,
                "today_triggers": today_triggers,
                "today_sent": today_sent,
                "today_failed": today_failed,
                "success_rate": round(success_rate, 2),
                "by_type": type_stats,
            }

    async def get_templates(self) -> List[Dict[str, str]]:
        """获取可用的通知模板列表"""
        from app.models import init_default_notification_templates
        templates = init_default_notification_templates(None)
        return templates


# ========== 全局单例 ==========
_notification_service: Optional[NotificationService] = None


def get_notification_service() -> NotificationService:
    """获取全局通知服务实例"""
    global _notification_service
    if _notification_service is None:
        _notification_service = NotificationService()
    return _notification_service
