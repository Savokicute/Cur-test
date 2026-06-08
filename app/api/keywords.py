# coding=utf-8
"""
关键词配置管理 API

提供关键词配置的读取、保存、解析和验证功能，
集成 TrendRadar 的 frequency_words.txt 配置系统。
"""

import shutil
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from trendradar.core.frequency import load_frequency_words, matches_word_groups

router = APIRouter(prefix="/keywords", tags=["关键词配置"])

# 配置文件路径（相对于项目根目录）
DEFAULT_CONFIG_PATH = Path("trendRadar/config/frequency_words.txt")
BACKUP_DIR = Path("trendRadar/config/backups")


class KeywordConfigResponse(BaseModel):
    """关键词配置响应"""
    success: bool
    data: Dict
    message: str = ""


class SaveConfigRequest(BaseModel):
    """保存配置请求"""
    content: str
    create_backup: bool = True


class ValidateRequest(BaseModel):
    """验证请求"""
    content: str


class ValidateResponse(BaseModel):
    """验证响应"""
    success: bool
    valid: bool
    errors: List[str] = []
    warnings: List[str] = []
    parsed_groups: int = 0
    filter_count: int = 0
    global_filter_count: int = 0


def _get_config_path() -> Path:
    """获取配置文件路径"""
    config_path = DEFAULT_CONFIG_PATH
    if not config_path.exists():
        # 尝试从环境变量获取
        import os
        env_path = os.environ.get("FREQUENCY_WORDS_PATH")
        if env_path:
            config_path = Path(env_path)
    
    return config_path


def _create_backup(config_path: Path) -> str:
    """创建配置文件备份"""
    if not BACKUP_DIR.exists():
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"frequency_words_{timestamp}.txt.bak"
    backup_path = BACKUP_DIR / backup_filename
    
    shutil.copy2(config_path, backup_path)
    
    return backup_filename


@router.get("/config")
async def get_keyword_config():
    """
    获取关键词配置文件原始内容
    
    返回 frequency_words.txt 的完整文本内容
    """
    try:
        config_path = _get_config_path()
        
        if not config_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"配置文件不存在: {config_path}"
            )
        
        with open(config_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # 获取文件修改时间
        mtime = datetime.fromtimestamp(config_path.stat().st_mtime)
        
        return KeywordConfigResponse(
            success=True,
            data={
                "content": content,
                "path": str(config_path),
                "modified_time": mtime.isoformat(),
                "size": len(content)
            },
            message="配置加载成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"读取配置失败: {str(e)}"
        )


@router.put("/config")
async def save_keyword_config(request: SaveConfigRequest):
    """
    保存关键词配置
    
    将新的配置内容写入 frequency_words.txt，
    可选择是否自动创建备份
    """
    try:
        config_path = _get_config_path()
        
        if not config_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"配置文件不存在: {config_path}"
            )
        
        # 创建备份（如果启用）
        backup_filename = None
        if request.create_backup:
            backup_filename = _create_backup(config_path)
        
        # 写入新配置
        with open(config_path, "w", encoding="utf-8") as f:
            f.write(request.content)
        
        return KeywordConfigResponse(
            success=True,
            data={
                "backup_created": backup_filename is not None,
                "backup_filename": backup_filename,
                "saved_at": datetime.now().isoformat()
            },
            message="配置保存成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"保存配置失败: {str(e)}"
        )


@router.get("/parsed")
async def get_parsed_keywords():
    """
    获取解析后的关键词配置
    
    返回结构化的关键词分组数据，
    包括每个分组的名称、关键词列表、类型等
    """
    try:
        config_path = _get_config_path()
        
        if not config_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"配置文件不存在: {config_path}"
            )
        
        # 使用 TrendRadar 的解析器
        word_groups, filter_words, global_filters = load_frequency_words(
            str(config_path)
        )
        
        # 构建结构化响应
        groups_data = []
        for idx, group in enumerate(word_groups, 1):
            # 提取普通关键词
            normal_words = []
            for w in group["normal"]:
                normal_words.append({
                    "word": w["word"],
                    "is_regex": w["is_regex"],
                    "display_name": w.get("display_name")
                })
            
            # 提取必须关键词
            required_words = []
            for w in group["required"]:
                required_words.append({
                    "word": w["word"],
                    "is_regex": w["is_regex"],
                    "display_name": w.get("display_name")
                })
            
            groups_data.append({
                "id": idx,
                "display_name": group.get("display_name"),
                "group_key": group["group_key"],
                "normal_words": normal_words,
                "required_words": required_words,
                "max_count": group["max_count"],
                "total_words": len(normal_words) + len(required_words)
            })
        
        # 提取过滤词
        filter_data = []
        for fw in filter_words:
            filter_data.append({
                "word": fw["word"],
                "is_regex": fw["is_regex"],
                "display_name": fw.get("display_name")
            })
        
        return KeywordConfigResponse(
            success=True,
            data={
                "groups": groups_data,
                "group_count": len(groups_data),
                "filter_words": filter_data,
                "filter_count": len(filter_data),
                "global_filters": global_filters,
                "global_filter_count": len(global_filters),
                "total_keywords": sum(g["total_words"] for g in groups_data)
            },
            message=f"成功解析 {len(groups_data)} 个关键词分组"
        )
        
    except HTTPException:
        raise
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"解析配置失败: {str(e)}"
        )


