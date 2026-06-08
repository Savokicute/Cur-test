# coding=utf-8
"""采集源配置 API - 热榜源、网站源、公众号源、浏览器配置"""

import json
import sqlite3
import subprocess
import uuid
from datetime import datetime, date as date_type
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.models import (
    get_db,
    HotspotSource,
    WebsiteSource,
    WeChatFeed,
    WeChatArticle,
    BrowserProfile,
    init_default_hotspot_sources,
)
from app.integrations import get_wemp_client, is_wemp_running

router = APIRouter()


# ============ 工具函数：获取今日日库路径 ============

def _get_today_news_db_path() -> Optional[Path]:
    """获取当日热榜数据库路径"""
    today = date_type.today().strftime("%Y-%m-%d")
    db_path = Path(__file__).parent.parent.parent / "trendRadar" / "output" / "news" / f"{today}.db"
    return db_path if db_path.exists() else None


def _read_platform_status_from_db(db_path: Path) -> Dict[str, Any]:
    """从 SQLite 日库读取各平台采集状态"""
    status_map: Dict[str, dict] = {}
    try:
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()

        # news_items 按平台统计
        for row in cur.execute(
            "SELECT COALESCE(platform_id, ''), COUNT(*), MAX(created_at) FROM news_items GROUP BY COALESCE(platform_id, '')"
        ):
            pid, count, last_at = row[0], row[1], row[2]
            status_map[pid] = {
                "status": "success",
                "news_count": count,
                "last_crawled": last_at,
                "error": None,
            }

        # article_contents 按失败统计（通过 url_norm 关联）
        # 找出每个平台的失败数
        failed_rows = cur.execute("""
            SELECT ni.platform_id, COUNT(ac.id)
            FROM article_contents ac
            JOIN news_items ni ON ac.news_item_id = ni.id
            WHERE ac.status != 'success'
            GROUP BY ni.platform_id
        """).fetchall()

        for pid, fail_count in failed_rows:
            if pid in status_map:
                status_map[pid]["failed_count"] = fail_count
                if fail_count > 0:
                    status_map[pid]["status"] = "partial"
            else:
                status_map[pid] = {
                    "status": "partial",
                    "news_count": 0,
                    "last_crawled": None,
                    "failed_count": fail_count,
                    "error": None,
                }

        conn.close()
    except Exception as e:
        print(f"[sources] 读取平台状态失败: {e}")

    return status_map


# ============ 配置文件读取函数 ============

def load_config_yaml():
    """加载 trendRadar/config/config.yaml"""
    config_path = Path(__file__).parent.parent.parent / "trendRadar" / "config" / "config.yaml"
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def get_config_yaml_path() -> Path:
    """获取 config.yaml 路径"""
    return Path(__file__).parent.parent.parent / "trendRadar" / "config" / "config.yaml"


def save_config_yaml(config: dict):
    """保存配置到 config.yaml（更新 platforms.enabled + sources 的 enabled 字段，保留其余内容）"""
    import re

    config_path = get_config_yaml_path()
    with open(config_path, 'r', encoding='utf-8') as f:
        content = f.read()

    platforms_config = config.get("platforms", {})

    # Step 1: 更新顶层 platforms.enabled 字段
    if "enabled" in platforms_config:
        top_enabled = platforms_config["enabled"]
        new_val = "true" if top_enabled else "false"
        top_pattern = r'(^platforms:\s*\n)([ \t]*enabled:\s*(true|false)\s*\n?)'
        top_match = re.search(top_pattern, content, re.MULTILINE)
        if top_match:
            abs_pos = top_match.start(2)
            abs_end = top_match.end(2)
            leading_ws = top_match.group(2)[:top_match.group(2).index('enabled')] if 'enabled' in top_match.group(2) else '  '
            content = content[:abs_pos] + f'{leading_ws}enabled: {new_val}\n' + content[abs_end:]
        else:
            insert_pattern = r'^platforms:\s*\n'
            insert_match = re.search(insert_pattern, content, re.MULTILINE)
            if insert_match:
                pos = insert_match.end()
                content = content[:pos] + f'  enabled: {new_val}\n' + content[pos:]

    # Step 2: 更新每个 source 的 enabled 字段（原有逻辑）
    new_sources = platforms_config.get("sources", [])

    for src in new_sources:
        if not isinstance(src, dict) or "id" not in src:
            continue
        pid = src["id"]
        is_en = src.get("enabled", True)
        new_val = "true" if is_en else "false"

        id_pattern = rf'(\s+)- id: ["\']?{re.escape(pid)}["\']?\s*\n'
        id_match = re.search(id_pattern, content)

        if not id_match:
            continue

        block_start = id_match.end()
        remaining = content[block_start:]
        next_entry = re.search(r'^(\s+)- id:', remaining, re.MULTILINE)
        block_end = block_start + (next_entry.start() if next_entry else len(remaining))
        block_content = content[block_start:block_end]

        enabled_pattern = r'enabled:\s*(true|false)\s*\n?'
        enabled_match = re.search(enabled_pattern, block_content, re.MULTILINE)

        if enabled_match:
            abs_pos = block_start + enabled_match.start()
            abs_end = block_start + enabled_match.end()
            has_newline = block_content[enabled_match.end()-1:enabled_match.end()] == '\n'
            content = content[:abs_pos] + f'enabled: {new_val}\n' + content[abs_end:]
        else:
            name_match = re.search(r'name:\s*["\']?.+?["\']?\s*$', block_content, re.MULTILINE)
            if name_match:
                insert_pos = block_start + name_match.end()
                content = content[:insert_pos] + f'\n      enabled: {new_val}' + content[insert_pos:]
            else:
                insert_pos = block_start
                content = content[:insert_pos] + f'\n      enabled: {new_val}' + content[insert_pos:]

    with open(config_path, 'w', encoding='utf-8') as f:
        f.write(content)


