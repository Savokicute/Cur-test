# coding=utf-8
"""TrendRadar 只读适配器 - 读取 trendRadar 数据库并提供统一的数据访问接口。"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from hot_content_bridge.config import BridgeConfig


class TrendRadarReader:
    """TrendRadar 数据库只读适配器。"""

    def __init__(self, cfg: BridgeConfig):
        self.cfg = cfg
        self.data_dir = cfg.data_dir

    def _get_db_path(self, date: Optional[str] = None) -> Path:
        """获取指定日期的数据库路径，如果没有日期则返回最新的数据库。"""
        from trendradar.utils.time import format_date_folder

        if date:
            tz = self.cfg._raw_tr_config.get("app", {}).get("timezone", "Asia/Shanghai")
            date_str = format_date_folder(date, tz)
            db_path = self.data_dir / "news" / f"{date_str}.db"
            if db_path.exists():
                return db_path

        # 如果没有指定日期或指定日期不存在，找最新的数据库
        news_dir = self.data_dir / "news"
        if not news_dir.exists():
            raise FileNotFoundError(f"数据目录不存在: {news_dir}")

        db_files = sorted(news_dir.glob("*.db"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not db_files:
            raise FileNotFoundError(f"未找到任何数据库文件在: {news_dir}")

        return db_files[0]

    def _connect(self, date: Optional[str] = None) -> sqlite3.Connection:
        """连接到数据库。"""
        db_path = self._get_db_path(date)
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def get_latest_crawl_time(self, date: Optional[str] = None) -> Optional[str]:
        """获取最新的抓取时间。"""
        try:
            conn = self._connect(date)
            try:
                cur = conn.cursor()
                cur.execute("SELECT crawl_time FROM crawl_records ORDER BY crawl_time DESC LIMIT 1")
                row = cur.fetchone()
                return row[0] if row else None
            finally:
                conn.close()
        except FileNotFoundError:
            return None

    def get_news_items(self, date: Optional[str] = None, crawl_time: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取新闻条目。

        Args:
            date: 日期字符串 (YYYY-MM-DD)，可选
            crawl_time: 抓取时间，可选，如果提供则只返回该批次的数据

        Returns:
            新闻条目列表
        """
        conn = self._connect(date)
        try:
            cur = conn.cursor()

            if crawl_time:
                # 查询指定批次的数据
                cur.execute(
                    """
                    SELECT n.id AS news_id, n.title, n.platform_id,
                           COALESCE(p.name, n.platform_id) AS platform_name,
                           n.rank, n.url, n.mobile_url, n.first_crawl_time,
                           n.last_crawl_time, n.crawl_count, n.raw_extra
                    FROM news_items n
                    LEFT JOIN platforms p ON n.platform_id = p.id
                    WHERE n.last_crawl_time = ?
                    ORDER BY n.platform_id, n.rank
                    """,
                    (crawl_time,),
                )
            else:
                # 查询最新批次的数据
                latest_crawl = self.get_latest_crawl_time(date)
                if not latest_crawl:
                    return []
                cur.execute(
                    """
                    SELECT n.id AS news_id, n.title, n.platform_id,
                           COALESCE(p.name, n.platform_id) AS platform_name,
                           n.rank, n.url, n.mobile_url, n.first_crawl_time,
                           n.last_crawl_time, n.crawl_count, n.raw_extra
                    FROM news_items n
                    LEFT JOIN platforms p ON n.platform_id = p.id
                    WHERE n.last_crawl_time = ?
                    ORDER BY n.platform_id, n.rank
                    """,
                    (latest_crawl,),
                )

            rows = [dict(r) for r in cur.fetchall()]

            # 为每条新闻获取排名历史（用于计算趋势）
            for row in rows:
                row["rank_history"] = self._get_rank_history(row["news_id"], conn)

            return rows
        finally:
            conn.close()

    def _get_rank_history(self, news_id: int, conn: sqlite3.Connection) -> List[Dict[str, Any]]:
        """获取新闻的排名历史。"""
        cur = conn.cursor()
        cur.execute(
            """
            SELECT rank, crawl_time, created_at
            FROM rank_history
            WHERE news_item_id = ?
            ORDER BY crawl_time DESC
            LIMIT 10
            """,
            (news_id,),
        )
        return [dict(r) for r in cur.fetchall()]

    def get_article_content(self, url_norm: str, date: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取文章正文内容。如果指定了日期则查对应DB，否则搜索所有DB。"""
        if date:
            return self._get_article_from_db(url_norm, date)

        # 无日期时，按时间倒序遍历所有 DB（最新的优先）
        import re
        news_dir = self.data_dir / "news"
        if not news_dir.exists():
            return None

        date_pattern = re.compile(r"^(\d{4}-\d{2}-\d{2})\.db$")
        for db_file in sorted(news_dir.glob("*.db"), reverse=True):
            match = date_pattern.match(db_file.name)
            if not match:
                continue
            source_date = match.group(1)
            result = self._get_article_from_db(url_norm, source_date)
            if result is not None:
                return result

        return None

    def _get_article_from_db(self, url_norm: str, date: str) -> Optional[Dict[str, Any]]:
        """从指定日期的数据库中查询文章内容。"""
        try:
            conn = self._connect(date)
            try:
                cur = conn.cursor()
                cur.execute(
                    """
                    SELECT id, news_item_id, url_norm, platform_id, title_snapshot,
                           status, http_status, markdown, extracted_title, error,
                           content_sha256, fetched_at, created_at, updated_at
                    FROM article_contents
                    WHERE url_norm = ?
                    """,
                    (url_norm,),
                )
                row = cur.fetchone()
                return dict(row) if row else None
            finally:
                conn.close()
        except (FileNotFoundError, sqlite3.OperationalError):
            return None

    def get_platforms(self, date: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取平台列表。"""
        conn = self._connect(date)
        try:
            cur = conn.cursor()
            cur.execute("SELECT id, name, is_active, updated_at FROM platforms ORDER BY name")
            return [dict(r) for r in cur.fetchall()]
        finally:
            conn.close()

    def get_available_dates(self) -> List[str]:
        """获取所有可用日期列表（从 news/*.db 文件名提取）。

        Returns:
            日期字符串列表，格式为 YYYY-MM-DD，按日期降序排列（最新在前）
        """
        import re

        news_dir = self.data_dir / "news"
        if not news_dir.exists():
            return []

        dates = []
        date_pattern = re.compile(r"^(\d{4}-\d{2}-\d{2})\.db$")

        for db_file in sorted(news_dir.glob("*.db"), reverse=True):
            match = date_pattern.match(db_file.name)
            if match:
                dates.append(match.group(1))

        return dates

    def get_hotspots_with_articles(self, date: Optional[str] = None) -> Tuple[Optional[str], List[Dict[str, Any]]]:
        """获取热榜数据并关联文章状态。

        Returns:
            (latest_crawl_time, hotspots_list)
        """
        latest_crawl = self.get_latest_crawl_time(date)
        if not latest_crawl:
            return None, []

        conn = self._connect(date)
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT n.id AS news_id, n.title, n.platform_id,
                       COALESCE(p.name, n.platform_id) AS platform_name,
                       n.rank, n.url AS url_norm, n.mobile_url,
                       n.first_crawl_time, n.last_crawl_time, n.crawl_count, n.raw_extra,
                       a.status AS article_status, a.fetched_at, a.error,
                       CASE WHEN a.markdown IS NOT NULL AND a.markdown != ''
                            THEN length(a.markdown) ELSE 0 END AS md_chars
                FROM news_items n
                LEFT JOIN platforms p ON n.platform_id = p.id
                LEFT JOIN article_contents a ON a.url_norm = n.url
                WHERE n.last_crawl_time = ?
                ORDER BY n.platform_id, n.rank
                """,
                (latest_crawl,),
            )
            rows = [dict(r) for r in cur.fetchall()]

            for row in rows:
                row["rank_history"] = self._get_rank_history(row["news_id"], conn)

            return latest_crawl, rows
        finally:
            conn.close()

    def get_all_hotspots_with_articles(self) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
        """获取所有可用日期的热榜数据聚合结果。

        遍历 news/ 下所有 .db 文件，合并所有热榜数据。
        每条记录附加 _source_date 字段标识来源日期。

        Returns:
            (all_hotspots_list, date_distribution{date_str: count})
        """
        import re

        all_items: List[Dict[str, Any]] = []
        date_distribution: Dict[str, int] = {}
        date_pattern = re.compile(r"^(\d{4}-\d{2}-\d{2})\.db$")
        news_dir = self.data_dir / "news"

        if not news_dir.exists():
            return [], {}

        for db_file in sorted(news_dir.glob("*.db")):
            match = date_pattern.match(db_file.name)
            if not match:
                continue

            source_date = match.group(1)
            try:
                crawl_time, items = self.get_hotspots_with_articles(source_date)
                if items:
                    for item in items:
                        item["_source_date"] = source_date
                        item["_crawl_time_full"] = f"{source_date} {crawl_time}" if crawl_time else source_date
                    all_items.extend(items)
                    date_distribution[source_date] = len(items)
            except Exception as e:
                print(f"[TrendRadarReader] 跳过 {db_file.name}: {e}")
                continue

        return all_items, date_distribution


def count_word_frequency(texts: List[str]) -> List[Tuple[str, int]]:
    """简单的词频统计（用于分组）。"""
    import re
    from collections import Counter

    words = []
    for text in texts:
        # 简单的分词（中文按字符，英文按单词）
        # 这里只是示例，实际应该使用 proper tokenizer
        text = text.lower()
        # 提取英文单词
        eng_words = re.findall(r'[a-zA-Z]{2,}', text)
        words.extend(eng_words)
        # 提取中文字符（简单按单个字）
        chi_chars = re.findall(r'[\u4e00-\u9fff]', text)
        words.extend(chi_chars)

    counter = Counter(words)
    return counter.most_common(100)
