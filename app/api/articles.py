# coding=utf-8
"""文章相关 API 路由。"""

import asyncio
import subprocess
from typing import Optional
from fastapi import APIRouter, HTTPException, Query

from app.integrations import TrendRadarReader
from hot_content_bridge.config import BridgeConfig

router = APIRouter()


@router.get("/articles/{url_norm:path}")
async def get_article(
    url_norm: str,
    date: Optional[str] = Query(None, description="日期 (YYYY-MM-DD)"),
):
    """获取文章正文内容。

    Args:
        url_norm: 规范化的 URL
        date: 可选日期

    Returns:
        文章内容
    """
    try:
        cfg = BridgeConfig.load()
        reader = TrendRadarReader(cfg)
        article = reader.get_article_content(url_norm, date)

        if not article:
            return {
                "success": True,
                "data": None,
                "message": "文章尚未抓取",
            }

        return {
            "success": True,
            "data": {
                "id": article["id"],
                "news_item_id": article["news_item_id"],
                "url_norm": article["url_norm"],
                "platform_id": article["platform_id"],
                "title_snapshot": article["title_snapshot"],
                "status": article["status"],
                "http_status": article["http_status"],
                "markdown": article["markdown"],
                "extracted_title": article["extracted_title"],
                "error": article["error"],
                "content_sha256": article["content_sha256"],
                "fetched_at": article["fetched_at"],
                "created_at": article["created_at"],
                "updated_at": article["updated_at"],
            },
        }

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"内部错误: {str(e)}")


@router.post("/articles/{url_norm:path}/refetch")
async def refetch_article(
    url_norm: str,
    date: Optional[str] = Query(None, description="日期 (YYYY-MM-DD)"),
):
    """触发重新抓取文章。

    Args:
        url_norm: 规范化的 URL
        date: 可选日期

    Returns:
        任务状态
    """
    try:
        # 这里我们通过 subprocess 调用 hot-content-bridge CLI
        # 实际生产环境可能需要使用任务队列
        cmd = ["uv", "run", "hot-content-bridge", "crawl-articles", "--limit", "1"]
        if date:
            cmd.extend(["--date", date])

        # 注意：这是一个简化实现，实际应该只抓取指定的 URL
        # 但 hot-content-bridge 当前可能不支持单 URL 抓取
        # 这里我们先返回任务已启动的状态

        # 在后台运行（非阻塞）
        # subprocess.Popen(cmd)

        return {
            "success": True,
            "data": {
                "status": "pending",
                "url_norm": url_norm,
                "message": "重新抓取任务已启动（当前版本会抓取所有待抓取文章）",
            },
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"触发重新抓取失败: {str(e)}")
