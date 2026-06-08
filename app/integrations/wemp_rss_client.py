#!/usr/bin/env python3
# coding=utf-8
"""
we-mp-rss API 集成客户端
用于在主应用中代理调用 we-mp-rss 服务
"""

import sys
import os
from pathlib import Path
from typing import Optional, Dict, Any, List
from urllib.parse import urljoin
import httpx
import logging

logger = logging.getLogger(__name__)

# we-mp-rss 默认端口
DEFAULT_WEMP_PORT = 8001

def get_wemp_base_url() -> str:
    """获取 we-mp-rss 服务的基础 URL"""
    # 从环境变量读取配置，默认使用 8001 端口
    env_url = os.getenv("WEMP_RSS_BASE_URL", f"http://127.0.0.1:{DEFAULT_WEMP_PORT}")
    return env_url.rstrip('/')


def is_wemp_available() -> bool:
    """检查 we-mp-rss 服务是否可用"""
    try:
        base_url = get_wemp_base_url()
        with httpx.Client(timeout=5) as client:
            response = client.get(f"{base_url}/")
            # 即使响应码不是 200，只要能连接就说明服务是启动的
            return True
    except Exception:
        return False


class WempRSSClient:
    """we-mp-rss API 客户端"""
    
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or get_wemp_base_url()
        self.client = httpx.Client(timeout=30)
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.client.close()
    
    def _request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict[str, Any]]:
        """统一的请求方法"""
        try:
            url = urljoin(self.base_url, endpoint)
            response = self.client.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"请求 we-mp-rss API 失败: {method} {endpoint}, 错误: {e}")
            return None
    
    # 公众号相关接口
    def get_mps(self, limit: int = 10, offset: int = 0, kw: str = "", status: Optional[int] = None) -> Dict[str, Any]:
        """获取公众号列表"""
        params = {"limit": limit, "offset": offset}
        if kw:
            params["kw"] = kw
        if status is not None:
            params["status"] = status
        result = self._request("GET", "/mps", params=params)
        return result or {"list": [], "total": 0}
    
    def get_mp(self, mp_id: str) -> Optional[Dict[str, Any]]:
        """获取公众号详情"""
        result = self._request("GET", f"/mps/{mp_id}")
        return result.get("data") if result else None
    
    def search_mps(self, kw: str, limit: int = 10, offset: int = 0) -> Dict[str, Any]:
        """搜索公众号"""
        result = self._request("GET", f"/mps/search/{kw}", params={"limit": limit, "offset": offset})
        return result or {"list": [], "total": 0}
    
    # 文章相关接口
    def get_articles(
        self,
        offset: int = 0,
        limit: int = 20,
        status: Optional[str] = None,
        search: Optional[str] = None,
        mp_id: Optional[str] = None,
        only_favorite: bool = False,
        has_content: Optional[bool] = None
    ) -> Dict[str, Any]:
        """获取文章列表"""
        params = {"offset": offset, "limit": limit, "only_favorite": only_favorite}
        if status:
            params["status"] = status
        if search:
            params["search"] = search
        if mp_id:
            params["mp_id"] = mp_id
        if has_content is not None:
            params["has_content"] = has_content
        
        result = self._request("GET", "/articles", params=params)
        return result or {"list": [], "total": 0}
    
    def get_article(self, article_id: str, include_content: bool = False) -> Optional[Dict[str, Any]]:
        """获取文章详情"""
        params = {"content": include_content}
        result = self._request("GET", f"/articles/{article_id}", params=params)
        return result.get("data") if result else None
    
    def mark_article_read(self, article_id: str, is_read: bool = True) -> Optional[Dict[str, Any]]:
        """标记文章阅读状态"""
        result = self._request("PUT", f"/articles/{article_id}/read", params={"is_read": is_read})
        return result.get("data") if result else None
    
    def mark_article_favorite(self, article_id: str, is_favorite: bool = True) -> Optional[Dict[str, Any]]:
        """标记文章收藏状态"""
        result = self._request("PUT", f"/articles/{article_id}/favorite", params={"is_favorite": is_favorite})
        return result.get("data") if result else None
    
    def refresh_article(self, article_id: str) -> Optional[Dict[str, Any]]:
        """刷新单篇文章"""
        result = self._request("POST", f"/articles/{article_id}/refresh")
        return result.get("data") if result else None
    
    def get_refresh_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """查询刷新任务状态"""
        result = self._request("GET", f"/articles/refresh/tasks/{task_id}")
        return result.get("data") if result else None


def get_wemp_client() -> WempRSSClient:
    """获取 we-mp-rss 客户端实例"""
    return WempRSSClient()


def is_wemp_running() -> bool:
    """检查 we-mp-rss 服务是否正在运行"""
    return is_wemp_available()

