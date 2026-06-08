# coding=utf-8
"""微信公众号相关 API 路由（代理 we-mp-rss）。
支持优雅降级：当 we-mp-rss 服务不可用时，自动返回 Mock 数据。
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query
from app.integrations import get_wemp_client, is_wemp_running, get_wemp_base_url

router = APIRouter()
logger = logging.getLogger(__name__)

# Mock 数据：用于 we-mp-rss 服务不可用时的降级展示
MOCK_MPS = [
    {
        "id": "demo-001",
        "name": "36氪",
        "avatar": "https://via.placeholder.com/100?text=36kr",
        "description": "科技创业新闻平台",
        "status": 1,
        "article_count": 156,
        "last_updated": "2026-06-02T10:00:00"
    },
    {
        "id": "demo-002",
        "name": "机器之心",
        "avatar": "https://via.placeholder.com/100?text=JQZX",
        "description": "专业的人工智能媒体",
        "status": 1,
        "article_count": 89,
        "last_updated": "2026-06-02T09:30:00"
    },
    {
        "id": "demo-003",
        "name": "量子位",
        "avatar": "https://via.placeholder.com/100?text=LZW",
        "description": "追踪AI技术和产品动态",
        "status": 1,
        "article_count": 234,
        "last_updated": "2026-06-02T08:15:00"
    }
]

MOCK_ARTICLES = [
    {
        "id": "article-001",
        "mp_id": "demo-001",
        "title": "【演示】OpenAI发布GPT-5：多模态能力大幅提升",
        "summary": "这是演示数据，实际使用请启动 we-mp-rss 服务...",
        "publish_time": "2026-06-02T08:00:00",
        "url": "#",
        "cover": "",
        "status": "success",
        "is_read": False,
        "is_favorite": False,
        "has_content": True
    },
    {
        "id": "article-002",
        "mp_id": "demo-002",
        "title": "【演示】谷歌DeepMind新突破：AlphaFold3预测蛋白质相互作用",
        "summary": "这是演示数据，实际使用请启动 we-mp-rss 服务...",
        "publish_time": "2026-06-01T20:30:00",
        "url": "#",
        "cover": "",
        "status": "success",
        "is_read": False,
        "is_favorite": False,
        "has_content": True
    }
]


def check_wemp_service() -> bool:
    """
    检查 we-mp-rss 服务是否可用。
    
    Returns:
        bool: 服务是否可用（True=可用，False=不可用）
    
    注意：
        不再抛出异常，而是返回布尔值，让调用方决定如何处理降级逻辑。
    """
    available = is_wemp_running()
    if not available:
        logger.warning("⚠️ we-mp-rss 服务未启动，当前使用 Mock 数据模式")
    return available


def create_mock_response(data: Any, **extra) -> Dict:
    """
    创建包含 Mock 标识的响应数据。
    
    Args:
        data: 响应数据内容
        **extra: 额外的响应字段
    
    Returns:
        Dict: 包含 mock=True 标识的响应字典
    """
    response = {
        "success": True,
        "data": data,
        "mock": True,  # 标识这是 Mock 数据
        **extra
    }
    return response


@router.get("/wechat/status")
async def get_wechat_status():
    """
    获取 we-mp-rss 服务状态。
    
    增强版状态检查：返回详细的服务信息和启动指引。
    """
    available = is_wemp_running()
    return {
        "success": True,
        "data": {
            "available": available,
            "service_url": get_wemp_base_url() if available else None,
            "message": "服务正常运行" if available else
                      "we-mp-rss 服务未启动，当前显示演示数据。启动方法：cd we-mp-rss && uv run python main.py -job True"
        },
        "mock": not available  # 标识是否处于 Mock 模式
    }


@router.get("/wechat/mps")
async def get_wechat_mps(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    kw: str = Query(""),
    status: Optional[int] = Query(None, description="状态筛选: 1=启用, 0=停用, 不传=全部")
):
    """
    获取微信公众号订阅列表。
    
    降级策略：当 we-mp-rss 不可用时，返回 Mock 公众号数据。
    """
    # 检查服务状态
    if not check_wemp_service():
        # 服务不可用：返回 Mock 数据
        logger.info("使用 Mock 数据返回公众号列表")
        return create_mock_response(
            data=MOCK_MPS,
            total=len(MOCK_MPS),
            page={"limit": limit, "offset": offset}
        )
    
    # 服务可用：正常调用
    client = get_wemp_client()
    result = client.get_mps(limit=limit, offset=offset, kw=kw, status=status)
    return {
        "success": True,
        "data": result.get("list", []),
        "total": result.get("total", 0),
        "page": {
            "limit": limit,
            "offset": offset
        }
    }


@router.get("/wechat/mps/search/{kw}")
async def search_wechat_mps(
    kw: str,
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """
    搜索微信公众号。
    
    降级策略：当 we-mp-rss 不可用时，在 Mock 数据中搜索。
    """
    # 检查服务状态
    if not check_wemp_service():
        # 服务不可用：在 Mock 数据中搜索
        logger.info(f"使用 Mock 数据搜索公众号: {kw}")
        filtered = [mp for mp in MOCK_MPS if kw.lower() in (mp.get('name') or '').lower()]
        return create_mock_response(
            data=filtered[:limit],
            total=len(filtered),
            page={"limit": limit, "offset": offset}
        )
    
    # 服务可用：正常调用
    client = get_wemp_client()
    result = client.search_mps(kw, limit=limit, offset=offset)
    return {
        "success": True,
        "data": result.get("list", []),
        "total": result.get("total", 0),
        "page": {
            "limit": limit,
            "offset": offset
        }
    }


@router.get("/wechat/mps/{mp_id}")
async def get_wechat_mp(mp_id: str):
    """
    获取微信公众号详情。
    
    降级策略：当 we-mp-rss 不可用时，从 Mock 数据中查找。
    """
    # 检查服务状态
    if not check_wemp_service():
        # 服务不可用：在 Mock 数据中查找
        logger.info(f"使用 Mock 数据获取公众号详情: {mp_id}")
        mp = next((m for m in MOCK_MPS if m['id'] == mp_id), None)
        if not mp:
            raise HTTPException(status_code=404, detail="公众号不存在（Mock 数据中未找到）")
        return create_mock_response(data=mp)
    
    # 服务可用：正常调用
    client = get_wemp_client()
    mp = client.get_mp(mp_id)
    if not mp:
        raise HTTPException(status_code=404, detail="公众号不存在")
    return {
        "success": True,
        "data": mp
    }


@router.get("/wechat/articles")
async def get_wechat_articles(
    mp_id: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    only_favorite: bool = Query(False),
    has_content: Optional[bool] = Query(None)
):
    """
    获取微信公众号文章列表。
    
    降级策略：当 we-mp-rss 不可用时，返回 Mock 文章数据。
    """
    # 检查服务状态
    if not check_wemp_service():
        # 服务不可用：返回 Mock 数据
        logger.info("使用 Mock 数据返回文章列表")
        
        # 根据 mp_id 过滤（如果指定了）
        articles = MOCK_ARTICLES
        if mp_id:
            articles = [a for a in articles if a['mp_id'] == mp_id]
        
        return create_mock_response(
            data=articles,
            total=len(articles),
            page={"limit": limit, "offset": offset}
        )
    
    # 服务可用：正常调用
    client = get_wemp_client()
    result = client.get_articles(
        offset=offset,
        limit=limit,
        status=status,
        search=search,
        mp_id=mp_id,
        only_favorite=only_favorite,
        has_content=has_content
    )
    return {
        "success": True,
        "data": result.get("list", []),
        "total": result.get("total", 0),
        "page": {
            "limit": limit,
            "offset": offset
        }
    }


@router.get("/wechat/articles/{article_id}")
async def get_wechat_article(article_id: str, include_content: bool = Query(False)):
    """
    获取微信公众号文章详情。
    
    降级策略：当 we-mp-rss 不可用时，从 Mock 数据中查找。
    """
    # 检查服务状态
    if not check_wemp_service():
        # 服务不可用：在 Mock 数据中查找
        logger.info(f"使用 Mock 数据获取文章详情: {article_id}")
        article = next((a for a in MOCK_ARTICLES if a['id'] == article_id), None)
        if not article:
            raise HTTPException(status_code=404, detail="文章不存在（Mock 数据中未找到）")
        
        # 如果需要内容，添加 Mock 内容
        if include_content:
            article_with_content = {**article, "content": "<p>这是演示内容。实际内容请启动 we-mp-rss 服务后查看。</p>"}
            return create_mock_response(data=article_with_content)
        
        return create_mock_response(data=article)
    
    # 服务可用：正常调用
    client = get_wemp_client()
    article = client.get_article(article_id, include_content=include_content)
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")
    return {
        "success": True,
        "data": article
    }


@router.put("/wechat/articles/{article_id}/read")
async def mark_wechat_article_read(article_id: str, is_read: bool = Query(True)):
    """
    标记文章阅读状态。
    
    降级策略：当 we-mp-rss 不可用时，返回 Mock 模式下的友好提示。
    """
    # 检查服务状态
    if not check_wemp_service():
        # 服务不可用：返回 Mock 模式提示
        logger.warning(f"Mock 模式下无法标记文章阅读状态: {article_id}")
        return create_mock_response(
            data={
                "success": False,
                "message": "当前为演示模式，无法修改数据。请启动 we-mp-rss 服务后重试。",
                "article_id": article_id,
                "is_read": is_read
            }
        )
    
    # 服务可用：正常调用
    client = get_wemp_client()
    result = client.mark_article_read(article_id, is_read=is_read)
    return {
        "success": True,
        "data": result
    }


@router.put("/wechat/articles/{article_id}/favorite")
async def mark_wechat_article_favorite(article_id: str, is_favorite: bool = Query(True)):
    """
    标记文章收藏状态。
    
    降级策略：当 we-mp-rss 不可用时，返回 Mock 模式下的友好提示。
    """
    # 检查服务状态
    if not check_wemp_service():
        # 服务不可用：返回 Mock 模式提示
        logger.warning(f"Mock 模式下无法标记文章收藏状态: {article_id}")
        return create_mock_response(
            data={
                "success": False,
                "message": "当前为演示模式，无法修改数据。请启动 we-mp-rss 服务后重试。",
                "article_id": article_id,
                "is_favorite": is_favorite
            }
        )
    
    # 服务可用：正常调用
    client = get_wemp_client()
    result = client.mark_article_favorite(article_id, is_favorite=is_favorite)
    return {
        "success": True,
        "data": result
    }


@router.post("/wechat/articles/{article_id}/refresh")
async def refresh_wechat_article(article_id: str):
    """
    刷新单篇文章。
    
    降级策略：当 we-mp-rss 不可用时，返回 Mock 模式下的友好提示。
    """
    # 检查服务状态
    if not check_wemp_service():
        # 服务不可用：返回 Mock 模式提示
        logger.warning(f"Mock 模式下无法刷新文章: {article_id}")
        return create_mock_response(
            data={
                "success": False,
                "message": "当前为演示模式，无法刷新文章。请启动 we-mp-rss 服务后重试。",
                "article_id": article_id
            }
        )
    
    # 服务可用：正常调用
    client = get_wemp_client()
    result = client.refresh_article(article_id)
    return {
        "success": True,
        "data": result
    }


@router.get("/wechat/articles/refresh/tasks/{task_id}")
async def get_wechat_refresh_task(task_id: str):
    """
    查询文章刷新任务状态。
    
    降级策略：当 we-mp-rss 不可用时，返回 Mock 模式下的友好提示。
    """
    # 检查服务状态
    if not check_wemp_service():
        # 服务不可用：返回 Mock 模式提示
        logger.warning(f"Mock 模式下无法查询刷新任务: {task_id}")
        return create_mock_response(
            data={
                "task_id": task_id,
                "status": "failed",
                "message": "当前为演示模式，无刷新任务。请启动 we-mp-rss 服务后重试。"
            }
        )
    
    # 服务可用：正常调用
    client = get_wemp_client()
    result = client.get_refresh_task_status(task_id)
    return {
        "success": True,
        "data": result
    }
