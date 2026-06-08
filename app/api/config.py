import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/config", tags=["系统配置"])


def _get_config_path() -> Path:
    # 方法1: 使用相对于项目根目录的路径
    project_root = Path(__file__).parent.parent.parent
    config_path = project_root / "trendRadar" / "config" / "config.yaml"

    # 如果路径不存在，尝试备选路径
    if not config_path.exists():
        # 备选1: 当前工作目录下的相对路径
        alt_path = Path("trendRadar/config/config.yaml")
        if alt_path.exists():
            return alt_path.resolve()

        # 备选2: 环境变量指定
        env_path = os.environ.get("TRENDRADAR_CONFIG")
        if env_path:
            return Path(env_path)

    return config_path


def _get_backup_dir() -> Path:
    config_path = _get_config_path()
    backup_dir = config_path.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    return backup_dir


@router.get("")
async def get_config():
    """读取完整 config.yaml 内容"""
    try:
        config_path = _get_config_path()
        if not config_path.exists():
            raise HTTPException(status_code=404, detail="config.yaml 不存在")

        with open(config_path, 'r', encoding='utf-8') as f:
            content = f.read()

        config = yaml.safe_load(content) or {}

        return {
            "success": True,
            "data": {
                "raw": content,
                "parsed": config,
                "modules": list(config.keys()),
                "modified_time": datetime.fromtimestamp(
                    config_path.stat().st_mtime
                ).isoformat(),
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取配置失败: {str(e)}")


@router.get("/module")
async def get_config_module(
    module: str = Query(..., description="模块名称，如 platforms/rss/schedule/ai 等"),
):
    """读取指定模块的配置"""
    try:
        config_path = _get_config_path()
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f) or {}

        if module not in config:
            raise HTTPException(
                status_code=404,
                detail=f"模块 '{module}' 不存在，可用模块: {list(config.keys())}"
            )

        return {"success": True, "data": { "module": module, "value": config[module] }}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取模块失败: {str(e)}")


@router.put("/module")
async def update_config_module(
    module: str = Query(..., description="模块名称"),
    value: Dict[str, Any] = None,
):
    """更新指定模块的配置（合并写入）"""
    try:
        config_path = _get_config_path()
        with open(config_path, 'r', encoding='utf-8') as f:
            content = f.read()
            config = yaml.safe_load(content) or {}

        if value is None:
            raise HTTPException(status_code=400, detail="请求体不能为空")

        # 解包前端传来的 {value: actualData} 结构
        actual_value = value.get("value") if "value" in value else value

        old_value = config.get(module)
        config[module] = actual_value

        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

        return {
            "success": True,
            "message": f"模块 [{module}] 已更新",
            "data": { "module": module, "old_value": old_value, "new_value": actual_value },
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新模块失败: {str(e)}")


@router.put("")
async def save_config(
    content: Optional[str] = None,
    parsed: Optional[Dict[str, Any]] = None,
    create_backup: bool = True,
):
    """
    保存完整 config.yaml
    - content: 原始 YAML 文本（优先使用）
    - parsed: 解析后的字典（将重新序列化为 YAML）
    - create_backup: 是否创建备份
    """
    try:
        config_path = _get_config_path()

        if not config_path.exists():
            raise HTTPException(status_code=404, detail="config.yaml 不存在")

        if create_backup:
            backup_dir = _get_backup_dir()
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = backup_dir / f"config_{ts}.yaml.bak"
            shutil.copy2(config_path, backup_path)

        if content is not None:
            with open(config_path, 'w', encoding='utf-8') as f:
                f.write(content)
        elif parsed is not None:
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(
                    parsed, f,
                    allow_unicode=True,
                    default_flow_style=False,
                    sort_keys=False,
                )
        else:
            raise HTTPException(status_code=400, detail="需要提供 content 或 parsed 参数")

        return {
            "success": True,
            "message": "配置已保存",
            "data": {
                "backup_created": create_backup,
                "backup_file": f"config_{ts}.yaml.bak" if create_backup else None,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存配置失败: {str(e)}")


@router.get("/backups")
async def list_backups():
    """列出配置备份文件"""
    try:
        backup_dir = _get_backup_dir()
        backups = []
        for f in sorted(backup_dir.glob("config_*.yaml.bak"), reverse=True):
            stat = f.stat()
            backups.append({
                "filename": f.name,
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            })
        return {"success": True, "data": {"backups": backups, "count": len(backups)}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/restore")
async def restore_backup(filename: str = Query(..., description="备份文件名")):
    """从备份恢复配置"""
    try:
        backup_dir = _get_backup_dir()
        config_path = _get_config_path()
        backup_path = backup_dir / filename

        if not backup_path.exists():
            raise HTTPException(status_code=404, detail=f"备份文件不存在: {filename}")

        shutil.copy2(backup_path, config_path)
        return {"success": True, "message": f"已从备份 {filename} 恢复配置"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"恢复失败: {str(e)}")


@router.get("/schema")
async def get_config_schema():
    """返回 config.yaml 的结构化 schema（用于前端表单生成）"""
    schema = {
        "app": {
            "title": "基础设置",
            "icon": "SettingOutlined",
            "fields": [
                {"key": "timezone", "label": "时区", "type": "select",
                 "options": ["Asia/Shanghai", "America/New_York", "Europe/London"],
                 "description": "影响所有时间显示和调度判断"},
                {"key": "show_version_update", "label": "显示版本更新提示", "type": "switch"},
            ],
        },
        "schedule": {
            "title": "调度系统",
            "icon": "ScheduleOutlined",
            "fields": [
                {"key": "enabled", "label": "启用调度系统", "type": "switch"},
                {"key": "preset", "label": "预设模板", "type": "select",
                 "options": [
                     ("always_on", "全天候"),
                     ("morning_evening", "全天推送+晚间汇总(推荐)"),
                     ("office_hours", "工作日三段式"),
                     ("night_owl", "午后速览+深夜汇总"),
                     ("custom", "完全自定义"),
                 ]},
            ],
        },
        "platforms": {
            "title": "热榜平台",
            "icon": "CloudServerOutlined",
            "type": "complex",
            "description": "管理热榜数据源平台的启停状态",
        },
        "rss": {
            "title": "RSS 订阅",
            "icon": "LinkOutlined",
            "type": "complex",
            "description": "管理 RSS 数据源订阅",
        },
        "report": {
            "title": "报告模式",
            "icon": "FileTextOutlined",
            "fields": [
                {"key": "mode", "label": "模式", "type": "select",
                 "options": [("daily", "每日"), ("current", "当前"), ("incremental", "增量")]},
                {"key": "display_mode", "label": "展示模式", "type": "select",
                 "options": [("keyword", "按关键词"), ("platform", "按平台")]},
                {"key": "rank_threshold", "label": "排名阈值", "type": "number", "min": 1, "max": 50},
                {"key": "sort_by_position_first", "label": "按排名优先排序", "type": "switch"},
            ],
        },
        "filter": {
            "title": "筛选策略",
            "icon": "FilterOutlined",
            "fields": [
                {"key": "method", "label": "筛选方法", "type": "select",
                 "options": [("keyword", "关键词匹配"), ("ai", "AI智能分类")]},
                {"key": "priority_sort_enabled", "label": "按标签优先级排序", "type": "switch"},
            ],
        },
        "ai_filter": {
            "title": "AI 筛选参数",
            "icon": "RobotOutlined",
            "fields": [
                {"key": "batch_size", "label": "每批处理数量", "type": "number", "min": 10, "max": 1000},
                {"key": "batch_interval", "label": "分批间隔(秒)", "type": "number", "min": 1, "max": 60},
                {"key": "min_score", "label": "最低分数阈值", "type": "number", "min": 0.0, "max": 1.0, "step": 0.1},
                {"key": "reclassify_threshold", "label": "重分类阈值", "type": "number", "min": 0.0, "max": 1.0, "step": 0.1},
            ],
        },
        "display": {
            "title": "推送内容控制",
            "icon": "EyeOutlined",
            "type": "complex",
        },
        "notification": {
            "title": "推送通知",
            "icon": "BellOutlined",
            "type": "complex",
            "description": "配置各类通知渠道的 webhook 和参数",
        },
        "storage": {
            "title": "存储配置",
            "icon": "DatabaseOutlined",
            "type": "complex",
        },
        "ai": {
            "title": "AI 模型",
            "icon": "ApiOutlined",
            "fields": [
                {"key": "model", "label": "模型名称", "type": "input"},
                {"key": "api_base", "label": "API 地址", "type": "input"},
                {"key": "api_key", "label": "API Key", "type": "password"},
                {"key": "timeout", "label": "超时时间(秒)", "type": "number", "min": 10, "max": 600},
                {"key": "temperature", "label": "Temperature", "type": "number", "min": 0.0, "max": 2.0, "step": 0.1},
                {"key": "max_tokens", "label": "最大 Token 数", "type": "number", "min": 100, "max": 32000},
            ],
        },
        "ai_analysis": {
            "title": "AI 分析功能",
            "icon": "ExperimentOutlined",
            "fields": [
                {"key": "enabled", "label": "启用 AI 分析", "type": "switch"},
                {"key": "language", "label": "分析语言", "type": "select",
                 "options": ["Chinese", "English"]},
                {"key": "mode", "label": "分析模式", "type": "select",
                 "options": [("follow_report", "跟随报告"), ("standalone", "独立分析")]},
                {"key": "max_news_for_analysis", "label": "最大分析新闻数", "type": "number", "min": 10, "max": 500},
            ],
        },
        "ai_translation": {
            "title": "AI 翻译功能",
            "icon": "TranslationOutlined",
            "fields": [
                {"key": "enabled", "label": "启用 AI 翻译", "type": "switch"},
                {"key": "language", "label": "目标语言", "type": "input"},
            ],
        },
        "advanced": {
            "title": "高级设置",
            "icon": "ToolOutlined",
            "fields": [
                {"key": "debug", "label": "调试模式", "type": "switch"},
                {"key": "crawler.request_interval", "label": "爬虫请求间隔(ms)", "type": "number", "min": 100, "max": 10000},
                {"key": "crawler.use_proxy", "label": "使用代理", "type": "switch"},
            ],
        },
    }
    return {"success": True, "data": {"modules": schema}}
