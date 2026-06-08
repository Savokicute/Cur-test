# coding=utf-8
"""数据库索引优化与迁移脚本 - 自动检测并创建缺失的索引"""

import logging
import time
from typing import Dict, List, Tuple, Any
from sqlalchemy import text, inspect
from app.core.database import get_engine, get_db_session

logger = logging.getLogger(__name__)


class IndexOptimizer:
    """
    数据库索引优化器

    功能：
    1. 自动检测缺失的索引
    2. 分析查询性能瓶颈
    3. 提供索引建议
    4. 执行索引创建/删除操作
    """

    # 预定义的索引配置（表名 -> 索引列表）
    RECOMMENDED_INDEXES = {
        "hotspot_news": [
            {
                "name": "idx_hotspots_platform_date",
                "columns": ["platform_id", "_source_date"],
                "type": "composite",
                "description": "平台+日期复合索引，加速按平台和时间范围查询"
            },
            {
                "name": "idx_hotspots_title_fts",
                "columns": ["title"],
                "type": "fulltext",
                "description": "标题全文索引，支持模糊搜索"
            },
        ],
        "articles": [
            {
                "name": "idx_articles_source_url",
                "columns": ["source_url"],
                "type": "unique",
                "description": "源URL唯一索引，防止重复"
            },
        ],
        "media_items": [
            {
                "name": "idx_media_items_article_type",
                "columns": ["article_id", "media_type"],
                "type": "composite",
                "description": "文章ID+类型复合索引"
            },
        ],
        "ai_analysis_reports": [
            {
                "name": "idx_ai_reports_config_status",
                "columns": ["config_id", "status"],
                "type": "composite",
                "description": "配置ID+状态复合索引"
            },
            {
                "name": "idx_ai_reports_created_at",
                "columns": ["created_at"],
                "type": "btree",
                "description": "创建时间索引，支持时间范围查询"
            },
        ],
        "wechat_articles": [
            {
                "name": "idx_wechat_articles_feed_status",
                "columns": ["feed_id", "status"],
                "type": "composite",
                "description": "订阅ID+状态复合索引"
            },
        ],
        "subscriptions": [
            {
                "name": "idx_subscriptions_active_type",
                "columns": ["is_active", "subscription_type"],
                "type": "composite",
                "description": "活跃状态+类型复合索引"
            },
        ],
        "notification_logs": [
            {
                "name": "idx_notification_logs_subscription_status",
                "columns": ["subscription_id", "status"],
                "type": "composite",
                "description": "订阅ID+状态复合索引"
            },
        ],
        "tasks": [
            {
                "name": "idx_tasks_priority_status",
                "columns": ["priority", "status"],
                "type": "composite",
                "description": "优先级+状态复合索引，用于任务队列"
            },
            {
                "name": "idx_tasks_next_retry",
                "columns": ["next_retry_at"],
                "type": "btree",
                "description": "下次重试时间索引"
            },
        ],
    }

    def __init__(self):
        self.engine = get_engine()
        self.inspector = inspect(self.engine)

    def get_existing_indexes(self, table_name: str) -> List[Dict[str, Any]]:
        """获取表的现有索引"""
        try:
            indexes = self.inspector.get_indexes(table_name)
            return indexes
        except Exception as e:
            logger.warning(f"获取表 {table_name} 索引失败: {e}")
            return []

    def analyze_missing_indexes(self) -> Dict[str, List[Dict]]:
        """分析缺失的索引"""
        missing = {}

        for table_name, recommended in self.RECOMMENDED_INDEXES.items():
            # 检查表是否存在
            if table_name not in self.inspector.get_table_names():
                logger.debug(f"表 {table_name} 不存在，跳过")
                continue

            existing_indexes = self.get_existing_indexes(table_name)
            existing_names = {idx["name"] for idx in existing_indexes}

            missing_for_table = []
            for index_config in recommended:
                if index_config["name"] not in existing_names:
                    missing_for_table.append(index_config)

            if missing_for_table:
                missing[table_name] = missing_for_table

        return missing

    def create_index(self, table_name: str, index_config: Dict[str, Any]) -> bool:
        """创建单个索引"""
        try:
            index_name = index_config["name"]
            columns = index_config["columns"]
            index_type = index_config.get("type", "btree")

            with self.engine.connect() as conn:
                if index_type == "unique":
                    sql = f"CREATE UNIQUE INDEX IF NOT EXISTS {index_name} ON {table_name} ({', '.join(columns)})"
                elif index_type == "fulltext":
                    # SQLite 使用 FTS5 或 GIN (PostgreSQL)
                    sql = f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name} ({', '.join(columns)})"
                else:
                    sql = f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name} ({', '.join(columns)})"

                conn.execute(text(sql))
                conn.commit()

            logger.info(f"已创建索引: {index_name} on {table_name}({', '.join(columns)})")
            return True

        except Exception as e:
            logger.error(f"创建索引失败 {index_config['name']}: {e}", exc_info=True)
            return False

    def optimize_all(self, auto_create: bool = False) -> Dict[str, Any]:
        """
        执行全面的索引优化分析

        Args:
            auto_create: 是否自动创建缺失的索引

        Returns:
            包含优化结果的字典
        """
        start_time = time.time()
        result = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "tables_analyzed": len(self.RECOMMENDED_INDEXES),
            "missing_indexes": {},
            "created_indexes": [],
            "errors": [],
            "duration_seconds": 0,
        }

        # 分析缺失索引
        missing = self.analyze_missing_indexes()
        result["missing_indexes"] = missing

        total_missing = sum(len(v) for v in missing.values())
        logger.info(f"索引分析完成: 发现 {total_missing} 个缺失索引")

        if auto_create and missing:
            # 自动创建缺失的索引
            for table_name, indexes in missing.items():
                for index_config in indexes:
                    success = self.create_index(table_name, index_config)
                    if success:
                        result["created_indexes"].append({
                            "table": table_name,
                            "index": index_config["name"],
                            "description": index_config.get("description", "")
                        })
                    else:
                        result["errors"].append({
                            "table": table_name,
                            "index": index_config["name"],
                        })

        result["duration_seconds"] = round(time.time() - start_time, 2)
        return result

    def get_query_suggestions(self) -> List[Dict[str, str]]:
        """基于现有索引提供查询优化建议"""
        suggestions = []

        # 检查常见查询模式是否缺少索引
        common_patterns = [
            {
                "pattern": "按平台和日期范围查询热榜",
                "tables": ["hotspot_news"],
                "recommended_index": "idx_hotspots_platform_date",
                "sql_example": "SELECT * FROM hotspot_news WHERE platform_id=? AND _source_date BETWEEN ? AND ?"
            },
            {
                "pattern": "按订阅ID和状态查询通知日志",
                "tables": ["notification_logs"],
                "recommended_index": "idx_notification_logs_subscription_status",
                "sql_example": "SELECT * FROM notification_logs WHERE subscription_id=? AND status=? ORDER BY created_at DESC LIMIT 50"
            },
            {
                "pattern": "按优先级获取待处理任务",
                "tables": ["tasks"],
                "recommended_index": "idx_tasks_priority_status",
                "sql_example": "SELECT * FROM tasks WHERE status='pending' ORDER BY priority DESC, created_at ASC LIMIT 10"
            },
        ]

        for pattern_info in common_patterns:
            index_exists = False
            for table_name in pattern_info["tables"]:
                existing = self.get_existing_indexes(table_name)
                existing_names = {idx["name"] for idx in existing}
                if pattern_info["recommended_index"] in existing_names:
                    index_exists = True
                    break

            if not index_exists:
                suggestions.append(pattern_info)

        return suggestions


