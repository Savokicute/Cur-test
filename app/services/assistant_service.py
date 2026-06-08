# coding=utf-8
"""
智能助手对话服务

核心业务逻辑层，负责：
- 多轮对话上下文管理
- 工具调用路由和结果回传
- 对话历史持久化（SQLite）
- 流式响应支持
"""

import logging
import json
import uuid
import asyncio
from typing import Dict, Any, List, Optional, AsyncGenerator
from datetime import datetime
from dataclasses import dataclass, field, asdict

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, JSON, ForeignKey,
    create_engine, Index
)
from sqlalchemy.orm import DeclarativeBase, sessionmaker

logger = logging.getLogger(__name__)


# ========== 数据库模型 ==========

class Base(DeclarativeBase):
    pass


class ChatSession(Base):
    """对话会话表"""
    __tablename__ = "chat_sessions"

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(256), nullable=True, comment="会话标题")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    message_count = Column(Integer, default=0, comment="消息数量")

    __table_args__ = (
        Index("idx_chat_sessions_updated", "updated_at"),
    )


class ChatMessage(Base):
    """聊天消息表"""
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(
        String(64),
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role = Column(String(16), nullable=False, comment="角色: user/assistant/system/tool")
    content = Column(Text, nullable=True, comment="消息内容")
    tool_calls = Column(JSON, nullable=True, comment="工具调用信息")
    tool_call_id = Column(String(64), nullable=True, comment="工具调用ID")
    metadata_ = Column(JSON, nullable=True, comment="元数据")
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_chat_messages_session_created", "session_id", "created_at"),
    )


# ========== 数据库管理 ==========

_db_path = None
_engine = None
_session_factory = None


def _get_database_path():
    """获取数据库路径"""
    global _db_path
    if _db_path is None:
        from hot_content_bridge.config import BridgeConfig
        cfg = BridgeConfig.load()
        _db_path = cfg.data_dir / "assistant.db"
    return _db_path


def _get_engine():
    """获取数据库引擎"""
    global _engine
    if _engine is None:
        db_path = _get_database_path()
        _engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False},
            echo=False,
        )
        Base.metadata.create_all(_engine)
    return _engine


def _get_session_factory():
    """获取 Session 工厂"""
    global _session_factory
    if _session_factory is None:
        engine = _get_engine()
        _session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    return _session_factory


# ========== 服务类 ==========

@dataclass
class DialogueContext:
    """对话上下文"""
    session_id: str
    messages: List[Dict[str, Any]] = field(default_factory=list)
    max_history: int = 20  # 最大保留消息数


