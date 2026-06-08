# coding=utf-8
"""
AI 分析 API 路由

提供完整的 RESTful API 接口用于：
- AI分析配置管理
- 分析任务触发和监控
- 报告查询和管理
- 预设模板管理
- 统计信息获取
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field
from datetime import datetime

from app.models import get_db
from app.services.ai_analysis_service import ai_analysis_service, AnalysisResult

router = APIRouter()


# ========== 数据模型（Pydantic）==========

class CreateAnalysisConfigRequest(BaseModel):
    """创建分析配置请求体"""
    name: str = Field(..., min_length=1, max_length=256, description="配置名称")
    description: Optional[str] = Field(None, max_length=2000, description="配置描述")
    prompt_template: str = Field(..., min_length=10, description="提示词模板")
    model_name: str = Field("gpt-4", description="模型名称")
    temperature: float = Field(0.7, ge=0.0, le=1.0, description="温度参数 (0-1)")
    max_tokens: int = Field(4096, ge=100, le=32000, description="最大token数")
    trigger_type: str = Field("manual", description="触发类型: manual/scheduled/event")
    schedule_cron: Optional[str] = Field(None, description="定时任务cron表达式")
    is_active: bool = Field(True, description="是否启用")


class UpdateAnalysisConfigRequest(BaseModel):
    """更新分析配置请求体"""
    name: Optional[str] = Field(None, min_length=1, max_length=256)
    description: Optional[str] = Field(None, max_length=2000)
    prompt_template: Optional[str] = Field(None, min_length=10)
    model_name: Optional[str] = None
    temperature: Optional[float] = Field(None, ge=0.0, le=1.0)
    max_tokens: Optional[int] = Field(None, ge=100, le=32000)
    trigger_type: Optional[str] = None
    schedule_cron: Optional[str] = None
    is_active: Optional[bool] = None


class TriggerAnalysisRequest(BaseModel):
    """触发分析请求体"""
    config_id: int = Field(..., description="配置ID")
    params: Optional[Dict[str, Any]] = Field(None, description="输入参数")


class UseTemplateRequest(BaseModel):
    """使用模板请求体"""
    template_id: int = Field(..., description="模板ID")
    custom_name: Optional[str] = Field(None, description="自定义配置名称")
    custom_params: Optional[Dict[str, Any]] = Field(None, description="自定义参数")


# ========== 配置管理接口 ==========

@router.post("/ai-analysis/configs")
async def create_analysis_config(
    request: CreateAnalysisConfigRequest,
    db=Depends(get_db),
):
    """创建AI分析配置

    创建一个新的AI分析配置，包含提示词模板、模型参数等设置。
    """
    try:
        config = ai_analysis_service.create_analysis_config(
            db=db,
            name=request.name,
            prompt_template=request.prompt_template,
            description=request.description,
            model_name=request.model_name,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            trigger_type=request.trigger_type,
            schedule_cron=request.schedule_cron,
            is_active=request.is_active,
        )

        return {
            "success": True,
            "data": _config_to_dict(config),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建配置失败: {str(e)}")


@router.get("/ai-analysis/configs")
async def list_analysis_configs(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    trigger_type: Optional[str] = Query(None, description="触发类型筛选"),
    is_active: Optional[bool] = Query(None, description="是否启用筛选"),
    db=Depends(get_db),
):
    """获取AI分析配置列表（分页）

    支持按触发类型、启用状态等条件筛选。
    """
    try:
        configs, total = ai_analysis_service.list_analysis_configs(
            db=db,
            page=page,
            page_size=page_size,
            trigger_type=trigger_type,
            is_active=is_active,
        )

        return {
            "success": True,
            "data": {
                "items": [_config_to_dict(c) for c in configs],
                "total": total,
                "page": page,
                "page_size": page_size,
            },
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取配置列表失败: {str(e)}")


@router.get("/ai-analysis/configs/{config_id}")
async def get_analysis_config(
    config_id: int,
    db=Depends(get_db),
):
    """获取单个AI分析配置详情"""
    try:
        config = ai_analysis_service.get_analysis_config(db, config_id)
        if not config:
            raise HTTPException(status_code=404, detail=f"配置不存在: {config_id}")

        return {
            "success": True,
            "data": _config_to_dict(config),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/ai-analysis/configs/{config_id}")
async def update_analysis_config(
    config_id: int,
    request: UpdateAnalysisConfigRequest,
    db=Depends(get_db),
):
    """更新AI分析配置

    支持部分字段更新，只传递需要修改的字段即可。
    """
    try:
        # 过滤掉None值，只更新提供的字段
        update_data = {k: v for k, v in request.dict().items() if v is not None}

        if not update_data:
            raise HTTPException(status_code=400, detail="没有提供要更新的字段")

        config = ai_analysis_service.update_analysis_config(db, config_id, **update_data)

        if not config:
            raise HTTPException(status_code=404, detail=f"配置不存在: {config_id}")

        return {
            "success": True,
            "data": _config_to_dict(config),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新配置失败: {str(e)}")


@router.delete("/ai-analysis/configs/{config_id}")
async def delete_analysis_config(
    config_id: int,
    db=Depends(get_db),
):
    """删除AI分析配置

    同时会级联删除该配置下的所有报告记录。
    """
    try:
        success = ai_analysis_service.delete_analysis_config(db, config_id)

        if not success:
            raise HTTPException(status_code=404, detail=f"配置不存在: {config_id}")

        return {
            "success": True,
            "message": f"已删除配置 {config_id}",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除配置失败: {str(e)}")


# ========== 分析任务接口 ==========

@router.post("/ai-analysis/trigger")
async def trigger_analysis(
    request: TriggerAnalysisRequest,
    db=Depends(get_db),
):
    """手动触发AI分析任务

    异步执行分析任务，立即返回report_id供后续轮询状态。
    """
    try:
        result: AnalysisResult = ai_analysis_service.trigger_analysis(
            db=db,
            config_id=request.config_id,
            params=request.params,
        )

        if not result.success:
            raise HTTPException(status_code=400, detail=result.error or "触发失败")

        return {
            "success": True,
            "data": {
                "report_id": result.report_id,
                "message": "分析任务已在后台启动",
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"触发分析失败: {str(e)}")


# ========== 报告管理接口 ==========

@router.get("/ai-analysis/reports")
async def list_analysis_reports(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    config_id: Optional[int] = Query(None, description="配置ID筛选"),
    status: Optional[str] = Query(None, description="状态筛选: pending/running/completed/failed"),
    start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM-DD)"),
    db=Depends(get_db),
):
    """获取分析报告列表（分页）

    支持多维度筛选：配置ID、状态、日期范围等。
    """
    try:
        reports, total = ai_analysis_service.list_analysis_reports(
            db=db,
            page=page,
            page_size=page_size,
            config_id=config_id,
            status=status,
            start_date=start_date,
            end_date=end_date,
        )

        return {
            "success": True,
            "data": {
                "items": [_report_to_dict(r) for r in reports],
                "total": total,
                "page": page,
                "page_size": page_size,
            },
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取报告列表失败: {str(e)}")


@router.get("/ai-analysis/reports/{report_id}")
async def get_analysis_report(
    report_id: int,
    db=Depends(get_db),
):
    """获取单个分析报告详情

    包含完整的报告内容（Markdown格式）、统计信息等。
    """
    try:
        report = ai_analysis_service.get_analysis_report(db, report_id)
        if not report:
            raise HTTPException(status_code=404, detail=f"报告不存在: {report_id}")

        return {
            "success": True,
            "data": _report_to_dict(report, include_content=True),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/ai-analysis/reports/{report_id}")
async def delete_analysis_report(
    report_id: int,
    db=Depends(get_db),
):
    """删除分析报告"""
    try:
        success = ai_analysis_service.delete_analysis_report(db, report_id)

        if not success:
            raise HTTPException(status_code=404, detail=f"报告不存在: {report_id}")

        return {
            "success": True,
            "message": f"已删除报告 {report_id}",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除报告失败: {str(e)}")


# ========== 模板管理接口 ==========

@router.get("/ai-analysis/templates")
async def get_system_templates(
    category: Optional[str] = Query(None, description="分类筛选"),
    only_system: bool = Query(True, description="是否只返回系统预设"),
    db=Depends(get_db),
):
    """获取预设模板列表

    返回系统预设的AI分析模板，可用于快速创建分析配置。
    """
    try:
        templates = ai_analysis_service.get_system_templates(
            db=db,
            category=category,
            only_system=only_system,
        )

        return {
            "success": True,
            "data": {
                "items": [_template_to_dict(t) for t in templates],
                "total": len(templates),
            },
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取模板列表失败: {str(e)}")


@router.post("/ai-analysis/templates/use")
async def use_template(
    request: UseTemplateRequest,
    db=Depends(get_db),
):
    """使用模板创建分析配置

    基于预设模板快速创建新的分析配置，可自定义部分参数。
    """
    try:
        config, error = ai_analysis_service.use_template(
            db=db,
            template_id=request.template_id,
            custom_name=request.custom_name,
            custom_params=request.custom_params,
        )

        if not config:
            raise HTTPException(status_code=400, detail=error or "使用模板失败")

        return {
            "success": True,
            "data": _config_to_dict(config),
            "message": f"已基于模板创建配置",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"使用模板失败: {str(e)}")


# ========== 统计接口 ==========

@router.get("/ai-analysis/stats")
async def get_analysis_stats(
    db=Depends(get_db),
):
    """获取AI分析统计信息

    返回报告总数、成功率、平均耗时等统计数据。
    """
    try:
        stats = ai_analysis_service.get_analysis_stats(db)

        return {
            "success": True,
            "data": stats,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")


# ========== 辅助函数 ==========

def _config_to_dict(config) -> Dict[str, Any]:
    """将配置对象转换为字典"""
    return {
        "id": config.id,
        "name": config.name,
        "description": config.description,
        "prompt_template": config.prompt_template,
        "model_name": config.model_name,
        "temperature": config.temperature,
        "max_tokens": config.max_tokens,
        "trigger_type": config.trigger_type,
        "schedule_cron": config.schedule_cron,
        "is_active": config.is_active,
        "created_at": config.created_at.isoformat() if config.created_at else None,
        "updated_at": config.updated_at.isoformat() if config.updated_at else None,
        "reports_count": config.reports.count() if hasattr(config, 'reports') else 0,
    }


def _report_to_dict(report, include_content: bool = False) -> Dict[str, Any]:
    """将报告对象转换为字典"""
    data = {
        "id": report.id,
        "config_id": report.config_id,
        "title": report.title,
        "summary": report.summary,
        "status": report.status,
        "input_params": report.input_params,
        "result_data": report.result_data,
        "error_message": report.error_message,
        "started_at": report.started_at.isoformat() if report.started_at else None,
        "completed_at": report.completed_at.isoformat() if report.completed_at else None,
        "total_items": report.total_items,
        "relevant_count": report.relevant_count,
        "created_at": report.created_at.isoformat() if report.created_at else None,
        "duration_seconds": None,
        "config_name": None,
    }

    # 计算耗时
    if report.started_at and report.completed_at:
        delta = report.completed_at - report.started_at
        data["duration_seconds"] = round(delta.total_seconds(), 2)

    # 获取配置名称
    if report.config:
        data["config_name"] = report.config.name

    # 根据参数决定是否包含完整内容
    if include_content:
        data["content"] = report.content

    return data


def _template_to_dict(template) -> Dict[str, Any]:
    """将模板对象转换为字典"""
    return {
        "id": template.id,
        "name": template.name,
        "category": template.category,
        "description": template.description,
        "prompt_template": template.prompt_template,
        "default_params": template.default_params,
        "is_system": template.is_system,
        "usage_count": template.usage_count,
        "sort_order": template.sort_order,
        "created_at": template.created_at.isoformat() if template.created_at else None,
    }