@router.post("/validate")
async def validate_keyword_config(request: ValidateRequest):
    """
    验证关键词配置语法
    
    检查配置内容是否符合语法规范，
    返回错误、警告和解析结果
    """
    errors = []
    warnings = []
    
    try:
        content = request.content
        
        # 基础语法检查
        lines = content.split("\n")
        
        # 检查必要的区域标记
        has_global_filter = False
        has_word_groups = False
        
        for line in lines:
            stripped = line.strip()
            if stripped == "[GLOBAL_FILTER]":
                has_global_filter = True
            elif stripped == "[WORD_GROUPS]":
                has_word_groups = True
        
        # 尝试解析配置
        # 写入临时文件进行解析
        import tempfile
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".txt",
            encoding="utf-8",
            delete=False
        ) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        
        try:
            word_groups, filter_words, global_filters = load_frequency_words(tmp_path)
            
            # 统计信息
            total_normal = sum(len(g["normal"]) for g in word_groups)
            total_required = sum(len(g["required"]) for g in word_groups)
            
            # 检查空分组警告
            for idx, group in enumerate(word_groups, 1):
                if not group["normal"] and not group["required"]:
                    warnings.append(f"第 {idx} 个分组没有定义任何关键词")
                
                if group["max_count"] > 0 and group["max_count"] < 3:
                    warnings.append(
                        f"分组 '{group.get('display_name') or group['group_key']}' "
                        f"限制显示 {group['max_count']} 条，可能过少"
                    )
            
            # 成功解析
            return ValidateResponse(
                success=True,
                valid=len(errors) == 0,
                errors=errors,
                warnings=warnings,
                parsed_groups=len(word_groups),
                filter_count=len(filter_words),
                global_filter_count=len(global_filters)
            )
            
        except re.error as e:
            errors.append(f"正则表达式错误: {str(e)}")
        except Exception as parse_error:
            errors.append(f"解析失败: {str(parse_error)}")
        finally:
            # 清理临时文件
            Path(tmp_path).unlink(missing_ok=True)
        
        # 有错误但仍然返回
        return ValidateResponse(
            success=True,
            valid=False,
            errors=errors,
            warnings=warnings,
            parsed_groups=0,
            filter_count=0,
            global_filter_count=0
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"验证过程出错: {str(e)}"
        )


