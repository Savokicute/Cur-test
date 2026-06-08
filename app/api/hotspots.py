# coding=utf-8
"""热榜相关 API 路由。"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query

from app.integrations import TrendRadarReader
from hot_content_bridge.config import BridgeConfig

router = APIRouter()


def _calculate_trend(rank_history: List[Dict[str, Any]]) -> str:
    """根据排名历史计算趋势。

    Returns:
        "up" | "down" | "same" | "new"
    """
    if len(rank_history) < 2:
        return "new"

    # 获取最近两次排名
    latest_rank = rank_history[0]["rank"]
    prev_rank = rank_history[1]["rank"]

    if latest_rank < prev_rank:
        return "up"  # 排名数字越小越好
    elif latest_rank > prev_rank:
        return "down"
    else:
        return "same"


def _group_hotspots(hotspots: List[Dict[str, Any]], date_str: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
    """按平台分组热榜数据。"""
    groups: Dict[str, List[Dict[str, Any]]] = {}

    for item in hotspots:
        platform = item["platform_name"] or item["platform_id"]
        if platform not in groups:
            groups[platform] = []

        trend = _calculate_trend(item.get("rank_history", []))

        # _source_date: 优先使用数据自带值，否则使用请求日期（用于文章详情回查）
        source_date = item.get("_source_date") or date_str

        groups[platform].append({
            "id": item["news_id"],
            "title": item["title"],
            "platform_id": item["platform_id"],
            "platform_name": platform,
            "rank": item["rank"],
            "url": item.get("url_norm"),
            "mobile_url": item.get("mobile_url"),
            "trend": trend,
            "article_status": item.get("article_status"),
            "md_chars": item.get("md_chars", 0),
            "fetched_at": item.get("fetched_at"),
            "error": item.get("error"),
            "first_crawl_time": item.get("first_crawl_time"),
            "last_crawl_time": item.get("last_crawl_time"),
            "_source_date": source_date,
            "_crawl_time_full": item.get("_crawl_time_full"),
        })

    return groups


@router.get("/hotspots")
async def get_hotspots(
    date: Optional[str] = Query(None, description="起始日期 (YYYY-MM-DD)，不填则获取全部"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM-DD)，与 date 配合使用做范围查询"),
    days: Optional[int] = Query(None, description="获取最近 N 天的汇总数据，不填或为 0 则返回所有天"),
    group_by: Optional[str] = Query("platform", description="分组方式: platform | none"),
):
    """获取热榜数据。

    Args:
        date: 起始日期（可选）
        end_date: 结束日期（可选，与 date 配合使用）
        days: 可选，获取最近 N 天（0 或不填 = 所有天）
        group_by: 分组方式

    Returns:
        包含热榜数据和元信息的响应
    """
    try:
        cfg = BridgeConfig.load()
        reader = TrendRadarReader(cfg)

        # 如果请求多天汇总数据
        if days and days > 0 and not date:
            return await _get_multi_day_summary(reader, days)

        # 日期范围查询：date + end_date
        if date and end_date:
            return await _get_date_range_hotspots(reader, date, end_date, group_by)

        # 指定了单日查询（无 end_date）
        if date:
            latest_crawl, hotspots = reader.get_hotspots_with_articles(date)
            if not latest_crawl:
                return {
                    "success": True,
                    "data": {
                        "last_fetch_time": None,
                        "total_items": 0,
                        "groups": {},
                        "date_distribution": {},
                    },
                }
            groups = _group_hotspots(hotspots, date_str=date)
            return {
                "success": True,
                "data": {
                    "last_fetch_time": latest_crawl,
                    "total_items": len(hotspots),
                    "groups": groups,
                    "date_distribution": {date: len(hotspots)},
                },
            }

        # 无参数：返回所有可用日期的聚合数据
        all_hotspots, date_dist = reader.get_all_hotspots_with_articles()

        if not all_hotspots:
            return {
                "success": True,
                "data": {
                    "last_fetch_time": None,
                    "total_items": 0,
                    "groups": {},
                    "date_distribution": {},
                },
            }

        # 取最新一条记录的完整时间作为 last_fetch_time
        latest_item_time = None
        for item in all_hotspots:
            t = item.get("_crawl_time_full") or item.get("last_crawl_time")
            if t:
                latest_item_time = t
                break

        if group_by == "none":
            result = {
                "success": True,
                "data": {
                    "last_fetch_time": latest_item_time,
                    "total_items": len(all_hotspots),
                    "date_distribution": date_dist,
                    "items": [
                        {
                            "id": item["news_id"],
                            "title": item["title"],
                            "platform_id": item["platform_id"],
                            "platform_name": item.get("platform_name"),
                            "rank": item["rank"],
                            "url": item.get("url_norm"),
                            "mobile_url": item.get("mobile_url"),
                            "trend": _calculate_trend(item.get("rank_history", [])),
                            "article_status": item.get("article_status"),
                            "md_chars": item.get("md_chars", 0),
                            "fetched_at": item.get("fetched_at"),
                            "_source_date": item.get("_source_date"),
                            "_crawl_time_full": item.get("_crawl_time_full"),
                        }
                        for item in all_hotspots
                    ],
                },
            }
        else:
            groups = _group_hotspots(all_hotspots, date_str=None)  # 多日聚合不设置统一日期
            result = {
                "success": True,
                "data": {
                    "last_fetch_time": latest_item_time,
                    "total_items": len(all_hotspots),
                    "groups": groups,
                    "date_distribution": date_dist,
                },
            }

        return result

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"内部错误: {str(e)}")


async def _get_date_range_hotspots(reader, start_date_str: str, end_date_str: str, group_by: str):
    """获取指定日期范围内的热榜数据。"""
    from datetime import datetime

    # 验证日期格式
    try:
        start_dt = datetime.strptime(start_date_str, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date_str, "%Y-%m-%d")
        if end_dt < start_dt:
            raise ValueError("结束日期不能早于起始日期")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"日期参数无效: {e}")

    # 获取全部数据后按 _source_date 过滤
    all_hotspots, _ = reader.get_all_hotspots_with_articles()
    filtered = []
    for item in all_hotspots:
        sd = item.get("_source_date")
        if sd:
            try:
                item_dt = datetime.strptime(sd, "%Y-%m-%d")
                if start_dt <= item_dt <= end_dt:
                    filtered.append(item)
            except ValueError:
                continue

    # 构建范围内的日期分布
    from collections import Counter
    date_counts = Counter(item.get("_source_date") for item in filtered)

    if group_by == "none":
        return {
            "success": True,
            "data": {
                "last_fetch_time": f"{start_date_str} ~ {end_date_str}",
                "total_items": len(filtered),
                "date_distribution": dict(date_counts),
                "items": [
                    {
                        "id": item["news_id"],
                        "title": item["title"],
                        "platform_id": item["platform_id"],
                        "platform_name": item.get("platform_name"),
                        "rank": item["rank"],
                        "url": item.get("url_norm"),
                        "mobile_url": item.get("mobile_url"),
                        "trend": _calculate_trend(item.get("rank_history", [])),
                        "article_status": item.get("article_status"),
                        "md_chars": item.get("md_chars", 0),
                        "fetched_at": item.get("fetched_at"),
                        "_source_date": item.get("_source_date"),
                        "_crawl_time_full": item.get("_crawl_time_full"),
                    }
                    for item in filtered
                ],
            },
        }

    groups = _group_hotspots(filtered, date_str=None)  # 无日期参数时不设置统一日期
    return {
        "success": True,
        "data": {
            "last_fetch_time": f"{start_date_str} ~ {end_date_str}",
            "total_items": len(filtered),
            "groups": groups,
            "date_distribution": dict(date_counts),
        },
    }


async def _get_multi_day_summary(reader: TrendRadarReader, days: int) -> Dict[str, Any]:
    """获取最近 N 天的热榜数据汇总。

    Args:
        reader: TrendRadarReader 实例
        days: 天数

    Returns:
        多天汇总数据
    """
    available_dates = reader.get_available_dates()
    dates_to_query = available_dates[:days]

    summary = {
        "dates_queried": dates_to_query,
        "total_days": len(dates_to_query),
        "daily_stats": [],
        "grand_total_items": 0,
    }

    for date_str in dates_to_query:
        try:
            latest_crawl, hotspots = reader.get_hotspots_with_articles(date_str)
            daily_stat = {
                "date": date_str,
                "last_fetch_time": latest_crawl,
                "total_items": len(hotspots),
                "has_data": latest_crawl is not None,
            }
            summary["daily_stats"].append(daily_stat)
            if latest_crawl:
                summary["grand_total_items"] += len(hotspots)
        except Exception:
            # 单个日期查询失败不影响整体结果
            summary["daily_stats"].append({
                "date": date_str,
                "last_fetch_time": None,
                "total_items": 0,
                "has_data": False,
            })

    return {
        "success": True,
        "data": summary,
    }


@router.get("/hotspots/dates")
async def get_available_dates():
    """获取所有可用日期列表。

    Returns:
        包含可用日期列表的响应
    """
    try:
        cfg = BridgeConfig.load()
        reader = TrendRadarReader(cfg)
        dates = reader.get_available_dates()

        return {
            "success": True,
            "data": {
                "dates": dates,
                "total": len(dates),
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"内部错误: {str(e)}")


@router.get("/hotspots/platforms")
async def get_platforms(date: Optional[str] = Query(None)):
    """获取平台列表。"""
    try:
        cfg = BridgeConfig.load()
        reader = TrendRadarReader(cfg)
        platforms = reader.get_platforms(date)

        return {
            "success": True,
            "data": platforms,
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"内部错误: {str(e)}")