# ============ Pydantic 模型 ============

class BrowserProfileCreate(BaseModel):
    """创建浏览器配置"""
    name: str = Field(..., min_length=1, max_length=128)
    config: Dict[str, Any] = Field(default_factory=dict)
    is_global_default: bool = False


class BrowserProfileUpdate(BaseModel):
    """更新浏览器配置"""
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    config: Optional[Dict[str, Any]] = None
    enabled: Optional[bool] = None
    is_global_default: Optional[bool] = None


class HotSourceUpdate(BaseModel):
    """更新热榜源"""
    enabled: Optional[bool] = None
    weight: Optional[int] = Field(None, ge=1, le=100)
    browser_profile_id: Optional[str] = None


class WebsiteSourceCreate(BaseModel):
    """创建网站源"""
    name: str = Field(..., min_length=1, max_length=256)
    url: str = Field(..., min_length=1)
    url_template: Optional[str] = None
    css_selector: Optional[str] = None
    source_type: str = "rss"
    weight: int = 5
    browser_profile_id: Optional[str] = None


class WebsiteSourceUpdate(BaseModel):
    """更新网站源"""
    name: Optional[str] = Field(None, min_length=1, max_length=256)
    url: Optional[str] = None
    url_template: Optional[str] = None
    css_selector: Optional[str] = None
    enabled: Optional[bool] = None
    max_age_days: Optional[int] = None
    weight: Optional[int] = Field(None, ge=1, le=100)
    source_type: Optional[str] = None
    browser_profile_id: Optional[str] = None


class WechatFeedCreate(BaseModel):
    """创建公众号订阅"""
    name: str = Field(..., min_length=1, max_length=256)
    account_id: Optional[str] = None
    avatar_url: Optional[str] = None
    feed_url: Optional[str] = None
    crawl_interval: int = 3600
    filter_rules: List[Any] = Field(default_factory=list)
    browser_profile_id: Optional[str] = None


class WechatFeedUpdate(BaseModel):
    """更新公众号订阅"""
    name: Optional[str] = Field(None, min_length=1, max_length=256)
    status: Optional[str] = None
    crawl_interval: Optional[int] = None
    filter_rules: Optional[List[Any]] = None
    browser_profile_id: Optional[str] = None


# ============ 6.2 热榜源配置 API ============