@dataclass
class ChatResponse:
    """对话响应"""
    content: str
    role: str = "assistant"
    session_id: str = ""
    message_id: int = 0
    tool_calls: Optional[List[Dict[str, Any]]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class AssistantService:
    """
    智能助手服务

    提供完整的对话功能，包括上下文管理、工具调用、历史记录等。
    """

    def __init__(self):
        """初始化服务"""
        self._contexts: Dict[str, DialogueContext] = {}
        self._system_prompt = self._load_system_prompt()

    # ========== 公开方法 ==========

    async def chat(
        self,
        message: str,
        session_id: Optional[str] = None,
        allowed_tools: Optional[List[str]] = None,
    ) -> ChatResponse:
        """
        执行对话（非流式）

        Args:
            message: 用户消息
            session_id: 会话ID
            allowed_tools: 允许使用的工具列表

        Returns:
            ChatResponse 响应对象
        """
        # 获取或创建会话
        context = await self._get_or_create_context(session_id)

        # 保存用户消息
        user_msg = await self._save_message(
            session_id=context.session_id,
            role="user",
            content=message,
        )
        context.messages.append({
            "role": "user",
            "content": message,
            "id": user_msg.id,
        })

        # 构建对话历史
        dialogue_history = self._build_dialogue_history(context)

        # 生成回复（包含工具调用逻辑）
        response = await self._generate_response(
            message=message,
            history=dialogue_history,
            allowed_tools=allowed_tools,
            session_id=context.session_id,
        )

        # 保存助手回复
        assistant_msg = await self._save_message(
            session_id=context.session_id,
            role=response.role,
            content=response.content,
            tool_calls=response.tool_calls,
            metadata=response.metadata,
        )

        response.message_id = assistant_msg.id
        response.session_id = context.session_id

        # 更新上下文
        context.messages.append({
            "role": response.role,
            "content": response.content,
            "id": assistant_msg.id,
            "tool_calls": response.tool_calls,
        })

        # 更新会话时间
        await self._update_session(context.session_id)

        return response

    async def stream_chat(
        self,
        message: str,
        session_id: Optional[str] = None,
        allowed_tools: Optional[List[str]] = None,
    ) -> AsyncGenerator[str, None]:
        """
        流式对话

        使用 SSE (Server-Sent Events) 格式返回。

        Args:
            message: 用户消息
            session_id: 会话ID
            allowed_tools: 允许使用的工具列表

        Yields:
            SSE 格式的字符串
        """
        # 获取或创建会话
        context = await self._get_or_create_context(session_id)

        # 保存用户消息
        user_msg = await self._save_message(
            session_id=context.session_id,
            role="user",
            content=message,
        )
        context.messages.append({
            "role": "user",
            "content": message,
            "id": user_msg.id,
        })

        # 发送开始事件
        yield self._format_sse_event("start", {
            "session_id": context.session_id,
            "timestamp": datetime.now().isoformat(),
        })

        # 构建对话历史
        dialogue_history = self._build_dialogue_history(context)

        # 生成流式回复
        full_content = ""
        async for chunk in self._generate_stream_response(
            message=message,
            history=dialogue_history,
            allowed_tools=allowed_tools,
            session_id=context.session_id,
        ):
            full_content += chunk
            yield self._format_sse_event("message", {
                "content": chunk,
                "delta": chunk,
            })

        # 保存完整回复
        assistant_msg = await self._save_message(
            session_id=context.session_id,
            role="assistant",
            content=full_content,
        )

        # 更新上下文
        context.messages.append({
            "role": "assistant",
            "content": full_content,
            "id": assistant_msg.id,
        })

        # 更新会话
        await self._update_session(context.session_id)

        # 发送结束事件
        yield self._format_sse_event("done", {
            "message_id": assistant_msg.id,
            "session_id": context.session_id,
            "timestamp": datetime.now().isoformat(),
        })

    async def get_history(
        self,
        session_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """
        获取对话历史

        Args:
            session_id: 会话ID
            limit: 数量限制
            offset: 偏移量

        Returns:
            历史记录字典
        """
        session_factory = _get_session_factory()
        db = session_factory()

        try:
            query = db.query(ChatMessage).order_by(ChatMessage.created_at.desc())

            if session_id:
                query = query.filter(ChatMessage.session_id == session_id)

            total = query.count()
            items = query.offset(offset).limit(limit).all()

            return {
                "items": [self._message_to_dict(msg) for msg in reversed(items)],
                "total": total,
                "has_more": (offset + limit) < total,
            }

        finally:
            db.close()

    async def clear_history(self, session_id: Optional[str] = None) -> int:
        """
        清除对话历史

        Args:
            session_id: 会话ID（不填则清除所有）

        Returns:
            清除的消息数量
        """
        session_factory = _get_session_factory()
        db = session_factory()

        try:
            query = db.query(ChatMessage)

            if session_id:
                query = query.filter(ChatMessage.session_id == session_id)

            count = query.count()
            query.delete()

            # 清除对应的会话
            if session_id:
                db.query(ChatSession).filter(ChatSession.id == session_id).delete()
            else:
                db.query(ChatSession).delete()

            db.commit()

            # 清除内存中的上下文
            if session_id and session_id in self._contexts:
                del self._contexts[session_id]
            elif not session_id:
                self._contexts.clear()

            return count

        finally:
            db.close()

    async def list_sessions(self, limit: int = 20, offset: int = 0) -> Dict[str, Any]:
        """
        列出所有会话

        Args:
            limit: 数量限制
            offset: 偏移量

        Returns:
            会话列表
        """
        session_factory = _get_session_factory()
        db = session_factory()

        try:
            sessions = (
                db.query(ChatSession)
                .order_by(ChatSession.updated_at.desc())
                .offset(offset)
                .limit(limit)
                .all()
            )

            total = db.query(ChatSession).count()

            return {
                "items": [
                    {
                        "id": s.id,
                        "title": s.title,
                        "created_at": s.created_at.isoformat() if s.created_at else None,
                        "updated_at": s.updated_at.isoformat() if s.updated_at else None,
                        "message_count": s.message_count,
                    }
                    for s in sessions
                ],
                "total": total,
                "has_more": (offset + limit) < total,
            }

        finally:
            db.close()

    async def delete_session(self, session_id: str) -> bool:
        """
        删除指定会话

        Args:
            session_id: 会话ID

        Returns:
            是否删除成功
        """
        session_factory = _get_session_factory()
        db = session_factory()

        try:
            session = db.query(ChatSession).filter(ChatSession.id == session_id).first()

            if not session:
                return False

            # 删除关联的消息
            db.query(ChatMessage).filter(ChatMessage.session_id == session_id).delete()
            db.delete(session)
            db.commit()

            # 清除内存中的上下文
            if session_id in self._contexts:
                del self._contexts[session_id]

            return True

        finally:
            db.close()

    # ========== 内部方法 ==========

    async def _get_or_create_context(self, session_id: Optional[str]) -> DialogueContext:
        """获取或创建对话上下文"""
        if session_id and session_id in self._contexts:
            return self._contexts[session_id]

        # 创建新会话
        new_session_id = session_id or str(uuid.uuid4())

        # 确保数据库中存在该会话
        session_factory = _get_session_factory()
        db = session_factory()

        try:
            existing = db.query(ChatSession).filter(ChatSession.id == new_session_id).first()

            if not existing:
                new_session = ChatSession(id=new_session_id)
                db.add(new_session)
                db.commit()

            # 加载历史消息到上下文
            messages = (
                db.query(ChatMessage)
                .filter(ChatMessage.session_id == new_session_id)
                .order_by(ChatMessage.created_at.asc())
                .limit(self._get_max_history())
                .all()
            )

            context = DialogueContext(
                session_id=new_session_id,
                messages=[self._message_to_dict(msg) for msg in messages],
            )

            self._contexts[new_session_id] = context

            return context

        finally:
            db.close()

    def _build_dialogue_history(self, context: DialogueContext) -> List[Dict[str, Any]]:
        """构建用于模型输入的对话历史"""
        messages = []

        # 添加系统提示词
        messages.append({
            "role": "system",
            "content": self._system_prompt,
        })

        # 添加历史消息（限制数量）
        recent_messages = context.messages[-self._get_max_history():]

        for msg in recent_messages:
            msg_dict = {
                "role": msg["role"],
                "content": msg.get("content", ""),
            }

            if msg.get("tool_calls"):
                msg_dict["tool_calls"] = msg["tool_calls"]

            if msg.get("tool_call_id"):
                msg_dict["tool_call_id"] = msg["tool_call_id"]

            messages.append(msg_dict)

        return messages

    async def _generate_response(
        self,
        message: str,
        history: List[Dict[str, Any]],
        allowed_tools: Optional[List[str]],
        session_id: str,
    ) -> ChatResponse:
        """
        生成回复（可能包含工具调用）

        实现简化的工具调用逻辑：
        1. 分析用户意图
        2. 决定是否需要调用工具
        3. 如需调用，执行工具并整合结果
        4. 生成最终回复
        """
        from app.services.mcp_tools import registry

        # 分析用户意图，决定是否使用工具
        tool_decision = self._analyze_intent(message, allowed_tools)

        tool_results = []

        if tool_decision["should_call_tool"]:
            # 执行工具调用
            for tool_call in tool_decision["tool_calls"]:
                tool_name = tool_call["name"]
                arguments = tool_call["arguments"]

                logger.info(f"调用工具: {tool_name}, 参数: {arguments}")

                result = await registry.invoke_tool(
                    name=tool_name,
                    arguments=arguments,
                )

                tool_results.append({
                    "call_id": result["call_id"],
                    "tool_name": tool_name,
                    "success": result["success"],
                    "result": result["result"],
                    "error": result["error"],
                })

                # 保存工具调用结果作为消息
                await self._save_message(
                    session_id=session_id,
                    role="tool",
                    content=json.dumps(result, ensure_ascii=False),
                    tool_call_id=result["call_id"],
                )

        # 生成最终回复
        content = self._generate_final_response(
            original_message=message,
            tool_results=tool_results,
            history=history,
        )

        return ChatResponse(
            content=content,
            session_id=session_id,
            tool_calls=tool_results if tool_results else None,
            metadata={
                "tool_calls_count": len(tool_results),
                "model": "builtin-rules-v1",
                "generated_at": datetime.now().isoformat(),
            },
        )

    async def _generate_stream_response(
        self,
        message: str,
        history: List[Dict[str, Any]],
        allowed_tools: Optional[List[str]],
        session_id: str,
    ) -> AsyncGenerator[str, None]:
        """
        生成流式回复

        简化实现：先完成所有处理，然后分块输出。
        """
        # 先获取完整响应
        response = await self._generate_response(
            message=message,
            history=history,
            allowed_tools=allowed_tools,
            session_id=session_id,
        )

        # 模拟流式输出：按句子或段落分块
        content = response.content
        chunks = self._split_into_chunks(content)

        for chunk in chunks:
            # 模拟网络延迟
            await asyncio.sleep(0.02)
            yield chunk

    def _analyze_intent(
        self,
        message: str,
        allowed_tools: Optional[List[str]],
    ) -> Dict[str, Any]:
        """
        分析用户意图，决定是否需要调用工具

        使用规则匹配的方式判断是否应该调用工具。

        Args:
            message: 用户消息
            allowed_tools: 允许的工具列表

        Returns:
            {
                "should_call_tool": bool,
                "tool_calls": [...],
                "confidence": float,
            }
        """
        message_lower = message.lower().strip()

        # 关键词匹配规则
        intent_rules = [
            # 搜索热榜相关
            {
                "keywords": ["热榜", "热搜", "热点", "热门", "今天", "新闻", "搜索"],
                "tool": "search_hotspots",
                "extract_params": self._extract_search_params,
            },
            # 文章详情相关
            {
                "keywords": ["文章", "详情", "内容", "查看文章", "阅读"],
                "tool": "get_article_detail",
                "extract_params": self._extract_article_params,
            },
            # 关键词分析相关
            {
                "keywords": ["关键词", "趋势", "热门词", "话题", "关键词分析"],
                "tool": "get_trending_keywords",
                "extract_params": self._extract_keywords_params,
            },
            # 统计数据相关
            {
                "keywords": ["统计", "数据", "概览", "平台", "总体", "汇总"],
                "tool": "get_platform_stats",
                "extract_params": self._extract_stats_params,
            },
        ]

        for rule in intent_rules:
            # 检查关键词匹配
            match_count = sum(1 for kw in rule["keywords"] if kw in message_lower)

            if match_count >= 1:  # 至少匹配一个关键词
                # 检查工具是否在允许列表中
                if allowed_tools and rule["tool"] not in allowed_tools:
                    continue

                # 提取参数
                params = rule["extract_params"](message)

                return {
                    "should_call_tool": True,
                    "tool_calls": [{
                        "name": rule["tool"],
                        "arguments": params,
                    }],
                    "confidence": min(match_count / len(rule["keywords"]), 1.0),
                }

        return {
            "should_call_tool": False,
            "tool_calls": [],
            "confidence": 0.0,
        }

    def _extract_search_params(self, message: str) -> Dict[str, Any]:
        """提取搜索参数"""
        import re

        params = {}

        # 提取日期
        date_match = re.search(r'(\d{4}-\d{2}-\d{2}|今天|昨天|前天)', message)
        if date_match:
            from datetime import timedelta
            date_str = date_match.group(1)
            if date_str == "今天":
                params["date"] = datetime.now().strftime("%Y-%m-%d")
            elif date_str == "昨天":
                params["date"] = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            elif date_str == "前天":
                params["date"] = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
            else:
                params["date"] = date_str

        # 提取数量
        num_match = re.search(r'(\d+)\s*(条|个|项)', message)
        if num_match:
            params["limit"] = int(num_match.group(1))

        # 提取平台
        platforms = ["百度", "微博", "知乎", "抖音", "baidu", "weibo", "zhihu", "douyin"]
        for platform in platforms:
            if platform in message:
                params["platform"] = platform.lower() if platform.isascii() else {
                    "百度": "baidu",
                    "微博": "weibo",
                    "知乎": "zhihu",
                    "抖音": "douyin",
                }.get(platform, platform)
                break

        # 提取关键词（排除其他已识别的参数）
        keywords = re.sub(r'(\d+\s*(条|个|项)|\d{4}-\d{2}-\d{2}|今天|昨天|前天)', '', message)
        keywords = re.sub(r'(热榜|热搜|热点|热门|新闻|搜索|帮我|给我|看看|查查|找找|的)', '', keywords).strip()
        if keywords:
            params["keyword"] = keywords

        return params

    def _extract_article_params(self, message: str) -> Dict[str, Any]:
        """提取文章参数"""
        import re

        # 尝试提取文章ID（假设是数字或特定格式）
        id_match = re.search(r'(?:文章|ID|id)\s*[:：]?\s*([a-zA-Z0-9_-]+)', message)
        if id_match:
            return {"article_id": id_match.group(1)}

        # 如果没有明确ID，尝试从URL或其他格式提取
        url_match = re.search(r'https?://[^\s]+', message)
        if url_match:
            return {"article_id": url_match.group(0)}

        return {"article_id": ""}  # 需要用户提供具体ID

    def _extract_keywords_params(self, message: str) -> Dict[str, Any]:
        """提取关键词查询参数"""
        import re

        params = {}

        # 提取日期
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', message)
        if date_match:
            params["date"] = date_match.group(1)

        # 提取数量
        num_match = re.search(r'(\d+)\s*(条|个|项)', message)
        if num_match:
            params["limit"] = int(num_match.group(1))

        return params

    def _extract_stats_params(self, message: str) -> Dict[str, Any]:
        """提取统计参数"""
        import re

        params = {}

        # 提取日期范围
        date_range_match = re.search(r'(\d{4}-\d{2}-\d{2})\s*[~至到,-]+\s*(\d{4}-\d{2}-\d{2})', message)
        if date_range_match:
            params["date_range"] = f"{date_range_match.group(1)},{date_range_match.group(2)}"

        return params

    def _generate_final_response(
        self,
        original_message: str,
        tool_results: List[Dict[str, Any]],
        history: List[Dict[str, Any]],
    ) -> str:
        """
        根据工具调用结果生成最终回复

        使用模板和规则生成自然语言回复。
        """
        if not tool_results:
            # 无工具调用，生成通用回复
            return self._generate_general_response(original_message)

        # 有工具调用结果，格式化输出
        response_parts = []

        for result in tool_results:
            if result["success"]:
                formatted = self._format_tool_result(result)
                response_parts.append(formatted)
            else:
                response_parts.append(f"⚠️ **工具调用失败**: {result['error']}")

        # 组合回复
        main_response = "\n\n".join(response_parts)

        # 添加总结和建议
        summary = self._generate_summary(original_message, tool_results)

        if summary:
            return f"{main_response}\n\n---\n\n{summary}"

        return main_response

    def _format_tool_result(self, result: Dict[str, Any]) -> str:
        """格式化单个工具的结果"""
        tool_name = result["tool_name"]
        data = result["result"]

        formatters = {
            "search_hotspots": self._format_search_result,
            "get_article_detail": self._format_article_result,
            "get_trending_keywords": self._format_keywords_result,
            "get_platform_stats": self._format_stats_result,
        }

        formatter = formatters.get(tool_name, self._format_generic_result)
        return formatter(data)

    def _format_search_result(self, data: Dict[str, Any]) -> str:
        """格式化搜索结果"""
        items = data.get("items", [])
        total = data.get("total", 0)
        query = data.get("query", {})

        if not items:
            return f"🔍 未找到符合条件的熱榜数据。\n\n查询条件: {query}"

        lines = [f"🔍 **找到 {total} 条熱榜数据**\n"]

        for i, item in enumerate(items[:15], 1):  # 最多显示15条
            trend_icon = {
                "up": "📈",
                "down": "📉",
                "same": "➡️",
                "new": "🆕",
            }.get(item.get("trend"), "")

            line = f"{i}. {trend_icon} **{item['title']}**"
            if item.get("platform"):
                line += f" [{item['platform']}]"
            if item.get("rank"):
                line += f" (排名: #{item['rank']})"
            lines.append(line)

        if total > 15:
            lines.append(f"\n... 还有 {total - 15} 条结果")

        return "\n".join(lines)

    def _format_article_result(self, data: Dict[str, Any]) -> str:
        """格式化文章详情"""
        lines = [f"📄 **{data.get('title', '未知标题')}**\n"]

        if data.get("author"):
            lines.append(f"**作者**: {data['author']}")

        if data.get("source"):
            lines.append(f"**来源**: {data['source']}")

        if data.get("publish_time"):
            lines.append(f"**发布时间**: {data['publish_time']}")

        lines.append("\n---\n")

        content = data.get("content", "")
        if content:
            # 截断过长内容
            if len(content) > 2000:
                content = content[:2000] + "\n\n...(内容过长，已截断)"
            lines.append(content)
        else:
            lines.append("*暂无内容*")

        if data.get("url"):
            lines.append(f"\n\n🔗 [查看原文]({data['url']})")

        return "\n".join(lines)

    def _format_keywords_result(self, data: Dict[str, Any]) -> str:
        """格式化关键词结果"""
        keywords = data.get("keywords", [])
        total = data.get("total", 0)

        if not keywords:
            return "🏷️ 当前暂无热门关键词数据。"

        lines = [f"🏷️ **热门关键词 TOP {min(total, len(keywords))}**\n"]

        for i, kw in enumerate(keywords[:20], 1):
            if isinstance(kw, dict):
                word = kw.get("word") or kw.get("keyword") or kw.get("text", "")
                count = kw.get("count") or kw.get("frequency") or kw.get("weight", "")
                line = f"{i}. **{word}"
                if count:
                    line += f"** ({count})"
                line += ")"
                lines.append(line)
            elif isinstance(kw, str):
                lines.append(f"{i}. **{kw}**")
            else:
                lines.append(f"{i}. {kw}")

        return "\n".join(lines)

    def _format_stats_result(self, data: Dict[str, Any]) -> str:
        """格式化统计数据"""
        lines = ["📊 **平台统计概览**\n"]

        lines.append(f"- **总热点数**: {data.get('total_items', 0)}")
        lines.append(f"- **覆盖天数**: {data.get('total_dates', 0)}")

        platforms = data.get("platforms", {})
        if platforms:
            lines.append("\n**各平台分布:**")
            for platform, count in list(platforms.items())[:10]:
                lines.append(f"  - {platform}: {count} 条")

        top_items = data.get("top_items", [])
        if top_items:
            lines.append("\n**当前 Top 热点:**")
            for item in top_items[:5]:
                rank = item.get("rank", "-")
                title = item.get("title", "未知")
                platform = item.get("platform", "")
                lines.append(f"  {rank}. {title} [{platform}]")

        return "\n".join(lines)

    def _format_generic_result(self, data: Any) -> str:
        """通用格式化"""
        return json.dumps(data, ensure_ascii=False, indent=2)

    def _generate_general_response(self, message: str) -> str:
        """生成通用回复（无工具调用时）"""
        # 简单的问候和引导
        greetings = ["你好", "您好", "hi", "hello", "嗨"]
        if any(g in message.lower() for g in greetings):
            return """你好！我是热点发现平台的智能助手 🤖

我可以帮你：

- 🔍 **搜索热榜** - 查看各平台的热门话题
- 📄 **查看文章** - 获取文章详细内容
- 🏷️ **关键词分析** - 了解当前热门趋势
- 📊 **数据统计** - 查看平台整体情况

你可以直接问我问题，比如：
- "今天最热的10条新闻"
- "科技领域有什么热点？"
- "帮我总结今天的趋势"

请问有什么可以帮你的吗？"""

        # 其他情况的默认回复
        return f"""我理解你想了解关于 "{message}" 的信息。

目前我可以通过以下方式帮助你：

1. **搜索热榜** - 说"今天的热榜"或"科技热点"
2. **查看文章** - 提供具体的文章ID
3. **关键词分析** - 问"现在的热门话题"
4. **数据统计** - 问"平台整体情况"

请告诉我你更想了解哪个方面的信息？"""

    def _generate_summary(
        self,
        original_message: str,
        tool_results: List[Dict[str, Any]],
    ) -> Optional[str]:
        """生成总结和建议"""
        successful_results = [r for r in tool_results if r["success"]]

        if not successful_results:
            return None

        tools_used = [r["tool_name"] for r in successful_results]

        suggestions = []
        if "search_hotspots" in tools_used:
            suggestions.append("- 💡 你可以点击任意热点查看详细信息")
        if "get_trending_keywords" in tools_used:
            suggestions.append("- 💡 可以根据这些关键词深入搜索相关热榜")
        if "get_platform_stats" in tools_used:
            suggestions.append("- 💡 可以按平台筛选查看更详细的数据")

        if suggestions:
            return "**建议下一步操作:**\n" + "\n".join(suggestions)

        return None

    # ========== 辅助方法 ==========

    async def _save_message(
        self,
        session_id: str,
        role: str,
        content: Optional[str],
        tool_calls: Optional[List[Dict]] = None,
        tool_call_id: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> ChatMessage:
        """保存消息到数据库"""
        session_factory = _get_session_factory()
        db = session_factory()

        try:
            msg = ChatMessage(
                session_id=session_id,
                role=role,
                content=content,
                tool_calls=tool_calls,
                tool_call_id=tool_call_id,
                metadata_=metadata,
            )
            db.add(msg)
            db.commit()
            db.refresh(msg)

            # 更新会话消息计数
            session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
            if session:
                session.message_count = (
                    db.query(ChatMessage)
                    .filter(ChatMessage.session_id == session_id)
                    .count()
                )
                db.commit()

            return msg

        finally:
            db.close()

    async def _update_session(self, session_id: str):
        """更新会话的最后更新时间"""
        session_factory = _get_session_factory()
        db = session_factory()

        try:
            session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
            if session:
                session.updated_at = datetime.utcnow()
                db.commit()

        finally:
            db.close()

    def _message_to_dict(self, msg: ChatMessage) -> Dict[str, Any]:
        """将消息对象转换为字典"""
        return {
            "id": msg.id,
            "session_id": msg.session_id,
            "role": msg.role,
            "content": msg.content,
            "tool_calls": msg.tool_calls,
            "tool_call_id": msg.tool_call_id,
            "metadata": msg.metadata_,
            "created_at": msg.created_at.isoformat() if msg.created_at else None,
        }

    @staticmethod
    def _split_into_chunks(text: str, chunk_size: int = 30) -> List[str]:
        """将文本分成块（用于流式输出）"""
        if len(text) <= chunk_size:
            return [text] if text else [""]

        chunks = []
        current_chunk = ""

        for char in text:
            current_chunk += char
            if len(current_chunk) >= chunk_size and char in ['。', '！', '？', '\n', ' ', ',']:
                chunks.append(current_chunk)
                current_chunk = ""

        if current_chunk:
            chunks.append(current_chunk)

        return chunks if chunks else [text]

    @staticmethod
    def _format_sse_event(event_type: str, data: Any) -> str:
        """格式化 SSE 事件"""
        return f"data: {json.dumps(data, ensure_ascii=False)}\nevent: {event_type}\n\n"

    @staticmethod
    def _get_max_history() -> int:
        """获取最大历史消息数"""
        return 20

    @staticmethod
    def _load_system_prompt() -> str:
        """加载系统提示词"""
        return """你是一个专业的热点发现平台智能助手，基于 TrendRadar 数据源。

## 你的能力

1. **热榜查询**: 可以搜索各平台的热榜数据（百度、微博、知乎、抖音等）
2. **文章详情**: 可以获取文章的详细内容和摘要
3. **关键词分析**: 可以分析当前热门关键词和趋势
4. **平台统计**: 可以提供平台整体的数据统计和分析

## 回答原则

- 使用中文回答（除非用户明确要求其他语言）
- 提供准确、有价值的信息
- 当需要数据时，主动调用相关工具获取最新信息
- 对于趋势分析，给出客观的解读和建议
- 保持专业但友好的语气
- 如果无法回答某个问题，诚实说明并建议替代方案

## 格式要求

- 使用 Markdown 格式组织回答
- 重要信息使用加粗或列表突出显示
- 数据引用时注明来源和时间
- 长回答使用分段和标题结构化"""
