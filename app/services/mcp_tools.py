# coding=utf-8
"""
MCP 工具集成框架 - 遵循 MCP (Model Context Protocol) 规范

提供工具注册、发现、调用和结果回传的完整实现。
支持动态注册新工具，并遵循 MCP 协议的 JSON-RPC 2.0 格式。
"""

import logging
import json
import uuid
from typing import Dict, Any, List, Optional, Callable, Awaitable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class ToolStatus(str, Enum):
    """工具状态枚举"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"


@dataclass
class ToolParameter:
    """MCP 工具参数定义

    遵循 JSON Schema 规范，用于描述工具的输入参数。
    """
    name: str
    type: str  # string, number, boolean, array, object
    description: str = ""
    required: bool = False
    default: Any = None
    enum: Optional[List[Any]] = None
    properties: Optional[Dict[str, Any]] = None  # 用于 object 类型


@dataclass
class MCPTool:
    """MCP 工具定义

    包含工具的元信息、参数 schema 和执行函数。
    """
    name: str
    description: str
    parameters: List[ToolParameter] = field(default_factory=list)
    handler: Optional[Callable[..., Awaitable[Dict[str, Any]]]] = None
    status: ToolStatus = ToolStatus.ACTIVE
    tags: List[str] = field(default_factory=list)
    version: str = "1.0.0"
    created_at: datetime = field(default_factory=datetime.now)
    error_message: Optional[str] = None

    def to_schema(self) -> Dict[str, Any]:
        """转换为 MCP 协议的 tool schema 格式

        Returns:
            符合 MCP 协议规范的工具 schema 字典
        """
        properties = {}
        required = []

        for param in self.parameters:
            prop_def: Dict[str, Any] = {
                "type": param.type,
                "description": param.description,
            }

            if param.enum:
                prop_def["enum"] = param.enum

            if param.default is not None:
                prop_def["default"] = param.default

            if param.properties:
                prop_def["properties"] = param.properties

            properties[param.name] = prop_def

            if param.required:
                required.append(param.name)

        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
            "status": self.status.value,
            "tags": self.tags,
            "version": self.version,
        }


class MCPToolRegistry:
    """
    MCP 工具注册表

    管理所有可用工具的注册、发现和调用。
    采用单例模式，全局共享工具实例。
    """

    _instance: Optional['MCPToolRegistry'] = None
    _tools: Dict[str, MCPTool] = {}

    def __new__(cls) -> 'MCPToolRegistry':
        """单例模式实现"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """初始化工具注册表"""
        self._tools: Dict[str, MCPTool] = {}
        logger.info("MCP 工具注册表已初始化")

    def register_tool(self, tool: MCPTool) -> bool:
        """
        注册新工具

        Args:
            tool: MCPTool 实例

        Returns:
            注册是否成功
        """
        if tool.name in self._tools:
            logger.warning(f"工具 '{tool.name}' 已存在，将被覆盖")
            # 更新现有工具而不是替换，保留状态信息
            existing = self._tools[tool.name]
            existing.handler = tool.handler
            existing.description = tool.description
            existing.parameters = tool.parameters
            existing.version = tool.version
            existing.error_message = None
            existing.status = ToolStatus.ACTIVE
            logger.info(f"工具 '{tool.name}' 已更新")
            return True

        self._tools[tool.name] = tool
        logger.info(f"工具 '{tool.name}' 已注册成功")
        return True

    def unregister_tool(self, name: str) -> bool:
        """
        注销工具

        Args:
            name: 工具名称

        Returns:
            注销是否成功
        """
        if name in self._tools:
            del self._tools[name]
            logger.info(f"工具 '{name}' 已注销")
            return True
        logger.warning(f"工具 '{name}' 不存在")
        return False

    def get_tool(self, name: str) -> Optional[MCPTool]:
        """
        获取工具实例

        Args:
            name: 工具名称

        Returns:
            MCPTool 实例或 None
        """
        return self._tools.get(name)

    def list_tools(
        self,
        status: Optional[ToolStatus] = None,
        tags: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        列出所有工具（支持过滤）

        Args:
            status: 按状态过滤
            tags: 按标签过滤（任一匹配）

        Returns:
            工具 schema 列表
        """
        tools = []

        for tool in self._tools.values():
            # 状态过滤
            if status and tool.status != status:
                continue

            # 标签过滤
            if tags and not any(tag in tool.tags for tag in tags):
                continue

            tools.append(tool.to_schema())

        return tools

    async def invoke_tool(
        self,
        name: str,
        arguments: Dict[str, Any],
        call_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        调用工具

        遵循 MCP 协议的调用格式，返回标准化的响应。

        Args:
            name: 工具名称
            arguments: 参数字典
            call_id: 调用 ID（用于追踪）

        Returns:
            MCP 协议格式的响应 {
                "success": bool,
                "result": Any,
                "error": Optional[str],
                "call_id": str,
                "tool_name": str,
                "timestamp": str
            }
        """
        if not call_id:
            call_id = str(uuid.uuid4())

        tool = self.get_tool(name)

        if not tool:
            return {
                "success": False,
                "result": None,
                "error": f"工具 '{name}' 未找到",
                "call_id": call_id,
                "tool_name": name,
                "timestamp": datetime.now().isoformat(),
            }

        if tool.status != ToolStatus.ACTIVE:
            return {
                "success": False,
                "result": None,
                "error": f"工具 '{name}' 当前不可用: {tool.error_message or '状态异常'}",
                "call_id": call_id,
                "tool_name": name,
                "timestamp": datetime.now().isoformat(),
            }

        if not tool.handler:
            return {
                "success": False,
                "result": None,
                "error": f"工具 '{name}' 缺少执行处理器",
                "call_id": call_id,
                "tool_name": name,
                "timestamp": datetime.now().isoformat(),
            }

        try:
            # 参数验证
            validated_args = self._validate_arguments(tool, arguments)

            # 执行工具
            result = await tool.handler(**validated_args)

            return {
                "success": True,
                "result": result,
                "error": None,
                "call_id": call_id,
                "tool_name": name,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"工具 '{name}' 调用失败: {e}", exc_info=True)
            return {
                "success": False,
                "result": None,
                "error": f"工具执行错误: {str(e)}",
                "call_id": call_id,
                "tool_name": name,
                "timestamp": datetime.now().isoformat(),
            }

    def _validate_arguments(
        self,
        tool: MCPTool,
        arguments: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        验证并规范化工具参数

        Args:
            tool: 工具实例
            arguments: 原始参数

        Returns:
            验证后的参数字典

        Raises:
            ValueError: 参数验证失败
        """
        validated = {}
        errors = []

        for param in tool.parameters:
            value = arguments.get(param.name)

            # 必填检查
            if param.required and value is None:
                if param.default is not None:
                    value = param.default
                else:
                    errors.append(f"缺少必填参数: {param.name}")
                    continue

            # 类型检查（基本验证）
            if value is not None:
                expected_type = param.type
                actual_type = type(value).__name__

                # 类型映射（Python -> JSON Schema）
                type_mapping = {
                    "string": ("str",),
                    "number": ("int", "float"),
                    "boolean": ("bool",),
                    "array": ("list",),
                    "object": ("dict",),
                }

                allowed_types = type_mapping.get(expected_type, (expected_type,))
                if actual_type not in allowed_types:
                    # 尝试类型转换
                    try:
                        if expected_type == "string":
                            value = str(value)
                        elif expected_type == "number":
                            value = float(value) if '.' in str(value) else int(value)
                        elif expected_type == "boolean":
                            value = bool(value)
                    except (ValueError, TypeError):
                        errors.append(
                            f"参数 '{param.name}' 类型错误: 期望 {expected_type}, 实际 {actual_type}"
                        )

            # 枚举值检查
            if param.enum and value is not None and value not in param.enum:
                errors.append(
                    f"参数 '{param.name}' 值不在允许范围内: {param.enum}"
                )

            validated[param.name] = value

        if errors:
            raise ValueError(f"参数验证失败: {'; '.join(errors)}")

        return validated

    def get_stats(self) -> Dict[str, Any]:
        """
        获取工具统计信息

        Returns:
            统计数据字典
        """
        total = len(self._tools)
        active = sum(1 for t in self._tools.values() if t.status == ToolStatus.ACTIVE)
        inactive = sum(1 for t in self._tools.values() if t.status == ToolStatus.INACTIVE)
        error = sum(1 for t in self._tools.values() if t.status == ToolStatus.ERROR)

        # 统计标签分布
        tag_counts: Dict[str, int] = {}
        for tool in self._tools.values():
            for tag in tool.tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

        return {
            "total_tools": total,
            "by_status": {
                "active": active,
                "inactive": inactive,
                "error": error,
            },
            "tags": tag_counts,
            "tool_names": list(self._tools.keys()),
        }


# 全局单例
registry = MCPToolRegistry()


def register_builtin_tools():
    """
    注册内置工具集

    在应用启动时调用，注册平台核心功能作为 MCP 工具。
    """
    from app.services.mcp_tools import (
        search_hotspots_handler,
        get_article_detail_handler,
        get_trending_keywords_handler,
        get_platform_stats_handler,
    )

    # 1. 搜索热榜
    registry.register_tool(MCPTool(
        name="search_hotspots",
        description="搜索热榜数据，支持按日期、平台、关键词过滤",
        parameters=[
            ToolParameter(
                name="date",
                type="string",
                description="查询日期 (YYYY-MM-DD)，不填则获取最新",
                required=False,
            ),
            ToolParameter(
                name="platform",
                type="string",
                description="平台ID筛选 (如 baidu, weibo, zhihu)",
                required=False,
            ),
            ToolParameter(
                name="keyword",
                type="string",
                description="关键词搜索",
                required=False,
            ),
            ToolParameter(
                name="limit",
                type="number",
                description="返回数量限制 (默认50)",
                required=False,
                default=50,
            ),
        ],
        handler=search_hotspots_handler,
        tags=["hotspots", "search", "read"],
    ))

    # 2. 获取文章详情
    registry.register_tool(MCPTool(
        name="get_article_detail",
        description="获取指定文章的详细内容",
        parameters=[
            ToolParameter(
                name="article_id",
                type="string",
                description="文章ID",
                required=True,
            ),
        ],
        handler=get_article_detail_handler,
        tags=["articles", "read", "detail"],
    ))

    # 3. 获取热门关键词
    registry.register_tool(MCPTool(
        name="get_trending_keywords",
        description="获取当前热门关键词和趋势",
        parameters=[
            ToolParameter(
                name="date",
                type="string",
                description="查询日期 (YYYY-MM-DD)",
                required=False,
            ),
            ToolParameter(
                name="limit",
                type="number",
                description="返回数量限制 (默认20)",
                required=False,
                default=20,
            ),
        ],
        handler=get_trending_keywords_handler,
        tags=["keywords", "trends", "analysis"],
    ))

    # 4. 获取平台统计
    registry.register_tool(MCPTool(
        name="get_platform_stats",
        description="获取平台整体统计数据",
        parameters=[
            ToolParameter(
                name="date_range",
                type="string",
                description="日期范围 (如 '2024-01-01,2024-01-07')",
                required=False,
            ),
        ],
        handler=get_platform_stats_handler,
        tags=["stats", "analytics", "overview"],
    ))

    logger.info(f"已注册 {len(registry._tools)} 个内置工具")


# ========== 内置工具处理器实现 ==========

async def search_hotspots_handler(
    date: Optional[str] = None,
    platform: Optional[str] = None,
    keyword: Optional[str] = None,
    limit: int = 50,
) -> Dict[str, Any]:
    """
    搜索热榜处理器

    Args:
        date: 日期
        platform: 平台ID
        keyword: 关键词
        limit: 数量限制

    Returns:
        热榜数据字典
    """
    from app.integrations import TrendRadarReader
    from hot_content_bridge.config import BridgeConfig

    cfg = BridgeConfig.load()
    reader = TrendRadarReader(cfg)

    # 获取热榜数据
    if date:
        _, hotspots = reader.get_hotspots_with_articles(date)
    else:
        hotspots, _ = reader.get_all_hotspots_with_articles()

    # 平台过滤
    if platform:
        hotspots = [h for h in hotspots if h.get("platform_id") == platform]

    # 关键词搜索
    if keyword:
        keyword_lower = keyword.lower()
        hotspots = [
            h for h in hotspots
            if keyword_lower in h.get("title", "").lower()
        ]

    # 限制数量
    hotspots = hotspots[:limit]

    # 格式化返回数据
    items = []
    for item in hotspots:
        items.append({
            "id": item.get("news_id"),
            "title": item.get("title"),
            "platform": item.get("platform_name") or item.get("platform_id"),
            "rank": item.get("rank"),
            "url": item.get("url_norm"),
            "trend": _calculate_trend(item.get("rank_history", [])),
            "fetched_at": item.get("_crawl_time_full") or item.get("last_crawl_time"),
        })

    return {
        "total": len(items),
        "items": items,
        "query": {"date": date, "platform": platform, "keyword": keyword},
    }


async def get_article_detail_handler(article_id: str) -> Dict[str, Any]:
    """
    获取文章详情处理器

    Args:
        article_id: 文章ID

    Returns:
        文章详情字典
    """
    from app.api.articles import get_article_by_id

    article = await get_article_by_id(article_id)

    if not article:
        raise ValueError(f"文章 '{article_id}' 未找到")

    return {
        "id": article.get("id"),
        "title": article.get("title"),
        "content": article.get("content"),
        "author": article.get("author"),
        "source": article.get("source"),
        "publish_time": article.get("publish_time"),
        "url": article.get("url"),
        "cover_image": article.get("cover_image"),
    }


async def get_trending_keywords_handler(
    date: Optional[str] = None,
    limit: int = 20,
) -> Dict[str, Any]:
    """
    获取热门关键词处理器

    Args:
        date: 日期
        limit: 数量限制

    Returns:
        关键词列表
    """
    from app.api.keywords import get_keywords_data

    keywords_data = await get_keywords_data(date=date, limit=limit)

    return {
        "keywords": keywords_data.get("keywords", []),
        "total": len(keywords_data.get("keywords", [])),
        "date": date or "latest",
    }


async def get_platform_stats_handler(
    date_range: Optional[str] = None,
) -> Dict[str, Any]:
    """
    获取平台统计处理器

    Args:
        date_range: 日期范围

    Returns:
        统计数据
    """
    from app.integrations import TrendRadarReader
    from hot_content_bridge.config import BridgeConfig
    from collections import Counter

    cfg = BridgeConfig.load()
    reader = TrendRadarReader(cfg)

    # 获取所有热榜数据
    all_hotspots, date_dist = reader.get_all_hotspots_with_articles()

    # 基础统计
    stats = {
        "total_items": len(all_hotspots),
        "total_dates": len(date_dist),
        "date_distribution": dict(date_dist.most_common(30)),
        "platforms": {},
        "top_items": [],
    }

    # 平台统计
    platform_counter = Counter()
    for item in all_hotspots:
        platform = item.get("platform_name") or item.get("platform_id", "unknown")
        platform_counter[platform] += 1

    stats["platforms"] = dict(platform_counter.most_common(20))

    # Top 热点（按排名聚合）
    top_items = sorted(all_hotspots, key=lambda x: x.get("rank", 999))[:10]
    stats["top_items"] = [
        {
            "title": item.get("title"),
            "platform": item.get("platform_name") or item.get("platform_id"),
            "rank": item.get("rank"),
        }
        for item in top_items
    ]

    return stats


def _calculate_trend(rank_history: list) -> str:
    """计算趋势"""
    if len(rank_history) < 2:
        return "new"

    latest_rank = rank_history[0].get("rank", 0)
    prev_rank = rank_history[1].get("rank", 0)

    if latest_rank < prev_rank:
        return "up"
    elif latest_rank > prev_rank:
        return "down"
    else:
        return "same"
