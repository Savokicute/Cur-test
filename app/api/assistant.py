# coding=utf-8
"""
智能助手 API 路由

提供对话、工具调用、历史记录等端点。
遵循 MCP 协议规范，支持流式响应。
"""

import logging
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter()


# ========== 请求/响应模型 ==========

class ChatMessage(BaseModel):
    """聊天消息模型"""
    role: str = Field(..., description="角色: user | assistant | system")
    content: str = Field(..., description="消息内容")
    tool_calls: Optional[List[Dict[str, Any]]] = Field(None, description="工具调用列表")
    tool_call_id: Optional[str] = Field(None, description="工具调用ID（用于工具结果消息）")


class ChatRequest(BaseModel):
    """聊天请求模型"""
    message: str = Field(..., description="用户消息")
    session_id: Optional[str] = Field(None, description="会话ID（用于多轮对话）")
    stream: bool = Field(False, description="是否使用流式响应")
    tools: Optional[List[str]] = Field(None, description="允许使用的工具列表（空=全部）")


class ToolInvokeRequest(BaseModel):
    """工具调用请求模型"""
    arguments: Dict[str, Any] = Field(..., description="工具参数")


class ClearHistoryRequest(BaseModel):
    """清除历史请求模型"""
    session_id: Optional[str] = Field(None, description="会话ID（不填则清除所有）")


# ========== API 端点 ==========

@router.post("/assistant/chat")
async def chat(request: ChatRequest):
    """
    智能助手对话端点

    支持普通和流式两种模式：
    - stream=false: 返回完整响应（JSON）
    - stream=true: 返回 SSE 流式响应

    Args:
        request: 聊天请求

    Returns:
        对话响应或 SSE 流
    """
    try:
        from app.services.assistant_service import AssistantService

        service = AssistantService()

        if request.stream:
            # 流式响应
            return StreamingResponse(
                service.stream_chat(
                    message=request.message,
                    session_id=request.session_id,
                    allowed_tools=request.tools,
                ),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "X-Accel-Buffering": "no",
                },
            )
        else:
            # 普通响应
            result = await service.chat(
                message=request.message,
                session_id=request.session_id,
                allowed_tools=request.tools,
            )

            return {
                "success": True,
                "data": result,
            }

    except Exception as e:
        logger.error(f"对话处理失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"内部错误: {str(e)}")


@router.get("/assistant/history")
async def get_chat_history(
    session_id: Optional[str] = Query(None, description="会话ID"),
    limit: int = Query(50, description="返回条数限制"),
    offset: int = Query(0, description="偏移量"),
):
    """
    获取对话历史记录

    Args:
        session_id: 会话ID（不填则获取全部）
        limit: 返回条数
        offset: 偏移量

    Returns:
        历史记录列表
    """
    try:
        from app.services.assistant_service import AssistantService

        service = AssistantService()
        history = await service.get_history(
            session_id=session_id,
            limit=limit,
            offset=offset,
        )

        return {
            "success": True,
            "data": {
                "items": history["items"],
                "total": history["total"],
                "has_more": history["has_more"],
            },
        }

    except Exception as e:
        logger.error(f"获取历史记录失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"内部错误: {str(e)}")


@router.post("/assistant/history/clear")
async def clear_chat_history(request: ClearHistoryRequest):
    """
    清除对话历史

    Args:
        request: 清除请求

    Returns:
        操作结果
    """
    try:
        from app.services.assistant_service import AssistantService

        service = AssistantService()
        cleared_count = await service.clear_history(session_id=request.session_id)

        return {
            "success": True,
            "data": {
                "cleared_count": cleared_count,
                "message": f"已清除 {cleared_count} 条历史记录",
            },
        }

    except Exception as e:
        logger.error(f"清除历史记录失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"内部错误: {str(e)}")


@router.get("/assistant/tools")
async def list_tools():
    """
    列出所有可用工具

    Returns:
        工具列表及统计信息
    """
    try:
        from app.services.mcp_tools import registry

        tools = registry.list_tools()
        stats = registry.get_stats()

        return {
            "success": True,
            "data": {
                "tools": tools,
                "stats": stats,
            },
        }

    except Exception as e:
        logger.error(f"获取工具列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"内部错误: {str(e)}")


@router.post("/assistant/tools/{tool_name}/invoke")
async def invoke_tool(tool_name: str, request: ToolInvokeRequest):
    """
    调用指定工具

    遵循 MCP 协议规范，返回标准化响应。

    Args:
        tool_name: 工具名称
        request: 工具调用请求

    Returns:
        工具执行结果
    """
    try:
        from app.services.mcp_tools import registry

        result = await registry.invoke_tool(
            name=tool_name,
            arguments=request.arguments,
        )

        return {
            "success": result["success"],
            "data": result,
        }

    except Exception as e:
        logger.error(f"工具调用失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"内部错误: {str(e)}")


@router.get("/assistant/sessions")
async def list_sessions(
    limit: int = Query(20, description="返回数量"),
    offset: int = Query(0, description="偏移量"),
):
    """
    列出所有会话

    Returns:
        会话列表
    """
    try:
        from app.services.assistant_service import AssistantService

        service = AssistantService()
        sessions = await service.list_sessions(limit=limit, offset=offset)

        return {
            "success": True,
            "data": sessions,
        }

    except Exception as e:
        logger.error(f"获取会话列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"内部错误: {str(e)}")


@router.delete("/assistant/sessions/{session_id}")
async def delete_session(session_id: str):
    """
    删除指定会话及其历史记录

    Args:
        session_id: 会话ID

    Returns:
        操作结果
    """
    try:
        from app.services.assistant_service import AssistantService

        service = AssistantService()
        deleted = await service.delete_session(session_id)

        if not deleted:
            raise HTTPException(status_code=404, detail="会话不存在")

        return {
            "success": True,
            "data": {"message": "会话已删除"},
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除会话失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"内部错误: {str(e)}")


@router.get("/assistant/config")
async def get_assistant_config():
    """
    获取智能助手配置信息

    Returns:
        配置数据（系统提示词、可用功能等）
    """
    try:
        from app.services.mcp_tools import registry

        tools = registry.list_tools()

        config = {
            "system_prompt": _get_system_prompt(),
            "available_tools": [t["name"] for t in tools],
            "features": [
                "multi_turn_dialogue",  # 多轮对话
                "tool_calling",         # 工具调用
                "streaming_response",   # 流式响应
                "history_persistence",  # 历史持久化
                "markdown_rendering",   # Markdown 渲染
            ],
            "version": "1.0.0",
        }

        return {
            "success": True,
            "data": config,
        }

    except Exception as e:
        logger.error(f"获取配置失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"内部错误: {str(e)}")


def _get_system_prompt() -> str:
    """获取系统提示词"""
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