def run_migration(dry_run: bool = False):
    """
    运行数据库迁移

    Args:
        dry_run: 如果为True，只分析不执行
    """
    logger.info("="*60)
    logger.info("开始数据库索引优化迁移")
    logger.info("="*60)

    optimizer = IndexOptimizer()

    # 执行分析
    result = optimizer.optimize_all(auto_create=not dry_run)

    # 输出结果
    logger.info("\n📊 迁移结果摘要:")
    logger.info(f"  - 分析表数量: {result['tables_analyzed']}")
    logger.info(f"  - 缺失索引数: {sum(len(v) for v in result['missing_indexes'].values())}")

    if result['created_indexes']:
        logger.info(f"  - 已创建索引数: {len(result['created_indexes'])}")
        for idx in result['created_indexes']:
            logger.info(f"    ✓ [{idx['table']}] {idx['index']} - {idx['description']}")

    if result['errors']:
        logger.warning(f"  - 创建失败数: {len(result['errors'])}")
        for err in result['errors']:
            logger.warning(f"    ✗ [{err['table']}] {err['index']}")

    # 输出查询优化建议
    suggestions = optimizer.get_query_suggestions()
    if suggestions:
        logger.info("\n💡 查询优化建议:")
        for sug in suggestions:
            logger.info(f"  - {sug['pattern']}")
            logger.info(f"    建议添加索引: {sug['recommended_index']}")
            logger.info(f"    示例SQL: {sug['sql_example']}")

    logger.info(f"\n⏱️ 总耗时: {result['duration_seconds']}秒")
    logger.info("="*60)

    return result


if __name__ == "__main__":
    import sys

    dry_run = "--dry-run" in sys.argv or "--check" in sys.argv

    print("\n" + "="*60)
    print("  TrendRadar 数据库索引优化工具")
    print("="*60)
    print()

    if dry_run:
        print("模式: 仅分析（不会修改数据库）\n")
    else:
        print("模式: 自动执行\n")

    result = run_migration(dry_run=dry_run)

    print("\n✅ 迁移完成!")
    print(f"   创建了 {len(result['created_indexes'])} 个索引")
    if result['errors']:
        print(f"   ⚠️  {len(result['errors'])} 个索引创建失败")