@router.post("/test-match")
async def test_keyword_match(
    title: str = Query(..., description="要测试的标题文本"),
    use_global_filter: bool = Query(True, description="是否使用全局过滤")
):
    """
    测试标题是否匹配当前关键词配置
    
    用于实时预览筛选效果
    """
    try:
        config_path = _get_config_path()
        
        if not config_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"配置文件不存在: {config_path}"
            )
        
        # 加载配置
        word_groups, filter_words, global_filters = load_frequency_words(
            str(config_path)
        )
        
        # 执行匹配
        global_filters_to_use = global_filters if use_global_filter else None
        is_match = matches_word_groups(
            title,
            word_groups,
            filter_words,
            global_filters_to_use
        )
        
        # 找出匹配的分组
        matched_groups = []
        if is_match and word_groups:
            for idx, group in enumerate(word_groups, 1):
                group_match = matches_word_groups(
                    title,
                    [group],
                    [],
                    None  # 不使用全局过滤单独检查每个分组
                )
                if group_match:
                    matched_groups.append({
                        "id": idx,
                        "name": group.get("display_name") or group["group_key"]
                    })
        
        # 检查是否被全局过滤
        blocked_by_global = False
        if use_global_filter and global_filters:
            title_lower = title.lower()
            blocked_by_global = any(
                gf.lower() in title_lower for gf in global_filters
            )
        
        # 检查是否被过滤词匹配
        blocked_by_filter = False
        if filter_words:
            from trendradar.core.frequency import _word_matches
            title_lower = title.lower()
            blocked_by_filter = any(
                _word_matches(fw, title_lower) for fw in filter_words
            )
        
        return {
            "success": True,
            "data": {
                "title": title,
                "is_match": is_match,
                "matched_groups": matched_groups,
                "blocked_by_global_filter": blocked_by_global,
                "blocked_by_group_filter": blocked_by_filter,
                "will_show": is_match and not blocked_by_global and not blocked_by_filter
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"测试匹配失败: {str(e)}"
        )


class BatchMatchRequest(BaseModel):
    """批量匹配请求"""
    titles: List[str]
    use_global_filter: bool = True


class BatchMatchResponse(BaseModel):
    """批量匹配响应"""
    success: bool
    data: Dict
    message: str = ""


@router.post("/batch-match")
async def batch_match_keywords(request: BatchMatchRequest):
    """
    批量匹配关键词（热榜集成专用）
    
    一次性提交多个标题，返回每个标题匹配的关键词分组信息。
    用于热榜总览页的关键词分组Tab筛选。
    """
    try:
        config_path = _get_config_path()
        
        if not config_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"配置文件不存在: {config_path}"
            )
        
        # 加载配置（只加载一次）
        word_groups, filter_words, global_filters = load_frequency_words(
            str(config_path)
        )
        
        global_filters_to_use = global_filters if request.use_global_filter else None
        
        results = []
        group_match_count = {}  # 统计每个分组的匹配数
        
        for title in request.titles:
            # 检查全局过滤
            blocked_by_global = False
            if request.use_global_filter and global_filters:
                title_lower = title.lower()
                blocked_by_global = any(
                    gf.lower() in title_lower for gf in global_filters
                )
            
            # 检查过滤词
            blocked_by_filter = False
            if filter_words:
                from trendradar.core.frequency import _word_matches
                title_lower = title.lower()
                blocked_by_filter = any(
                    _word_matches(fw, title_lower) for fw in filter_words
                )
            
            # 找出匹配的分组
            matched_group_ids = []
            if not blocked_by_global and not blocked_by_filter:
                for idx, group in enumerate(word_groups, 1):
                    group_match = matches_word_groups(
                        title,
                        [group],
                        [],
                        None
                    )
                    if group_match:
                        matched_group_ids.append(idx)
                        group_name = group.get("display_name") or group["group_key"]
                        group_match_count[group_name] = group_match_count.get(group_name, 0) + 1
            
            results.append({
                "title": title[:50],  # 截断避免响应过大
                "matched_group_ids": matched_group_ids,
                "blocked": blocked_by_global or blocked_by_filter,
                "has_match": len(matched_group_ids) > 0
            })
        
        return BatchMatchResponse(
            success=True,
            data={
                "results": results,
                "total": len(results),
                "matched_count": sum(1 for r in results if r["has_match"]),
                "group_match_count": group_match_count,
                "group_definitions": [
                    {
                        "id": idx,
                        "name": g.get("display_name") or g["group_key"],
                        "group_key": g["group_key"]
                    }
                    for idx, g in enumerate(word_groups, 1)
                ]
            },
            message=f"完成 {len(request.titles)} 条标题的关键词匹配"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"批量匹配失败: {str(e)}"
        )


@router.get("/backups")
async def list_backups():
    """
    列出所有配置备份文件
    """
    try:
        if not BACKUP_DIR.exists():
            return KeywordConfigResponse(
                success=True,
                data={"backups": [], "count": 0},
                message="暂无备份"
            )
        
        backups = sorted(
            [f for f in BACKUP_DIR.iterdir() if f.suffix == ".bak"],
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )
        
        backup_list = []
        for backup in backups[:20]:  # 只返回最近20个
            mtime = datetime.fromtimestamp(backup.stat().st_mtime)
            backup_list.append({
                "filename": backup.name,
                "size": backup.stat().st_size,
                "created_at": mtime.isoformat()
            })
        
        return KeywordConfigResponse(
            success=True,
            data={
                "backups": backup_list,
                "count": len(backup_list)
            },
            message=f"找到 {len(backup_list)} 个备份文件"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"列出备份失败: {str(e)}"
        )