@router.get("/hot-sources")
async def get_hot_sources(db: Session = Depends(get_db)):
    """获取热榜源列表（从 config.yaml 读取平台配置，合并数据库状态）"""
    try:
        config = load_config_yaml()
        platforms_config = config.get("platforms", {})
        config_sources = platforms_config.get("sources", [])
        hot_sources_enabled = platforms_config.get("enabled", True)

        db_sources = {s.id: s for s in db.query(HotspotSource).all()}

        available_platforms = []
        for platform in config_sources:
            platform_id = platform["id"]
            config_enabled = platform.get("enabled", True)
            if platform_id in db_sources:
                db_source = db_sources[platform_id]
                available_platforms.append({
                    "id": db_source.id,
                    "name": db_source.name or platform["name"],
                    "enabled": db_source.enabled,
                    "weight": db_source.weight
                })
            else:
                available_platforms.append({
                    "id": platform_id,
                    "name": platform["name"],
                    "enabled": config_enabled,
                    "weight": 5
                })

        return {
            "success": True,
            "data": {
                "hotSourcesEnabled": hot_sources_enabled,
                "availablePlatforms": available_platforms,
                "enabledPlatforms": [
                    {"id": p["id"], "name": p["name"]}
                    for p in available_platforms if p["enabled"]
                ]
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/hot-sources")
async def update_hot_sources(request: Dict[str, Any], db: Session = Depends(get_db)):
    """批量更新热榜源配置（同步到 config.yaml + 数据库，DB 不可用时仅保存 config.yaml）"""
    try:
        config = load_config_yaml()

        if "hotSourcesEnabled" in request:
            if "platforms" not in config:
                config["platforms"] = {}
            config["platforms"]["enabled"] = request["hotSourcesEnabled"]

        if "enabledPlatforms" in request:
            platforms_config = config.setdefault("platforms", {})
            config_sources_list = platforms_config.setdefault("sources", [])

            platform_enabled_map = {}
            for p in request["enabledPlatforms"]:
                if p.get("id"):
                    platform_enabled_map[p["id"]] = p.get("enabled", True)

            for source_item in config_sources_list:
                if isinstance(source_item, dict) and "id" in source_item:
                    pid = source_item["id"]
                    is_enabled = platform_enabled_map.get(pid, True)
                    source_item["enabled"] = is_enabled

            disabled_in_request = []
            all_config_ids = {s["id"] for s in config_sources_list if isinstance(s, dict)}
            for platform_data in request["enabledPlatforms"]:
                pid = platform_data.get("id")
                if pid and pid not in all_config_ids:
                    disabled_in_request.append(platform_data)

            for new_p in disabled_in_request:
                config_sources_list.append({
                    "id": new_p["id"],
                    "name": new_p.get("name", new_p["id"]),
                    "enabled": new_p.get("enabled", True)
                })

        save_config_yaml(config)

        try:
            _sync_to_database(db, request)
            return {"success": True, "message": "热榜源配置已同步到 config.yaml 和数据库"}
        except Exception as db_err:
            print(f"[sources] DB 同步失败（config.yaml 已保存）: {db_err}")
            return {"success": True, "message": "热榜源配置已同步到 config.yaml（数据库暂时不可用）"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存失败: {str(e)}")


def _sync_to_database(db: Session, request: Dict[str, Any]):
    """将配置同步到 SQLAlchemy 数据库（内部函数，异常由调用方处理）。"""
    platform_enabled_map = {}
    for p in request.get("enabledPlatforms", []):
        if p.get("id"):
            platform_enabled_map[p["id"]] = p.get("enabled", True)

    for pid, is_enabled in platform_enabled_map.items():
        source = db.query(HotspotSource).filter_by(id=pid).first()
        if source:
            source.enabled = is_enabled
            name_match = next(
                (p.get("name") for p in request["enabledPlatforms"] if p.get("id") == pid), None
            )
            if name_match:
                source.name = name_match
        else:
            platform_data = next((p for p in request["enabledPlatforms"] if p.get("id") == pid), {})
            db.add(HotspotSource(
                id=pid,
                name=platform_data.get("name") or pid,
                enabled=is_enabled,
                weight=platform_data.get("weight", 5)
            ))

    all_existing = {s.id for s in db.query(HotspotSource.id).all()}
    for platform_data in request.get("enabledPlatforms", []):
        pid = platform_data.get("id")
        if pid and pid not in all_existing:
            db.add(HotspotSource(
                id=pid,
                name=platform_data.get("name", pid),
                enabled=platform_data.get("enabled", True),
                weight=platform_data.get("weight", 5)
            ))

    db.commit()


@router.put("/hot-sources/{source_id}")
async def update_hot_source(source_id: str, update: HotSourceUpdate, db: Session = Depends(get_db)):
    """更新单个热榜源配置"""
    source = db.query(HotspotSource).filter_by(id=source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="热榜源不存在")

    update_data = update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(source, key, value)

    db.commit()
    return {"success": True, "message": "热榜源已更新"}


@router.get("/hot-sources/status")
async def get_platform_status():
    """获取各热榜平台的采集状态（从当日 SQLite 日库读取）"""
    db_path = _get_today_news_db_path()

    if not db_path:
        return {
            "success": True,
            "data": {
                "date": date_type.today().strftime("%Y-%m-%d"),
                "db_exists": False,
                "platforms": [],
            }
        }

    status_map = _read_platform_status_from_db(db_path)

    # 合并 config.yaml 中的平台列表，确保所有平台都有状态
    try:
        config = load_config_yaml()
        config_sources = config.get("platforms", {}).get("sources", [])
        all_platforms = []
        for src in config_sources:
            pid = src.get("id", "")
            pname = src.get("name", pid)
            pstatus = status_map.get(pid, {"status": "pending", "news_count": 0, "last_crawled": None, "error": None})
            all_platforms.append({
                "id": pid,
                "name": pname,
                **pstatus,
            })
    except Exception:
        all_platforms = [{"id": k, "name": k, **v} for k, v in status_map.items()]

    return {
        "success": True,
        "data": {
            "date": date_type.today().strftime("%Y-%m-%d"),
            "db_exists": True,
            "platforms": all_platforms,
        }
    }


class PlatformRetryRequest(BaseModel):
    """平台重试请求"""
    mode: str = Field(default="quick", description="重试模式: quick=仅热榜, full=完整trendradar")


@router.post("/hot-sources/{platform_id}/retry")
async def retry_platform(platform_id: str, request: PlatformRetryRequest = PlatformRetryRequest()):
    """
    重试指定平台的数据采集。

    调用 hot_content_bridge 的 fetch-hotlist-only 或 sync-hotlist 子命令，
    仅针对该平台重新采集。
    """
    import sys

    # 验证平台是否存在
    try:
        config = load_config_yaml()
        config_sources = config.get("platforms", {}).get("sources", [])
        platform_ids = [s.get("id") for s in config_sources]
        if platform_id not in platform_ids:
            raise HTTPException(status_code=404, detail=f"平台 '{platform_id}' 不在配置中")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取配置失败: {e}")

    # 构建命令
    repo_root = Path(__file__).parent.parent.parent
    cmd = [sys.executable, "-m", "hot_content_bridge.cli"]

    if request.mode == "full":
        cmd.extend(["sync-hotlist", "--platform", platform_id])
    else:
        cmd.extend(["fetch-hotlist-only", "--platform", platform_id])

    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(repo_root),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
        )
        # 异步启动，不等待完成（采集可能需要较长时间）
        return {
            "success": True,
            "message": f"已触发平台 '{platform_id}' 重试采集 (mode={request.mode})",
            "data": {
                "platform_id": platform_id,
                "mode": request.mode,
                "pid": proc.pid,
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"触发重试失败: {e}")


@router.get("/config-yaml")
async def get_config_yaml():
    """获取完整的 config.yaml 配置内容（用于前端展示）"""
    try:
        config = load_config_yaml()
        return {
            "success": True,
            "data": config
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取配置文件失败: {str(e)}")


# ============ 6.3 网站源配置 API ============

@router.get("/website-sources")
async def get_website_sources(db: Session = Depends(get_db)):
    """获取网站源列表"""
    sources = db.query(WebsiteSource).order_by(WebsiteSource.weight.desc()).all()
    return {
        "success": True,
        "data": {
            "rssEnabled": any(s.source_type == "rss" and s.enabled for s in sources),
            "feeds": [
                {
                    "id": s.id,
                    "name": s.name,
                    "url": s.url,
                    "url_template": s.url_template,
                    "css_selector": s.css_selector,
                    "enabled": s.enabled,
                    "max_age_days": s.max_age_days,
                    "weight": s.weight,
                    "source_type": s.source_type,
                    "browser_profile_id": s.browser_profile_id,
                }
                for s in sources
            ]
        }
    }


@router.post("/website-sources", status_code=201)
async def add_website_source(source: WebsiteSourceCreate, db: Session = Depends(get_db)):
    """添加网站源"""
    new_source = WebsiteSource(
        id=str(uuid.uuid4())[:8],
        **source.model_dump()
    )
    db.add(new_source)
    db.commit()
    db.refresh(new_source)
    return {"success": True, "message": "网站源已添加", "data": {"id": new_source.id}}


@router.put("/website-sources/{source_id}")
async def update_website_source(source_id: str, update: WebsiteSourceUpdate, db: Session = Depends(get_db)):
    """更新网站源"""
    source = db.query(WebsiteSource).filter_by(id=source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="网站源不存在")

    update_data = update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(source, key, value)

    db.commit()
    return {"success": True, "message": "网站源已更新"}


@router.delete("/website-sources/{source_id}")
async def delete_website_source(source_id: str, db: Session = Depends(get_db)):
    """删除网站源"""
    source = db.query(WebsiteSource).filter_by(id=source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="网站源不存在")

    db.delete(source)
    db.commit()
    return {"success": True, "message": "网站源已删除"}


# ============ 6.4+6.5 微信公众号 API ============

@router.get("/wechat-mps")
async def get_wechat_mps_sources(
    status: Optional[str] = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db)
):
    """获取公众号列表（本地 + we-mp-rss）"""
    query = db.query(WeChatFeed)
    if status:
        query = query.filter(WeChatFeed.status == status)

    total = query.count()
    feeds = query.order_by(WeChatFeed.created_at.desc()).offset(offset).limit(limit).all()

    # 尝试从 we-mp-rss 获取实时数据
    wemp_available = is_wemp_running()
    wemp_mps = []
    if wemp_available:
        try:
            client = get_wemp_client()
            result = client.get_mps(limit=limit, offset=offset)
            wemp_mps = result.get("list", [])
        except Exception:
            wemp_available = False

    return {
        "success": True,
        "data": {
            "localFeeds": [
                {
                    "id": f.id,
                    "name": f.name,
                    "account_id": f.account_id,
                    "avatar_url": f.avatar_url,
                    "status": f.status,
                    "crawl_interval": f.crawl_interval,
                    "last_fetch_time": f.last_fetch_time.isoformat() if f.last_fetch_time else None,
                    "browser_profile_id": f.browser_profile_id,
                }
                for f in feeds
            ],
            "wempAvailable": wemp_available,
            "wempMps": wemp_mps,
            "total": total,
        }
    }


@router.post("/wechat-mps", status_code=201)
async def add_wechat_mp(feed: WechatFeedCreate, db: Session = Depends(get_db)):
    """添加公众号订阅"""
    new_feed = WeChatFeed(**feed.model_dump())
    db.add(new_feed)
    db.commit()
    db.refresh(new_feed)
    return {"success": True, "message": "公众号已添加", "data": {"id": new_feed.id}}


@router.put("/wechat-mps/{feed_id}")
async def update_wechat_mp(feed_id: int, update: WechatFeedUpdate, db: Session = Depends(get_db)):
    """更新公众号订阅"""
    feed = db.query(WeChatFeed).filter_by(id=feed_id).first()
    if not feed:
        raise HTTPException(status_code=404, detail="公众号不存在")

    update_data = update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(feed, key, value)

    db.commit()
    return {"success": True, "message": "公众号已更新"}


@router.delete("/wechat-mps/{feed_id}")
async def delete_wechat_mp(feed_id: int, db: Session = Depends(get_db)):
    """删除公众号订阅"""
    feed = db.query(WeChatFeed).filter_by(id=feed_id).first()
    if not feed:
        raise HTTPException(status_code=404, detail="公众号不存在")

    db.delete(feed)
    db.commit()
    return {"success": True, "message": "公众号已删除"}


@router.post("/wechat-mps/search")
async def search_wechat_mps(request: Dict[str, str]):
    """搜索公众号（代理到 we-mp-rss）"""
    if not is_wemp_running():
        return {"success": False, "error": "we-mp-rss 服务未启动"}

    client = get_wemp_client()
    keyword = request.get("keyword", "")
    result = client.search_mps(keyword, limit=10, offset=0)
    return {"success": True, "data": result}


@router.post("/wechat-mps/{feed_id}/fetch")
async def trigger_wechat_fetch(feed_id: int, db: Session = Depends(get_db)):
    """手动触发公众号文章抓取"""
    feed = db.query(WeChatFeed).filter_by(id=feed_id).first()
    if not feed:
        raise HTTPException(status_code=404, detail="公众号不存在")

    if not is_wemp_running():
        raise HTTPException(status_code=503, detail="we-mp-rss 服务未启动")

    try:
        client = get_wemp_client()
        # 调用刷新接口
        result = client.refresh_article(str(feed_id)) if feed.account_id else None
        feed.last_fetch_time = datetime.utcnow()
        db.commit()

        return {
            "success": True,
            "message": "抓取任务已触发",
            "data": {"task_id": result.get("task_id") if result else None}
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"触发抓取失败: {str(e)}")


# ============ 6.6 浏览器配置文件管理 API ============

@router.get("/browser-profiles")
async def get_browser_profiles(db: Session = Depends(get_db)):
    """获取浏览器配置列表"""
    profiles = db.query(BrowserProfile).order_by(BrowserProfile.created_at.desc()).all()
    return {
        "success": True,
        "data": [
            {
                "id": p.id,
                "name": p.name,
                "config": p.config,
                "enabled": p.enabled,
                "is_global_default": p.is_global_default,
                "size": p.size,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in profiles
        ]
    }


@router.post("/browser-profiles", status_code=201)
async def create_browser_profile(profile: BrowserProfileCreate, db: Session = Depends(get_db)):
    """创建浏览器配置"""
    # 如果设为全局默认，先取消其他默认
    if profile.is_global_default:
        db.query(BrowserProfile).filter(BrowserProfile.is_global_default == True).update(
            {"is_global_default": False}
        )

    new_profile = BrowserProfile(
        id=str(uuid.uuid4())[:12],
        **profile.model_dump()
    )
    db.add(new_profile)
    db.commit()
    db.refresh(new_profile)
    return {"success": True, "message": "浏览器配置已创建", "data": {"id": new_profile.id}}


@router.put("/browser-profiles/{profile_id}")
async def update_browser_profile(profile_id: str, update: BrowserProfileUpdate, db: Session = Depends(get_db)):
    """更新浏览器配置"""
    profile = db.query(BrowserProfile).filter_by(id=profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="浏览器配置不存在")

    update_data = update.model_dump(exclude_unset=True)

    # 如果设为全局默认，先取消其他默认
    if update_data.get("is_global_default"):
        db.query(BrowserProfile).filter(
            BrowserProfile.is_global_default == True,
            BrowserProfile.id != profile_id
        ).update({"is_global_default": False})

    for key, value in update_data.items():
        setattr(profile, key, value)

    db.commit()
    return {"success": True, "message": "浏览器配置已更新"}


@router.delete("/browser-profiles/{profile_id}")
async def delete_browser_profile(profile_id: str, db: Session = Depends(get_db)):
    """删除浏览器配置"""
    profile = db.query(BrowserProfile).filter_by(id=profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="浏览器配置不存在")

    db.delete(profile)
    db.commit()
    return {"success": True, "message": "浏览器配置已删除"}


# ============ 6.7 来源与配置文件关联 API ============

@router.get("/associations")
async def get_source_associations(db: Session = Depends(get_db)):
    """获取所有来源与配置文件的关联关系"""
    hotspot_assocs = [
        {"source_type": "hotspot", "source_id": s.id, "browser_profile_id": s.browser_profile_id}
        for s in db.query(HotspotSource).filter(HotspotSource.browser_profile_id.isnot(None)).all()
    ]
    website_assocs = [
        {"source_type": "website", "source_id": s.id, "browser_profile_id": s.browser_profile_id}
        for s in db.query(WebsiteSource).filter(WebsiteSource.browser_profile_id.isnot(None)).all()
    ]
    wechat_assocs = [
        {"source_type": "wechat", "source_id": f.id, "browser_profile_id": f.browser_profile_id}
        for f in db.query(WeChatFeed).filter(WeChatFeed.browser_profile_id.isnot(None)).all()
    ]

    return {
        "success": True,
        "data": {
            "associations": hotspot_assocs + website_assocs + wechat_assocs,
            "globalDefault": db.query(BrowserProfile).filter_by(is_global_default=True).first()
        }
    }


@router.post("/associations/set-global-default")
async def set_global_default(request: Dict[str, str], db: Session = Depends(get_db)):
    """设置全局默认浏览器配置"""
    profile_id = request.get("profile_id")
    if not profile_id:
        raise HTTPException(status_code=400, detail="缺少 profile_id 参数")

    profile = db.query(BrowserProfile).filter_by(id=profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="浏览器配置不存在")

    # 取消其他默认
    db.query(BrowserProfile).filter(BrowserProfile.is_global_default == True).update(
        {"is_global_default": False}
    )
    profile.is_global_default = True
    db.commit()

    return {"success": True, "message": f"已将 '{profile.name}' 设为全局默认"}
